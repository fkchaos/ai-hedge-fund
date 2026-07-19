#!/usr/bin/env python3
"""
非交互式运行ai-hedge-fund分析A股
"""
import os
import sys
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, '/root/ai-hedge-fund')

load_dotenv('/root/ai-hedge-fund/.env')

from src.main import run_hedge_fund
from src.utils.display import print_trading_output

# 配置
TICKERS = ["600519", "000858", "000001", "601318", "600036"]  # 茅台、五粮液、平安、招商
START_DATE = "2026-01-01"
END_DATE = "2026-07-17"

# 所有analysts（使用正确的名字）
ALL_ANALYSTS = [
    "fundamentals_analyst",
    "sentiment_analyst", 
    "technical_analyst",
    "valuation_analyst",
    "news_sentiment_analyst",
]

# 投资大师（选择几个代表性的）
MASTER_ANALYSTS = [
    "warren_buffett",
    "charlie_munger",
    "michael_burry",
    "nassim_taleb",
    "peter_lynch",
]

# 构建portfolio
portfolio = {
    "cash": 100000,
    "margin_requirement": 0.5,
    "margin_used": 0.0,
    "positions": {
        ticker: {
            "long": 0,
            "short": 0,
            "long_cost_basis": 0.0,
            "short_cost_basis": 0.0,
            "short_margin_used": 0.0,
        }
        for ticker in TICKERS
    },
    "realized_gains": {
        ticker: {
            "long": 0.0,
            "short": 0.0,
        }
        for ticker in TICKERS
    },
}

print("=" * 60)
print("AI Hedge Fund - A股分析")
print("=" * 60)
print(f"股票: {TICKERS}")
print(f"时间: {START_DATE} ~ {END_DATE}")
print(f"初始资金: {portfolio['cash']}")
print(f"Analysts: {ALL_ANALYSTS + MASTER_ANALYSTS}")
print("=" * 60)

# 运行分析
result = run_hedge_fund(
    tickers=TICKERS,
    start_date=START_DATE,
    end_date=END_DATE,
    portfolio=portfolio,
    show_reasoning=True,
    selected_analysts=ALL_ANALYSTS + MASTER_ANALYSTS,
    model_name="mimo-v2.5",
    model_provider="OpenAI",
)

print_trading_output(result)
