"""
Price Data Service for managing market price data
"""

import sqlite3
import json
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timedelta
import pandas as pd
from pathlib import Path


class PriceDataService:
    """Service for managing price data in local database"""

    def __init__(self, db_path: str = None):
        """Initialize price data service"""
        if db_path is None:
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent.parent.parent
            db_path = project_root / "results" / "fco_analysis_results.db"
        self.db_path = str(db_path)

    def save_price_data(
        self,
        symbol: str,
        dates: List[date],
        prices: List[float],
        data_source: str = "synthetic",
        volumes: Optional[List[float]] = None
    ) -> bool:
        """
        Save price data to local database

        Args:
            symbol: Stock symbol
            dates: List of dates
            prices: List of closing prices
            data_source: Data source identifier
            volumes: Optional list of volumes

        Returns:
            Success status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for i, (dt, price) in enumerate(zip(dates, prices)):
                    volume = volumes[i] if volumes else None
                    log_close = np.log(price) if price > 0 else None

                    cursor.execute("""
                        INSERT OR REPLACE INTO market_price_data
                        (symbol, date, close, log_close, volume, data_source, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (symbol, dt, price, log_close, volume, data_source))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error saving price data: {e}")
            return False

    def get_price_data(
        self,
        symbol: str,
        end_date: date,
        days: int = 365
    ) -> Optional[Dict[str, Any]]:
        """
        Get price data from local database

        Args:
            symbol: Stock symbol
            end_date: End date for data
            days: Number of days to retrieve

        Returns:
            Dictionary with dates, prices, and log_prices
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Calculate start date
                start_date = end_date - timedelta(days=days)

                df = pd.read_sql_query("""
                    SELECT date, close, log_close
                    FROM market_price_data
                    WHERE symbol = ? AND date >= ? AND date <= ?
                    ORDER BY date ASC
                """, conn, params=(symbol, start_date, end_date))

                if df.empty:
                    return None

                return {
                    'dates': df['date'].tolist(),
                    'prices': df['close'].tolist(),
                    'log_prices': df['log_close'].tolist()
                }

        except Exception as e:
            print(f"Error getting price data: {e}")
            return None

    def save_lppl_fit(
        self,
        analysis_id: int,
        symbol: str,
        params: Dict[str, float],
        fitted_values: List[float],
        dates: List[str],
        fit_start: date,
        fit_end: date
    ) -> bool:
        """
        Save LPPL fit results to database

        Args:
            analysis_id: Analysis ID
            symbol: Stock symbol
            params: LPPL parameters
            fitted_values: Fitted LPPL values
            dates: Corresponding dates
            fit_start: Fit start date
            fit_end: Fit end date

        Returns:
            Success status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO lppl_fitted_curves
                    (analysis_id, symbol, fit_start_date, fit_end_date,
                     num_points, tc, m, omega, phi, a, b, c,
                     r_squared, rmse, damping,
                     fitted_values, dates)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id, symbol, fit_start, fit_end,
                    len(fitted_values),
                    params.get('tc'), params.get('m'),
                    params.get('omega'), params.get('phi'),
                    params.get('a'), params.get('b'), params.get('c'),
                    params.get('r_squared'), params.get('rmse'),
                    params.get('damping'),
                    json.dumps(fitted_values),
                    json.dumps(dates)
                ))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error saving LPPL fit: {e}")
            return False

    def get_lppl_fit(
        self,
        analysis_id: int,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get LPPL fit from database

        Args:
            analysis_id: Analysis ID
            symbol: Stock symbol

        Returns:
            Dictionary with LPPL fit data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM lppl_fitted_curves
                    WHERE analysis_id = ? AND symbol = ?
                """, (analysis_id, symbol))

                columns = [description[0] for description in cursor.description]
                row = cursor.fetchone()

                if row:
                    result = dict(zip(columns, row))
                    # Parse JSON fields
                    result['fitted_values'] = json.loads(result['fitted_values'])
                    result['dates'] = json.loads(result['dates'])
                    return result

                return None

        except Exception as e:
            print(f"Error getting LPPL fit: {e}")
            return None

    def check_data_availability(
        self,
        symbol: str,
        end_date: date,
        required_days: int = 365
    ) -> Dict[str, Any]:
        """
        Check data availability for a symbol

        Args:
            symbol: Stock symbol
            end_date: End date
            required_days: Required number of days

        Returns:
            Dict with availability info
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as count,
                           MIN(date) as min_date,
                           MAX(date) as max_date
                    FROM market_price_data
                    WHERE symbol = ? AND date <= ?
                """, (symbol, end_date))

                row = cursor.fetchone()

                return {
                    'available': row[0] >= required_days,
                    'count': row[0],
                    'min_date': row[1],
                    'max_date': row[2],
                    'required': required_days
                }

        except Exception as e:
            print(f"Error checking data availability: {e}")
            return {
                'available': False,
                'count': 0,
                'error': str(e)
            }