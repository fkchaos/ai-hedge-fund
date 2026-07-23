"""Market data module — combines yfinance (US) + akshare (A-share) for debate context."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexSnapshot:
    """A single index/ETF snapshot."""
    name: str
    price: float | None = None
    change_pct: float | None = None
    pe: float | None = None
    pb: float | None = None
    dividend_yield: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    ma50: float | None = None
    ma200: float | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class StockSnapshot:
    """Detailed stock data for debate."""
    ticker: str
    name: str = ""
    price: float | None = None
    pe_trailing: float | None = None
    pe_forward: float | None = None
    pb: float | None = None
    peg: float | None = None
    roe: float | None = None
    roa: float | None = None
    profit_margin: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    dividend_yield: float | None = None
    market_cap: float | None = None
    free_cashflow: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    ma50: float | None = None
    ma200: float | None = None
    analyst_rating: str = ""
    target_price: float | None = None
    num_analysts: int | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class MarketDataBundle:
    """Complete market data for a debate."""
    us_indices: list[IndexSnapshot] = field(default_factory=list)
    cn_indices: list[IndexSnapshot] = field(default_factory=list)
    macro: dict = field(default_factory=dict)  # VIX, yields, etc.
    stocks: list[StockSnapshot] = field(default_factory=list)
    recent_trend: str = ""
    timestamp: str = ""
    quant_signals: str = ""  # 量化预计算指标（技术+估值）

    def to_text(self) -> str:
        """Format as readable text for LLM context."""
        lines = []
        lines.append(f"市场数据快照 ({self.timestamp})")
        lines.append("=" * 60)

        # ── 量化预计算指标（优先展示）──
        if self.quant_signals:
            lines.append("")
            lines.append(self.quant_signals)

        # ── Macro ──
        if self.macro:
            lines.append("\n📊 宏观指标:")
            for k, v in self.macro.items():
                lines.append(f"  {k}: {v}")

        # ── US indices ──
        if self.us_indices:
            lines.append("\n🇺🇸 美股指数/ETF:")
            for idx in self.us_indices:
                chg = f" ({idx.change_pct:+.2f}%)" if idx.change_pct is not None else ""
                pe_str = f"PE={idx.pe:.1f}" if idx.pe else ""
                pb_str = f"PB={idx.pb:.2f}" if idx.pb else ""
                val_str = " | ".join(s for s in [pe_str, pb_str] if s)
                lines.append(f"  {idx.name}: {idx.price:.2f}{chg}  [{val_str}]")
                if idx.high_52w and idx.low_52w:
                    pos = (idx.price - idx.low_52w) / (idx.high_52w - idx.low_52w) * 100 if idx.high_52w != idx.low_52w else 50
                    lines.append(f"    52周区间: {idx.low_52w:.2f} ~ {idx.high_52w:.2f} (当前位置: {pos:.0f}%)")
                if idx.ma50:
                    above_below = "上方" if idx.price > idx.ma50 else "下方"
                    lines.append(f"    MA50: {idx.ma50:.2f} ({idx.name}在其{above_below})")
                if idx.ma200:
                    above_below = "上方" if idx.price > idx.ma200 else "下方"
                    lines.append(f"    MA200: {idx.ma200:.2f} ({idx.name}在其{above_below})")
                if idx.dividend_yield:
                    lines.append(f"    股息率: {idx.dividend_yield:.2f}%")

        # ── Individual stocks ──
        if self.stocks:
            lines.append("\n📈 个股详情:")
            for s in self.stocks:
                lines.append(f"\n  【{s.ticker}】{s.name}")
                lines.append(f"    价格: {s.price}")
                if s.pe_trailing:
                    lines.append(f"    PE(TTM): {s.pe_trailing:.1f}  |  PE(FWD): {s.pe_forward:.1f}" if s.pe_forward else f"    PE(TTM): {s.pe_trailing:.1f}")
                if s.pb:
                    lines.append(f"    PB: {s.pb:.2f}  |  PEG: {s.peg:.2f}" if s.peg else f"    PB: {s.pb:.2f}")
                if s.roe:
                    lines.append(f"    ROE: {s.roe:.1%}  |  ROA: {s.roa:.1%}" if s.roa else f"    ROE: {s.roe:.1%}")
                if s.gross_margin:
                    lines.append(f"    毛利率: {s.gross_margin:.1%}  |  营业利润率: {s.operating_margin:.1%}  |  净利率: {s.profit_margin:.1%}")
                if s.debt_to_equity:
                    lines.append(f"    D/E: {s.debt_to_equity:.1f}  |  流动比率: {s.current_ratio:.2f}" if s.current_ratio else f"    D/E: {s.debt_to_equity:.1f}")
                if s.revenue_growth:
                    lines.append(f"    营收增长: {s.revenue_growth:.1%}  |  盈利增长: {s.earnings_growth:.1%}" if s.earnings_growth else f"    营收增长: {s.revenue_growth:.1%}")
                if s.dividend_yield:
                    lines.append(f"    股息率: {s.dividend_yield:.2f}%")
                if s.market_cap:
                    cap_b = s.market_cap / 1e9
                    lines.append(f"    市值: ${cap_b:,.0f}B")
                if s.free_cashflow:
                    fcf_b = s.free_cashflow / 1e9
                    lines.append(f"    自由现金流: ${fcf_b:,.1f}B")
                if s.high_52w and s.low_52w and s.price:
                    pos = (s.price - s.low_52w) / (s.high_52w - s.low_52w) * 100
                    lines.append(f"    52周区间: {s.low_52w:.2f} ~ {s.high_52w:.2f} (当前{pos:.0f}%)")
                if s.analyst_rating:
                    lines.append(f"    分析师评级: {s.analyst_rating}  |  目标价: ${s.target_price:.2f}" if s.target_price else f"    分析师评级: {s.analyst_rating}")
                if s.num_analysts:
                    lines.append(f"    覆盖分析师: {s.num_analysts}人")

        # ── Trend summary ──
        if self.recent_trend:
            lines.append(f"\n📉 近期走势:\n{self.recent_trend}")

        return "\n".join(lines)


def _safe_float(val) -> float | None:
    """Convert to float, return None on failure."""
    if val is None:
        return None
    try:
        import math
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def _pct_change(current: float, previous: float) -> float:
    """Calculate percentage change."""
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def fetch_us_data(tickers: list[str] | None = None) -> tuple[list[IndexSnapshot], list[StockSnapshot], dict]:
    """Fetch US market data via yfinance.

    Returns (indices, stocks, macro_dict).
    """
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")

    tickers = tickers or ["SPY", "QQQ", "DIA", "IWM"]
    indices = []
    stocks = []
    macro = {}

    # ── VIX ──
    try:
        vix = yf.Ticker("^VIX")
        vix_info = vix.info
        vix_price = _safe_float(vix_info.get("regularMarketPrice"))
        vix_prev = _safe_float(vix_info.get("regularMarketPreviousClose"))
        if vix_price:
            chg = _pct_change(vix_price, vix_prev) if vix_prev else None
            macro["VIX恐慌指数"] = f"{vix_price:.2f}" + (f" ({chg:+.2f}%)" if chg is not None else "")
            if vix_price < 15:
                macro["VIX解读"] = "极低 — 市场极度乐观，可能低估风险"
            elif vix_price < 20:
                macro["VIX解读"] = "低位 — 市场情绪平稳"
            elif vix_price < 25:
                macro["VIX解读"] = "中等 — 存在一定不确定性"
            elif vix_price < 30:
                macro["VIX解读"] = "偏高 — 市场恐慌升温"
            else:
                macro["VIX解读"] = "极高 — 市场恐慌，可能是逆向买入信号"
    except Exception as e:
        logger.warning(f"VIX fetch failed: {e}")
        macro["VIX恐慌指数"] = "获取失败"

    # ── 10Y Treasury ──
    try:
        tnx = yf.Ticker("^TNX")
        tnx_info = tnx.info
        tnx_price = _safe_float(tnx_info.get("regularMarketPrice"))
        if tnx_price:
            macro["10年期美债收益率"] = f"{tnx_price:.3f}%"
    except Exception as e:
        logger.warning(f"TNX fetch failed: {e}")

    # ── US Dollar Index ──
    try:
        udx = yf.Ticker("DX-Y.NYB")
        udx_info = udx.info
        udx_price = _safe_float(udx_info.get("regularMarketPrice"))
        if udx_price:
            macro["美元指数(DXY)"] = f"{udx_price:.2f}"
    except Exception as e:
        logger.warning(f"DXY fetch failed: {e}")

    # ── Gold ──
    try:
        gold = yf.Ticker("GC=F")
        gold_info = gold.info
        gold_price = _safe_float(gold_info.get("regularMarketPrice"))
        if gold_price:
            macro["黄金(期货)"] = f"${gold_price:.2f}"
    except Exception as e:
        logger.warning(f"Gold fetch failed: {e}")

    # ── Indices / ETFs ──
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            price = _safe_float(info.get("regularMarketPrice")) or _safe_float(info.get("previousClose"))
            prev = _safe_float(info.get("regularMarketPreviousClose"))
            chg = _pct_change(price, prev) if (price and prev) else None

            snap = IndexSnapshot(
                name=info.get("shortName", ticker),
                price=price,
                change_pct=chg,
                pe=_safe_float(info.get("trailingPE")),
                pb=_safe_float(info.get("priceToBook")),
                dividend_yield=_safe_float(info.get("dividendYield")),
                high_52w=_safe_float(info.get("fiftyTwoWeekHigh")),
                low_52w=_safe_float(info.get("fiftyTwoWeekLow")),
                ma50=_safe_float(info.get("fiftyDayAverage")),
                ma200=_safe_float(info.get("twoHundredDayAverage")),
            )
            indices.append(snap)
        except Exception as e:
            logger.warning(f"Index {ticker} fetch failed: {e}")

    return indices, stocks, macro


def fetch_stock_data(ticker: str) -> StockSnapshot | None:
    """Fetch detailed single stock data via yfinance."""
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")

    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("trailingPE") is None:
            return None

        return StockSnapshot(
            ticker=ticker,
            name=info.get("shortName", ""),
            price=_safe_float(info.get("regularMarketPrice")) or _safe_float(info.get("previousClose")),
            pe_trailing=_safe_float(info.get("trailingPE")),
            pe_forward=_safe_float(info.get("forwardPE")),
            pb=_safe_float(info.get("priceToBook")),
            peg=_safe_float(info.get("pegRatio")),
            roe=_safe_float(info.get("returnOnEquity")),
            roa=_safe_float(info.get("returnOnAssets")),
            profit_margin=_safe_float(info.get("profitMargins")),
            gross_margin=_safe_float(info.get("grossMargins")),
            operating_margin=_safe_float(info.get("operatingMargins")),
            debt_to_equity=_safe_float(info.get("debtToEquity")),
            current_ratio=_safe_float(info.get("currentRatio")),
            revenue_growth=_safe_float(info.get("revenueGrowth")),
            earnings_growth=_safe_float(info.get("earningsGrowth")),
            dividend_yield=_safe_float(info.get("dividendYield")),
            market_cap=_safe_float(info.get("marketCap")),
            free_cashflow=_safe_float(info.get("freeCashflow")),
            high_52w=_safe_float(info.get("fiftyTwoWeekHigh")),
            low_52w=_safe_float(info.get("fiftyTwoWeekLow")),
            ma50=_safe_float(info.get("fiftyDayAverage")),
            ma200=_safe_float(info.get("twoHundredDayAverage")),
            analyst_rating=info.get("recommendationKey", ""),
            target_price=_safe_float(info.get("targetMeanPrice")),
            num_analysts=_safe_float(info.get("numberOfAnalystOpinions")),
        )
    except Exception as e:
        logger.warning(f"Stock {ticker} fetch failed: {e}")
        return None



def fetch_recent_trend(ticker: str = "SPY", days: int = 10) -> str:
    """Fetch recent daily trend for context."""
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")

    try:
        hist = yf.download(ticker, period=f"{days + 5}d", progress=False)
        if hist is None or len(hist) < 2:
            return ""
        # Get last N rows
        recent = hist.tail(days)
        lines = [f"近{len(recent)}个交易日 {ticker} 走势:"]
        for date, row in recent.iterrows():
            close_val = row["Close"]
            vol_val = row["Volume"]
            if hasattr(close_val, 'iloc'):
                close_val = close_val.iloc[0]
            if hasattr(vol_val, 'iloc'):
                vol_val = vol_val.iloc[0]
            date_str = date.strftime("%m-%d") if hasattr(date, "strftime") else str(date)[:5]
            lines.append(f"  {date_str}  收盘: {close_val:.2f}  成交量: {vol_val/1e6:.1f}M")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Trend fetch failed: {e}")
        return ""


def get_market_data(
    stock_tickers: list[str] | None = None,
    index_tickers: list[str] | None = None,
) -> MarketDataBundle:
    """Fetch comprehensive market data for debate.

    Args:
        stock_tickers: Individual stocks to analyze (e.g., ["AAPL", "MSFT"])
        index_tickers: US index ETFs (default: SPY, QQQ, DIA, IWM)
    """
    bundle = MarketDataBundle(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    # US indices + macro
    us_indices, us_stocks, macro = fetch_us_data(index_tickers)
    bundle.us_indices = us_indices
    bundle.macro = macro

    # Individual stocks
    if stock_tickers:
        for ticker in stock_tickers:
            snap = fetch_stock_data(ticker)
            if snap:
                bundle.stocks.append(snap)

    # Recent trend
    bundle.recent_trend = fetch_recent_trend("SPY", 10)

    # 量化预计算指标（技术+估值）
    try:
        from .quant_signals import format_quant_summary
        spy_price = 0
        if bundle.us_indices:
            spy_price = bundle.us_indices[0].price or 0
        bundle.quant_signals = format_quant_summary(spy_price)
    except Exception as e:
        logger.warning(f"Quant signals failed: {e}")

    return bundle
