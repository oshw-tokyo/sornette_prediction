#!/usr/bin/env python3
"""
Batch Scheduled Analyzer (backfill-v2)
Efficient batch data fetching for multiple analysis periods

Key Features:
- Fetch data once, analyze multiple periods
- API call reduction: N×M calls → M calls (N=periods, M=symbols)
- CoinGecko 365-day limit handling with multi-fetch
- Memory-efficient caching strategy
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

from infrastructure.database.schedule_manager import ScheduleManager, ScheduleConfig
from infrastructure.database.integration_helpers import AnalysisResultSaver
from infrastructure.data_sources.unified_data_client import UnifiedDataClient
from core.fitting.multi_criteria_selection import MultiCriteriaSelector
from infrastructure.visualization.lppl_visualizer import LPPLVisualizer
from infrastructure.config.matplotlib_config import configure_matplotlib_for_automation

# Configure matplotlib for non-interactive mode
configure_matplotlib_for_automation()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchDataCache:
    """
    Memory-efficient batch data cache
    Stores full period data for each symbol to avoid repeated API calls
    """
    
    def __init__(self):
        """Initialize cache structure"""
        self.cache = {}
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def get_or_fetch(self, symbol: str, start_date: str, end_date: str, 
                     data_client: UnifiedDataClient) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Get data from cache or fetch from API
        
        Args:
            symbol: Symbol to fetch
            start_date: Start date for data
            end_date: End date for data
            data_client: Unified data client for API calls
            
        Returns:
            (DataFrame, source): Data and source name
        """
        cache_key = symbol
        
        # Check if we have cached data for this symbol
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cached_start = cached_data['data'].index[0]
            cached_end = cached_data['data'].index[-1]
            
            requested_start = pd.to_datetime(start_date)
            requested_end = pd.to_datetime(end_date)
            
            # Check if cached data covers requested period
            if cached_start <= requested_start and cached_end >= requested_end:
                self.stats['cache_hits'] += 1
                logger.info(f"✅ Cache hit for {symbol}: using cached data")
                
                # Return subset of cached data
                subset = cached_data['data'][
                    (cached_data['data'].index >= requested_start) &
                    (cached_data['data'].index <= requested_end)
                ].copy()
                
                return subset, cached_data['source']
        
        # Cache miss - need to fetch data
        self.stats['cache_misses'] += 1
        logger.info(f"❌ Cache miss for {symbol}: fetching from API")
        
        # Determine optimal fetch period (maximize data retrieval)
        # For backfill, we want to get as much historical data as possible
        extended_start = (pd.to_datetime(start_date) - timedelta(days=365*2)).strftime('%Y-%m-%d')
        extended_end = (pd.to_datetime(end_date) + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Fetch data with extended period
        data, source = self._fetch_with_source_priority(
            symbol, extended_start, extended_end, data_client
        )
        
        if data is not None and not data.empty:
            # Store in cache
            self.cache[cache_key] = {
                'data': data,
                'source': source,
                'fetched_at': datetime.now(),
                'original_start': extended_start,
                'original_end': extended_end
            }
            
            # Return requested subset
            requested_start = pd.to_datetime(start_date)
            requested_end = pd.to_datetime(end_date)
            
            subset = data[
                (data.index >= requested_start) &
                (data.index <= requested_end)
            ].copy()
            
            return subset, source
        
        return None, 'failed'
    
    def _fetch_with_source_priority(self, symbol: str, start_date: str, end_date: str,
                                   data_client: UnifiedDataClient) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Fetch data with intelligent source selection
        Handles CoinGecko 365-day limit with multiple fetches
        
        Args:
            symbol: Symbol to fetch
            start_date: Start date
            end_date: End date
            data_client: Data client
            
        Returns:
            (DataFrame, source): Combined data and source
        """
        self.stats['api_calls'] += 1
        
        # Check symbol mapping to determine source
        symbol_mapping = data_client.symbol_mapping.get(symbol, {})
        
        # Debug: Check if symbol_mapping is properly loaded
        if not symbol_mapping:
            logger.debug(f"Symbol {symbol} not found in mapping, available: {list(data_client.symbol_mapping.keys())[:5]}")
        
        # Try FRED first (no limits)
        if 'fred' in symbol_mapping:
            logger.info(f"📊 Fetching {symbol} from FRED (unlimited period)")
            data, source = data_client.get_data_with_fallback(
                symbol, start_date, end_date, preferred_source='fred'
            )
            if data is not None:
                return data, source
        
        # Try Alpha Vantage (20+ years available)
        if 'alpha_vantage' in symbol_mapping:
            logger.info(f"📊 Fetching {symbol} from Alpha Vantage (full history)")
            data, source = data_client.get_data_with_fallback(
                symbol, start_date, end_date, preferred_source='alpha_vantage'
            )
            if data is not None:
                return data, source
        
        # Handle CoinGecko with 365-day limit
        if 'coingecko' in symbol_mapping:
            logger.info(f"📊 Fetching {symbol} from CoinGecko (365-day chunks)")
            return self._fetch_coingecko_multi_period(
                symbol, start_date, end_date, data_client
            )
        
        # Fallback to any available source
        logger.warning(f"⚠️ No specific source for {symbol}, trying all sources")
        return data_client.get_data_with_fallback(symbol, start_date, end_date)
    
    def _fetch_coingecko_multi_period(self, symbol: str, start_date: str, end_date: str,
                                     data_client: UnifiedDataClient) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Fetch CoinGecko data in 365-day chunks and combine
        
        Args:
            symbol: Symbol to fetch
            start_date: Start date
            end_date: End date
            data_client: Data client
            
        Returns:
            (DataFrame, source): Combined data
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Calculate number of 365-day periods needed
        total_days = (end_dt - start_dt).days
        num_periods = (total_days // 365) + 1
        
        all_data = []
        
        for i in range(num_periods):
            # Calculate period boundaries
            period_end = end_dt - timedelta(days=365 * i)
            period_start = max(period_end - timedelta(days=364), start_dt)
            
            if period_end < start_dt:
                break
            
            logger.info(f"  📅 Fetching period {i+1}/{num_periods}: "
                       f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
            
            # Fetch this period
            period_data, source = data_client.get_data_with_fallback(
                symbol,
                period_start.strftime('%Y-%m-%d'),
                period_end.strftime('%Y-%m-%d'),
                preferred_source='coingecko'
            )
            
            if period_data is not None and not period_data.empty:
                all_data.append(period_data)
            else:
                logger.warning(f"  ⚠️ Failed to fetch period {i+1} for {symbol}")
                # Decide whether to continue or abort
                if i == 0:
                    # First period failed - critical
                    logger.error(f"  ❌ Cannot fetch most recent data for {symbol}")
                    return None, 'coingecko_failed'
            
            # Rate limiting between periods
            if i < num_periods - 1:
                time.sleep(3)  # CoinGecko rate limit
        
        if not all_data:
            return None, 'coingecko_failed'
        
        # Combine all periods
        combined_data = pd.concat(all_data, axis=0)
        
        # Remove duplicates (keep first occurrence)
        combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
        
        # Sort by date
        combined_data = combined_data.sort_index()
        
        logger.info(f"✅ Combined {len(all_data)} periods for {symbol}: "
                   f"{len(combined_data)} total days")
        
        return combined_data, 'coingecko'
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            **self.stats,
            'symbols_cached': len(self.cache),
            'cache_efficiency': (
                self.stats['cache_hits'] / 
                max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
            ) * 100
        }


class BatchScheduledAnalyzer:
    """
    Batch version of scheduled analyzer (backfill-v2)
    Optimized for multi-period analysis with minimal API calls
    """
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        Initialize batch analyzer
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self.schedule_manager = ScheduleManager(db_path)
        
        # Initialize components
        self.data_client = UnifiedDataClient()
        self.selector = MultiCriteriaSelector()
        self.db_saver = AnalysisResultSaver(db_path)
        self.visualizer = LPPLVisualizer(db_path)
        
        # Batch data cache
        self.batch_cache = BatchDataCache()
        
        # Statistics
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'skipped_duplicates': 0
        }
    
    def run_batch_backfill(self, start_date: str, end_date: Optional[str] = None,
                          schedule_name: str = 'fred_weekly',
                          dry_run: bool = False) -> Dict:
        """
        Run batch backfill analysis
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to yesterday
            schedule_name: Schedule configuration name
            dry_run: If True, only simulate without saving
            
        Returns:
            Dict: Analysis results and statistics
        """
        print(f"\n{'='*60}")
        print(f"🚀 Batch Backfill v2 Started")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        
        # Get schedule configuration
        config = self.schedule_manager.get_schedule_config(schedule_name)
        if not config:
            raise ValueError(f"Schedule not found: {schedule_name}")
        
        # Calculate periods to analyze
        periods = self._generate_analysis_periods(start_date, end_date, config)
        print(f"📅 Analysis periods: {len(periods)}")
        print(f"🎯 Target symbols: {len(config.symbols)}")
        print(f"📊 Traditional API calls: {len(periods) * len(config.symbols)}")
        print(f"⚡ Optimized API calls: ~{len(config.symbols)} (estimated)")
        
        if dry_run:
            print("\n⚠️ DRY RUN MODE - No data will be saved")
        
        # Process each symbol with batch data
        results = {
            'periods': periods,
            'symbols': config.symbols,
            'successful': [],
            'failed': [],
            'api_stats': {},
            'cache_stats': {}
        }
        
        for symbol_idx, symbol in enumerate(config.symbols, 1):
            print(f"\n📊 Processing {symbol} ({symbol_idx}/{len(config.symbols)})")
            
            symbol_results = self._process_symbol_batch(
                symbol, periods, schedule_name, dry_run
            )
            
            if symbol_results['success_count'] > 0:
                results['successful'].extend(symbol_results['successful_analyses'])
            if symbol_results['failure_count'] > 0:
                results['failed'].extend(symbol_results['failed_analyses'])
        
        # Final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        cache_stats = self.batch_cache.get_cache_stats()
        
        print(f"\n{'='*60}")
        print(f"📊 Batch Backfill v2 Complete")
        print(f"{'='*60}")
        print(f"⏱️ Total time: {duration:.1f} seconds")
        print(f"✅ Successful analyses: {len(results['successful'])}")
        print(f"❌ Failed analyses: {len(results['failed'])}")
        print(f"📈 API efficiency:")
        print(f"   - Traditional calls: {len(periods) * len(config.symbols)}")
        print(f"   - Actual API calls: {cache_stats['api_calls']}")
        print(f"   - Reduction: {(1 - cache_stats['api_calls'] / max(1, len(periods) * len(config.symbols))) * 100:.1f}%")
        print(f"💾 Cache efficiency: {cache_stats['cache_efficiency']:.1f}%")
        
        results['duration'] = duration
        results['cache_stats'] = cache_stats
        
        return results
    
    def _generate_analysis_periods(self, start_date: str, end_date: Optional[str],
                                  config: ScheduleConfig) -> List[str]:
        """
        Generate analysis periods based on schedule configuration
        
        Args:
            start_date: Start date
            end_date: End date (optional)
            config: Schedule configuration
            
        Returns:
            List of period dates (YYYY-MM-DD format)
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) if end_date else datetime.now() - timedelta(days=1)
        
        periods = []
        
        if config.frequency == 'weekly':
            # Generate weekly periods aligned to day_of_week
            current = start_dt
            while current <= end_dt:
                # Align to specified day of week
                days_ahead = config.day_of_week - current.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                aligned_date = current + timedelta(days=days_ahead)
                
                if aligned_date <= end_dt:
                    periods.append(aligned_date.strftime('%Y-%m-%d'))
                
                current = aligned_date + timedelta(days=7)
        
        elif config.frequency == 'daily':
            # Generate daily periods
            current = start_dt
            while current <= end_dt:
                periods.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        
        return periods
    
    def _process_symbol_batch(self, symbol: str, periods: List[str],
                             schedule_name: str, dry_run: bool) -> Dict:
        """
        Process a single symbol for multiple periods using batch data
        
        Args:
            symbol: Symbol to process
            periods: List of analysis periods
            schedule_name: Schedule name
            dry_run: Dry run mode
            
        Returns:
            Dict: Processing results
        """
        results = {
            'symbol': symbol,
            'successful_analyses': [],
            'failed_analyses': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        # Determine data range needed for all periods
        all_periods_start = (pd.to_datetime(min(periods)) - timedelta(days=365)).strftime('%Y-%m-%d')
        all_periods_end = max(periods)
        
        # Fetch data once for all periods (using cache)
        print(f"  📥 Fetching data for {symbol} ({all_periods_start} to {all_periods_end})")
        
        base_data, source = self.batch_cache.get_or_fetch(
            symbol, all_periods_start, all_periods_end, self.data_client
        )
        
        if base_data is None or base_data.empty:
            print(f"  ❌ Failed to fetch data for {symbol}")
            for period in periods:
                results['failed_analyses'].append(f"{period}:{symbol}")
                results['failure_count'] += 1
            return results
        
        print(f"  ✅ Data fetched from {source}: {len(base_data)} days")
        
        # Analyze each period using the cached data
        for period_idx, period in enumerate(periods, 1):
            print(f"  📊 Analyzing period {period_idx}/{len(periods)}: {period}")
            
            # Extract data for this specific period (365 days before period date)
            period_end = pd.to_datetime(period)
            period_start = period_end - timedelta(days=364)
            
            period_data = base_data[
                (base_data.index >= period_start) &
                (base_data.index <= period_end)
            ].copy()
            
            if len(period_data) < 100:  # Minimum data requirement
                print(f"    ⚠️ Insufficient data for {period}: {len(period_data)} days")
                results['failed_analyses'].append(f"{period}:{symbol}")
                results['failure_count'] += 1
                continue
            
            # Run LPPL analysis
            try:
                if not dry_run:
                    success = self._analyze_and_save(
                        symbol, period_data, period, source, schedule_name
                    )
                else:
                    # Dry run - just validate
                    success = len(period_data) >= 100
                
                if success:
                    results['successful_analyses'].append(f"{period}:{symbol}")
                    results['success_count'] += 1
                    print(f"    ✅ Analysis complete for {period}")
                else:
                    results['failed_analyses'].append(f"{period}:{symbol}")
                    results['failure_count'] += 1
                    print(f"    ❌ Analysis failed for {period}")
                    
            except Exception as e:
                logger.error(f"Analysis error for {symbol} on {period}: {e}")
                results['failed_analyses'].append(f"{period}:{symbol}")
                results['failure_count'] += 1
        
        return results
    
    def _analyze_and_save(self, symbol: str, data: pd.DataFrame, basis_date: str,
                         source: str, schedule_name: str) -> bool:
        """
        Run LPPL analysis and save results
        
        Args:
            symbol: Symbol
            data: Price data
            basis_date: Analysis basis date
            source: Data source
            schedule_name: Schedule name
            
        Returns:
            bool: Success status
        """
        try:
            # Run LPPL analysis
            result = self.selector.perform_comprehensive_fitting(data)
            if result is None:
                return False
            
            # Save to database
            analysis_id = self.db_saver.save_lppl_analysis_with_schedule(
                symbol=symbol,
                data=data,
                result=result,
                data_source=source,
                schedule_name=schedule_name,
                basis_date=basis_date,
                backfill_batch_id=f"batch_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Generate visualization
            self.visualizer.create_comprehensive_visualization(analysis_id)
            
            self.stats['successful_analyses'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Save error for {symbol}: {e}")
            self.stats['failed_analyses'] += 1
            return False


def main():
    """Test batch analyzer with small dataset"""
    print("🧪 Testing Batch Scheduled Analyzer (backfill-v2)")
    
    analyzer = BatchScheduledAnalyzer()
    
    # Test with a short period and limited symbols
    results = analyzer.run_batch_backfill(
        start_date='2025-08-01',
        end_date='2025-08-08',
        schedule_name='fred_weekly',
        dry_run=True  # Dry run for testing
    )
    
    print(f"\n📊 Test Results:")
    print(f"  - Periods analyzed: {len(results['periods'])}")
    print(f"  - Symbols processed: {len(results['symbols'])}")
    print(f"  - Cache efficiency: {results['cache_stats']['cache_efficiency']:.1f}%")


if __name__ == "__main__":
    main()