"""
S&P500 七大佬辩论出手时机判断器 — 标准接口

用法:
    # 基础用法
    from src.debate.sp500_timing import check_sp500_timing
    result = check_sp500_timing()
    print(result.summary)

    # 命令行
    python -m src.debate.sp500_timing
"""
from __future__ import annotations

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.debate.market_data import get_market_data
from src.debate.debater import MarketDebater
from src.debate.agents import ALL_AGENTS


# ── 估值区间定义 ──────────────────────────────────────────
VALUATION_BANDS = {
    "pe":       {"cheap": 18, "fair": 22, "expensive": 27},
    "vix_fear": {"cheap": 30, "fair": 25, "expensive": 15},  # 反向：越高越恐慌=越便宜
    "pos_52w":  {"cheap": 30, "fair": 50, "expensive": 80},
    "tnx":      {"cheap": 2.5, "fair": 3.5, "expensive": 4.5},
}


@dataclass
class TimingResult:
    """出手时机判断结果"""
    # 估值信号
    valuation_signal: str = ""  # "🟢" / "🟡" / "🔴"
    valuation_desc: str = ""    # "强烈买入" / "可以分批买" / "观望" / "不买"
    
    # 关键指标
    spy_price: float = 0.0
    pe: float = 0.0
    vix: float = 0.0
    pos_52w: float = 0.0  # 52周位置百分比
    tnx_10y: float = 0.0  # 10年期国债收益率
    
    # 辩论结论
    debate_enabled: bool = False
    debate_consensus: str = ""  # "bullish" / "bearish" / "neutral"
    debate_confidence: int = 0  # 平均置信度 0-100
    debate_agreement: list[str] = field(default_factory=list)  # 一致同意点
    debate_risks: list[str] = field(default_factory=list)      # 风险提示
    action_items: list[str] = field(default_factory=list)      # 行动建议
    avg_target_position: int = 0  # 七大佬平均目标仓位 0-100%
    
    # 综合判断
    final_signal: str = ""   # 最终信号
    final_advice: str = ""   # 最终建议
    summary: str = ""        # 可读的总结报告


def classify(val, bands):
    """根据区间判断信号。vix_fear为反向指标。"""
    if val is None:
        return "❓", "数据缺失"
    if bands == VALUATION_BANDS["vix_fear"]:
        # VIX反向：越高越便宜
        if val >= bands["cheap"]:
            return "🟢", "恐慌=买入机会"
        elif val >= bands["fair"]:
            return "🟡", "偏高=可关注"
        elif val >= bands["expensive"]:
            return "🟠", "中性"
        else:
            return "🔴", "贪婪=小心"
    else:
        if val <= bands["cheap"]:
            return "🟢", "便宜"
        elif val <= bands["fair"]:
            return "🟡", "合理"
        elif val <= bands["expensive"]:
            return "🟠", "偏贵"
        else:
            return "🔴", "极贵"


def get_overall_signal(pe, vix, pos, tnx):
    """综合判断信号。"""
    signals = []
    if pe is not None:
        signals.append("cheap" if pe <= 22 else "expensive" if pe >= 27 else "fair")
    if vix is not None:
        signals.append("cheap" if vix >= 25 else "expensive" if vix <= 15 else "fair")
    if pos is not None:
        signals.append("cheap" if pos <= 50 else "expensive" if pos >= 80 else "fair")
    if tnx is not None:
        signals.append("cheap" if tnx <= 3.5 else "expensive" if tnx >= 4.5 else "fair")

    if not signals:
        return "❓", "数据不足", 0

    cheap_count = signals.count("cheap")
    expensive_count = signals.count("expensive")

    if cheap_count >= 3:
        return "🟢", "强烈买入", cheap_count
    elif cheap_count >= 2:
        return "🟢", "可以分批买入", cheap_count
    elif expensive_count >= 3:
        return "🔴", "不建议买入", expensive_count
    elif expensive_count >= 2:
        return "🟠", "偏贵，观望", expensive_count
    else:
        return "🟡", "中性，等待更明确信号", 0


def get_debate_trigger(signal, cheap_count, expensive_count):
    """根据估值信号决定是否触发辩论及辩论强度。"""
    if signal == "🟢" and cheap_count >= 3:
        # 强烈买入 → 快速辩论确认
        return True, 2, "强烈买入信号，快速确认"
    elif signal == "🟢" and cheap_count >= 2:
        # 可以分批买 → 标准辩论
        return True, 2, "买入机会，标准辩论"
    elif signal == "🔴" and expensive_count >= 3:
        # 不建议买入 → 标准辩论确认风险
        return True, 2, "高风险信号，确认风险"
    elif signal == "🟠" and expensive_count >= 2:
        # 偏贵观望 → 轻量辩论
        return True, 1, "偏贵信号，轻量辩论"
    else:
        # 中性 → 不辩论
        return False, 0, "中性信号，无需辩论"


def format_summary(result: TimingResult) -> str:
    """生成可读的总结报告。"""
    lines = []
    
    # 标题
    lines.append("═" * 60)
    lines.append("  S&P500 出手时机判断报告")
    lines.append("═" * 60)
    lines.append(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    # 估值指标
    lines.append("📊 估值指标")
    lines.append("─" * 60)
    lines.append(f"  SPY价格: ${result.spy_price:.2f}")
    
    # 逐项指标
    items = [
        ("PE", result.pe, VALUATION_BANDS["pe"]),
        ("VIX", result.vix, VALUATION_BANDS["vix_fear"]),
        ("52周位置", result.pos_52w, VALUATION_BANDS["pos_52w"]),
        ("10Y国债", result.tnx_10y, VALUATION_BANDS["tnx"]),
    ]
    
    for name, val, bands in items:
        icon, label = classify(val, bands)
        val_str = f"{val}" if val is not None else "N/A"
        lines.append(f"  {icon} {name}: {val_str} → {label}")
    
    lines.append("")
    lines.append(f"  📈 综合信号: {result.valuation_signal} {result.valuation_desc}")
    
    # 辩论结论
    if result.debate_enabled:
        lines.append("")
        lines.append("═" * 60)
        lines.append("  七大佬辩论结论")
        lines.append("═" * 60)
        
        emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(result.debate_consensus, "⚪")
        lines.append(f"  共识: {emoji} {result.debate_consensus.upper()} | 平均置信度: {result.debate_confidence}%")

        # 目标仓位
        if result.avg_target_position > 0:
            pos = result.avg_target_position
            if pos >= 80:
                pos_emoji = "🟢 满仓区间"
            elif pos >= 60:
                pos_emoji = "🟢 偏多"
            elif pos >= 40:
                pos_emoji = "⚪ 中性"
            elif pos >= 20:
                pos_emoji = "🟠 偏空"
            else:
                pos_emoji = "🔴 轻仓区间"
            lines.append(f"  📊 七大佬平均目标仓位: {pos}% {pos_emoji}")
        
        if result.debate_agreement:
            lines.append("")
            lines.append("  ✅ 一致同意:")
            for p in result.debate_agreement:
                lines.append(f"    • {p}")
        
        if result.debate_risks:
            lines.append("")
            lines.append("  🚨 风险提示:")
            for p in result.debate_risks:
                lines.append(f"    • {p}")
        
        if result.action_items:
            lines.append("")
            lines.append("  📋 行动建议:")
            for p in result.action_items:
                lines.append(f"    • {p}")
    
    # 最终建议
    lines.append("")
    lines.append("═" * 60)
    lines.append(f"  最终建议: {result.final_signal} {result.final_advice}")
    lines.append("═" * 60)
    
    # 针对摩根标普基金的具体行动建议
    lines.append("")
    lines.append("  📌 针对摩根标普500ETF基金(019305)的行动建议:")
    lines.append("  ─────────────────────────────────────────────────")
    
    if result.final_signal == "🟢":
        if result.valuation_signal == "🟢" and result.debate_consensus == "bullish":
            lines.append("  • 行动: 可以买入/加仓")
            lines.append("  • 仓位: 建议配置20-30%仓位")
            lines.append("  • 策略: 分批买入，每下跌5%加一次")
            lines.append("  • 止损: 设置-15%止损位")
        else:
            lines.append("  • 行动: 可以分批买入")
            lines.append("  • 仓位: 建议配置10-20%仓位")
            lines.append("  • 策略: 定投方式，每周定额买入")
            lines.append("  • 止损: 设置-10%止损位")
    elif result.final_signal == "🔴":
        lines.append("  • 行动: 不建议买入，考虑减仓")
        lines.append("  • 仓位: 已有仓位建议减至5%以下")
        lines.append("  • 策略: 等待回调，52周位置<50%再考虑")
        lines.append("  • 止损: 已有仓位设置-10%止损")
    else:
        lines.append("  • 行动: 观望，等待更明确信号")
        lines.append("  • 仓位: 维持现有仓位，不加不减")
        lines.append("  • 策略: 关注PE和VIX变化")
        lines.append("  • 止损: 已有仓位设置-12%止损")
    
    lines.append("  ─────────────────────────────────────────────────")
    lines.append("  ⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。")
    lines.append("     投资有风险，入市需谨慎。")
    lines.append("═" * 60)
    
    return "\n".join(lines)


def check_sp500_timing(
    debate_rounds: int = 2,
    stock_tickers: list[str] | None = None,
    topic: str = "当前市场环境下，是否应该投资摩根标普500ETF基金(019305)?",
    force_debate: bool = False,
    call_timeout: float = 30.0,
) -> TimingResult:
    """
    七大佬辩论判断S&P500出手时机
    
    Args:
        debate_rounds: 辩论轮数（默认2）
        stock_tickers: 个股代码列表（可选）
        topic: 辩论主题
        force_debate: 强制辩论（即使估值中性）
    
    Returns:
        TimingResult: 包含估值信号、辩论结论、行动建议
    """
    result = TimingResult()
    
    # 获取市场数据
    bundle = get_market_data()
    
    # 提取关键指标
    spy = bundle.us_indices[0] if bundle.us_indices else None
    result.spy_price = spy.price if spy else 0
    result.pe = spy.pe if spy else 0
    
    # 52周位置
    if spy and spy.high_52w and spy.low_52w and spy.price:
        result.pos_52w = (spy.price - spy.low_52w) / (spy.high_52w - spy.low_52w) * 100
    
    # VIX
    vix_str = bundle.macro.get("VIX恐慌指数", "")
    if vix_str:
        try:
            result.vix = float(vix_str.split("(")[0].strip())
        except:
            pass
    
    # 10年期国债
    tnx_str = bundle.macro.get("10年期美债收益率", "")
    if tnx_str:
        try:
            result.tnx_10y = float(tnx_str.replace("%", ""))
        except:
            pass
    
    # 估值信号
    result.valuation_signal, result.valuation_desc, cheap_count = get_overall_signal(
        result.pe, result.vix, result.pos_52w, result.tnx_10y
    )
    
    # 决定是否辩论
    use_debate, auto_rounds, trigger_reason = get_debate_trigger(
        result.valuation_signal, cheap_count, cheap_count
    )
    
    if force_debate:
        use_debate = True
        trigger_reason = "强制辩论"
    
    if use_debate:
        debate_rounds = auto_rounds if auto_rounds > 0 else debate_rounds
        result.debate_enabled = True
        
        # 运行辩论
        debater = MarketDebater(agents=ALL_AGENTS, rounds=debate_rounds, call_timeout=call_timeout)
        debate_result = debater.run(
            topic=topic, market_data=bundle.to_text(),
            spy_price=result.spy_price, pe=result.pe, vix=result.vix,
            pos_52w=result.pos_52w, tnx_10y=result.tnx_10y,
            valuation_signal=result.valuation_signal,
        )
        
        # 提取辩论结果
        if debate_result.consensus:
            c = debate_result.consensus
            result.debate_consensus = c.get("consensus", "neutral")
            result.debate_confidence = c.get("confidence_avg", 0)
            result.debate_agreement = c.get("agreement_points", [])
            result.debate_risks = c.get("risks", [])
            result.action_items = c.get("action_items", [])
            result.avg_target_position = debate_result.avg_target_position
    
    # 综合判断
    if result.debate_enabled and result.debate_consensus:
        # 估值信号 + 辩论结论综合
        val_score = 0
        if result.valuation_signal == "🟢":
            val_score = 2
        elif result.valuation_signal == "🟡":
            val_score = 1
        
        debate_score = 0
        if result.debate_consensus == "bullish":
            debate_score = 2
        elif result.debate_consensus == "neutral":
            debate_score = 1
        
        total = val_score + debate_score
        if total >= 3:
            result.final_signal = "🟢"
            result.final_advice = "可以买入（估值+辩论双重确认）"
        elif total >= 2:
            result.final_signal = "🟢"
            result.final_advice = "可以分批买入（信号偏正面）"
        elif total <= 1:
            result.final_signal = "🔴"
            result.final_advice = "不建议买入（信号偏负面）"
        else:
            result.final_signal = "🟡"
            result.final_advice = "观望（信号中性）"
    else:
        # 仅估值信号
        result.final_signal = result.valuation_signal
        result.final_advice = result.valuation_desc
    
    # 生成总结报告
    result.summary = format_summary(result)
    
    return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="S&P500 七大佬辩论出手时机判断器")
    parser.add_argument("--rounds", type=int, default=2, help="辩论轮数（默认2）")
    parser.add_argument("--stocks", type=str, default=None, help="个股代码（逗号分隔）")
    parser.add_argument("--topic", type=str, default="当前市场环境下，是否应该投资S&P500?", help="辩论主题")
    parser.add_argument("--force-debate", action="store_true", help="强制辩论")
    parser.add_argument("--timeout", type=float, default=30.0, help="LLM单次调用超时秒数（默认30）")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--brief", action="store_true", help="简洁模式")
    args = parser.parse_args()
    
    stock_tickers = None
    if args.stocks:
        stock_tickers = [s.strip().upper() for s in args.stocks.split(",")]
    
    result = check_sp500_timing(
        debate_rounds=args.rounds,
        stock_tickers=stock_tickers,
        topic=args.topic,
        force_debate=args.force_debate,
        call_timeout=args.timeout,
    )
    
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "valuation": {
                "spy_price": result.spy_price,
                "pe": result.pe,
                "vix": result.vix,
                "pos_52w": result.pos_52w,
                "tnx_10y": result.tnx_10y,
                "signal": result.valuation_signal,
                "description": result.valuation_desc,
            },
            "debate": {
                "enabled": result.debate_enabled,
                "consensus": result.debate_consensus,
                "confidence": result.debate_confidence,
                "avg_target_position": result.avg_target_position,
                "agreement": result.debate_agreement,
                "risks": result.debate_risks,
                "action_items": result.action_items,
            },
            "final": {
                "signal": result.final_signal,
                "advice": result.final_advice,
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.brief:
        emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(result.debate_consensus, "⚪")
        print(f"\n{result.final_signal} S&P500出手时机: {result.final_advice}")
        print(f"  SPY: ${result.spy_price:.2f} | PE: {result.pe:.1f} | VIX: {result.vix} | 52周: {result.pos_52w:.0f}%")
        if result.debate_enabled:
            print(f"  辩论: {emoji} {result.debate_consensus.upper()} | 置信度: {result.debate_confidence}% | 目标仓位: {result.avg_target_position}%")
    else:
        print(result.summary)


if __name__ == "__main__":
    main()
