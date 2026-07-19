#!/usr/bin/env python3
"""
S&P500 估值快速查询器

用法:
    python check_valuation.py              # 查询全部指标
    python check_valuation.py --json       # JSON格式输出
    python check_valuation.py --brief      # 简洁模式，只看结论
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

# ── 估值区间定义 ──────────────────────────────────────────
VALUATION_BANDS = {
    "pe":       {"cheap": 18, "fair": 22, "expensive": 27},
    "vix_fear": {"cheap": 30, "fair": 25, "expensive": 15},  # 反向：越高越恐慌=越便宜
    "pos_52w":  {"cheap": 30, "fair": 50, "expensive": 80},
    "tnx":      {"cheap": 2.5, "fair": 3.5, "expensive": 4.5},
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
        return "❓", "数据不足"

    cheap_count = signals.count("cheap")
    expensive_count = signals.count("expensive")

    if cheap_count >= 3:
        return "🟢", "强烈买入信号"
    elif cheap_count >= 2:
        return "🟢", "可以分批买入"
    elif expensive_count >= 3:
        return "🔴", "不建议买入"
    elif expensive_count >= 2:
        return "🟠", "偏贵，观望"
    else:
        return "🟡", "中性，等待更明确信号"


def main():
    parser = argparse.ArgumentParser(description="S&P500估值查询器")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--brief", action="store_true", help="简洁模式")
    args = parser.parse_args()

    print("正在获取数据...")
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

    # JSON输出
    if args.json:
        result = {
            "timestamp": datetime.now().isoformat(),
            "spy_price": spy.price if spy else None,
            "pe": pe,
            "vix": vix,
            "pos_52w": round(pos, 1) if pos else None,
            "tnx_10y": tnx,
            "overall_signal": get_overall_signal(pe, vix, pos, tnx)[1],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 简洁模式
    if args.brief:
        sig, desc = get_overall_signal(pe, vix, pos, tnx)
        print(f"\n{sig} S&P500综合信号: {desc}")
        print(f"  SPY: ${spy.price:.2f} | PE: {pe:.1f} | VIX: {vix} | 52周位置: {pos:.0f}% | 10Y: {tnx}%")
        return

    # 完整输出
    print("\n" + "=" * 50)
    print("  S&P500 估值速查")
    print("=" * 50)

    if spy:
        print(f"\n  SPY价格: ${spy.price:.2f}")
        if spy.change_pct is not None:
            print(f"  今日涨跌: {spy.change_pct:+.2f}%")

    # 逐项指标
    items = [
        ("S&P500 PE", pe, VALUATION_BANDS["pe"]),
        ("VIX恐慌指数", vix, VALUATION_BANDS["vix_fear"]),
        ("52周位置(%)", round(pos, 1) if pos else None, VALUATION_BANDS["pos_52w"]),
        ("10Y国债收益率(%)", tnx, VALUATION_BANDS["tnx"]),
    ]

    print()
    for name, val, bands in items:
        icon, label = classify(val, bands)
        val_str = f"{val}" if val is not None else "N/A"
        print(f"  {icon} {name}: {val_str}  → {label}")

    # 综合判断
    sig, desc = get_overall_signal(pe, vix, pos, tnx)
    print(f"\n{'─' * 50}")
    print(f"  {sig} 综合判断: {desc}")
    print(f"{'─' * 50}")

    # 其他宏观数据
    print()
    for k, v in bundle.macro.items():
        if k not in ("VIX恐慌指数", "10年期美债收益率"):
            print(f"  {k}: {v}")

    print(f"\n  数据时间: {bundle.timestamp}")
    print("=" * 50)


if __name__ == "__main__":
    main()
