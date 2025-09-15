"""
FCO Analysis Service
Wraps existing Python FCO implementation
"""

import sys
import os
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd

# Add parent directory to path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

# Import existing FCO implementation
from infrastructure.database.fco_results_database import FCOResultsDatabase
# Note: fco_engine and unified_data_client modules need to be created
# For now, we'll just work with the database

from app.models.fco import (
    FCOAnalysisResponse,
    FCOSymbolSummary,
    FCOTimeSeriesData,
    FCOHistoricalQuery
)


class FCOService:
    """Service for FCO analysis operations"""
    
    def __init__(self):
        """Initialize FCO service with existing components"""
        self.db = FCOResultsDatabase()
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
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND analysis_basis_date <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY analysis_basis_date DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
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
            confidence_values.append(analysis['ds_lppls_confidence'])
            confidence_neg_values.append(analysis['ds_lppls_confidence_neg'])
            trust_values.append(analysis['ds_lppls_trust'])
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
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        with sqlite3.connect(self.db.db_path) as conn:
            # Get unique symbols from database
            cursor = conn.execute(
                "SELECT DISTINCT symbol FROM fco_analysis_results ORDER BY symbol"
            )
            return [row[0] for row in cursor.fetchall()]
    
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