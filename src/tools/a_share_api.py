"""
A股数据适配层 - 从本地SQLite数据库读取A股数据
替换原来的 financialdatasets.ai API
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = Path("/root/a-share-quant-sim/data/quant_stocks.db")


def get_prices_from_db(
    ticker: str,
    start_date: str,
    end_date: str,
    db_path: Optional[str] = None
) -> list:
    """
    从本地SQLite数据库获取A股价格数据
    
    Args:
        ticker: 股票代码（如 '600519' 或 '600519.SH'）
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        db_path: 数据库路径（可选）
    
    Returns:
        list: Price对象列表
    """
    # 导入Price模型
    from src.data.models import Price
    
    # 处理股票代码格式
    # 移除后缀（.SH, .SZ等）
    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    
    # 确定数据库路径
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    
    if not db.exists():
        logger.warning(f"Database not found: {db}")
        return []
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        
        # 查询日K线数据
        # 表结构：daily_kline (code, date, open, high, low, close, volume, amount)
        query = """
            SELECT date, open, high, low, close, volume, amount
            FROM daily_kline
            WHERE code = ?
            AND date >= ?
            AND date <= ?
            ORDER BY date ASC
        """
        
        cursor.execute(query, (clean_ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning(f"No data found for {ticker} between {start_date} and {end_date}")
            return []
        
        # 转换为Price对象列表
        prices = []
        for row in rows:
            date_val, open_price, high, low, close, volume, amount = row
            
            # 格式化日期为 'YYYY-MM-DD'
            if isinstance(date_val, str):
                date_str = date_val
            else:
                date_str = str(date_val)
            
            # 确保日期格式正确
            if len(date_str) == 8:  # YYYYMMDD格式
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            
            price = Price(
                open=float(open_price),
                close=float(close),
                high=float(high),
                low=float(low),
                volume=int(volume),
                time=date_str
            )
            prices.append(price)
        
        logger.info(f"Loaded {len(prices)} prices for {ticker} from local DB")
        return prices
        
    except Exception as e:
        logger.error(f"Error loading prices from DB for {ticker}: {e}")
        return []


def get_financial_metrics_from_db(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    db_path: Optional[str] = None
) -> list:
    """
    从本地数据库获取财务指标（简化版）
    由于我们的数据库可能没有完整的财务数据，返回空列表或基本数据
    """
    # A股量化策略通常不依赖基本面数据
    # 返回空列表，让Agent使用技术面和情绪面分析
    logger.info(f"Financial metrics not available for A-share {ticker}, using technical analysis only")
    return []


def search_line_items_from_db(
    ticker: str,
    line_items: list,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    db_path: Optional[str] = None
) -> list:
    """
    搜索财务项目（简化版）
    """
    return []


def get_insider_trades_from_db(
    ticker: str,
    end_date: str,
    db_path: Optional[str] = None
) -> list:
    """
    从本地数据库获取内部交易数据
    """
    from src.data.models import InsiderTrade
    
    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    
    if not db.exists():
        return []
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        
        # 检查insider_trades表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='insider_trades'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return []
        
        # 查询内部交易
        query = """
            SELECT stock_code, holder_name, trade_date, trade_volume, trade_price
            FROM insider_trades
            WHERE stock_code = ?
            AND trade_date <= ?
            ORDER BY trade_date DESC
            LIMIT ?
        """
        
        cursor.execute(query, (clean_ticker, end_date, limit))
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            code, holder, date, volume, price = row
            
            # 格式化日期
            if isinstance(date, str) and len(date) == 8:
                date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            
            trade = InsiderTrade(
                ticker=ticker,
                issuer=code,
                name=holder,
                title="",
                is_board_director=False,
                transaction_date=date,
                transaction_shares=float(volume) if volume else None,
                transaction_price_per_share=float(price) if price else None,
                transaction_value=float(volume * price) if volume and price else None,
                shares_owned_before_transaction=None,
                shares_owned_after_transaction=None,
                security_title="",
                filing_date=date or end_date
            )
            trades.append(trade)
        
        return trades
        
    except Exception as e:
        logger.error(f"Error loading insider trades for {ticker}: {e}")
        return []


def get_company_news_from_db(
    ticker: str,
    end_date: str,
    db_path: Optional[str] = None
) -> list:
    """
    获取公司新闻（简化版）
    A股新闻需要从其他来源获取
    """
    return []


def get_company_facts_from_db(
    ticker: str,
    db_path: Optional[str] = None
) -> dict:
    """
    获取公司基本信息
    """
    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    
    if not db.exists():
        return {}
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        
        # 从stock_pool获取基本信息
        query = """
            SELECT code, name, industry
            FROM stock_pool
            WHERE code = ?
        """
        
        cursor.execute(query, (clean_ticker,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "ticker": ticker,
                "name": row[1],
                "industry": row[2],
                "sector": "",
                "exchange": "SH" if clean_ticker.startswith("6") else "SZ"
            }
        
        return {}
        
    except Exception as e:
        logger.error(f"Error loading company facts for {ticker}: {e}")
        return {}


def get_stock_pool(db_path: Optional[str] = None) -> List[str]:
    """
    获取股票池（zz1800成分股）
    """
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    
    if not db.exists():
        return []
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        
        query = "SELECT code FROM stock_pool ORDER BY code"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
        
    except Exception as e:
        logger.error(f"Error loading stock pool: {e}")
        return []


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
    try:
        from src.tools.a_share_financials import get_financial_metrics_from_db as _get_financials
        return _get_financials(ticker, end_date, period, limit, db_path)
    except Exception as e:
        logger.warning(f"Failed to load financials for {ticker}: {e}")
        return []
