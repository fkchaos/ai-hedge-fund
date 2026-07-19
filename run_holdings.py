#!/usr/bin/env python3
"""
分析我们持仓的股票
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, '/root/ai-hedge-fund')
load_dotenv('/root/ai-hedge-fund/.env')

from src.main import run_hedge_fund
from src.utils.display import print_trading_output

# 我们持仓的股票（去重后）
HOLDINGS = [
    "000498",  # 山东路桥 - 两个账户都有
    "003039",  # 顺控发展 - 账户1
    "301215",  # 中汽股份 - 账户1
    "301327",  # 华宝新能 - 账户1
    "301339",  # 通行宝 - 账户1
    "600639",  # 浦东金桥 - 账户2
    "603043",  # 广州酒家 - 账户2
    "603376",  # 大明电子 - 账户2
    "603406",  # 天富龙 - 账户2
]

START_DATE = "2026-01-01"
END_DATE = "2026-07-17"

# 所有analysts
ALL_ANALYSTS = [
    "fundamentals_analyst",
    "sentiment_analyst", 
    "technical_analyst",
    "valuation_analyst",
    "news_sentiment_analyst",
    "warren_buffett",
    "charlie_munger",
    "michael_burry",
    "nassim_taleb",
    "peter_lynch",
]

portfolio = {
    "cash": 100000,
    "margin_requirement": 0.5,
    "margin_used": 0.0,
    "positions": {
        ticker: {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0, "short_margin_used": 0.0}
        for ticker in HOLDINGS
    },
    "realized_gains": {
        ticker: {"long": 0.0, "short": 0.0}
        for ticker in HOLDINGS
    },
}

print("=" * 60)
print("AI Hedge Fund - 持仓股票分析")
print("=" * 60)
print(f"股票: {HOLDINGS}")
print(f"时间: {START_DATE} ~ {END_DATE}")
print("=" * 60)

result = run_hedge_fund(
    tickers=HOLDINGS,
    start_date=START_DATE,
    end_date=END_DATE,
    portfolio=portfolio,
    show_reasoning=True,
    selected_analysts=ALL_ANALYSTS,
    model_name="mimo-v2.5",
    model_provider="OpenAI",
)

print_trading_output(result)
