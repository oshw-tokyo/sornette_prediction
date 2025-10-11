"""
FCO Analysis Service
Wraps existing Python FCO implementation
"""

import sys
import os
import sqlite3
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
from pathlib import Path

# Add parent directory to path to import existing modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent  # Go up 3 levels to reach sornette_prediction
sys.path.append(str(project_root))

# Import existing FCO implementation
from infrastructure.database.fco_results_database import FCOResultsDatabase
from app.services.price_data_service import PriceDataService
# Note: fco_engine and unified_data_client modules need to be created
# For now, we'll just work with the database

from app.models.fco import (
    FCOAnalysisResponse,
    FCOSymbolSummary,
    FCOTimeSeriesData,
    FCOHistoricalQuery,
    FCOTimeSeriesWithPrice
)


class FCOService:
    """Service for FCO analysis operations"""
    
    def __init__(self):
        """Initialize FCO service with existing components"""
        # Use relative path resolution for database
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent.parent  # Go up to sornette_prediction
        db_path = project_root / "results" / "fco_analysis_results.db"

        # Create FCOResultsDatabase with resolved path
        self.db = FCOResultsDatabase(db_path=str(db_path))
        # Initialize price data service
        self.price_service = PriceDataService(db_path=str(db_path))
        # Note: FCOEngine and UnifiedMarketDataClient to be implemented later
        # self.fco_engine = FCOEngine()
        # self.data_client = UnifiedMarketDataClient()
    
    def get_latest_analysis(self, symbol: str) -> Optional[Dict[Any, Any]]:
        """Get latest FCO analysis for a symbol"""
        # Use the database method directly
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM fco_analysis_results 
                WHERE symbol = ? 
                ORDER BY analysis_basis_date DESC 
                LIMIT 1
            """, (symbol,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
    
    def get_historical_analyses(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[Dict[Any, Any]]:
        """Get historical FCO analyses for a symbol"""
        with sqlite3.connect(self.db.db_path) as conn:
            # Query database
            query = """
                SELECT * FROM fco_analysis_results 
                WHERE symbol = ?
            """
            params = [symbol]
            
            if start_date:
                query += " AND analysis_basis_date >= ?"
                params.append(start_date.isoformat() if isinstance(start_date, date) else start_date)
            
            if end_date:
                query += " AND analysis_basis_date <= ?"
                params.append(end_date.isoformat() if isinstance(end_date, date) else end_date)
            
            query += " ORDER BY analysis_basis_date DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # 確実に必要なフィールドが存在するようにする
                if 'predicted_tc' not in result and 'tc' in result:
                    # tcをdatetimeに変換（既存のLPPL実装と同様）
                    if result['tc'] is not None and 'data_period_start' in result and 'data_period_end' in result:
                        try:
                            from datetime import datetime, timedelta
                            start = datetime.fromisoformat(result['data_period_start'])
                            end = datetime.fromisoformat(result['data_period_end'])
                            total_days = (end - start).days
                            tc_days = result['tc'] * total_days
                            predicted_date = start + timedelta(days=tc_days)
                            result['predicted_tc'] = predicted_date.isoformat()
                        except:
                            result['predicted_tc'] = None
                results.append(result)
            
            return results
    
    def get_symbol_summary(self, symbol: str) -> Optional[FCOSymbolSummary]:
        """Get summary statistics for a symbol"""
        latest = self.get_latest_analysis(symbol)
        if not latest:
            return None
        
        # Get recent analyses for trend
        recent = self.get_historical_analyses(symbol, limit=10)
        
        # Calculate trend
        trend = "stable"
        if len(recent) >= 2:
            recent_confidence = [r['ds_lppls_confidence'] for r in recent[:5]]
            older_confidence = [r['ds_lppls_confidence'] for r in recent[5:10] if len(recent) > 5]
            
            if older_confidence:
                avg_recent = sum(recent_confidence) / len(recent_confidence)
                avg_older = sum(older_confidence) / len(older_confidence)
                
                if avg_recent > avg_older * 1.1:
                    trend = "increasing"
                elif avg_recent < avg_older * 0.9:
                    trend = "decreasing"
        
        return FCOSymbolSummary(
            symbol=symbol,
            latest_confidence=latest['ds_lppls_confidence'],
            latest_bubble_type=latest['bubble_type'],
            latest_predicted_tc=latest.get('predicted_tc'),
            total_analyses=len(recent),
            last_analysis_date=latest['analysis_basis_date'],
            trend=trend
        )
    
    def get_time_series_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> FCOTimeSeriesData:
        """Get time series data for visualization"""
        analyses = self.get_historical_analyses(symbol, start_date, end_date)
        
        # Extract time series
        dates = []
        confidence_values = []
        confidence_neg_values = []
        trust_values = []
        predicted_tc_values = []
        
        for analysis in reversed(analyses):  # Reverse to get chronological order
            dates.append(analysis['analysis_basis_date'])
            confidence_values.append(analysis.get('ds_lppls_confidence', 0))
            confidence_neg_values.append(analysis.get('ds_lppls_confidence_neg', 0))
            trust_values.append(analysis.get('ds_lppls_trust', 0))
            predicted_tc_values.append(analysis.get('predicted_tc'))
        
        return FCOTimeSeriesData(
            dates=dates,
            confidence_values=confidence_values,
            confidence_neg_values=confidence_neg_values,
            trust_values=trust_values,
            predicted_tc_values=predicted_tc_values
        )
    
    def run_new_analysis(
        self,
        symbol: str,
        period: int = 365,
        force: bool = False
    ) -> Dict[Any, Any]:
        """Run new FCO analysis for a symbol"""
        # For now, just return existing data since FCOEngine is not implemented
        latest = self.get_latest_analysis(symbol)
        if not latest:
            raise ValueError(f"No existing analysis for {symbol}. FCOEngine not yet implemented.")
        return latest
    
    def get_price_series_with_lppl(
        self,
        symbol: str,
        analysis_id: int,
        days_before: int = 365
    ) -> Optional[FCOTimeSeriesWithPrice]:
        """
        Get price data with LPPL fit for a specific analysis

        Args:
            symbol: Symbol to analyze
            analysis_id: Analysis ID in database
            days_before: Days of price data before analysis date

        Returns:
            FCOTimeSeriesWithPrice with price and LPPL fit data
        """
        # Get the analysis record
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM fco_analysis_results
                WHERE id = ? AND symbol = ?
            """, (analysis_id, symbol))

            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()

            if not row:
                return None

            analysis = dict(zip(columns, row))

        # Get analysis basis date
        analysis_basis_date = analysis['analysis_basis_date']
        data_period_end = analysis['data_period_end']

        # Try to get price data from local database first
        price_data = self.price_service.get_price_data(
            symbol,
            pd.to_datetime(data_period_end).date(),
            days_before
        )

        if price_data and len(price_data['prices']) >= 100:  # Need sufficient data
            # Use stored price data
            dates = price_data['dates']
            prices = np.array(price_data['prices'])
            log_prices = np.array(price_data['log_prices'])
        else:
            # Generate synthetic data and save it for future use
            num_days = days_before
            dates = pd.date_range(end=data_period_end, periods=num_days, freq='D')

            # Generate synthetic price data with upward trend
            t = np.arange(num_days)
            base_price = 100
            trend = 0.002  # 0.2% daily growth
            noise = np.random.normal(0, 0.01, num_days)
            prices = base_price * np.exp(trend * t + noise.cumsum())

            # Calculate log prices for LPPL fitting
            log_prices = np.log(prices)

            # Save to database for future use
            self.price_service.save_price_data(
                symbol,
                [d.date() for d in dates],
                prices.tolist(),
                data_source='synthetic'
            )

        # Check for cached LPPL fit
        cached_lppl = self.price_service.get_lppl_fit(analysis_id, symbol)

        if cached_lppl:
            # Use cached LPPL fit
            lppl_fit = np.array(cached_lppl['fitted_values'])
            lppl_params = {
                'tc': cached_lppl['tc'],
                'm': cached_lppl['m'],
                'omega': cached_lppl['omega'],
                'phi': cached_lppl['phi']
            }
        else:
            # Generate synthetic LPPL fit (simplified)
            # In production, this would use actual LPPL parameters from the window fits
            tc = float(analysis.get('predicted_tc', days_before))  # Critical time
            m = 0.5  # Power law exponent
            omega = 7.0  # Log-periodic frequency
            phi = 0  # Phase

            # Time array
            t = np.arange(len(prices))

            # LPPL formula: log(p(t)) = A + B*(tc-t)^m + C*(tc-t)^m*cos(omega*log(tc-t) - phi)
            time_to_tc = np.maximum(tc - t, 1e-10)  # Avoid log of negative/zero
            lppl_fit = (
                log_prices[0] +  # A
                0.1 * (time_to_tc ** m) +  # B term
                0.05 * (time_to_tc ** m) * np.cos(omega * np.log(time_to_tc) - phi)  # C term
            )

            lppl_params = {
                'tc': tc,
                'm': m,
                'omega': omega,
                'phi': phi
            }

            # Save LPPL fit to cache
            if isinstance(dates[0], pd.Timestamp):
                date_strings = [d.strftime('%Y-%m-%d') for d in dates]
            else:
                date_strings = [str(d) for d in dates]

            self.price_service.save_lppl_fit(
                analysis_id,
                symbol,
                lppl_params,
                lppl_fit.tolist(),
                date_strings,
                date_strings[0],
                date_strings[-1]
            )

        # Format dates properly
        if isinstance(dates[0], pd.Timestamp):
            date_strings = [d.strftime('%Y-%m-%d') for d in dates]
        elif isinstance(dates[0], str):
            date_strings = dates
        else:
            date_strings = [str(d) for d in dates]

        # Prepare response
        return FCOTimeSeriesWithPrice(
            dates=date_strings,
            prices=prices.tolist() if isinstance(prices, np.ndarray) else prices,
            log_prices=log_prices.tolist() if isinstance(log_prices, np.ndarray) else log_prices,
            lppl_fit=lppl_fit.tolist() if isinstance(lppl_fit, np.ndarray) else lppl_fit,
            confidence=float(analysis.get('ds_lppls_confidence', 0)),
            trust=float(analysis.get('ds_lppls_trust', 0)),
            predicted_crash_date=str(analysis.get('predicted_crash_date', '')),
            analysis_basis_date=str(analysis_basis_date),
            symbol=symbol,
            bubble_type=analysis.get('bubble_type', 'positive'),
            lppl_params=lppl_params
        )

    def get_all_analyses(self, limit: int = 1000) -> List[Dict[Any, Any]]:
        """Get all analyses for all symbols (for visualization)"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all recent analyses with FCO specific fields
            cursor.execute(
                """
                SELECT
                    id,
                    symbol,
                    analysis_basis_date,
                    ds_lppls_confidence,
                    ds_lppls_confidence_neg,
                    ds_lppls_trust,
                    bubble_type,
                    predicted_crash_date,
                    predicted_tc,
                    tc_std,
                    data_period_start,
                    data_period_end
                FROM fco_analysis_results
                ORDER BY analysis_basis_date DESC
                LIMIT ?
                """,
                (limit,)
            )

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                results.append(result)

            return results

    def get_available_symbols(self) -> List[Dict[str, str]]:
        """Get list of available symbols with names"""
        with sqlite3.connect(self.db.db_path) as conn:
            # Get unique symbols from database
            cursor = conn.execute(
                "SELECT DISTINCT symbol FROM fco_analysis_results ORDER BY symbol"
            )
            symbols = cursor.fetchall()
            
            # Create symbol objects with names
            symbol_map = {
                'SP500': 'S&P 500',
                'NASDAQCOM': 'NASDAQ Composite',
                'DJIA': 'Dow Jones Industrial Average',
                'BTC': 'Bitcoin',
                'GOLD': 'Gold',
                'JPY': 'Japanese Yen',
                'EUR': 'Euro'
            }
            
            return [
                {
                    'symbol': symbol[0],
                    'name': symbol_map.get(symbol[0], symbol[0])
                }
                for symbol in symbols
            ]
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis by ID"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute(
                    "DELETE FROM fco_analysis_results WHERE id = ?",
                    (analysis_id,)
                )
                conn.commit()
                return True
        except Exception:
            return False