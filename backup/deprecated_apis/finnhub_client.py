#!/usr/bin/env python3
"""
Finnhub API Client
- 制限: 60req/分 (無料プラン)  
- 対応: 株式中心、一部仮想通貨
- Alpha Vantage株式データの代替候補
"""

import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinnhubClient:
    """Finnhub API クライアント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Finnhub APIキー（環境変数から自動取得）
        """
        self.api_key = api_key or os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY environment variable not set")
        
        self.base_url = "https://finnhub.io/api/v1"
        self.session = requests.Session()
        
        # レート制限: 60req/分 → 安全マージンで50req/分
        self.rate_limit_per_minute = 50
        self.last_request_time = 0
        self.request_interval = 60 / self.rate_limit_per_minute  # 1.2秒間隔
        
        logger.info(f"✅ Finnhub API initialized (Rate limit: {self.rate_limit_per_minute}/min)")
    
    def _wait_for_rate_limit(self):
        """レート制限の待機処理"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            wait_time = self.request_interval - time_since_last
            logger.debug(f"⏳ Rate limit wait: {wait_time:.1f} seconds")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """
        API リクエストの実行
        
        Args:
            endpoint: APIエンドポイント
            params: パラメータ辞書
            
        Returns:
            APIレスポンス
        """
        self._wait_for_rate_limit()
        
        # APIキーを追加
        params['token'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # エラーチェック
            if isinstance(data, dict) and 'error' in data:
                raise Exception(f"Finnhub API error: {data['error']}")
            
            logger.debug(f"✅ Finnhub request successful: {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Finnhub request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Finnhub API error: {e}")
            raise
    
    def get_stock_candles(
        self,
        symbol: str,
        resolution: str = "D",
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        count: Optional[int] = None
    ) -> pd.DataFrame:
        """
        株式キャンドルスティックデータ取得
        
        Args:
            symbol: 株式シンボル (例: "AAPL", "MSFT")
            resolution: 解像度 (1, 5, 15, 30, 60, D, W, M)
            from_timestamp: 開始タイムスタンプ (UNIX)
            to_timestamp: 終了タイムスタンプ (UNIX)  
            count: データ件数 (最大5000)
            
        Returns:
            pandas.DataFrame: 日付、OHLCV データ
        """
        # デフォルト値設定
        if to_timestamp is None:
            to_timestamp = int(datetime.now().timestamp())
        
        if from_timestamp is None:
            if count:
                # countベースで開始日計算
                if resolution == "D":
                    days_back = count
                elif resolution == "W":
                    days_back = count * 7
                elif resolution == "M":
                    days_back = count * 30
                else:
                    days_back = count  # 分足の場合
                
                from_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp())
            else:
                # デフォルトで1年前から
                from_timestamp = int((datetime.now() - timedelta(days=365)).timestamp())
        
        params = {
            'symbol': symbol,
            'resolution': resolution,
            'from': from_timestamp,
            'to': to_timestamp
        }
        
        logger.info(f"📊 Requesting candles: {symbol} ({resolution})")
        
        data = self._make_request("stock/candle", params)
        
        if data.get('s') != 'ok' or not data.get('c'):
            logger.warning(f"⚠️ No candle data for {symbol}")
            return pd.DataFrame()
        
        # データフレーム変換
        df = pd.DataFrame({
            'timestamp': data['t'],
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        
        if df.empty:
            logger.warning(f"⚠️ Empty candle data for {symbol}")
            return df
        
        # タイムスタンプを日付に変換
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.drop('timestamp', axis=1)
        
        # データ型変換
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 日付でソート（古い順）
        df = df.sort_values('datetime')
        df = df.reset_index(drop=True)
        
        logger.info(f"✅ Retrieved {len(df)} candle records for {symbol}")
        return df
    
    def get_series_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        統合クライアント互換性のためのアダプターメソッド
        
        Args:
            symbol: シンボル 
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            
        Returns:
            pandas.DataFrame: 価格データ
        """
        # 日付をタイムスタンプに変換
        from_timestamp = int(pd.to_datetime(start_date).timestamp())
        to_timestamp = int(pd.to_datetime(end_date).timestamp())
        
        # 仮想通貨かどうかの判定（簡易）
        if any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'USDT', 'USDC', 'BINANCE:']):
            return self.get_crypto_candles(
                symbol=symbol,
                resolution="D",
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
        else:
            return self.get_stock_candles(
                symbol=symbol,
                resolution="D", 
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
    
    def get_quote(self, symbol: str) -> Dict:
        """
        リアルタイム株式価格取得
        
        Args:
            symbol: 株式シンボル
            
        Returns:
            価格情報辞書
        """
        params = {'symbol': symbol}
        
        logger.info(f"💰 Requesting quote: {symbol}")
        
        data = self._make_request("quote", params)
        
        if not data:
            logger.warning(f"⚠️ No quote data for {symbol}")
            return {}
        
        logger.info(f"✅ Quote retrieved for {symbol}: ${data.get('c', 'N/A')}")
        return data
    
    def search_symbol(self, query: str) -> List[Dict]:
        """
        シンボル検索
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索結果リスト
        """
        params = {'q': query}
        
        logger.info(f"🔍 Searching symbol: {query}")
        
        try:
            data = self._make_request("search", params)
            
            if 'result' in data:
                results = data['result']
                logger.info(f"✅ Found {len(results)} symbols for '{query}'")
                return results
            else:
                logger.warning(f"⚠️ No search results for '{query}'")
                return []
                
        except Exception as e:
            logger.error(f"❌ Symbol search failed for '{query}': {e}")
            return []
    
    def get_crypto_candles(
        self,
        symbol: str,
        resolution: str = "D",
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        count: Optional[int] = None
    ) -> pd.DataFrame:
        """
        仮想通貨キャンドルスティックデータ取得
        
        Args:
            symbol: 仮想通貨シンボル (例: "BINANCE:BTCUSDT")
            resolution: 解像度 (1, 5, 15, 30, 60, D, W, M)
            from_timestamp: 開始タイムスタンプ (UNIX)
            to_timestamp: 終了タイムスタンプ (UNIX)
            count: データ件数
            
        Returns:
            pandas.DataFrame: 日付、OHLCV データ
        """
        # デフォルト値設定
        if to_timestamp is None:
            to_timestamp = int(datetime.now().timestamp())
        
        if from_timestamp is None:
            if count:
                days_back = count if resolution == "D" else count * 7
                from_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp())
            else:
                from_timestamp = int((datetime.now() - timedelta(days=365)).timestamp())
        
        params = {
            'symbol': symbol,
            'resolution': resolution,
            'from': from_timestamp,
            'to': to_timestamp
        }
        
        logger.info(f"📊 Requesting crypto candles: {symbol} ({resolution})")
        
        data = self._make_request("crypto/candle", params)
        
        if data.get('s') != 'ok' or not data.get('c'):
            logger.warning(f"⚠️ No crypto candle data for {symbol}")
            return pd.DataFrame()
        
        # データフレーム変換 (stock_candlesと同じ処理)
        df = pd.DataFrame({
            'timestamp': data['t'],
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        
        if df.empty:
            logger.warning(f"⚠️ Empty crypto candle data for {symbol}")
            return df
        
        # タイムスタンプを日付に変換
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.drop('timestamp', axis=1)
        
        # データ型変換
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 日付でソート（古い順）
        df = df.sort_values('datetime')
        df = df.reset_index(drop=True)
        
        logger.info(f"✅ Retrieved {len(df)} crypto candle records for {symbol}")
        return df
    
    def test_connection(self) -> bool:
        """
        接続テスト
        
        Returns:
            接続成功可否
        """
        try:
            # 簡単なクエリでテスト (Apple株)
            data = self.get_quote("AAPL")
            
            if data and 'c' in data:
                logger.info("✅ Finnhub API connection test successful")
                return True
            else:
                logger.warning("⚠️ Finnhub API connection test failed - no data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Finnhub API connection test failed: {e}")
            return False

def main():
    """テスト実行"""
    try:
        # .env ファイル読み込み（テスト実行用）
        try:
            from dotenv import load_dotenv
            import sys
            import os
            
            # プロジェクトルートの.envを読み込み
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            env_path = os.path.join(project_root, '.env')
            load_dotenv(env_path)
            logger.info(f"✅ Loaded .env from {env_path}")
        except ImportError:
            logger.warning("⚠️ python-dotenv not available, using system environment variables")
        except Exception as e:
            logger.warning(f"⚠️ Could not load .env: {e}")
        
        # クライアント初期化
        client = FinnhubClient()
        
        # 接続テスト
        if not client.test_connection():
            logger.error("❌ Connection test failed")
            return
        
        # Apple株価取得テスト
        print("\n=== AAPL Quote Test ===")
        aapl_quote = client.get_quote("AAPL")
        if aapl_quote:
            print(f"AAPL Price: ${aapl_quote.get('c', 'N/A')}")
            print(f"Change: {aapl_quote.get('d', 'N/A')} ({aapl_quote.get('dp', 'N/A')}%)")
        
        # シンボル検索テスト
        print("\n=== Symbol Search Test ===")
        search_results = client.search_symbol("apple")
        for result in search_results[:3]:  # 上位3件
            print(f"Symbol: {result.get('symbol', 'N/A')}, Description: {result.get('description', 'N/A')}")
        
        # 株式時系列データテスト（小さなデータセット）
        print("\n=== Stock Candles Test ===")
        
        candles_data = client.get_stock_candles(
            symbol="AAPL",
            resolution="D",
            count=7  # 過去7日間
        )
        
        if not candles_data.empty:
            print(f"Retrieved {len(candles_data)} days of AAPL data")
            print(f"Latest close: ${candles_data.iloc[-1]['close']:.2f}")
            print(f"Date range: {candles_data.iloc[0]['datetime'].date()} to {candles_data.iloc[-1]['datetime'].date()}")
        
        # 仮想通貨データテスト（可能であれば）
        print("\n=== Crypto Test ===")
        try:
            crypto_data = client.get_crypto_candles(
                symbol="BINANCE:BTCUSDT",
                resolution="D",
                count=5  # 過去5日間
            )
            
            if not crypto_data.empty:
                print(f"Retrieved {len(crypto_data)} days of BTC data")
                print(f"Latest close: ${crypto_data.iloc[-1]['close']:.2f}")
            else:
                print("No crypto data available (may require premium plan)")
                
        except Exception as e:
            print(f"Crypto data not available: {e}")
        
        print("\n✅ All tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()