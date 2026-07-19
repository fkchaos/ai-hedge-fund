#!/usr/bin/env python3
"""
S&P500 估值查询 + 四大佬辩论 集成工具

用法:
    # 仅估值查询（默认）
    python check_valuation_with_debate.py
    
    # 估值查询 + 辩论
    python check_valuation_with_debate.py --with-debate
    
    # 指定辩论轮数
    python check_valuation_with_debate.py --with-debate --rounds 3
    
    # 指定个股分析
    python check_valuation_with_debate.py --with-debate --stocks AAPL,MSFT,GOOGL
    
    # 自定义辩论主题
    python check_valuation_with_debate.py --with-debate --topic "当前是否应该加仓标普500?"
    
    # JSON输出
    python check_valuation_with_debate.py --with-debate --json

估值信号:
    🟢 强烈买入: PE≤18 + VIX≥30 + 52周≤30%
    🟢 可以分批买: PE≤22 + VIX≥25 + 52周≤50%
    🟡 观望: PE 22-27 + VIX 15-25
    🔴 不买: PE≥27 或 VIX≤15 或 52周≥80%

辩论大佬:
    - Warren Buffett: 价值投资者，长期持有
    - Peter Lynch: GARP投资者，成长+合理估值
    - Charlie Munger: 质量投资者，逆向思维
    - Michael Burry: 逆向投资者，泡沫探测器
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.debate.market_data import get_market_data
from src.debate.debater import MarketDebater
from src.debate.agents import ALL_AGENTS, BUFFETT, LYNCH, MUNGER, BURRY

# ── 估值区间定义 ──────────────────────────────────────────
VALUATION_BANDS = {
    "pe":       {"cheap": 18, "fair": 22, "expensive": 27},
    "vix_fear": {"cheap": 30, "fair": 25, "expensive": 15},  # 反向：越高越恐慌=越便宜
    "pos_52w":  {"cheap": 30, "fair": 50, "expensive": 80},
    "tnx":      {"cheap": 2.5, "fair": 3.5, "expensive": 4.5},
}

AGENT_MAP = {
    "buffett": BUFFETT,
    "lynch": LYNCH,
    "munger": MUNGER,
    "burry": BURRY,
}


def classify(val, bands):
    """根据区间判断信号。vix_fair为反向指标。"""
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
        return "🟢", "强烈买入信号", cheap_count
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


def format_valuation_report(pe, vix, pos, tnx, spy_price, spy_change):
    """格式化估值报告。"""
    lines = []
    lines.append("\n" + "=" * 60)
    lines.append("  S&P500 估值速查")
    lines.append("=" * 60)

    if spy_price:
        lines.append(f"\n  SPY价格: ${spy_price:.2f}")
        if spy_change is not None:
            lines.append(f"  今日涨跌: {spy_change:+.2f}%")

    # 逐项指标
    items = [
        ("S&P500 PE", pe, VALUATION_BANDS["pe"]),
        ("VIX恐慌指数", vix, VALUATION_BANDS["vix_fear"]),
        ("52周位置(%)", round(pos, 1) if pos else None, VALUATION_BANDS["pos_52w"]),
        ("10Y国债收益率(%)", tnx, VALUATION_BANDS["tnx"]),
    ]

    lines.append("\n")
    for name, val, bands in items:
        icon, label = classify(val, bands)
        val_str = f"{val}" if val is not None else "N/A"
        lines.append(f"  {icon} {name}: {val_str}  → {label}")

    # 综合判断
    sig, desc, count = get_overall_signal(pe, vix, pos, tnx)
    lines.append(f"\n{'─' * 60}")
    lines.append(f"  {sig} 综合判断: {desc}")
    lines.append(f"{'─' * 60}")

    return "\n".join(lines), sig, desc, count


def format_debate_result(result):
    """格式化辩论结果。"""
    lines = []
    lines.append("\n" + "=" * 60)
    lines.append("  四大佬辩论")
    lines.append("=" * 60)

    # Group by round
    agents_per_round = len(set(r.agent_name for r in result.rounds))
    num_rounds = len(result.rounds) // agents_per_round if agents_per_round else 0

    for rnd in range(num_rounds):
        lines.append(f"\n{'─' * 60}")
        lines.append(f"  ROUND {rnd + 1}")
        lines.append(f"{'─' * 60}")
        start = rnd * agents_per_round
        end = start + agents_per_round
        for r in result.rounds[start:end]:
            emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(r.signal, "⚪")
            lines.append(f"\n{emoji} {r.agent_name} ({r.role})")
            lines.append(f"   信号: {r.signal.upper()} | 置信度: {r.confidence}%")
            lines.append(f"   论点: {r.reasoning}")

    # Consensus
    if result.consensus:
        lines.append(f"\n{'═' * 60}")
        lines.append(f"  综合结论")
        lines.append(f"{'═' * 60}")
        c = result.consensus
        emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(c.get("consensus", ""), "⚪")
        lines.append(f"\n{emoji} 共识: {c.get('consensus', 'N/A').upper()}")
        lines.append(f"   平均置信度: {c.get('confidence_avg', 'N/A')}%")

        if c.get("agreement_points"):
            lines.append(f"\n   ✅ 一致同意:")
            for p in c["agreement_points"]:
                lines.append(f"      • {p}")

        if c.get("disagreement_points"):
            lines.append(f"\n   ⚠️ 分歧点:")
            for p in c["disagreement_points"]:
                lines.append(f"      • {p}")

        if c.get("risks"):
            lines.append(f"\n   🚨 风险提示:")
            for p in c["risks"]:
                lines.append(f"      • {p}")

        if c.get("action_items"):
            lines.append(f"\n   📋 行动建议:")
            for p in c["action_items"]:
                lines.append(f"      • {p}")

    lines.append(f"\n{'═' * 60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="S&P500 估值查询 + 四大佬辩论")
    parser.add_argument("--with-debate", action="store_true", help="启用辩论")
    parser.add_argument("--rounds", type=int, default=2, help="辩论轮数（默认2）")
    parser.add_argument("--stocks", type=str, default=None, help="个股代码（逗号分隔）")
    parser.add_argument("--topic", type=str, default="当前市场环境下，是否应该投资S&P500?", help="辩论主题")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--brief", action="store_true", help="简洁模式，只看结论")
    args = parser.parse_args()

    print("正在获取市场数据...")
    bundle = get_market_data()

    # 提取关键指标
    spy = bundle.us_indices[0] if bundle.us_indices else None
    pe = spy.pe if spy else None
    pos = None
    if spy and spy.high_52w and spy.low_52w and spy.price:
        pos = (spy.price - spy.low_52w) / (spy.high_52w - spy.low_52w) * 100

    vix_str = bundle.macro.get("VIX恐慌指数", "")
    vix = None
    if vix_str:
        try:
            vix = float(vix_str.split("(")[0].strip())
        except:
            pass

    tnx_str = bundle.macro.get("10年期美债收益率", "")
    tnx = None
    if tnx_str:
        try:
            tnx = float(tnx_str.replace("%", ""))
        except:
            pass

    # 估值报告
    valuation_report, sig, desc, count = format_valuation_report(
        pe, vix, pos, tnx, 
        spy.price if spy else None, 
        spy.change_pct if spy else None
    )

    # 决定是否辩论
    use_debate = args.with_debate
    debate_rounds = args.rounds
    trigger_reason = ""

    if not use_debate:
        # 自动判断是否需要辩论
        use_debate, debate_rounds, trigger_reason = get_debate_trigger(sig, count, count)

    # 输出结果
    if args.json:
        result = {
            "timestamp": datetime.now().isoformat(),
            "valuation": {
                "spy_price": spy.price if spy else None,
                "pe": pe,
                "vix": vix,
                "pos_52w": round(pos, 1) if pos else None,
                "tnx_10y": tnx,
                "signal": sig,
                "description": desc,
            },
            "debate": {
                "enabled": use_debate,
                "rounds": debate_rounds,
                "trigger_reason": trigger_reason,
            },
        }

        if use_debate:
            print(f"\n{valuation_report}")
            print(f"\n触发辩论: {trigger_reason}")

            # 解析个股
            stock_tickers = None
            if args.stocks:
                stock_tickers = [s.strip().upper() for s in args.stocks.split(",")]

            debater = MarketDebater(agents=ALL_AGENTS, rounds=debate_rounds)
            debate_result = debater.run(topic=args.topic, market_data=bundle.to_text())

            # 提取辩论结果
            result["debate"]["topic"] = debate_result.topic
            result["debate"]["rounds"] = [
                {
                    "agent": r.agent_name,
                    "role": r.role,
                    "signal": r.signal,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                }
                for r in debate_result.rounds
            ]
            result["debate"]["consensus"] = debate_result.consensus

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 简洁模式
    if args.brief:
        print(f"\n{sig} S&P500综合信号: {desc}")
        print(f"  SPY: ${spy.price:.2f} | PE: {pe:.1f} | VIX: {vix} | 52周位置: {pos:.0f}% | 10Y: {tnx}%")

        if use_debate:
            print(f"\n触发辩论: {trigger_reason}")
            stock_tickers = None
            if args.stocks:
                stock_tickers = [s.strip().upper() for s in args.stocks.split(",")]

            debater = MarketDebater(agents=ALL_AGENTS, rounds=debate_rounds)
            debate_result = debater.run(topic=args.topic, market_data=bundle.to_text())

            if debate_result.consensus:
                c = debate_result.consensus
                emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(c.get("consensus", ""), "⚪")
                print(f"\n{emoji} 辩论共识: {c.get('consensus', 'N/A').upper()} | 平均置信度: {c.get('confidence_avg', 'N/A')}%")
        return

    # 完整输出
    print(valuation_report)

    if use_debate:
        print(f"\n{'─' * 60}")
        print(f"  触发辩论: {trigger_reason}")
        print(f"{'─' * 60}")

        stock_tickers = None
        if args.stocks:
            stock_tickers = [s.strip().upper() for s in args.stocks.split(",")]
            print(f"  个股分析: {', '.join(stock_tickers)}")

        debater = MarketDebater(agents=ALL_AGENTS, rounds=debate_rounds)
        debate_result = debater.run(topic=args.topic, market_data=bundle.to_text())

        print(format_debate_result(debate_result))
    else:
        print(f"\n{'─' * 60}")
        print(f"  💡 估值信号中性，无需辩论")
        print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
