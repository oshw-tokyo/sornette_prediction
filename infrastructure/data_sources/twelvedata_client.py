#!/usr/bin/env python3
"""
Twelve Data API Client
- 制限: 800req/日 (無料プラン)
- 対応: 仮想通貨+株式+FX
- CoinGecko代替の最優先候補
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

class TwelveDataClient:
    """Twelve Data API クライアント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Twelve Data APIキー（環境変数から自動取得）
        """
        self.api_key = api_key or os.getenv('TWELVE_DATA_API_KEY')
        if not self.api_key:
            raise ValueError("TWELVE_DATA_API_KEY environment variable not set")
        
        self.base_url = "https://api.twelvedata.com"
        self.session = requests.Session()
        
        # レート制限: 800req/日 → 約33req/時間 → 安全マージンで30req/時間
        self.rate_limit_per_hour = 30
        self.last_request_time = 0
        self.request_interval = 3600 / self.rate_limit_per_hour  # 120秒間隔
        
        logger.info(f"✅ Twelve Data API initialized (Rate limit: {self.rate_limit_per_hour}/hour)")
    
    def _wait_for_rate_limit(self):
        """レート制限の待機処理"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            wait_time = self.request_interval - time_since_last
            logger.info(f"⏳ Rate limit wait: {wait_time:.1f} seconds")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
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
        params['apikey'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # エラーチェック
            if 'status' in data and data['status'] == 'error':
                raise Exception(f"Twelve Data API error: {data.get('message', 'Unknown error')}")
            
            logger.debug(f"✅ Twelve Data request successful: {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Twelve Data request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Twelve Data API error: {e}")
            raise
    
    def get_time_series(
        self,
        symbol: str,
        interval: str = "1day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        outputsize: int = 5000
    ) -> pd.DataFrame:
        """
        時系列データの取得
        
        Args:
            symbol: シンボル (例: "BTC/USD", "AAPL", "EUR/USD")
            interval: データ間隔 (1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month)
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            outputsize: 最大データ数
            
        Returns:
            pandas.DataFrame: 日付、価格データ
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'outputsize': outputsize,
            'format': 'JSON'
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        logger.info(f"📊 Requesting time series: {symbol} ({interval})")
        
        data = self._make_request("time_series", params)
        
        if 'values' not in data:
            logger.warning(f"⚠️ No time series data for {symbol}")
            return pd.DataFrame()
        
        # データフレーム変換
        df = pd.DataFrame(data['values'])
        
        if df.empty:
            logger.warning(f"⚠️ Empty time series data for {symbol}")
            return df
        
        # データ型変換（volume列の存在確認）
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        
        # volume列が存在する場合のみ変換
        if 'volume' in df.columns:
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        else:
            logger.warning(f"⚠️ Volume data not available for {symbol}")
            df['volume'] = 0  # デフォルト値設定
        
        # 日付でソート（古い順）
        df = df.sort_values('datetime')
        df = df.reset_index(drop=True)
        
        # 統合クライアント互換性のため日付カラム名をdateに変更
        df = df.rename(columns={'datetime': 'date'})
        
        logger.info(f"✅ Retrieved {len(df)} records for {symbol}")
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
        return self.get_time_series(
            symbol=symbol,
            interval="1day",
            start_date=start_date,
            end_date=end_date,
            outputsize=5000
        )
    
    def search_symbol(self, query: str) -> List[Dict]:
        """
        シンボル検索
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索結果リスト
        """
        params = {'symbol': query}
        
        logger.info(f"🔍 Searching symbol: {query}")
        
        try:
            data = self._make_request("symbol_search", params)
            
            if 'data' in data:
                results = data['data']
                logger.info(f"✅ Found {len(results)} symbols for '{query}'")
                return results
            else:
                logger.warning(f"⚠️ No search results for '{query}'")
                return []
                
        except Exception as e:
            logger.error(f"❌ Symbol search failed for '{query}': {e}")
            return []
    
    def get_quote(self, symbol: str) -> Dict:
        """
        リアルタイム価格取得
        
        Args:
            symbol: シンボル
            
        Returns:
            価格情報辞書
        """
        params = {'symbol': symbol}
        
        logger.info(f"💰 Requesting quote: {symbol}")
        
        data = self._make_request("quote", params)
        
        if not data:
            logger.warning(f"⚠️ No quote data for {symbol}")
            return {}
        
        logger.info(f"✅ Quote retrieved for {symbol}: ${data.get('close', 'N/A')}")
        return data
    
    def test_connection(self) -> bool:
        """
        接続テスト
        
        Returns:
            接続成功可否
        """
        try:
            # 簡単なクエリでテスト
            data = self.get_quote("BTC/USD")
            
            if data and 'close' in data:
                logger.info("✅ Twelve Data API connection test successful")
                return True
            else:
                logger.warning("⚠️ Twelve Data API connection test failed - no data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Twelve Data API connection test failed: {e}")
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
        client = TwelveDataClient()
        
        # 接続テスト
        if not client.test_connection():
            logger.error("❌ Connection test failed")
            return
        
        # BTC価格取得テスト
        print("\n=== BTC Quote Test ===")
        btc_quote = client.get_quote("BTC/USD")
        if btc_quote:
            print(f"BTC Price: ${btc_quote.get('close', 'N/A')}")
        
        # シンボル検索テスト
        print("\n=== Symbol Search Test ===")
        search_results = client.search_symbol("bitcoin")
        for result in search_results[:3]:  # 上位3件
            print(f"Symbol: {result.get('symbol', 'N/A')}, Name: {result.get('instrument_name', 'N/A')}")
        
        # 時系列データテスト（小さなデータセット）
        print("\n=== Time Series Test ===")
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        ts_data = client.get_time_series(
            symbol="BTC/USD",
            start_date=start_date,
            end_date=end_date,
            outputsize=10
        )
        
        if not ts_data.empty:
            print(f"Retrieved {len(ts_data)} days of BTC data")
            print(f"Latest close: ${ts_data.iloc[-1]['close']:.2f}")
            print(f"Date range: {ts_data.iloc[0]['datetime'].date()} to {ts_data.iloc[-1]['datetime'].date()}")
        
        print("\n✅ All tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()