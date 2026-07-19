"""Core debate engine — orchestrates multi-round investor debates."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .agents import (
    Agent, BUFFETT, LYNCH, MUNGER, BURRY, ALL_AGENTS,
    INITIAL_PROMPT_TEMPLATE, CHALLENGE_PROMPT_TEMPLATE, SYNTHESIS_PROMPT,
)
from .llm import MiMoLLM

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


@dataclass
class DebateResult:
    """Complete debate output."""
    topic: str
    rounds: List[DebateRound] = field(default_factory=list)
    consensus: Optional[dict] = None
    market_data: str = ""


class MarketDebater:
    """Orchestrates multi-round debates between investment personas."""

    def __init__(
        self,
        agents: List[Agent] | None = None,
        llm: MiMoLLM | None = None,
        rounds: int = 2,
    ):
        self.agents = agents or ALL_AGENTS
        self.llm = llm or MiMoLLM()
        self.rounds = rounds

    def _call_llm(self, system: str, user: str) -> str:
        """Call LLM with error handling."""
        try:
            return self.llm.complete(system, user)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def _parse_response(self, text: str) -> dict:
        """Extract JSON from LLM response, with robust fallback for truncated JSON."""
        import re
        text = text.strip()
        if not text:
            return {"signal": "neutral", "confidence": 50, "reasoning": "(empty response)"}

        # 1. Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Try extracting from markdown fence
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            try:
                return json.loads(fence.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Find first { ... } and try to parse
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

        # 4. Truncated JSON: find last complete key-value pair
        if start != -1:
            # Try progressively shorter substrings
            last_brace = text.rfind("}")
            if last_brace > start:
                try:
                    return json.loads(text[start : last_brace + 1])
                except json.JSONDecodeError:
                    pass

            # Extract signal/confidence/reasoning with regex as last resort
            signal_m = re.search(r'"signal"\s*:\s*"(bullish|bearish|neutral)"', text)
            conf_m = re.search(r'"confidence"\s*:\s*(\d+)', text)
            reason_m = re.search(r'"reasoning"\s*:\s*"(.+?)"', text, re.DOTALL)
            if signal_m:
                return {
                    "signal": signal_m.group(1),
                    "confidence": int(conf_m.group(1)) if conf_m else 50,
                    "reasoning": reason_m.group(1)[:500] if reason_m else text[start:start+500],
                }

        # 5. Complete fallback: interpret sentiment from text
        text_lower = text.lower()
        if "bullish" in text_lower or "buy" in text_lower:
            signal = "bullish"
        elif "bearish" in text_lower or "sell" in text_lower:
            signal = "bearish"
        else:
            signal = "neutral"
        return {"signal": signal, "confidence": 50, "reasoning": text[:500]}

    def _format_views(self, rounds: List[DebateRound]) -> str:
        """Format previous rounds for challenge prompt."""
        lines = []
        for r in rounds:
            lines.append(f"【{r.agent_name}】{r.role}")
            lines.append(f"  信号: {r.signal.upper()} | 置信度: {r.confidence}%")
            lines.append(f"  {r.reasoning}")
            lines.append("")
        return "\n".join(lines)

    def _call_llm_with_retry(self, system: str, user: str, max_retries: int = 2) -> str:
        """Call LLM with retry on empty/failure responses."""
        for attempt in range(max_retries + 1):
            raw = self._call_llm(system, user)
            if raw and raw.strip():
                return raw
            logger.warning(f"Empty LLM response (attempt {attempt + 1}), retrying...")
        return ""

    def run(self, topic: str, market_data: str) -> DebateResult:
        """Run a full debate.

        Args:
            topic: The question being debated (e.g., "Should I invest in S&P500 now?")
            market_data: Market data string to provide context

        Returns:
            DebateResult with all rounds and consensus
        """
        result = DebateResult(topic=topic, market_data=market_data)

        # ── Round 1: Initial views ────────────────────────────────────
        logger.info("=== ROUND 1: Initial Views ===")
        for agent in self.agents:
            prompt = INITIAL_PROMPT_TEMPLATE.format(
                market_data=market_data,
                name=agent.name,
            )
            raw = self._call_llm_with_retry(agent.system_prompt, prompt)
            parsed = self._parse_response(raw)

            round_obj = DebateRound(
                agent_name=agent.name,
                role=agent.role,
                signal=parsed.get("signal", "neutral"),
                confidence=parsed.get("confidence", 50),
                reasoning=parsed.get("reasoning", ""),
                raw_response=raw,
            )
            result.rounds.append(round_obj)
            logger.info(f"  {agent.name}: {round_obj.signal} ({round_obj.confidence}%)")

        # ── Rounds 2+: Challenges ─────────────────────────────────────
        for round_num in range(2, self.rounds + 1):
            logger.info(f"=== ROUND {round_num}: Challenges ===")
            for agent in self.agents:
                # Build context from all previous rounds
                previous = [r for r in result.rounds if r.agent_name != agent.name]
                previous_text = self._format_views(previous)

                prompt = CHALLENGE_PROMPT_TEMPLATE.format(
                    previous_views=previous_text,
                    market_data=market_data,
                )
                raw = self._call_llm_with_retry(agent.system_prompt, prompt)
                parsed = self._parse_response(raw)

                round_obj = DebateRound(
                    agent_name=agent.name,
                    role=agent.role,
                    signal=parsed.get("signal", "neutral"),
                    confidence=parsed.get("confidence", 50),
                    reasoning=parsed.get("reasoning", ""),
                    raw_response=raw,
                )
                result.rounds.append(round_obj)
                logger.info(f"  {agent.name}: {round_obj.signal} ({round_obj.confidence}%)")

        # ── Synthesis ─────────────────────────────────────────────────
        logger.info("=== SYNTHESIS ===")
        full_debate = self._format_views(result.rounds)
        raw = self._call_llm_with_retry(
            "You are a debate moderator synthesizing investor views.",
            SYNTHESIS_PROMPT.format(full_debate=full_debate),
        )
        result.consensus = self._parse_response(raw)
        logger.info(f"  Consensus: {result.consensus.get('consensus', 'N/A')}")

        return result
