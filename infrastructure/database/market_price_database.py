"""
市場価格データベース読み込みモジュール

ローカルデータベースから価格データを効率的に取得します。
カスタムFCO分析用に最適化されています。
"""

import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# デフォルトのデータベースパス
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "results" / "fco_analysis_results.db"


def get_prices_from_db(
    symbol: str,
    period_days: int,
    end_date: str,
    use_log_scale: bool = True,
    db_path: Optional[str] = None
) -> Optional[np.ndarray]:
    """
    ローカルデータベースから価格データを取得

    【科学的精度保証】
    - use_log_scale=True: ログスケール最適化（Phase Bで実装済み）
    - prepare_normalized_data_from_log_prices()と完全連携
    - np.log()の重複実行を回避（5-10%高速化）

    Args:
        symbol: 銘柄名
        period_days: 期間（日数）
        end_date: 終了日 (YYYY-MM-DD)
        use_log_scale: ログスケールデータを返すか（デフォルト: True）
        db_path: データベースパス（省略時はデフォルト）

    Returns:
        prices: 価格データ
            - use_log_scale=True: log_close（対数変換済み）
            - use_log_scale=False: close（生データ）
            - データが存在しない場合: None

    【使用例】
    ```python
    # カスタムFCO分析用（ログスケール最適化）
    log_prices = get_prices_from_db('SP500', 365, '2025-10-12', use_log_scale=True)

    # 準備関数に渡す（np.log()スキップ）
    from core.fitting.lppl_utils import prepare_normalized_data_from_log_prices
    t, log_prices_norm = prepare_normalized_data_from_log_prices(log_prices)
    ```
    """
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)

    # 期間計算
    end = datetime.strptime(end_date, '%Y-%m-%d')
    start = end - timedelta(days=period_days)

    try:
        with sqlite3.connect(db_path) as conn:
            if use_log_scale:
                # ログスケールデータを取得（最適化済み）
                query = """
                    SELECT log_close
                    FROM market_price_data
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date ASC
                """
            else:
                # 生データを取得
                query = """
                    SELECT close
                    FROM market_price_data
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date ASC
                """

            cursor = conn.execute(query, (symbol, start.strftime('%Y-%m-%d'), end_date))
            rows = cursor.fetchall()

            if len(rows) == 0:
                logger.warning(f"データなし: {symbol} ({start.strftime('%Y-%m-%d')} ~ {end_date})")
                return None

            prices = np.array([row[0] for row in rows])

            logger.info(
                f"データ取得成功: {symbol} - {len(prices)}点 "
                f"({'log_close' if use_log_scale else 'close'})"
            )

            return prices

    except Exception as e:
        logger.error(f"データベース読み込みエラー: {symbol} - {e}")
        return None


def get_prices_with_dates(
    symbol: str,
    period_days: int,
    end_date: str,
    use_log_scale: bool = True,
    db_path: Optional[str] = None
) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    ローカルデータベースから価格データと日付を取得

    Args:
        symbol: 銘柄名
        period_days: 期間（日数）
        end_date: 終了日 (YYYY-MM-DD)
        use_log_scale: ログスケールデータを返すか（デフォルト: True）
        db_path: データベースパス（省略時はデフォルト）

    Returns:
        (dates, prices): 日付配列と価格データのタプル
            - dates: datetime.date オブジェクトの配列
            - prices: 価格データ（use_log_scaleに応じてlog_closeまたはclose）
            - データが存在しない場合: None
    """
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)

    # 期間計算
    end = datetime.strptime(end_date, '%Y-%m-%d')
    start = end - timedelta(days=period_days)

    try:
        with sqlite3.connect(db_path) as conn:
            if use_log_scale:
                query = """
                    SELECT date, log_close
                    FROM market_price_data
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date ASC
                """
            else:
                query = """
                    SELECT date, close
                    FROM market_price_data
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date ASC
                """

            cursor = conn.execute(query, (symbol, start.strftime('%Y-%m-%d'), end_date))
            rows = cursor.fetchall()

            if len(rows) == 0:
                logger.warning(f"データなし: {symbol} ({start.strftime('%Y-%m-%d')} ~ {end_date})")
                return None

            dates = np.array([datetime.strptime(row[0], '%Y-%m-%d').date() for row in rows])
            prices = np.array([row[1] for row in rows])

            logger.info(
                f"データ取得成功: {symbol} - {len(prices)}点 "
                f"({'log_close' if use_log_scale else 'close'})"
            )

            return dates, prices

    except Exception as e:
        logger.error(f"データベース読み込みエラー: {symbol} - {e}")
        return None


def check_data_availability(
    symbol: str,
    period_days: int,
    end_date: str,
    db_path: Optional[str] = None
) -> dict:
    """
    データの利用可能性を確認

    Args:
        symbol: 銘柄名
        period_days: 期間（日数）
        end_date: 終了日 (YYYY-MM-DD)
        db_path: データベースパス（省略時はデフォルト）

    Returns:
        availability: データ利用可能性情報
            - available: データが利用可能か (bool)
            - data_points: データポイント数 (int)
            - coverage: データカバレッジ率 (float, 0-1)
            - start_date: 実際の開始日 (str)
            - end_date: 実際の終了日 (str)
    """
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)

    # 期間計算
    end = datetime.strptime(end_date, '%Y-%m-%d')
    start = end - timedelta(days=period_days)

    try:
        with sqlite3.connect(db_path) as conn:
            query = """
                SELECT
                    COUNT(*) as data_points,
                    MIN(date) as start_date,
                    MAX(date) as end_date
                FROM market_price_data
                WHERE symbol = ? AND date BETWEEN ? AND ?
            """

            cursor = conn.execute(query, (symbol, start.strftime('%Y-%m-%d'), end_date))
            row = cursor.fetchone()

            data_points = row[0] if row else 0
            actual_start = row[1] if row and row[1] else None
            actual_end = row[2] if row and row[2] else None

            # カバレッジ率計算
            coverage = data_points / period_days if period_days > 0 else 0.0

            # 利用可能性判定（70%以上のデータがあれば利用可能）
            available = coverage >= 0.7

            return {
                'available': available,
                'data_points': data_points,
                'coverage': coverage,
                'start_date': actual_start,
                'end_date': actual_end
            }

    except Exception as e:
        logger.error(f"データ利用可能性確認エラー: {symbol} - {e}")
        return {
            'available': False,
            'data_points': 0,
            'coverage': 0.0,
            'start_date': None,
            'end_date': None
        }
