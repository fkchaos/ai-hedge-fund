"""Core debate engine — Phase 1/2/3 focused debate mechanism with memory.

Phase 1 (Vote):     All agents快速投票 → 统计分歧
Phase 2 (Challenge): 只让有分歧的代表深入辩论 → 聚焦核心争议
Phase 3 (Final Vote): 所有人看到辩论结果后最终表态
Synthesis:           主持人综合出结论

Features:
- Per-agent timeout with graceful degradation
- Intermediate checkpoints saved after each phase
- History memory: load past debates for agent context
- Performance tracking: track SPY change after each debate
- Supports 4-7+ agents without timeout issues
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from openai import APITimeoutError, APIConnectionError

from .agents import (
    Agent,
    ALL_AGENTS,
    VOTE_PROMPT_TEMPLATE,
    CHALLENGE_PROMPT_TEMPLATE,
    FINAL_VOTE_PROMPT_TEMPLATE,
    SYNTHESIS_PROMPT,
)
from .llm import MiMoLLM
from .history import DebateHistory, DebateRecord, record_from_debate_result

logger = logging.getLogger(__name__)


@dataclass
class DebateRound:
    """A single round of debate from one agent."""
    agent_name: str
    role: str
    signal: str  # bullish / bearish / neutral
    confidence: int
    reasoning: str
    raw_response: str = ""
    phase: str = ""  # "vote", "challenge", "final_vote", "synthesis"


@dataclass
class AgentStatus:
    """Track per-agent health across phases."""
    name: str
    successes: int = 0
    failures: int = 0
    last_error: str = ""
    is_disabled: bool = False


@dataclass
class DebateResult:
    """Complete debate output."""
    topic: str
    rounds: List[DebateRound] = field(default_factory=list)
    consensus: Optional[dict] = None
    market_data: str = ""
    # Diagnostics
    agent_statuses: dict = field(default_factory=dict)
    total_llm_calls: int = 0
    total_time: float = 0.0
    skipped_agents: List[str] = field(default_factory=list)
    phase_times: dict = field(default_factory=dict)  # phase -> seconds
    debate_record_id: str = ""  # 保存到历史的记录ID


class MarketDebater:
    """Orchestrates focused multi-phase debates between investment personas.

    Mechanism:
    Phase 1 — Vote:     All agents快速投票，统计bullish/bearish/neutral分布
    Phase 2 — Challenge: 找出分歧最大的代表深入辩论（最多4人参与）
    Phase 3 — Final Vote: 所有人看到辩论结果后重新表态（可改票）
    Synthesis:           主持人综合出最终结论
    """

    def __init__(
        self,
        agents: List[Agent] | None = None,
        llm: MiMoLLM | None = None,
        rounds: int = 2,
        call_timeout: float = 30.0,
        checkpoint_dir: str | Path | None = None,
        history_dir: str | Path | None = None,
        memory_rounds: int = 3,
    ):
        self.agents = agents or ALL_AGENTS
        self.llm = llm or MiMoLLM(timeout=call_timeout)
        self.rounds = rounds
        self.call_timeout = call_timeout
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self._statuses: dict[str, AgentStatus] = {
            a.name: AgentStatus(name=a.name) for a in self.agents
        }
        # 历史记忆系统
        self.history = DebateHistory(history_dir)
        self.memory_rounds = memory_rounds  # 加载最近N次辩论作为记忆

    # ── LLM call with timeout + graceful degradation ──────────────────

    def _call_llm_safe(self, agent: Agent, system: str, user: str) -> str:
        """Call LLM with timeout + error handling. Returns "" on failure."""
        status = self._statuses[agent.name]
        if status.is_disabled:
            logger.warning(f"  {agent.name}: DISABLED, skipping")
            return ""

        for attempt in range(2):  # 1 retry
            try:
                raw = self.llm.complete(system, user)
                if raw and raw.strip():
                    status.successes += 1
                    return raw
                logger.warning(f"  {agent.name}: empty response (attempt {attempt+1})")
            except (APITimeoutError, APIConnectionError) as e:
                logger.warning(f"  {agent.name}: {type(e).__name__} (attempt {attempt+1})")
                status.failures += 1
                status.last_error = str(e)
                if status.failures >= 2:
                    status.is_disabled = True
                    logger.warning(f"  {agent.name}: DISABLED after {status.failures} failures")
            except Exception as e:
                logger.error(f"  {agent.name}: unexpected error: {e}")
                status.failures += 1
                status.last_error = str(e)
                if status.failures >= 2:
                    status.is_disabled = True

        return ""

    # ── JSON parsing (robust) ─────────────────────────────────────────

    def _parse_response(self, text: str) -> dict:
        """Extract JSON from LLM response, with robust fallback."""
        import re
        text = text.strip()
        if not text:
            return {"signal": "neutral", "confidence": 50, "reasoning": "(empty response)"}

        # 1. Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Markdown fence
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            try:
                return json.loads(fence.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Find first { ... }
        start = text.find("{")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break

        # 4. Truncated JSON
        if start != -1:
            last_brace = text.rfind("}")
            if last_brace > start:
                try:
                    return json.loads(text[start : last_brace + 1])
                except json.JSONDecodeError:
                    pass

            signal_m = re.search(r'"signal"\s*:\s*"(bullish|bearish|neutral)"', text)
            conf_m = re.search(r'"confidence"\s*:\s*(\d+)', text)
            reason_m = re.search(r'"reasoning"\s*:\s*"(.+?)"', text, re.DOTALL)
            if signal_m:
                return {
                    "signal": signal_m.group(1),
                    "confidence": int(conf_m.group(1)) if conf_m else 50,
                    "reasoning": reason_m.group(1)[:500] if reason_m else text[start:start+500],
                }

        # 5. Sentiment fallback
        text_lower = text.lower()
        if "bullish" in text_lower or "buy" in text_lower:
            signal = "bullish"
        elif "bearish" in text_lower or "sell" in text_lower:
            signal = "bearish"
        else:
            signal = "neutral"
        return {"signal": signal, "confidence": 50, "reasoning": text[:500]}

    # ── Formatting helpers ────────────────────────────────────────────

    def _format_views(self, rounds: List[DebateRound]) -> str:
        """Format rounds for challenge/final prompts."""
        lines = []
        for r in rounds:
            lines.append(f"【{r.agent_name}】{r.role}")
            lines.append(f"  信号: {r.signal.upper()} | 置信度: {r.confidence}%")
            lines.append(f"  {r.reasoning}")
            lines.append("")
        return "\n".join(lines)

    def _classify_votes(self, rounds: List[DebateRound]) -> dict[str, List[DebateRound]]:
        """Classify votes into bullish/bearish/neutral groups."""
        groups = {"bullish": [], "bearish": [], "neutral": []}
        for r in rounds:
            sig = r.signal.lower()
            if sig in groups:
                groups[sig].append(r)
            else:
                groups["neutral"].append(r)
        return groups

    def _select_debaters(self, groups: dict[str, List[DebateRound]]) -> List[str]:
        """Select agents for Phase 2 challenge debate.

        Strategy:
        - If unanimous (all same signal): no debate needed, skip Phase 2
        - If one dissenter: dissenter + 1 strongest majority defender
        - If 2-way split (e.g. 4:3): top confidence from each camp
        - If 3-way split: top from each group
        """
        # Filter out empty groups
        active_groups = {k: v for k, v in groups.items() if v}

        if len(active_groups) <= 1:
            return []  # Unanimous, no debate needed

        # Sort groups by size (smallest first — the dissenters)
        sorted_groups = sorted(active_groups.items(), key=lambda x: len(x[1]))

        debaters = []
        # Minority representatives (dissenters)
        for signal, voters in sorted_groups[:2]:  # up to 2 minority groups
            # Pick highest confidence voter
            best = max(voters, key=lambda r: r.confidence)
            if best.agent_name not in debaters:
                debaters.append(best.agent_name)

        # Majority defenders
        majority_signal = sorted_groups[-1][0]
        majority_voters = sorted_groups[-1][1]
        # Pick highest confidence from majority as defender
        defender = max(majority_voters, key=lambda r: r.confidence)
        if defender.agent_name not in debaters:
            debaters.append(defender.agent_name)

        # Cap at 4 debaters to keep it manageable
        return debaters[:4]

    # ── Checkpoint ────────────────────────────────────────────────────

    def _save_checkpoint(self, result: DebateResult, stage: str):
        """Save intermediate debate state to disk."""
        if not self.checkpoint_dir:
            return
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        path = self.checkpoint_dir / f"debate_{ts}_{stage}.json"
        data = {
            "topic": result.topic,
            "stage": stage,
            "rounds": [
                {"agent": r.agent_name, "signal": r.signal,
                 "confidence": r.confidence, "reasoning": r.reasoning,
                 "phase": r.phase}
                for r in result.rounds
            ],
            "agent_statuses": {
                name: {"successes": s.successes, "failures": s.failures,
                       "disabled": s.is_disabled, "last_error": s.last_error}
                for name, s in self._statuses.items()
            },
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"  Checkpoint saved: {path.name}")

    # ══════════════════════════════════════════════════════════════════
    # Main debate flow
    # ══════════════════════════════════════════════════════════════════

    def run(self, topic: str, market_data: str, spy_price: float = 0.0,
            pe: float = 0.0, vix: float = 0.0, pos_52w: float = 0.0,
            tnx_10y: float = 0.0, valuation_signal: str = "") -> DebateResult:
        """Run a focused multi-phase debate with memory.

        Phase 1 — Vote:        All agents快速投票 (N calls)
        Phase 2 — Challenge:   代表深入辩论 (最多4人 × challenge_rounds calls)
        Phase 3 — Final Vote:  所有人最终表态 (N calls)
        Synthesis:             主持人综合 (1 call)

        Args:
            topic: 辩论主题
            market_data: 市场数据文本
            spy_price: 当前SPY价格（用于表现追踪）
            pe/vix/pos_52w/tnx_10y: 估值指标（用于历史记录）
            valuation_signal: 估值信号（用于历史记录）
        """
        start_time = time.time()
        result = DebateResult(topic=topic, market_data=market_data)

        # ── 加载历史记忆 ──────────────────────────────────────────
        if spy_price > 0:
            self.history.update_performance(spy_price)  # 更新上一次辩论的后续表现

        history_context = self.history.format_memory_context(n=self.memory_rounds)
        if history_context:
            logger.info(f"  Loaded {self.memory_rounds} debate records as memory")

        # ── Phase 1: Vote ─────────────────────────────────────────────
        phase_start = time.time()
        logger.info(f"=== PHASE 1: VOTE ({len(self.agents)} agents) ===")

        vote_rounds: List[DebateRound] = []
        for agent in self.agents:
            prompt = VOTE_PROMPT_TEMPLATE.format(
                market_data=market_data,
                history_context=history_context,
                name=agent.name,
            )
            raw = self._call_llm_safe(agent, agent.system_prompt, prompt)
            result.total_llm_calls += 1
            parsed = self._parse_response(raw)

            round_obj = DebateRound(
                agent_name=agent.name,
                role=agent.role,
                signal=parsed.get("signal", "neutral"),
                confidence=parsed.get("confidence", 50),
                reasoning=parsed.get("reasoning", ""),
                raw_response=raw,
                phase="vote",
            )
            vote_rounds.append(round_obj)
            result.rounds.append(round_obj)
            logger.info(f"  {agent.name}: {round_obj.signal} ({round_obj.confidence}%)")

        # Classify votes
        groups = self._classify_votes(vote_rounds)
        vote_summary = {k: len(v) for k, v in groups.items()}
        logger.info(f"  Vote distribution: {vote_summary}")

        self._save_checkpoint(result, "phase1_vote")
        result.phase_times["vote"] = time.time() - phase_start

        # ── Phase 2: Focused Challenge ────────────────────────────────
        debaters = self._select_debaters(groups)
        challenge_rounds = self.rounds  # reuse rounds parameter

        if debaters:
            phase_start = time.time()
            logger.info(f"=== PHASE 2: CHALLENGE ({len(debaters)} debaters, {challenge_rounds} rounds) ===")
            logger.info(f"  Debaters: {', '.join(debaters)}")

            challenge_results: List[DebateRound] = []
            for round_num in range(1, challenge_rounds + 1):
                logger.info(f"  --- Challenge Round {round_num} ---")
                for agent_name in debaters:
                    agent = next(a for a in self.agents if a.name == agent_name)
                    # Build context from all vote rounds + previous challenge rounds
                    context_rounds = vote_rounds + challenge_results
                    context_rounds_filtered = [r for r in context_rounds if r.agent_name != agent.name]
                    previous_text = self._format_views(context_rounds_filtered)

                    prompt = CHALLENGE_PROMPT_TEMPLATE.format(
                        previous_views=previous_text,
                        market_data=market_data,
                        name=agent.name,
                    )
                    raw = self._call_llm_safe(agent, agent.system_prompt, prompt)
                    result.total_llm_calls += 1
                    parsed = self._parse_response(raw)

                    round_obj = DebateRound(
                        agent_name=agent.name,
                        role=agent.role,
                        signal=parsed.get("signal", "neutral"),
                        confidence=parsed.get("confidence", 50),
                        reasoning=parsed.get("reasoning", ""),
                        raw_response=raw,
                        phase="challenge",
                    )
                    challenge_results.append(round_obj)
                    result.rounds.append(round_obj)
                    logger.info(f"    {agent.name}: {round_obj.signal} ({round_obj.confidence}%)")

            self._save_checkpoint(result, "phase2_challenge")
            result.phase_times["challenge"] = time.time() - phase_start
        else:
            logger.info("=== PHASE 2: SKIPPED (unanimous vote) ===")
            result.phase_times["challenge"] = 0.0

        # ── Phase 3: Final Vote ───────────────────────────────────────
        phase_start = time.time()
        logger.info(f"=== PHASE 3: FINAL VOTE ({len(self.agents)} agents) ===")

        # Build debate summary for final vote prompt
        if debaters:
            debate_summary = self._format_views(vote_rounds + challenge_results)
        else:
            debate_summary = self._format_views(vote_rounds)

        final_rounds: List[DebateRound] = []
        for agent in self.agents:
            prompt = FINAL_VOTE_PROMPT_TEMPLATE.format(
                market_data=market_data,
                debate_summary=debate_summary,
                name=agent.name,
            )
            raw = self._call_llm_safe(agent, agent.system_prompt, prompt)
            result.total_llm_calls += 1
            parsed = self._parse_response(raw)

            round_obj = DebateRound(
                agent_name=agent.name,
                role=agent.role,
                signal=parsed.get("signal", "neutral"),
                confidence=parsed.get("confidence", 50),
                reasoning=parsed.get("reasoning", ""),
                raw_response=raw,
                phase="final_vote",
            )
            final_rounds.append(round_obj)
            result.rounds.append(round_obj)
            logger.info(f"  {agent.name}: {round_obj.signal} ({round_obj.confidence}%)")

        self._save_checkpoint(result, "phase3_final_vote")
        result.phase_times["final_vote"] = time.time() - phase_start

        # ── Synthesis ─────────────────────────────────────────────────
        phase_start = time.time()
        logger.info("=== SYNTHESIS ===")

        # Use all rounds for synthesis
        full_debate = self._format_views(result.rounds)
        raw = self._call_llm_safe(
            self.agents[0],
            "You are a debate moderator synthesizing investor views.",
            SYNTHESIS_PROMPT.format(full_debate=full_debate),
        )
        result.total_llm_calls += 1
        result.consensus = self._parse_response(raw)
        logger.info(f"  Consensus: {result.consensus.get('consensus', 'N/A')}")

        result.phase_times["synthesis"] = time.time() - phase_start

        # ── Finalize ──────────────────────────────────────────────────
        result.total_time = time.time() - start_time
        result.agent_statuses = {name: s for name, s in self._statuses.items()}
        result.skipped_agents = [
            name for name, s in self._statuses.items() if s.is_disabled
        ]

        # Log diagnostics
        active = sum(1 for s in self._statuses.values() if not s.is_disabled)
        logger.info(f"  Completed in {result.total_time:.1f}s, "
                     f"{result.total_llm_calls} LLM calls, "
                     f"{active}/{len(self.agents)} agents active")
        logger.info(f"  Phase times: {result.phase_times}")
        if result.skipped_agents:
            logger.warning(f"  Skipped agents: {', '.join(result.skipped_agents)}")

        self._save_checkpoint(result, "final")

        # ── 保存辩论记录到历史 ──────────────────────────────────────
        record = record_from_debate_result(
            result, topic=topic, market_data=market_data,
            spy_price=spy_price, pe=pe, vix=vix,
            pos_52w=pos_52w, tnx_10y=tnx_10y,
            valuation_signal=valuation_signal,
        )
        record_path = self.history.save(record)
        result.debate_record_id = record.id
        logger.info(f"  Debate record saved: {record_path.name} (id={record.id})")

        return result
