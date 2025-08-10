#!/usr/bin/env python3
"""
CoinGecko API クライアント実装

目的: 仮想通貨データの安定的取得
特徴:
- 厳格なレート制限対応（実測値ベース）
- FRED互換データ形式
- エラーハンドリング・リトライ機能
- 主要仮想通貨のマッピング
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import Optional, Dict, List
import json
from pathlib import Path
import logging

class CoinGeckoClient:
    """CoinGecko API クライアント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        CoinGecko クライアント初期化
        
        Args:
            api_key: CoinGecko Pro API key (無料版はNone)
        """
        self.api_key = api_key or os.getenv('COINGECKO_API_KEY')
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        
        # レート制限設定（実測値ベース + 2025-08-10 安全マージン追加）
        if self.api_key:
            # Pro版: より緩い制限
            self.rate_limit_delay = 1.0  # 安全マージンで1秒間隔に調整
            print("✅ CoinGecko Pro API 初期化（レート制限強化）")
        else:
            # 無料版: より厳しい制限（ユーザーログに基づく調整）
            self.rate_limit_delay = 8.0  # 10回/分 → 8秒間隔（安全マージン）
            print("⚠️ CoinGecko 無料API 初期化（レート制限強化）")
        
        self.last_request_time = 0
        self.max_retries = 3
        
        # ログ設定
        self.logger = logging.getLogger(__name__)
        
        # 主要仮想通貨マッピング（CoinGecko API調査結果に基づく正確なマッピング）
        # 注意：カタログから直接CoinGecko IDが渡される場合もあるため、
        # シンボル→ID変換とID→ID変換の両方をサポート
        self.symbol_mapping = {
            # 標準シンボル → CoinGecko ID マッピング
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'ADA': 'cardano',
            'SOL': 'solana',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'AVAX': 'avalanche-2',
            'SHIB': 'shiba-inu',
            'LINK': 'chainlink',
            'TRX': 'tron',
            'MATIC': 'matic-network',  # polygon → matic-network に修正
            'UNI': 'uniswap',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ATOM': 'cosmos',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'XLM': 'stellar',
            'FLR': 'flare-networks',
            'USDC': 'usd-coin',       # 新規追加: メインのUSD Coin
            'USDT': 'tether',         # 新規追加: Tether
            
            # カタログが直接CoinGecko IDを渡す場合の対応（ID → ID マッピング）
            'bitcoin': 'bitcoin',
            'ethereum': 'ethereum', 
            'binancecoin': 'binancecoin',
            'cardano': 'cardano',
            'solana': 'solana',
            'ripple': 'ripple',
            'polkadot': 'polkadot',
            'dogecoin': 'dogecoin',
            'avalanche-2': 'avalanche-2',
            'shiba-inu': 'shiba-inu',
            'chainlink': 'chainlink',
            'tron': 'tron',
            'matic-network': 'matic-network',
            'uniswap': 'uniswap',
            'algorand': 'algorand',
            'vechain': 'vechain',
            'cosmos': 'cosmos',
            'litecoin': 'litecoin',
            'bitcoin-cash': 'bitcoin-cash',
            'stellar': 'stellar',
            'flare-networks': 'flare-networks',
            'usd-coin': 'usd-coin',
            'tether': 'tether'
        }
        
        # 逆マッピング
        self.id_to_symbol = {v: k for k, v in self.symbol_mapping.items()}
    
    def _rate_limit(self):
        """レート制限の実装"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_request_time
        
        if time_since_last_call < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_call
            if sleep_time > 1:  # 1秒以上の場合のみ表示
                print(f"   ⏱️ CoinGecko レート制限: {sleep_time:.1f}秒待機...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        APIリクエスト実行（リトライ機能付き）
        
        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ
            
        Returns:
            Dict: APIレスポンス
        """
        url = f"{self.base_url}/{endpoint}"
        
        if params is None:
            params = {}
        
        # API key追加（Pro版の場合）
        if self.api_key:
            params['x_cg_pro_api_key'] = self.api_key
        
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # レート制限エラー
                    wait_time = min(60, (attempt + 1) * 10)  # 最大60秒
                    print(f"⚠️ CoinGecko レート制限 (試行{attempt + 1}/{self.max_retries}): {wait_time}秒待機...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ CoinGecko HTTP エラー: {response.status_code}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ CoinGecko リクエストエラー (試行{attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数バックオフ
                    continue
                else:
                    return None
        
        print(f"❌ CoinGecko: {self.max_retries}回の試行全てが失敗")
        return None
    
    def test_connection(self) -> bool:
        """API接続テスト"""
        print("🔍 CoinGecko API接続テスト中...")
        
        response = self._make_request("ping")
        
        if response:
            print("✅ CoinGecko API接続成功")
            return True
        else:
            print("❌ CoinGecko API接続失敗")
            return False
    
    def get_series_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        FRED互換インターフェース：指定期間の仮想通貨データを取得
        
        Args:
            symbol: 仮想通貨シンボル (例: 'BTC', 'ETH')
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            
        Returns:
            DataFrame: FRED互換形式のデータ（Close価格メイン）
        """
        # シンボルをCoinGecko IDに変換（統合マッピングで両形式をサポート）
        coin_id = self.symbol_mapping.get(symbol.upper()) or self.symbol_mapping.get(symbol.lower())
        
        if not coin_id:
            print(f"❌ 未対応シンボル: {symbol}")
            print(f"   サポート形式例: BTC, SOL, solana, bitcoin等")
            return None
        
        print(f"📋 CoinGecko マッピング: {symbol} -> {coin_id}")
        
        # 日数計算
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        days = (end_dt - start_dt).days + 1
        
        print(f"📊 CoinGecko {symbol} データ取得中: {days}日間")
        
        # データ取得
        response = self._make_request(
            f"coins/{coin_id}/market_chart",
            params={
                'vs_currency': 'usd',
                'days': str(min(days, 365)),  # CoinGecko制限
                'interval': 'daily'
            }
        )
        
        if not response:
            return None
        
        # データ変換
        prices = response.get('prices', [])
        volumes = response.get('total_volumes', [])
        
        if not prices:
            print(f"❌ {symbol} 価格データが空です")
            return None
        
        try:
            # DataFrameに変換
            df = pd.DataFrame(prices, columns=['timestamp', 'Close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # ボリューム追加
            if volumes:
                volume_df = pd.DataFrame(volumes, columns=['timestamp', 'Volume'])
                volume_df['timestamp'] = pd.to_datetime(volume_df['timestamp'], unit='ms')
                volume_df.set_index('timestamp', inplace=True)
                df['Volume'] = volume_df['Volume']
            else:
                df['Volume'] = 0
            
            # OHLC補完（日次データなので同値）
            df['Open'] = df['Close']
            df['High'] = df['Close']
            df['Low'] = df['Close']
            
            # 日付範囲でフィルタリング
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            
            if len(df) > 0:
                print(f"✅ CoinGecko {symbol} データ取得成功: {len(df)}日分")
                print(f"   期間: {df.index[0].date()} - {df.index[-1].date()}")
                print(f"   価格範囲: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
                
                return df
            else:
                print(f"⚠️ {symbol} 指定期間にデータがありません")
                return None
                
        except Exception as e:
            print(f"❌ {symbol} データ変換エラー: {e}")
            return None
    
    def get_supported_symbols(self) -> List[str]:
        """サポートされている仮想通貨シンボル一覧"""
        return list(self.symbol_mapping.keys())
    
    def get_coin_info(self, symbol: str) -> Optional[Dict]:
        """仮想通貨の基本情報取得"""
        coin_id = self.symbol_mapping.get(symbol.upper())
        if not coin_id:
            return None
        
        response = self._make_request(
            f"coins/{coin_id}",
            params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
        )
        
        if response:
            return {
                'id': response.get('id'),
                'symbol': response.get('symbol', '').upper(),
                'name': response.get('name'),
                'current_price': response.get('market_data', {}).get('current_price', {}).get('usd'),
                'market_cap': response.get('market_data', {}).get('market_cap', {}).get('usd'),
                'total_volume': response.get('market_data', {}).get('total_volume', {}).get('usd'),
                'market_cap_rank': response.get('market_cap_rank'),
            }
        
        return None
    
    def get_price_data(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        簡単な価格データ取得（期間指定）
        
        Args:
            symbol: 仮想通貨シンボル
            days: 取得日数
            
        Returns:
            DataFrame: 価格データ
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.get_series_data(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

def test_coingecko_client():
    """CoinGeckoクライアントのテスト"""
    print("🧪 CoinGecko クライアント テスト")
    print("=" * 50)
    
    # クライアント初期化
    client = CoinGeckoClient()
    
    # 接続テスト
    if not client.test_connection():
        print("❌ CoinGecko接続に失敗しました")
        return
    
    # サポート銘柄表示
    print(f"\n📋 サポート仮想通貨: {len(client.get_supported_symbols())}種類")
    major_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']
    print(f"主要銘柄例: {major_symbols}")
    
    # データ取得テスト（制限対策で少数のみ）
    test_symbols = ['BTC', 'ETH']  # テストは2銘柄のみ
    
    for symbol in test_symbols:
        print(f"\n🔍 {symbol} テスト:")
        
        # 基本情報取得
        info = client.get_coin_info(symbol)
        if info:
            print(f"   通貨名: {info['name']}")
            print(f"   現在価格: ${info['current_price']:,.2f}")
            print(f"   ランク: #{info['market_cap_rank']}")
        
        # 30日間データ取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        data = client.get_series_data(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if data is not None:
            print(f"   ✅ データ取得成功: {len(data)}日分")
            print(f"   最新価格: ${data['Close'].iloc[-1]:,.2f}")
        else:
            print(f"   ❌ データ取得失敗")
    
    print("\n📊 CoinGecko統合評価:")
    print("✅ 利点:")
    print("   - 20+種類の主要仮想通貨対応")
    print("   - リアルタイム市場データ")
    print("   - FRED互換インターフェース")
    print("   - エラーハンドリング・リトライ機能")
    
    print("⚠️ 制限:")
    print("   - 無料版: 3秒間隔（20 calls/minute）")
    print("   - 連続大量取得には不向き")
    print("   - FRED仮想通貨データより制限が厳しい")

if __name__ == "__main__":
    test_coingecko_client()