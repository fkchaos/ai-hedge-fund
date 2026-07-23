"""辩论历史记录与大佬记忆系统

功能：
1. 辩论存档：每次辩论自动保存完整记录到JSON
2. 历史加载：读取最近N次辩论，供大佬参考
3. 记忆注入：Phase1投票前把历史上下文注入prompt
4. 表现追踪：辩论后记录SPY涨跌，评估各大佬预测准确率
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 默认存储路径
DEFAULT_HISTORY_DIR = Path(__file__).parent.parent.parent / "data" / "debate_history"


@dataclass
class DebateRecord:
    """单次辩论完整记录"""
    id: str = ""  # UUID
    timestamp: str = ""  # ISO format
    topic: str = ""
    # 市场快照
    spy_price: float = 0.0
    pe: float = 0.0
    vix: float = 0.0
    pos_52w: float = 0.0
    tnx_10y: float = 0.0
    valuation_signal: str = ""
    # Phase 1 投票
    votes: list[dict] = field(default_factory=list)  # [{agent, signal, confidence, reasoning}]
    vote_distribution: dict = field(default_factory=dict)  # {bullish: N, bearish: N, neutral: N}
    # Phase 2 挑战
    challenge_participants: list[str] = field(default_factory=list)
    challenges: list[dict] = field(default_factory=list)  # [{agent, signal, confidence, reasoning}]
    # Phase 3 最终投票
    final_votes: list[dict] = field(default_factory=list)
    # 综合结论
    consensus: str = ""
    confidence_avg: int = 0
    agreement_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    final_signal: str = ""
    final_advice: str = ""
    # 后续表现（辩论后填充）
    spy_price_at_debate: float = 0.0  # 辩论时SPY价格
    spy_price_after: float = 0.0  # N天后SPY价格（下次辩论时自动填充）
    spy_change_pct: float = 0.0  # 涨跌幅
    # 各大佬准确率
    agent_accuracy: dict = field(default_factory=dict)  # {name: {correct: N, total: N}}
    # 运行信息
    total_time: float = 0.0
    total_llm_calls: int = 0


class DebateHistory:
    """辩论历史管理器

    职责：
    1. 保存辩论记录到JSON文件
    2. 加载最近N次辩论记录
    3. 格式化历史上下文供大佬参考
    4. 追踪后续表现并更新准确率
    """

    def __init__(self, history_dir: str | Path | None = None):
        self.history_dir = Path(history_dir) if history_dir else DEFAULT_HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)

    # ── 保存辩论记录 ──────────────────────────────────────────────

    def save(self, record: DebateRecord) -> Path:
        """保存辩论记录到JSON文件"""
        if not record.id:
            record.id = str(uuid.uuid4())[:8]
        if not record.timestamp:
            record.timestamp = datetime.now().isoformat()

        filename = f"{record.timestamp[:10]}_{record.id}.json"
        filepath = self.history_dir / filename

        data = asdict(record)
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"Debate record saved: {filepath.name}")
        return filepath

    # ── 加载历史记录 ──────────────────────────────────────────────

    def load_recent(self, n: int = 3) -> list[DebateRecord]:
        """加载最近N次辩论记录（按时间倒序）"""
        files = sorted(self.history_dir.glob("*.json"), reverse=True)[:n]
        records = []
        for f in files:
            try:
                data = json.loads(f.read_text())
                record = DebateRecord(**{k: v for k, v in data.items()
                                         if k in DebateRecord.__dataclass_fields__})
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to load {f.name}: {e}")
        return records

    def get_agent_stats(self) -> dict[str, dict]:
        """统计各大佬的历史准确率"""
        records = self.load_recent(20)  # 最近20次
        stats: dict[str, dict] = {}

        for rec in records:
            if rec.spy_change_pct == 0:
                continue  # 跳过没有后续数据的

            actual = "bullish" if rec.spy_change_pct > 0.5 else "bearish" if rec.spy_change_pct < -0.5 else "neutral"

            for vote in rec.final_votes:
                name = vote.get("agent", "")
                signal = vote.get("signal", "neutral")
                if name not in stats:
                    stats[name] = {"correct": 0, "total": 0, "bullish_correct": 0, "bearish_correct": 0}
                stats[name]["total"] += 1
                # 简化判断：看方向是否正确
                if signal == actual:
                    stats[name]["correct"] += 1
                    if signal == "bullish":
                        stats[name]["bullish_correct"] += 1
                    elif signal == "bearish":
                        stats[name]["bearish_correct"] += 1

        # 计算准确率
        for name, s in stats.items():
            s["accuracy"] = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0

        return stats

    # ── 后续表现追踪 ──────────────────────────────────────────────

    def update_performance(self, current_spy_price: float):
        """用当前SPY价格更新上一次辩论的后续表现

        每次新辩论开始时调用，自动填充上一次辩论的 spy_price_after
        """
        records = self.load_recent(1)
        if not records:
            return

        last = records[0]
        if last.spy_price_after > 0:
            return  # 已经更新过了

        if last.spy_price_at_debate > 0:
            last.spy_price_after = current_spy_price
            last.spy_change_pct = round(
                (current_spy_price - last.spy_price_at_debate) / last.spy_price_at_debate * 100, 2
            )
            # 更新准确率
            self._update_agent_accuracy(last)

            # 重新保存
            filepath = self.history_dir / f"{last.timestamp[:10]}_{last.id}.json"
            if filepath.exists():
                data = asdict(last)
                filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                logger.info(f"Updated performance for {last.id}: SPY {last.spy_change_pct:+.2f}%")

    def _update_agent_accuracy(self, record: DebateRecord):
        """根据后续表现更新各大佬的准确率"""
        if record.spy_change_pct == 0:
            return

        actual = "bullish" if record.spy_change_pct > 0.5 else "bearish" if record.spy_change_pct < -0.5 else "neutral"

        for vote in record.final_votes:
            name = vote.get("agent", "")
            signal = vote.get("signal", "neutral")
            if name not in record.agent_accuracy:
                record.agent_accuracy[name] = {"correct": 0, "total": 0}
            record.agent_accuracy[name]["total"] += 1
            if signal == actual:
                record.agent_accuracy[name]["correct"] += 1

    # ── 记忆上下文格式化 ──────────────────────────────────────────

    def format_memory_context(self, n: int = 3) -> str:
        """格式化最近N次辩论记录为大佬可读的上下文

        用于注入到Phase1投票prompt中
        """
        records = self.load_recent(n)
        if not records:
            return ""

        lines = ["═══ 历史辩论记录（供参考）═══\n"]

        for i, rec in enumerate(records, 1):
            lines.append(f"── 第{i}次辩论: {rec.timestamp[:16]} ──")
            lines.append(f"  市场: SPY=${rec.spy_price_at_debate:.2f} PE={rec.pe:.1f} VIX={rec.vix:.1f}")
            lines.append(f"  估值信号: {rec.valuation_signal}")

            # 投票分布
            dist = rec.vote_distribution
            if dist:
                lines.append(f"  投票: 看多{dist.get('bullish',0)} 看空{dist.get('bearish',0)} 中性{dist.get('neutral',0)}")

            # 最终结论
            lines.append(f"  结论: {rec.consensus} (置信度{rec.confidence_avg}%)")

            # 后续表现
            if rec.spy_change_pct != 0:
                emoji = "📈" if rec.spy_change_pct > 0 else "📉"
                lines.append(f"  后续: SPY {rec.spy_change_pct:+.2f}% {emoji}")

                # 各大佬准确率
                if rec.agent_accuracy:
                    for name, acc in rec.agent_accuracy.items():
                        correct = acc.get("correct", 0)
                        total = acc.get("total", 0)
                        if total > 0:
                            lines.append(f"    {name}: {'✅正确' if correct > 0 else '❌错误'} ({correct}/{total})")

            lines.append("")

        # 各大佬历史准确率汇总
        stats = self.get_agent_stats()
        if stats:
            lines.append("═══ 各大佬历史准确率 ═══")
            for name, s in sorted(stats.items(), key=lambda x: x[1]["accuracy"], reverse=True):
                lines.append(f"  {name}: {s['accuracy']}% ({s['correct']}/{s['total']})")
            lines.append("")

        return "\n".join(lines)


def record_from_debate_result(result, topic: str, market_data: str = "",
                               spy_price: float = 0.0, pe: float = 0.0,
                               vix: float = 0.0, pos_52w: float = 0.0,
                               tnx_10y: float = 0.0, valuation_signal: str = ""
                               ) -> DebateRecord:
    """从 DebateResult 构建 DebateRecord"""
    record = DebateRecord(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().isoformat(),
        topic=topic,
        spy_price_at_debate=spy_price,
        pe=pe,
        vix=vix,
        pos_52w=pos_52w,
        tnx_10y=tnx_10y,
        valuation_signal=valuation_signal,
        total_time=result.total_time,
        total_llm_calls=result.total_llm_calls,
    )

    # 按phase分类rounds
    for r in result.rounds:
        entry = {
            "agent": r.agent_name,
            "signal": r.signal,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
        }
        if r.phase == "vote":
            record.votes.append(entry)
        elif r.phase == "challenge":
            record.challenges.append(entry)
            if r.agent_name not in record.challenge_participants:
                record.challenge_participants.append(r.agent_name)
        elif r.phase == "final_vote":
            record.final_votes.append(entry)

    # 投票分布
    record.vote_distribution = {
        "bullish": sum(1 for v in record.votes if v["signal"] == "bullish"),
        "bearish": sum(1 for v in record.votes if v["signal"] == "bearish"),
        "neutral": sum(1 for v in record.votes if v["signal"] == "neutral"),
    }

    # 综合结论
    if result.consensus:
        record.consensus = result.consensus.get("consensus", "")
        record.confidence_avg = result.consensus.get("confidence_avg", 0)
        record.agreement_points = result.consensus.get("agreement_points", [])
        record.risks = result.consensus.get("risks", [])
        record.action_items = result.consensus.get("action_items", [])

    return record
