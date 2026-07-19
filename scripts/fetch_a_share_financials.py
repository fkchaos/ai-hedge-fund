#!/usr/bin/env python3
"""
获取A股财务数据 - 使用akshare stock_financial_abstract_ths
"""
import sqlite3
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "a_share_financials.db"

# 需要分析的股票
HOLDINGS = [
    ("000498", "山东路桥"),
    ("003039", "顺控发展"),
    ("301215", "中汽股份"),
    ("301327", "华宝新能"),
    ("301339", "通行宝"),
    ("600639", "浦东金桥"),
    ("603043", "广州酒家"),
    ("603376", "大明电子"),
    ("603406", "天富龙"),
]


def init_db():
    """初始化数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS financial_metrics (
            ticker TEXT,
            name TEXT,
            report_period TEXT,
            net_profit REAL,
            net_profit_growth REAL,
            revenue REAL,
            revenue_growth REAL,
            eps REAL,
            bvps REAL,
            capital_reserve_per_share REAL,
            undistributed_profit_per_share REAL,
            operating_cash_flow_per_share REAL,
            net_margin REAL,
            gross_margin REAL,
            roe REAL,
            roe_diluted REAL,
            operating_cycle REAL,
            inventory_turnover REAL,
            inventory_turnover_days REAL,
            receivable_turnover_days REAL,
            current_ratio REAL,
            quick_ratio REAL,
            conservative_quick_ratio REAL,
            equity_ratio REAL,
            debt_to_assets REAL,
            updated_at TEXT,
            PRIMARY KEY (ticker, report_period)
        )
    """)
    conn.commit()
    return conn


def safe_float(val):
    """安全转换为float，处理亿/万单位"""
    if val is None or val == '' or val == '--' or val == 'False' or val is False:
        return None
    try:
        if isinstance(val, str):
            val = val.strip()
            if '亿' in val:
                val = float(val.replace('亿', '')) * 100000000
            elif '万' in val:
                val = float(val.replace('万', '')) * 10000
            elif '%' in val:
                val = float(val.replace('%', ''))
            else:
                val = float(val)
        return float(val)
    except:
        return None


def fetch_and_store():
    """获取并存储财务数据"""
    print("=" * 60)
    print("获取A股财务数据 (akshare)")
    print("=" * 60)
    
    conn = init_db()
    
    for ticker, name in HOLDINGS:
        print(f"\n处理 {ticker} {name}...")
        
        try:
            df = ak.stock_financial_abstract_ths(symbol=ticker)
            if df.empty:
                print(f"  跳过（无数据）")
                continue
            
            print(f"  获取到 {len(df)} 条记录")
            
            # 取最近8个季度
            for _, row in df.tail(8).iterrows():
                report_period = str(row.get('报告期', ''))
                if not report_period:
                    continue
                
                metrics = {
                    'ticker': ticker,
                    'name': name,
                    'report_period': report_period,
                    'net_profit': safe_float(row.get('净利润')),
                    'net_profit_growth': safe_float(row.get('净利润同比增长率')),
                    'revenue': safe_float(row.get('营业总收入')),
                    'revenue_growth': safe_float(row.get('营业总收入同比增长率')),
                    'eps': safe_float(row.get('基本每股收益')),
                    'bvps': safe_float(row.get('每股净资产')),
                    'capital_reserve_per_share': safe_float(row.get('每股资本公积金')),
                    'undistributed_profit_per_share': safe_float(row.get('每股未分配利润')),
                    'operating_cash_flow_per_share': safe_float(row.get('每股经营现金流')),
                    'net_margin': safe_float(row.get('销售净利率')),
                    'gross_margin': safe_float(row.get('销售毛利率')),
                    'roe': safe_float(row.get('净资产收益率')),
                    'roe_diluted': safe_float(row.get('净资产收益率-摊薄')),
                    'operating_cycle': safe_float(row.get('营业周期')),
                    'inventory_turnover': safe_float(row.get('存货周转率')),
                    'inventory_turnover_days': safe_float(row.get('存货周转天数')),
                    'receivable_turnover_days': safe_float(row.get('应收账款周转天数')),
                    'current_ratio': safe_float(row.get('流动比率')),
                    'quick_ratio': safe_float(row.get('速动比率')),
                    'conservative_quick_ratio': safe_float(row.get('保守速动比率')),
                    'equity_ratio': safe_float(row.get('产权比率')),
                    'debt_to_assets': safe_float(row.get('资产负债率')),
                    'updated_at': datetime.now().isoformat(),
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO financial_metrics 
                    (ticker, name, report_period, net_profit, net_profit_growth,
                     revenue, revenue_growth, eps, bvps, capital_reserve_per_share,
                     undistributed_profit_per_share, operating_cash_flow_per_share,
                     net_margin, gross_margin, roe, roe_diluted, operating_cycle,
                     inventory_turnover, inventory_turnover_days, receivable_turnover_days,
                     current_ratio, quick_ratio, conservative_quick_ratio, equity_ratio,
                     debt_to_assets, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, tuple(metrics.values()))
            
            conn.commit()
            print(f"  存储成功")
            
        except Exception as e:
            print(f"  失败: {e}")
    
    # 统计
    cursor = conn.execute("SELECT COUNT(DISTINCT ticker) FROM financial_metrics")
    count = cursor.fetchone()[0]
    print(f"\n{'='*60}")
    print(f"完成！共存储 {count} 只股票的财务数据")
    print(f"数据库: {DB_PATH}")
    
    conn.close()


if __name__ == "__main__":
    fetch_and_store()
