"""
Enhanced Price Data Service with Incremental Updates
差分更新機能を持つ改善版価格データサービス
"""

import sqlite3
import json
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from datetime import date, datetime, timedelta
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PriceDataServiceEnhanced:
    """Enhanced service for managing price data with incremental updates"""

    def __init__(self, db_path: str = None):
        """Initialize enhanced price data service"""
        if db_path is None:
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent.parent.parent
            db_path = project_root / "results" / "fco_analysis_results.db"
        self.db_path = str(db_path)
        logger.info(f"PriceDataServiceEnhanced initialized with DB: {self.db_path}")

    def get_missing_date_ranges(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[Tuple[date, date]]:
        """
        特定の期間で欠損している日付範囲を特定

        Args:
            symbol: シンボル
            start_date: 開始日
            end_date: 終了日

        Returns:
            欠損している日付範囲のリスト [(start1, end1), (start2, end2), ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 既存データの日付を取得
                df = pd.read_sql_query("""
                    SELECT DISTINCT date
                    FROM market_price_data
                    WHERE symbol = ? AND date >= ? AND date <= ?
                    ORDER BY date ASC
                """, conn, params=(symbol, start_date, end_date))

                if df.empty:
                    # データが全くない場合は全期間が欠損
                    return [(start_date, end_date)]

                # 既存の日付セット
                existing_dates = set(pd.to_datetime(df['date']).dt.date)

                # 必要な全ての営業日を生成（週末を除く）
                all_dates = pd.bdate_range(start=start_date, end=end_date).date

                # 欠損している日付を特定
                missing_dates = sorted([d for d in all_dates if d not in existing_dates])

                if not missing_dates:
                    return []

                # 連続する欠損期間をグループ化
                ranges = []
                range_start = missing_dates[0]
                prev_date = missing_dates[0]

                for current_date in missing_dates[1:]:
                    # 営業日ベースで5日以上離れていたら新しい範囲
                    if (current_date - prev_date).days > 5:
                        ranges.append((range_start, prev_date))
                        range_start = current_date
                    prev_date = current_date

                # 最後の範囲を追加
                ranges.append((range_start, prev_date))

                logger.info(f"Found {len(ranges)} missing date ranges for {symbol}")
                return ranges

        except Exception as e:
            logger.error(f"Error identifying missing date ranges: {e}")
            return [(start_date, end_date)]  # エラー時は全期間を返す

    def save_incremental_data(
        self,
        symbol: str,
        dates: List[date],
        prices: List[float],
        data_source: str = "external_api",
        volumes: Optional[List[float]] = None,
        overwrite: bool = False
    ) -> int:
        """
        差分データの保存（重複を避けて効率的に保存）

        Args:
            symbol: シンボル
            dates: 日付リスト
            prices: 価格リスト
            data_source: データソース
            volumes: 出来高リスト（オプション）
            overwrite: 既存データを上書きするか

        Returns:
            保存された新規レコード数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 既存データの日付を取得（上書きしない場合）
                existing_dates = set()
                if not overwrite:
                    result = cursor.execute("""
                        SELECT DISTINCT date
                        FROM market_price_data
                        WHERE symbol = ?
                    """, (symbol,))
                    existing_dates = {row[0] for row in result.fetchall()}

                # 新規または更新するデータのみ保存
                saved_count = 0
                for i, (dt, price) in enumerate(zip(dates, prices)):
                    # 日付の形式を統一
                    if isinstance(dt, str):
                        dt = pd.to_datetime(dt).date()
                    elif hasattr(dt, 'date'):
                        dt = dt.date()

                    # 既存データがあり、上書きしない場合はスキップ
                    if not overwrite and str(dt) in existing_dates:
                        continue

                    volume = volumes[i] if volumes else None
                    log_close = np.log(price) if price > 0 else None

                    cursor.execute("""
                        INSERT OR REPLACE INTO market_price_data
                        (symbol, date, close, log_close, volume, data_source, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (symbol, str(dt), price, log_close, volume, data_source))

                    saved_count += 1

                conn.commit()
                logger.info(f"Saved {saved_count} new records for {symbol}")
                return saved_count

        except Exception as e:
            logger.error(f"Error saving incremental data: {e}")
            return 0

    def get_data_with_fill(
        self,
        symbol: str,
        end_date: date,
        days: int = 365,
        fill_method: str = 'forward'
    ) -> Optional[Dict[str, Any]]:
        """
        データ取得（欠損値を補完）

        Args:
            symbol: シンボル
            end_date: 終了日
            days: 取得日数
            fill_method: 補完方法 ('forward', 'interpolate', 'none')

        Returns:
            補完されたデータ
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                start_date = end_date - timedelta(days=days)

                df = pd.read_sql_query("""
                    SELECT date, close, log_close, volume
                    FROM market_price_data
                    WHERE symbol = ? AND date >= ? AND date <= ?
                    ORDER BY date ASC
                """, conn, params=(symbol, start_date, end_date))

                if df.empty:
                    return None

                # 日付インデックスを作成
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)

                # 営業日ベースで再インデックス
                business_days = pd.bdate_range(start=start_date, end=end_date)
                df = df.reindex(business_days)

                # 欠損値の補完
                if fill_method == 'forward':
                    df.fillna(method='ffill', inplace=True)
                elif fill_method == 'interpolate':
                    df['close'].interpolate(method='linear', inplace=True)
                    df['log_close'] = np.log(df['close'])
                    df['volume'].fillna(method='ffill', inplace=True)

                # NaNが残っている行を削除
                df.dropna(subset=['close'], inplace=True)

                if df.empty:
                    return None

                return {
                    'dates': df.index.date.tolist(),
                    'prices': df['close'].tolist(),
                    'log_prices': df['log_close'].tolist(),
                    'volumes': df['volume'].tolist() if 'volume' in df else None,
                    'data_points': len(df),
                    'fill_method': fill_method
                }

        except Exception as e:
            logger.error(f"Error getting data with fill: {e}")
            return None

    def get_data_statistics(
        self,
        symbol: str,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        データの統計情報を取得

        Args:
            symbol: シンボル
            end_date: 基準日（Noneの場合は最新）

        Returns:
            統計情報
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 基準日の設定
                if end_date is None:
                    end_date = datetime.now().date()

                # 全体の統計
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_records,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        MIN(close) as min_price,
                        MAX(close) as max_price,
                        AVG(close) as avg_price,
                        COUNT(DISTINCT data_source) as num_sources
                    FROM market_price_data
                    WHERE symbol = ? AND date <= ?
                """, (symbol, end_date))

                stats = cursor.fetchone()

                if stats[0] == 0:  # No records
                    return {
                        'symbol': symbol,
                        'has_data': False,
                        'total_records': 0
                    }

                # データソース別の統計
                source_stats = pd.read_sql_query("""
                    SELECT
                        data_source,
                        COUNT(*) as record_count,
                        MIN(date) as first_date,
                        MAX(date) as last_date
                    FROM market_price_data
                    WHERE symbol = ? AND date <= ?
                    GROUP BY data_source
                """, conn, params=(symbol, end_date))

                return {
                    'symbol': symbol,
                    'has_data': True,
                    'total_records': stats[0],
                    'date_range': {
                        'start': stats[1],
                        'end': stats[2]
                    },
                    'price_range': {
                        'min': stats[3],
                        'max': stats[4],
                        'avg': stats[5]
                    },
                    'data_sources': source_stats.to_dict('records'),
                    'coverage_days': (pd.to_datetime(stats[2]) - pd.to_datetime(stats[1])).days + 1,
                    'completeness': stats[0] / ((pd.to_datetime(stats[2]) - pd.to_datetime(stats[1])).days + 1)
                }

        except Exception as e:
            logger.error(f"Error getting data statistics: {e}")
            return {
                'symbol': symbol,
                'has_data': False,
                'error': str(e)
            }

    def clean_duplicate_data(
        self,
        symbol: str,
        prefer_source: str = 'external_api'
    ) -> int:
        """
        重複データをクリーンアップ

        Args:
            symbol: シンボル
            prefer_source: 優先するデータソース

        Returns:
            削除されたレコード数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 重複する日付を特定
                duplicates = cursor.execute("""
                    SELECT date, COUNT(*) as cnt
                    FROM market_price_data
                    WHERE symbol = ?
                    GROUP BY date
                    HAVING cnt > 1
                """, (symbol,)).fetchall()

                if not duplicates:
                    logger.info(f"No duplicate data found for {symbol}")
                    return 0

                deleted_count = 0
                for dup_date, _ in duplicates:
                    # 優先データソースのレコードを保持
                    cursor.execute("""
                        DELETE FROM market_price_data
                        WHERE symbol = ? AND date = ?
                        AND rowid NOT IN (
                            SELECT rowid
                            FROM market_price_data
                            WHERE symbol = ? AND date = ?
                            ORDER BY
                                CASE WHEN data_source = ? THEN 0 ELSE 1 END,
                                updated_at DESC
                            LIMIT 1
                        )
                    """, (symbol, dup_date, symbol, dup_date, prefer_source))

                    deleted_count += cursor.rowcount

                conn.commit()
                logger.info(f"Cleaned {deleted_count} duplicate records for {symbol}")
                return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning duplicate data: {e}")
            return 0

    # 既存のメソッドも保持（後方互換性）
    def save_price_data(self, symbol, dates, prices, data_source="synthetic", volumes=None):
        """既存の save_price_data メソッド（後方互換性）"""
        return self.save_incremental_data(symbol, dates, prices, data_source, volumes, overwrite=True) > 0

    def get_price_data(self, symbol, end_date, days=365):
        """既存の get_price_data メソッド（後方互換性）"""
        return self.get_data_with_fill(symbol, end_date, days, fill_method='none')