"""量化预计算模块 — 用Python精确计算技术指标，喂给LLM解释

核心理念：不让LLM猜技术指标，而是用pandas精确计算后作为结构化数据喂给它。

计算指标：
- 均线系统：MA5/20/50/200，均线排列，价格相对位置
- 动量指标：RSI(14)，MACD(12,26,9)
- 波动率：布林带(20,2)，ATR(14)
- 成交量：OBV趋势，量价关系
- 趋势强度：ADX(14)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TechSignals:
    """技术指标计算结果"""
    # 均线
    ma5: float = 0.0
    ma20: float = 0.0
    ma50: float = 0.0
    ma200: float = 0.0
    price_vs_ma200: str = ""  # "上方X%" / "下方X%"
    ma_alignment: str = ""    # "多头排列" / "空头排列" / "缠绕"

    # 动量
    rsi_14: float = 50.0
    rsi_signal: str = ""      # "超买" / "超卖" / "中性"
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    macd_trend: str = ""      # "金叉" / "死叉" / "零轴上方" / "零轴下方"

    # 波动率
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_position: str = ""     # "上轨附近" / "下轨附近" / "中轨附近"
    atr_14: float = 0.0
    atr_pct: float = 0.0     # ATR占价格百分比

    # 成交量
    vol_ma20: float = 0.0
    vol_ratio: float = 1.0   # 今日量/20日均量
    vol_signal: str = ""      # "放量" / "缩量" / "正常"

    # 趋势
    adx_14: float = 0.0
    trend_strength: str = ""  # "强趋势" / "弱趋势" / "震荡"

    # 综合
    technical_score: str = ""  # "偏多" / "偏空" / "中性"
    key_levels: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        """格式化为LLM可读文本"""
        lines = []
        lines.append("═══ 技术指标（Python精确计算）═══")

        # 均线
        lines.append("")
        lines.append("📊 均线系统:")
        lines.append(f"  MA5={self.ma5:.2f} | MA20={self.ma20:.2f} | MA50={self.ma50:.2f} | MA200={self.ma200:.2f}")
        lines.append(f"  价格vs MA200: {self.price_vs_ma200}")
        lines.append(f"  均线排列: {self.ma_alignment}")

        # 动量
        lines.append("")
        lines.append("📈 动量指标:")
        lines.append(f"  RSI(14): {self.rsi_14:.1f} → {self.rsi_signal}")
        lines.append(f"  MACD: {self.macd:.3f} | Signal: {self.macd_signal:.3f} | Hist: {self.macd_hist:.3f}")
        lines.append(f"  MACD趋势: {self.macd_trend}")

        # 波动率
        lines.append("")
        lines.append("📉 波动率:")
        lines.append(f"  布林带: 上轨={self.bb_upper:.2f} | 中轨={self.bb_middle:.2f} | 下轨={self.bb_lower:.2f}")
        lines.append(f"  价格在布林带位置: {self.bb_position}")
        lines.append(f"  ATR(14): {self.atr_14:.2f} ({self.atr_pct:.1f}%)")

        # 成交量
        lines.append("")
        lines.append("📊 成交量:")
        lines.append(f"  20日均量: {self.vol_ma20/1e6:.1f}M | 量比: {self.vol_ratio:.2f}")
        lines.append(f"  量能信号: {self.vol_signal}")

        # 趋势
        lines.append("")
        lines.append("📐 趋势强度:")
        lines.append(f"  ADX(14): {self.adx_14:.1f} → {self.trend_strength}")

        # 综合
        lines.append("")
        lines.append(f"🎯 技术综合判断: {self.technical_score}")

        if self.key_levels:
            lines.append("")
            lines.append("🔑 关键价位:")
            for lvl in self.key_levels:
                lines.append(f"  • {lvl}")

        return "\n".join(lines)


def calculate_tech_signals(spy_price: float = 0.0) -> TechSignals:
    """用yfinance拉取SPY历史数据，计算全部技术指标

    Args:
        spy_price: 当前SPY价格（用于计算相对位置）
    """
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import warnings
    warnings.filterwarnings("ignore")

    signals = TechSignals()

    try:
        # 拉取1年历史数据（足够算MA200）
        hist = yf.download("SPY", period="1y", progress=False)
        if hist is None or len(hist) < 50:
            logger.warning("Insufficient SPY history for tech signals")
            return signals

        # 处理MultiIndex columns（yfinance有时返回MultiIndex）
        if hasattr(hist.columns, 'levels') and len(hist.columns.levels) > 1:
            hist.columns = hist.columns.get_level_values(0)

        close = hist["Close"].squeeze()
        high = hist["High"].squeeze()
        low = hist["Low"].squeeze()
        volume = hist["Volume"].squeeze()

        if spy_price <= 0:
            spy_price = float(close.iloc[-1])

        # ── 均线 ──────────────────────────────────────────────
        signals.ma5 = float(close.rolling(5).mean().iloc[-1])
        signals.ma20 = float(close.rolling(20).mean().iloc[-1])
        signals.ma50 = float(close.rolling(50).mean().iloc[-1])
        signals.ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else signals.ma50

        # 价格vs MA200
        pct_vs_200 = (spy_price - signals.ma200) / signals.ma200 * 100
        if pct_vs_200 > 0:
            signals.price_vs_ma200 = f"MA200上方 {pct_vs_200:.1f}%"
        else:
            signals.price_vs_ma200 = f"MA200下方 {abs(pct_vs_200):.1f}%"

        # 均线排列
        if signals.ma5 > signals.ma20 > signals.ma50 > signals.ma200:
            signals.ma_alignment = "多头排列（MA5>MA20>MA50>MA200）"
        elif signals.ma5 < signals.ma20 < signals.ma50 < signals.ma200:
            signals.ma_alignment = "空头排列（MA5<MA20<MA50<MA200）"
        else:
            signals.ma_alignment = "均线缠绕（无明确方向）"

        # ── RSI ───────────────────────────────────────────────
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        signals.rsi_14 = float(rsi.iloc[-1])

        if signals.rsi_14 >= 70:
            signals.rsi_signal = "超买区间（≥70），短期有回调风险"
        elif signals.rsi_14 <= 30:
            signals.rsi_signal = "超卖区间（≤30），短期可能反弹"
        elif signals.rsi_14 >= 60:
            signals.rsi_signal = "偏强（60-70）"
        elif signals.rsi_14 <= 40:
            signals.rsi_signal = "偏弱（30-40）"
        else:
            signals.rsi_signal = "中性（40-60）"

        # ── MACD ──────────────────────────────────────────────
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        signals.macd = float(macd_line.iloc[-1])
        signals.macd_signal = float(signal_line.iloc[-1])
        signals.macd_hist = float(macd_hist.iloc[-1])

        # MACD趋势判断
        prev_macd = float(macd_line.iloc[-2])
        prev_signal = float(signal_line.iloc[-2])
        if prev_macd <= prev_signal and signals.macd > signals.macd_signal:
            signals.macd_trend = "金叉（MACD上穿Signal，看多信号）"
        elif prev_macd >= prev_signal and signals.macd < signals.macd_signal:
            signals.macd_trend = "死叉（MACD下穿Signal，看空信号）"
        elif signals.macd > 0 and signals.macd_signal > 0:
            signals.macd_trend = "零轴上方（中期趋势偏多）"
        elif signals.macd < 0 and signals.macd_signal < 0:
            signals.macd_trend = "零轴下方（中期趋势偏空）"
        else:
            signals.macd_trend = "交叉区域（方向不明）"

        # ── 布林带 ────────────────────────────────────────────
        signals.bb_middle = float(close.rolling(20).mean().iloc[-1])
        bb_std = float(close.rolling(20).std().iloc[-1])
        signals.bb_upper = signals.bb_middle + 2 * bb_std
        signals.bb_lower = signals.bb_middle - 2 * bb_std

        bb_range = signals.bb_upper - signals.bb_lower
        bb_pos = (spy_price - signals.bb_lower) / bb_range * 100 if bb_range > 0 else 50
        if bb_pos >= 80:
            signals.bb_position = f"上轨附近（{bb_pos:.0f}%位，接近超买）"
        elif bb_pos <= 20:
            signals.bb_position = f"下轨附近（{bb_pos:.0f}%位，接近超卖）"
        else:
            signals.bb_position = f"中轨附近（{bb_pos:.0f}%位）"

        # ── ATR ───────────────────────────────────────────────
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        signals.atr_14 = float(atr.iloc[-1])
        signals.atr_pct = signals.atr_14 / spy_price * 100

        # ── 成交量 ────────────────────────────────────────────
        signals.vol_ma20 = float(volume.rolling(20).mean().iloc[-1])
        signals.vol_ratio = float(volume.iloc[-1]) / signals.vol_ma20 if signals.vol_ma20 > 0 else 1.0

        if signals.vol_ratio >= 1.5:
            signals.vol_signal = f"明显放量（量比{signals.vol_ratio:.2f}）"
        elif signals.vol_ratio >= 1.2:
            signals.vol_signal = f"温和放量（量比{signals.vol_ratio:.2f}）"
        elif signals.vol_ratio <= 0.7:
            signals.vol_signal = f"明显缩量（量比{signals.vol_ratio:.2f}）"
        else:
            signals.vol_signal = f"正常（量比{signals.vol_ratio:.2f}）"

        # ── ADX（趋势强度）────────────────────────────────────
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        atr_14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.rolling(14).mean()
        signals.adx_14 = float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else 25.0

        if signals.adx_14 >= 40:
            signals.trend_strength = "强趋势（ADX≥40），趋势交易有效"
        elif signals.adx_14 >= 25:
            signals.trend_strength = "中等趋势（ADX 25-40）"
        else:
            signals.trend_strength = "弱趋势/震荡（ADX<25），适合区间交易"

        # ── 综合技术评分 ──────────────────────────────────────
        bullish_score = 0
        bearish_score = 0

        # 均线
        if signals.ma_alignment.startswith("多头"):
            bullish_score += 2
        elif signals.ma_alignment.startswith("空头"):
            bearish_score += 2

        # RSI
        if signals.rsi_14 < 30:
            bullish_score += 1
        elif signals.rsi_14 > 70:
            bearish_score += 1

        # MACD
        if "金叉" in signals.macd_trend or "零轴上方" in signals.macd_trend:
            bullish_score += 1
        elif "死叉" in signals.macd_trend or "零轴下方" in signals.macd_trend:
            bearish_score += 1

        # 布林带
        if bb_pos < 20:
            bullish_score += 1
        elif bb_pos > 80:
            bearish_score += 1

        # 量价
        if signals.vol_ratio > 1.2 and spy_price > close.iloc[-2]:
            bullish_score += 1  # 放量上涨
        elif signals.vol_ratio > 1.2 and spy_price < close.iloc[-2]:
            bearish_score += 1  # 放量下跌

        if bullish_score > bearish_score + 1:
            signals.technical_score = f"偏多（多头{bullish_score}分 vs 空头{bearish_score}分）"
        elif bearish_score > bullish_score + 1:
            signals.technical_score = f"偏空（空头{bearish_score}分 vs 多头{bullish_score}分）"
        else:
            signals.technical_score = f"中性（多头{bullish_score}分 vs 空头{bearish_score}分）"

        # ── 关键价位 ──────────────────────────────────────────
        signals.key_levels = [
            f"MA200支撑: {signals.ma200:.2f}",
            f"MA50支撑: {signals.ma50:.2f}",
            f"布林上轨阻力: {signals.bb_upper:.2f}",
            f"布林下轨支撑: {signals.bb_lower:.2f}",
        ]

    except Exception as e:
        logger.error(f"Tech signals calculation failed: {e}")
        import traceback
        traceback.print_exc()

    return signals


def get_index_valuation() -> dict:
    """获取指数估值指标：CAPE(席勒PE) + ERP(股权风险溢价)

    ERP = 盈利收益率(1/PE) - 10年期国债收益率
    - ERP > 4%: 股票相对债券有吸引力
    - ERP 2-4%: 中性
    - ERP < 2%: 股票相对债券偏贵
    """
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")

    result = {}

    # 获取SPY PE（用yfinance的trailingPE）
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        pe = _safe_float(info.get("trailingPE"))
        if pe:
            result["S&P500 PE(TTM)"] = f"{pe:.1f}"
            # 盈利收益率
            ey = 1 / pe * 100
            result["盈利收益率(EY)"] = f"{ey:.2f}%"
    except Exception as e:
        logger.warning(f"SPY PE fetch failed: {e}")

    # 获取10年期国债收益率
    try:
        tnx = yf.Ticker("^TNX")
        tnx_info = tnx.info
        tnx_price = _safe_float(tnx_info.get("regularMarketPrice"))
        if tnx_price:
            result["10年期国债收益率"] = f"{tnx_price:.3f}%"
    except Exception as e:
        logger.warning(f"TNX fetch failed: {e}")

    # 计算ERP
    ey_str = result.get("盈利收益率(EY)", "")
    tnx_str = result.get("10年期国债收益率", "")
    if ey_str and tnx_str:
        try:
            ey = float(ey_str.replace("%", ""))
            tnx = float(tnx_str.replace("%", ""))
            erp = ey - tnx
            result["股权风险溢价(ERP)"] = f"{erp:.2f}%"
            if erp >= 4:
                result["ERP解读"] = "股票相对债券有较强吸引力"
            elif erp >= 2:
                result["ERP解读"] = "股票相对债券吸引力中性"
            else:
                result["ERP解读"] = "股票相对债券偏贵，债券更有吸引力"
        except ValueError:
            pass

    # 尝试获取CAPE（Shiller PE）— yfinance有trailingPE但没有直接的CAPE
    # 用一个近似：如果PE > 25，可能CAPE更高
    pe_str = result.get("S&P500 PE(TTM)", "")
    if pe_str:
        try:
            pe = float(pe_str)
            # 历史平均PE约16，当前PE相对历史的偏离
            pe_vs_hist = (pe - 16) / 16 * 100
            result["PE相对历史均值"] = f"偏离{pe_vs_hist:+.0f}%（历史均值PE≈16）"
        except ValueError:
            pass

    return result


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


def format_quant_summary(spy_price: float = 0.0) -> str:
    """获取完整量化预计算摘要（技术指标+指数估值）

    返回格式化文本，直接注入到market_data中
    """
    lines = []

    # 技术指标
    tech = calculate_tech_signals(spy_price)
    lines.append(tech.to_text())

    # 指数估值
    valuation = get_index_valuation()
    if valuation:
        lines.append("")
        lines.append("═══ 指数估值（量化计算）═══")
        for k, v in valuation.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)
