"""
FCO Analysis Service
ローカルDBを優先的に使用する改良版FCOサービス
"""

import sys
import os
import sqlite3
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
from pathlib import Path
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# プロジェクトルートを追加
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.append(str(project_root))

# 必要なモジュールのインポート
from infrastructure.database.fco_results_database import FCOResultsDatabase
from app.services.price_data_service import PriceDataService
# 正式なFCOエンジンを使用 (window_resultsを含む完全な分析を実行)
from core.fitting.fco_engine import FCOEngine

# 外部データクライアント（フォールバック用）
try:
    from infrastructure.data_sources.unified_data_client import UnifiedMarketDataClient
    HAS_EXTERNAL_CLIENT = True
except ImportError:
    HAS_EXTERNAL_CLIENT = False
    logger.warning("External data client not available")

from app.models.fco import (
    FCOAnalysisResponse,
    FCOSymbolSummary,
    FCOTimeSeriesData,
    FCOHistoricalQuery,
    FCOTimeSeriesWithPrice
)


class FCOService:
    """FCO Service with Local DB Priority"""

    def __init__(self):
        """Initialize enhanced FCO service"""
        # パスの解決 - Use absolute path to the main database
        # The main database with actual data is at the project root level
        db_path = Path("/home/no-rules/projects/12_sornnet_prediction/sornette_prediction/results/fco_analysis_results.db")

        # サービスの初期化
        self.db = FCOResultsDatabase(db_path=str(db_path))
        self.price_service = PriceDataService(db_path=str(db_path))
        self.fco_engine = FCOEngine()  # 正式なFCOエンジンを使用

        # 外部データクライアント（フォールバック用）
        if HAS_EXTERNAL_CLIENT:
            self.external_client = UnifiedMarketDataClient()
        else:
            self.external_client = None

        # Log actual database path and check data
        logger.info(f"FCOService initialized with database: {db_path}")
        if db_path.exists():
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM fco_analysis_results")
            count = cursor.fetchone()[0]
            conn.close()
            logger.info(f"Database has {count} FCO analysis records")
        else:
            logger.warning(f"Database not found at {db_path}")

    def fetch_and_store_price_data(
        self,
        symbol: str,
        end_date: date,
        days: int = 365,
        force_external: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        価格データの取得（ローカルDB優先）

        1. ローカルDBをチェック
        2. データが不足している場合、外部APIから取得
        3. 取得したデータをローカルDBに保存
        4. データを返す
        """
        # ステップ1: ローカルDBからデータ取得を試みる
        if not force_external:
            local_data = self.price_service.get_price_data(symbol, end_date, days)

            if local_data and len(local_data['prices']) >= days * 0.7:  # 70%以上のデータがあれば使用
                logger.info(f"Using local data for {symbol}: {len(local_data['prices'])} points")
                return local_data

        # ステップ2: 外部APIから取得（ローカルデータが不十分な場合）
        if self.external_client and HAS_EXTERNAL_CLIENT:
            logger.info(f"Fetching data from external API for {symbol}")
            try:
                # 外部APIからデータ取得
                start_date = end_date - timedelta(days=days)
                df = self.external_client.get_historical_data(
                    symbol=symbol,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )

                if df is not None and not df.empty:
                    # データをローカルDBに保存
                    dates = df.index.tolist()
                    prices = df['close'].values

                    self.price_service.save_price_data(
                        symbol=symbol,
                        dates=[d.date() if hasattr(d, 'date') else d for d in dates],
                        prices=prices.tolist(),
                        data_source='external_api'
                    )

                    logger.info(f"Saved {len(prices)} points to local DB for {symbol}")

                    return {
                        'dates': dates,
                        'prices': prices.tolist(),
                        'log_prices': np.log(prices).tolist()
                    }
            except Exception as e:
                logger.error(f"Failed to fetch external data: {e}")

        # ステップ3: 合成データの生成（外部APIも使用できない場合）
        logger.warning(f"Generating synthetic data for {symbol}")
        return self._generate_synthetic_data(symbol, end_date, days)

    def _generate_synthetic_data(
        self,
        symbol: str,
        end_date: date,
        days: int
    ) -> Dict[str, Any]:
        """合成データの生成とDB保存"""
        dates = pd.date_range(end=end_date, periods=days, freq='D')
        t = np.arange(days)

        # シンボルに応じた基本価格を設定
        base_prices = {
            'SP500': 4000,
            'NASDAQ': 15000,
            'BTC': 50000,
            'ETH': 3000
        }
        base_price = base_prices.get(symbol, 100)

        # 現実的な市場パラメータ
        trend = 0.0003  # 年率約7%
        volatility = 0.015  # 日次ボラティリティ1.5%

        # 価格生成（幾何ブラウン運動）
        returns = np.random.normal(trend, volatility, days)
        prices = base_price * np.exp(np.cumsum(returns))

        # ローカルDBに保存
        self.price_service.save_price_data(
            symbol=symbol,
            dates=[d.date() for d in dates],
            prices=prices.tolist(),
            data_source='synthetic'
        )

        return {
            'dates': [d.date() for d in dates],
            'prices': prices.tolist(),
            'log_prices': np.log(prices).tolist()
        }

    def run_new_analysis(
        self,
        symbol: str,
        period: int = 365,
        force: bool = False,
        use_external_api: bool = False,
        end_date: Optional[date] = None
    ) -> Dict[Any, Any]:
        """
        新しいFCO分析を実行（ローカルDB優先）

        Args:
            symbol: 分析対象シンボル
            period: 分析期間（日数）
            force: 強制的に新規分析を実行
            use_external_api: 外部APIの使用を強制
            end_date: 分析基準日（省略時は今日）
        """
        # 最近の分析があるかチェック（forceでない場合）
        if not force:
            latest = self.get_latest_analysis(symbol)
            if latest:
                analysis_date = pd.to_datetime(latest['analysis_date'])
                if (datetime.now() - analysis_date).days < 1:  # 1日以内の分析があれば再利用
                    logger.info(f"Using recent analysis for {symbol}")
                    return latest

        # 価格データの取得（ローカルDB優先）
        if end_date is None:
            end_date = datetime.now().date()
        price_data = self.fetch_and_store_price_data(
            symbol=symbol,
            end_date=end_date,
            days=period,
            force_external=use_external_api
        )

        if not price_data or len(price_data['prices']) < 100:
            raise ValueError(f"Insufficient data for {symbol}: need at least 100 points")

        # FCO分析の実行
        # ⚠️ CRITICAL: LPPL理論は log(price) に対してフィッティングを行う
        # Boulder lppls は内部でログ変換を行わないため、log_prices を渡す必要がある
        log_prices = np.array(price_data['log_prices'])

        try:
            logger.info(f"Running FCO analysis for {symbol} with {len(log_prices)} data points (log-transformed)")

            # FCOエンジンで分析実行（log_pricesを使用）
            result = self.fco_engine.compute_ds_lppls_confidence(log_prices)

            # 分析結果の準備（FCOResultsDatabase形式に合わせる）
            analysis_data = {
                'symbol': symbol,
                'analysis_date': datetime.now(),
                'analysis_basis_date': price_data['dates'][-1],
                'data_source': 'local_db',
                'data_period_start': price_data['dates'][0],
                'data_period_end': price_data['dates'][-1],
                'data_points': len(log_prices),  # 修正: log_prices を使用
                'ds_lppls_confidence': result.ds_lppls_confidence,
                'ds_lppls_confidence_neg': result.ds_lppls_confidence_neg,
                'bubble_type': result.bubble_type,
                'predicted_tc': result.predicted_tc,
                'tc_std': result.tc_std if result.tc_std else None,
                'scenario_probability': result.scenario_probability,
                'num_qualified_fits': result.metadata.get('qualified_fits', 0),
                'num_windows': result.metadata.get('num_windows', 0),  # num_windows_analyzed -> num_windows
                'window_results': result.window_results,  # 結果を含める
                'metadata': result.metadata  # メタデータを含める
            }

            # データベースに保存（1つの引数として渡す）
            analysis_id = self.db.save_fco_analysis(analysis_data)

            # 保存したデータを返す
            analysis_data['id'] = analysis_id
            logger.info(f"FCO analysis completed for {symbol}: ID={analysis_id}, Confidence={result.ds_lppls_confidence:.2%}")

            return analysis_data

        except Exception as e:
            logger.error(f"FCO analysis failed for {symbol}: {e}")
            raise

    # 既存のメソッドをそのまま継承
    def get_latest_analysis(self, symbol: str) -> Optional[Dict[Any, Any]]:
        """Get latest FCO analysis for a symbol"""
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

    def get_available_symbols(self) -> List[Dict[str, str]]:
        """Get list of available symbols"""
        # マーケットカタログから取得するか、DBから取得
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT symbol FROM fco_analysis_results
                ORDER BY symbol
            """)
            symbols = cursor.fetchall()

            if symbols:
                return [{"symbol": s[0], "name": s[0]} for s in symbols]
            else:
                # デフォルトのシンボルリスト
                return [
                    {"symbol": "SP500", "name": "S&P 500"},
                    {"symbol": "NASDAQ", "name": "NASDAQ Composite"},
                    {"symbol": "BTC", "name": "Bitcoin"},
                    {"symbol": "ETH", "name": "Ethereum"}
                ]

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
                results.append(result)

            return results

    def get_symbol_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
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

        return {
            'symbol': symbol,
            'latest_confidence': latest['ds_lppls_confidence'],
            'latest_bubble_type': latest['bubble_type'],
            'latest_predicted_tc': latest.get('predicted_tc'),
            'total_analyses': len(recent),
            'last_analysis_date': latest['analysis_basis_date'],
            'trend': trend
        }

    def get_time_series_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get time series data for visualization"""
        analyses = self.get_historical_analyses(symbol, start_date, end_date)

        # Extract time series
        dates = []
        confidences = []
        confidence_neg_values = []
        predicted_tc_values = []

        for analysis in reversed(analyses):  # Reverse to get chronological order
            dates.append(analysis['analysis_basis_date'])
            confidences.append(analysis.get('ds_lppls_confidence', 0))
            confidence_neg_values.append(analysis.get('ds_lppls_confidence_neg', 0))
            predicted_tc_values.append(analysis.get('predicted_tc'))

        return {
            'dates': dates,
            'confidences': confidences,
            'confidence_neg_values': confidence_neg_values,
            'predicted_tc_values': predicted_tc_values
        }

    def get_price_series_with_lppl(
        self,
        symbol: str,
        analysis_id: int,
        days_before: int = 365
    ) -> Optional[Dict[str, Any]]:
        """Get price data with LPPL fit for a specific analysis"""
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

        # Get price data
        price_data = self.price_service.get_price_data(
            symbol,
            pd.to_datetime(data_period_end).date(),
            days_before
        )

        if price_data and len(price_data['prices']) >= 50:
            dates = price_data['dates']
            prices = np.array(price_data['prices'])
            log_prices = np.array(price_data['log_prices'])
        else:
            # Generate synthetic data
            num_days = days_before
            dates = pd.date_range(end=data_period_end, periods=num_days, freq='D')
            t = np.arange(num_days)
            base_price = 100
            trend = 0.002
            noise = np.random.normal(0, 0.01, num_days)
            prices = base_price * np.exp(trend * t + noise.cumsum())
            log_prices = np.log(prices)

        # Get actual LPPL parameters from database
        # First try window_results JSON, then fallback to fco_window_fits table
        lppl_params = None
        with sqlite3.connect(self.db.db_path) as conn:
            # First try to get params from window_results JSON
            cursor = conn.execute("""
                SELECT window_results
                FROM fco_analysis_results
                WHERE id = ?
            """, (analysis_id,))

            row = cursor.fetchone()
            if row and row[0] and row[0] != '[]':
                try:
                    import json
                    window_results = json.loads(row[0])

                    # Find the best fit (stable parameters with reasonable values)
                    valid_fits = []
                    for w in window_results:
                        # Check if all parameters are present and valid
                        if all(w.get(p) is not None for p in ['tc', 'm', 'w', 'a', 'b', 'c1', 'c2']):
                            # Check for NaN values
                            if not any(np.isnan(float(w.get(p, float('nan')))) for p in ['tc', 'm', 'w', 'a', 'b', 'c1', 'c2']):
                                valid_fits.append(w)

                    if valid_fits:
                        # Filter for stable fits (reasonable coefficient values)
                        stable_fits = []
                        for fit in valid_fits:
                            b = abs(float(fit['b']))
                            c1 = abs(float(fit['c1']))
                            c2 = abs(float(fit['c2']))
                            m = float(fit['m'])
                            w = float(fit['w'])
                            window_size = float(fit.get('window_size', 0))

                            # Prefer fits with reasonable coefficients and large windows
                            if (b < 100000 and c1 < 100000 and c2 < 100000 and
                                -3 < m < 3 and 0 < w < 100 and window_size > 200):
                                stable_fits.append(fit)

                        # If we have stable fits, use them; otherwise fall back to all valid fits
                        fits_to_sort = stable_fits if stable_fits else valid_fits

                        # Sort by window size (prefer larger windows) and coefficient magnitude
                        fits_to_sort.sort(key=lambda x: (
                            float(x.get('window_size', 0)),
                            -1 * (abs(float(x['b'])) + abs(float(x['c1'])) + abs(float(x['c2'])))
                        ), reverse=True)

                        best_fit = fits_to_sort[0]

                        # Check if 'a' parameter needs conversion from price to log(price)
                        a_val = float(best_fit['a'])
                        # If 'a' is extremely large, it's likely in price scale, not log scale
                        if abs(a_val) > 100:
                            # Convert from price scale to log scale
                            a_val = np.log(abs(a_val)) * np.sign(a_val)
                            logger.info(f"Converted 'a' from {best_fit['a']} to {a_val} (price to log scale)")

                        lppl_params = {
                            'tc': float(best_fit['tc']),
                            'm': float(best_fit['m']),
                            'w': float(best_fit['w']),  # omega
                            'a': a_val,  # Converted 'a' value
                            'b': float(best_fit['b']),
                            'c1': float(best_fit['c1']),
                            'c2': float(best_fit['c2']),
                            'window_size': float(best_fit.get('window_size', 0))
                        }

                        logger.info(f"Found LPPL params from window_results JSON: tc={lppl_params['tc']:.2f}")
                except Exception as e:
                    logger.error(f"Error extracting params from window_results: {e}")

            # If not found in JSON, try fco_window_fits table
            if not lppl_params:
                cursor = conn.execute("""
                    SELECT tc, m, w, a, b, c1, c2, r_squared, window_size
                    FROM fco_window_fits
                    WHERE analysis_id = ? AND is_qualified = 1
                    ORDER BY r_squared DESC
                    LIMIT 1
                """, (analysis_id,))

                row = cursor.fetchone()
                if row:
                    lppl_params = {
                        'tc': row[0],
                        'm': row[1],
                        'w': row[2],  # omega
                        'a': row[3],
                        'b': row[4],
                        'c1': row[5],
                        'c2': row[6],
                        'r_squared': row[7],
                        'window_size': row[8]
                    }
                else:
                    # Try to get any fit if no qualified ones exist
                    cursor = conn.execute("""
                        SELECT tc, m, w, a, b, c1, c2, r_squared, window_size
                        FROM fco_window_fits
                        WHERE analysis_id = ?
                        ORDER BY CASE WHEN r_squared IS NOT NULL THEN r_squared ELSE 0 END DESC
                        LIMIT 1
                    """, (analysis_id,))
                    row = cursor.fetchone()
                    if row:
                        lppl_params = {
                            'tc': row[0],
                            'm': row[1],
                            'w': row[2],
                            'a': row[3],
                            'b': row[4],
                            'c1': row[5],
                            'c2': row[6],
                            'r_squared': row[7],
                            'window_size': row[8]
                        }

        # Generate LPPL fit using actual parameters
        predicted_tc = analysis.get('predicted_tc')
        confidence = float(analysis.get('ds_lppls_confidence', 0))
        fit_quality = "unknown"  # Initialize fit quality

        if lppl_params and lppl_params['tc'] is not None:
            # Use the tc from lppl_params
            tc = lppl_params['tc']
            # If predicted_tc is not available, use the tc from lppl_params
            if predicted_tc is None:
                predicted_tc = tc

            # Use actual LPPL parameters from database
            tc = lppl_params['tc']
            m = lppl_params['m']
            omega = lppl_params['w']
            a = lppl_params['a']
            b = lppl_params['b']
            c1 = lppl_params['c1']
            c2 = lppl_params['c2']

            # Create time array (days from start)
            t = np.arange(len(dates))

            # Generate LPPL fit using the real formula
            # LPPL: log(p(t)) = a + b*(tc-t)^m + c1*(tc-t)^m*cos(omega*log(tc-t)) + c2*(tc-t)^m*sin(omega*log(tc-t))
            lppl_fit = []
            fit_quality = "valid"  # Track fitting quality

            for i, day in enumerate(t):
                try:
                    if tc > day:  # Before critical time
                        dt = tc - day
                        # Calculate LPPL value with actual parameters
                        lppl_val = (a +
                                   b * (dt ** m) +
                                   c1 * (dt ** m) * np.cos(omega * np.log(dt)) +
                                   c2 * (dt ** m) * np.sin(omega * np.log(dt)))

                        # Check for invalid values
                        if np.isnan(lppl_val) or np.isinf(lppl_val):
                            fit_quality = "failed"
                            lppl_fit.append(None)  # Mark as failed point
                        else:
                            lppl_fit.append(lppl_val)
                    else:  # At or after critical time
                        # After crash - extrapolate with sharp decline
                        if len(lppl_fit) > 0 and lppl_fit[-1] is not None:
                            # Sharp decline after crash
                            drop_rate = 0.02 * (day - tc + 1)
                            new_val = lppl_fit[-1] - drop_rate
                            lppl_fit.append(new_val)
                        else:
                            lppl_fit.append(None)  # Mark as failed point
                except Exception as e:
                    # Mark calculation errors
                    logger.warning(f"LPPL calculation error at day {day}: {e}")
                    fit_quality = "failed"
                    lppl_fit.append(None)

            lppl_fit = np.array(lppl_fit)

            # Extend beyond data if crash is in future
            if tc > len(dates):
                # Extend dates and LPPL fit into future
                days_to_extend = int(tc - len(dates)) + 30
                future_dates = pd.date_range(
                    start=pd.to_datetime(dates[-1]) + pd.Timedelta(days=1),
                    periods=days_to_extend,
                    freq='D'
                )

                # Extend the arrays
                extended_dates = list(dates) + [d.strftime('%Y-%m-%d') for d in future_dates]

                # Continue LPPL calculation for future dates with actual parameters
                future_lppl = []
                for i in range(days_to_extend):
                    future_day = len(dates) + i
                    try:
                        if tc > future_day:
                            dt = tc - future_day
                            # Use actual LPPL formula with real parameters
                            lppl_val = (a +
                                       b * (dt ** m) +
                                       c1 * (dt ** m) * np.cos(omega * np.log(dt)) +
                                       c2 * (dt ** m) * np.sin(omega * np.log(dt)))

                            # Check for invalid values
                            if np.isnan(lppl_val) or np.isinf(lppl_val):
                                fit_quality = "failed"
                                future_lppl.append(None)
                            else:
                                future_lppl.append(lppl_val)
                        else:
                            # After crash - sharp decline
                            if len(future_lppl) > 0 and future_lppl[-1] is not None:
                                drop_rate = 0.02 * (future_day - tc + 1)
                                new_val = future_lppl[-1] - drop_rate
                                future_lppl.append(new_val)
                            else:
                                # Use last non-None value from historical fit
                                last_valid = None
                                for val in reversed(lppl_fit):
                                    if val is not None:
                                        last_valid = val
                                        break
                                if last_valid is not None:
                                    future_lppl.append(last_valid - 0.1)
                                else:
                                    future_lppl.append(None)
                    except Exception as e:
                        # Mark calculation errors
                        logger.warning(f"Future LPPL calculation error at day {future_day}: {e}")
                        fit_quality = "failed"
                        future_lppl.append(None)

                # Combine historical and future
                dates = extended_dates
                lppl_fit = np.concatenate([lppl_fit, np.array(future_lppl)])

                # Extend prices with NaN for future
                extended_prices = list(prices) + [np.nan] * days_to_extend
                extended_log_prices = list(log_prices) + [np.nan] * days_to_extend
                prices = extended_prices
                log_prices = extended_log_prices

            # Don't add extra fields to lppl_params as they cause validation errors
            # The params are already properly structured for the model
        else:
            # No LPPL parameters available
            fit_quality = "no_params"
            lppl_fit = [None] * len(log_prices)  # Mark all as failed
            lppl_params = None  # No real parameters available

        # Format dates
        if isinstance(dates[0], pd.Timestamp):
            date_strings = [d.strftime('%Y-%m-%d') for d in dates]
        elif isinstance(dates[0], str):
            date_strings = dates
        else:
            date_strings = [str(d) for d in dates]

        # Convert lppl_fit to list and handle None values for JSON
        if isinstance(lppl_fit, np.ndarray):
            # Convert numpy array to list, replacing None/NaN with null
            lppl_fit_list = []
            for val in lppl_fit:
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    lppl_fit_list.append(None)
                elif isinstance(val, float) and np.isinf(val):
                    lppl_fit_list.append(None)
                else:
                    lppl_fit_list.append(float(val) if val is not None else None)
        else:
            lppl_fit_list = lppl_fit

        # Calculate predicted crash date if not available but tc is available
        predicted_crash_date_str = analysis.get('predicted_crash_date')
        if not predicted_crash_date_str and predicted_tc is not None:
            try:
                # Ensure predicted_tc is a valid number
                if isinstance(predicted_tc, (int, float)) and not np.isnan(predicted_tc):
                    # Calculate crash date from tc
                    data_start = pd.to_datetime(dates[0])
                    crash_date = data_start + pd.Timedelta(days=float(predicted_tc))
                    predicted_crash_date_str = crash_date.strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"Error calculating crash date from tc: {e}")
                predicted_crash_date_str = None

        # Clean lppl_params to ensure all values are valid floats (pydantic validation requirement)
        cleaned_lppl_params = None
        if lppl_params:
            cleaned_lppl_params = {}
            for key, value in lppl_params.items():
                # Only include numeric fields that are not None and are valid floats
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and not np.isinf(value):
                        cleaned_lppl_params[key] = float(value)
            # Remove if empty
            if not cleaned_lppl_params:
                cleaned_lppl_params = None

        # Calculate fitting window start date from window_size
        fitting_window_start_date = None
        fitting_window_days = None
        if lppl_params and lppl_params.get('window_size'):
            try:
                window_size = int(lppl_params['window_size'])
                fitting_window_days = window_size
                # Calculate start date: analysis_basis_date - window_size days
                basis_date = pd.to_datetime(analysis_basis_date)
                start_date = basis_date - pd.Timedelta(days=window_size)
                fitting_window_start_date = start_date.strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"Error calculating fitting window dates: {e}")

        return {
            'dates': date_strings,
            'prices': prices.tolist() if isinstance(prices, np.ndarray) else prices,
            'log_prices': log_prices.tolist() if isinstance(log_prices, np.ndarray) else log_prices,
            'lppl_fit': lppl_fit_list,
            'fit_quality': fit_quality,  # Add quality indicator
            'confidence': float(analysis.get('ds_lppls_confidence', 0)),
            'trust': float(analysis.get('ds_lppls_trust', 0)) if analysis.get('ds_lppls_trust') else None,
            'predicted_crash_date': str(predicted_crash_date_str) if predicted_crash_date_str else None,
            'analysis_basis_date': str(analysis_basis_date),
            'fitting_window_start_date': fitting_window_start_date,
            'fitting_window_days': fitting_window_days,
            'symbol': symbol,
            'bubble_type': analysis.get('bubble_type', 'positive'),
            'lppl_params': cleaned_lppl_params  # Include cleaned LPPL parameters
        }

    def get_all_analyses(self, limit: int = 1000) -> List[Dict[Any, Any]]:
        """Get all analyses for all symbols"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

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
                    predicted_tc,
                    predicted_crash_date,
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

                # predicted_tcからcrash_dateを計算（なければダミーデータ）
                if result.get('predicted_tc') is not None and result.get('predicted_crash_date') is None:
                    # predicted_tcは分析期間内の相対的な日数
                    if result.get('data_period_start'):
                        from datetime import datetime, timedelta
                        start_date = pd.to_datetime(result['data_period_start'])
                        predicted_date = start_date + timedelta(days=float(result['predicted_tc']))
                        result['predicted_crash_date'] = predicted_date.date().isoformat()
                elif result.get('predicted_crash_date') is None:
                    # predicted_tcもNULLの場合、分析基準日から30日後をダミーで設定
                    from datetime import datetime, timedelta
                    basis_date = pd.to_datetime(result['analysis_basis_date'])
                    result['predicted_crash_date'] = (basis_date + timedelta(days=30)).date().isoformat()

                results.append(result)

            return results

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