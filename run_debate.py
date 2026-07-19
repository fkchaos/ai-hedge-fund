#!/usr/bin/env python3
"""
Multi-agent debate runner for ai-hedge-fund.

Usage:
    python run_debate.py --topic "Should I invest in S&P500 now?"
    python run_debate.py --topic "AAPL估值" --stocks AAPL,MSFT,GOOGL
    python run_debate.py --topic "摩根标普500ETF基金(019305)估值" --agents buffett,lynch --rounds 3

Environment:
    OPENAI_API_KEY    — MiMo API key
    OPENAI_API_BASE   — MiMo API base URL
    OPENAI_API_MODEL  — Model name (default: mimo-v2.5)
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Setup path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.debate.debater import MarketDebater
from src.debate.agents import ALL_AGENTS, BUFFETT, LYNCH, MUNGER, BURRY
from src.debate.market_data import get_market_data


AGENT_MAP = {
    "buffett": BUFFETT,
    "lynch": LYNCH,
    "munger": MUNGER,
    "burry": BURRY,
}


def format_result(result) -> str:
    """Format debate result for display."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  多大佬辩论: {result.topic}")
    lines.append(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
    parser = argparse.ArgumentParser(description="Multi-agent investment debate")
    parser.add_argument("--topic", type=str, default="当前市场环境下，是否应该投资S&P500?",
                        help="Debate topic/question")
    parser.add_argument("--agents", type=str, default=None,
                        help="Comma-separated agent names (default: all)")
    parser.add_argument("--stocks", type=str, default=None,
                        help="Comma-separated stock tickers for detailed analysis (e.g., AAPL,MSFT)")
    parser.add_argument("--rounds", type=int, default=2,
                        help="Number of debate rounds (default: 2)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save result to file")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    # Select agents
    if args.agents:
        names = [n.strip().lower() for n in args.agents.split(",")]
        agents = [AGENT_MAP[n] for n in names if n in AGENT_MAP]
        if not agents:
            print(f"Error: No valid agents. Available: {list(AGENT_MAP.keys())}")
            sys.exit(1)
    else:
        agents = ALL_AGENTS

    # Parse stock tickers
    stock_tickers = None
    if args.stocks:
        stock_tickers = [s.strip().upper() for s in args.stocks.split(",")]

    # Get market data
    print("正在获取市场数据...")
    bundle = get_market_data(stock_tickers=stock_tickers)
    market_data_text = bundle.to_text()
    print(market_data_text)
    print()

    # Run debate
    print(f"开始辩论: {args.topic}")
    print(f"参与大佬: {', '.join(a.name for a in agents)}")
    print(f"辩论轮数: {args.rounds}")
    print()

    debater = MarketDebater(agents=agents, rounds=args.rounds)
    result = debater.run(topic=args.topic, market_data=market_data_text)

    # Output
    if args.json:
        output = json.dumps({
            "topic": result.topic,
            "rounds": [
                {
                    "agent": r.agent_name,
                    "role": r.role,
                    "signal": r.signal,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                }
                for r in result.rounds
            ],
            "consensus": result.consensus,
        }, ensure_ascii=False, indent=2)
    else:
        output = format_result(result)

    print(output)

    # Save
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"\n结果已保存: {args.output}")


if __name__ == "__main__":
    main()
