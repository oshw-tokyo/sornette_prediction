#!/usr/bin/env python3
"""
Alpha Vantage API クライアント実装

目的: Yahoo Finance制限を回避し、信頼性の高い金融データを取得

Alpha Vantage の利点:
- 無料プランあり（500 calls/日）
- 20年以上の歴史データ
- 高品質なデータ
- 株価、指数、為替、商品など幅広いデータ
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import Optional, Dict
import json

class AlphaVantageClient:
    """Alpha Vantage API クライアント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Alpha Vantageクライアント初期化
        
        Args:
            api_key: Alpha Vantage API key (環境変数 ALPHA_VANTAGE_KEY からも取得可能)
        """
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_KEY')
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()
        
        if not self.api_key:
            print("⚠️ Alpha Vantage API key が設定されていません")
            print("   1. https://www.alphavantage.co/support/#api-key で無料APIキーを取得")
            print("   2. 環境変数 ALPHA_VANTAGE_KEY に設定するか、初期化時に指定")
    
    def get_daily_data(self, symbol: str, outputsize: str = 'full') -> Optional[pd.DataFrame]:
        """
        日次株価データを取得
        
        Args:
            symbol: 銘柄シンボル (例: 'SPY' for S&P 500 ETF)
            outputsize: 'compact' (最新100日) or 'full' (20年分)
            
        Returns:
            DataFrame: 株価データ (OHLCV)
        """
        if not self.api_key:
            print("❌ APIキーが設定されていません")
            return None
        
        print(f"📊 Alpha Vantage データ取得中: {symbol} ({outputsize})")
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize,
            'apikey': self.api_key
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # エラーメッセージチェック
                if 'Error Message' in data:
                    print(f"❌ API エラー: {data['Error Message']}")
                    return None
                
                if 'Note' in data:
                    print(f"⚠️ API制限: {data['Note']}")
                    return None
                
                # データ存在チェック
                if 'Time Series (Daily)' not in data:
                    print(f"❌ データが見つかりません: {list(data.keys())}")
                    return None
                
                # データ変換
                time_series = data['Time Series (Daily)']
                
                # DataFrameに変換
                df = pd.DataFrame.from_dict(time_series, orient='index')
                
                # データ型とカラム名の調整
                df.index = pd.to_datetime(df.index)
                df = df.astype(float)
                
                # カラム名を標準化
                column_mapping = {
                    '1. open': 'Open',
                    '2. high': 'High', 
                    '3. low': 'Low',
                    '4. close': 'Close',
                    '5. volume': 'Volume'
                }
                df.rename(columns=column_mapping, inplace=True)
                
                # 日付順でソート
                df.sort_index(inplace=True)
                
                print(f"✅ Alpha Vantage データ取得成功: {len(df)}日分")
                print(f"   期間: {df.index[0].date()} - {df.index[-1].date()}")
                print(f"   価格範囲: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
                
                return df
            
            else:
                print(f"❌ HTTP エラー ({response.status_code}): {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ リクエストタイムアウト")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ ネットワークエラー: {e}")
            return None
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            return None
    
    def get_sp500_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        S&P 500データの取得（SPY ETFを使用）
        
        Args:
            start_date: 開始日 (YYYY-MM-DD形式、Noneで全期間)
            end_date: 終了日 (YYYY-MM-DD形式、Noneで全期間)
            
        Returns:
            DataFrame: S&P500価格データ
        """
        # SPY ETF（S&P500追跡）のデータを取得
        data = self.get_daily_data('SPY', outputsize='full')
        
        if data is None:
            return None
        
        # 日付範囲でフィルタリング
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        return data
    
    def test_connection(self) -> bool:
        """API接続テスト"""
        print("🔍 Alpha Vantage API接続テスト中...")
        
        if not self.api_key:
            print("❌ APIキーが設定されていません")
            return False
        
        try:
            # 少量データで接続テスト
            test_data = self.get_daily_data('SPY', outputsize='compact')
            
            if test_data is not None and len(test_data) > 0:
                print("✅ Alpha Vantage API接続成功")
                return True
            else:
                print("❌ Alpha Vantage API接続失敗: データが取得できません")
                return False
                
        except Exception as e:
            print(f"❌ Alpha Vantage API接続テストエラー: {e}")
            return False
    
    def get_1987_black_monday_data(self) -> Optional[pd.DataFrame]:
        """1987年ブラックマンデー前後のデータを取得"""
        print("📊 1987年ブラックマンデーデータ取得中...")
        
        # 全データを取得してから期間でフィルタ
        full_data = self.get_sp500_data()
        
        if full_data is None:
            return None
        
        # 1985-1987年のデータを抽出
        start_date = '1985-01-01'
        end_date = '1987-10-31'
        
        period_data = full_data[(full_data.index >= start_date) & (full_data.index <= end_date)]
        
        if len(period_data) > 0:
            print(f"✅ 1987年期間データ取得成功: {len(period_data)}日分")
            
            # 1987年10月（ブラックマンデー）の詳細
            october_1987 = period_data[
                (period_data.index.year == 1987) & (period_data.index.month == 10)
            ]
            
            if len(october_1987) > 0:
                print(f"   1987年10月データ: {len(october_1987)}日分")
                oct_start = october_1987['Close'].iloc[0]
                oct_end = october_1987['Close'].iloc[-1]
                oct_change = ((oct_end / oct_start) - 1) * 100
                print(f"   10月変動: {oct_change:.1f}%")
            
            return period_data
        else:
            print("❌ 指定期間のデータが見つかりません")
            return None

def setup_alpha_vantage_api():
    """Alpha Vantage API設定のガイダンス"""
    print("=== Alpha Vantage API セットアップガイド ===\n")
    
    print("1. Alpha Vantage APIキーの取得:")
    print("   - https://www.alphavantage.co/support/#api-key にアクセス")
    print("   - 名前とメールアドレスで無料登録")
    print("   - APIキーを取得（即座に利用可能）")
    
    print("\n2. APIキーの設定方法:")
    print("   方法A: 環境変数に設定")
    print("   export ALPHA_VANTAGE_KEY='your_api_key_here'")
    
    print("\n   方法B: .envファイルに記載")
    print("   ALPHA_VANTAGE_KEY=your_api_key_here")
    
    print("\n   方法C: コード内で直接指定")
    print("   client = AlphaVantageClient(api_key='your_api_key_here')")
    
    print("\n3. 利用制限:")
    print("   - 無料プラン: 5 API calls/分, 500 calls/日")
    print("   - 有料プラン: $49.99/月で制限緩和")
    print("   - 20年以上の歴史データ")

def test_alpha_vantage_implementation():
    """Alpha Vantage実装のテスト"""
    print("=== Alpha Vantage実装テスト ===\n")
    
    # Alpha Vantageクライアント初期化
    client = AlphaVantageClient()
    
    # 接続テスト
    if not client.test_connection():
        print("❌ Alpha Vantage API接続に失敗しました")
        print("\n🔧 解決方法:")
        setup_alpha_vantage_api()
        return None
    
    # 1987年データ取得テスト
    print("\n📊 1987年ブラックマンデーデータ取得テスト")
    
    data_1987 = client.get_1987_black_monday_data()
    
    if data_1987 is not None:
        print(f"\n🎉 1987年データ取得成功!")
        print(f"   総データ数: {len(data_1987)}日分")
        print(f"   期間: {data_1987.index[0].date()} - {data_1987.index[-1].date()}")
        
        # データ品質チェック
        print(f"\n📋 データ品質チェック:")
        print(f"   欠損値: {data_1987.isnull().sum().sum()}")
        print(f"   価格範囲: ${data_1987['Close'].min():.2f} - ${data_1987['Close'].max():.2f}")
        
        # 年別データ分布
        yearly_counts = data_1987.groupby(data_1987.index.year).size()
        print(f"   年別データ数:")
        for year, count in yearly_counts.items():
            print(f"     {year}年: {count}日")
        
        return data_1987
    
    else:
        print("❌ 1987年データ取得に失敗")
        return None

def create_unified_data_client():
    """統合データクライアントの作成"""
    
    unified_client_code = '''#!/usr/bin/env python3
"""
統合金融データクライアント

複数のAPIを統合し、フォールバック機能を提供
- Alpha Vantage (プライマリ)
- FRED (セカンダリ)
- エラーハンドリングと自動切り替え
"""

import pandas as pd
from typing import Optional, Tuple
import time

from .alpha_vantage_client import AlphaVantageClient
from .fred_data_client import FREDDataClient

class UnifiedDataClient:
    """統合データクライアント"""
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, fred_key: Optional[str] = None):
        self.av_client = AlphaVantageClient(alpha_vantage_key)
        self.fred_client = FREDDataClient(fred_key)
        
        # 利用可能なクライアントをチェック
        self.available_clients = []
        
        if self.av_client.test_connection():
            self.available_clients.append(('alpha_vantage', self.av_client))
            
        if self.fred_client.test_connection():
            self.available_clients.append(('fred', self.fred_client))
        
        print(f"利用可能なデータソース: {len(self.available_clients)}")
    
    def get_sp500_historical_data(self, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
        """
        S&P500歴史データを複数ソースから取得
        
        Returns:
            (data, source): データとソース名
        """
        
        for source_name, client in self.available_clients:
            try:
                print(f"🔄 {source_name} でデータ取得試行中...")
                
                if source_name == 'alpha_vantage':
                    data = client.get_sp500_data(start_date, end_date)
                elif source_name == 'fred':
                    data = client.get_sp500_data(start_date, end_date)
                
                if data is not None and len(data) > 0:
                    print(f"✅ {source_name} でデータ取得成功")
                    return data, source_name
                    
            except Exception as e:
                print(f"❌ {source_name} エラー: {str(e)[:50]}...")
                continue
            
            time.sleep(1)  # レート制限対策
        
        print("❌ 全てのデータソースで取得失敗")
        return None, "none"
'''
    
    os.makedirs('src/data_sources/', exist_ok=True)
    
    with open('src/data_sources/unified_data_client.py', 'w', encoding='utf-8') as f:
        f.write(unified_client_code)
    
    print("📁 統合クライアント保存: src/data_sources/unified_data_client.py")

def main():
    """メイン実行関数"""
    print("🎯 Alpha Vantage API実装・テスト開始\n")
    
    # API設定ガイド表示
    if not os.getenv('ALPHA_VANTAGE_KEY'):
        setup_alpha_vantage_api()
        print("\n" + "="*50)
        print("APIキー設定後、再度実行してください")
        return
    
    # Alpha Vantage実装テスト
    data = test_alpha_vantage_implementation()
    
    if data is not None:
        print(f"\n✅ Alpha Vantage APIによる実市場データ取得成功")
        print(f"✅ 1987年ブラックマンデーデータ準備完了")
        print(f"✅ 実市場データでのLPPL検証が可能")
        
        # 統合クライアント作成
        create_unified_data_client()
        
        print(f"\n📋 Next Steps:")
        print("1. Alpha Vantageデータを使用したLPPL実市場検証の実行")
        print("2. 論文値との詳細比較")
        print("3. 統合データクライアントでの運用テスト")
        
    else:
        print(f"\n❌ Alpha Vantage API実装に問題があります")

if __name__ == "__main__":
    main()