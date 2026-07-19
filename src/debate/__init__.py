"""Multi-agent debate module for ai-hedge-fund.

Allows investment personas to debate a market question in rounds,
producing structured debate results with consensus/disagreement tracking.
"""

from .debater import MarketDebater, DebateRound, DebateResult
from .llm import MiMoLLM
from .market_data import get_market_data, MarketDataBundle

__all__ = [
    "MarketDebater", "DebateRound", "DebateResult",
    "MiMoLLM", "get_market_data", "MarketDataBundle",
]
