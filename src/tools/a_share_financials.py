"""
A股财务数据读取 - 从本地数据库
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 财务数据库路径
FINANCIALS_DB_PATH = Path(__file__).parent.parent.parent / "data" / "a_share_financials.db"


def get_financial_metrics_from_db(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    db_path: Optional[str] = None
) -> list:
    """
    从本地数据库获取A股财务指标
    """
    from src.data.models import FinancialMetrics
    
    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    db = Path(db_path) if db_path else FINANCIALS_DB_PATH
    
    if not db.exists():
        logger.warning(f"Financials DB not found: {db}")
        return []
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        
        # 查询财务指标
        query = """
            SELECT ticker, report_period, net_margin, gross_margin, roe,
                   debt_to_assets, current_ratio, quick_ratio, eps, bvps,
                   revenue_growth, net_profit_growth, inventory_turnover,
                   receivable_turnover_days, operating_cycle
            FROM financial_metrics
            WHERE ticker = ?
            ORDER BY report_period DESC
            LIMIT ?
        """
        
        cursor.execute(query, (clean_ticker, limit))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning(f"No financial data for {ticker}")
            return []
        
        metrics_list = []
        for row in rows:
            (ticker_code, report_period, net_margin, gross_margin, roe,
             debt_to_assets, current_ratio, quick_ratio, eps, bvps,
             revenue_growth, net_profit_growth, inventory_turnover,
             receivable_turnover_days, operating_cycle) = row
            
            # 构建FinancialMetrics对象
            metrics = FinancialMetrics(
                ticker=ticker,
                report_period=report_period,
                period="Q4",  # 默认
                currency="CNY",
                market_cap=None,
                enterprise_value=None,
                price_to_earnings_ratio=None,
                price_to_book_ratio=None,
                price_to_sales_ratio=None,
                enterprise_value_to_ebitda_ratio=None,
                enterprise_value_to_revenue_ratio=None,
                free_cash_flow_yield=None,
                peg_ratio=None,
                gross_margin=gross_margin,
                operating_margin=net_margin,
                net_margin=net_margin,
                return_on_equity=roe,
                return_on_assets=None,
                return_on_invested_capital=None,
                asset_turnover=None,
                inventory_turnover=inventory_turnover,
                receivables_turnover=None,
                days_sales_outstanding=receivable_turnover_days,
                operating_cycle=operating_cycle,
                working_capital_turnover=None,
                current_ratio=current_ratio,
                quick_ratio=quick_ratio,
                cash_ratio=None,
                operating_cash_flow_ratio=None,
                debt_to_equity=debt_to_assets,
                debt_to_assets=debt_to_assets,
                interest_coverage=None,
                revenue_growth=revenue_growth,
                earnings_growth=net_profit_growth,
                book_value_growth=None,
                earnings_per_share_growth=None,
                free_cash_flow_growth=None,
                operating_income_growth=None,
                ebitda_growth=None,
                payout_ratio=None,
                earnings_per_share=eps,
                book_value_per_share=bvps,
                free_cash_flow_per_share=None,
            )
            metrics_list.append(metrics)
        
        logger.info(f"Loaded {len(metrics_list)} financial records for {ticker}")
        return metrics_list
        
    except Exception as e:
        logger.error(f"Error loading financials for {ticker}: {e}")
        return []
