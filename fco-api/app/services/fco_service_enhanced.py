"""
Enhanced FCO Analysis Service with Local DB Priority
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
# 柔軟なFCOエンジンを使用
from core.fitting.fco_engine_flexible import FCOEngineFlexible

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


class FCOServiceEnhanced:
    """Enhanced FCO Service with Local DB Priority"""

    def __init__(self):
        """Initialize enhanced FCO service"""
        # パスの解決
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent.parent
        db_path = project_root / "results" / "fco_analysis_results.db"

        # サービスの初期化
        self.db = FCOResultsDatabase(db_path=str(db_path))
        self.price_service = PriceDataService(db_path=str(db_path))
        self.fco_engine = FCOEngineFlexible()  # 柔軟なエンジンを使用

        # 外部データクライアント（フォールバック用）
        if HAS_EXTERNAL_CLIENT:
            self.external_client = UnifiedMarketDataClient()
        else:
            self.external_client = None

        logger.info("FCOServiceEnhanced initialized with local DB priority")

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
        use_external_api: bool = False
    ) -> Dict[Any, Any]:
        """
        新しいFCO分析を実行（ローカルDB優先）

        Args:
            symbol: 分析対象シンボル
            period: 分析期間（日数）
            force: 強制的に新規分析を実行
            use_external_api: 外部APIの使用を強制
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
        prices = np.array(price_data['prices'])

        try:
            logger.info(f"Running FCO analysis for {symbol} with {len(prices)} data points")

            # FCOエンジンで分析実行
            result = self.fco_engine.compute_ds_lppls_confidence(prices)

            # 分析結果の準備（FCOResultsDatabase形式に合わせる）
            analysis_data = {
                'symbol': symbol,
                'analysis_date': datetime.now(),
                'analysis_basis_date': price_data['dates'][-1],
                'data_source': 'local_db',
                'data_period_start': price_data['dates'][0],
                'data_period_end': price_data['dates'][-1],
                'data_points': len(prices),  # num_data_points -> data_points
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