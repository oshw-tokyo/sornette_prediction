#!/usr/bin/env python3
"""
FRED (Federal Reserve Economic Data) クライアント実装

目的: Yahoo Finance API制限を回避し、信頼性の高い政府データソースから
     S&P500歴史データを取得する

FRED API の利点:
- 政府機関による高信頼性データ
- 無料利用可能（APIキー必要）
- 豊富な歴史データ（数十年分）
- 120 requests/60秒の十分な制限
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import Optional, Dict, List
import json

class FREDDataClient:
    """FRED (Federal Reserve Economic Data) クライアント"""
    
    # FRED で利用可能な主要指数
    AVAILABLE_INDICES = {
        'SP500': 'SP500',  # S&P 500 Index
        'DJIA': 'DJIA',    # Dow Jones Industrial Average  
        'NASDAQCOM': 'NASDAQCOM',  # NASDAQ Composite Index
        'VIXCLS': 'VIXCLS'  # VIX Volatility Index
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        FREDクライアント初期化
        
        Args:
            api_key: FRED API key (環境変数 FRED_API_KEY からも取得可能)
        """
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = requests.Session()
        
        if not self.api_key:
            print("⚠️ FRED API key が設定されていません")
            print("   1. https://fred.stlouisfed.org/docs/api/api_key.html でAPIキーを取得")
            print("   2. 環境変数 FRED_API_KEY に設定するか、初期化時に指定")
    
    def get_series_data(self, series_id: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        FRED時系列データを取得
        
        Args:
            series_id: FREDシリーズID (例: 'SP500')
            start_date: 開始日 (YYYY-MM-DD形式)
            end_date: 終了日 (YYYY-MM-DD形式)
            
        Returns:
            DataFrame: 日付をインデックスとする価格データ
        """
        if not self.api_key:
            print("❌ APIキーが設定されていません")
            return None
        
        print(f"📊 FRED データ取得中: {series_id} ({start_date} - {end_date})")
        
        # API parameters
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'observation_start': start_date,
            'observation_end': end_date,
            'sort_order': 'asc'
        }
        
        try:
            # データ取得リクエスト
            url = f"{self.base_url}/series/observations"
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'observations' in data:
                    # DataFrameに変換
                    observations = data['observations']
                    df = pd.DataFrame(observations)
                    
                    # 必要なカラムの存在チェック
                    if 'value' not in df.columns or 'date' not in df.columns:
                        print(f"❌ 予期しないデータ形式: {df.columns.tolist()}")
                        return None
                    
                    # データクリーニング
                    df = df[df['value'] != '.']  # 欠損値 '.' を除去
                    df = df.dropna(subset=['value'])  # NaN値を除去
                    
                    if df.empty:
                        print("❌ 有効なデータがありません")
                        return None
                    
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    
                    # NaN値が生成された行を除去
                    df = df.dropna()
                    
                    if df.empty:
                        print("❌ 数値変換後にデータが空になりました")
                        return None
                    
                    # インデックス設定とソート
                    df.set_index('date', inplace=True)
                    df.sort_index(inplace=True)
                    
                    # カラム名を標準化
                    df.rename(columns={'value': 'Close'}, inplace=True)
                    
                    print(f"✅ FRED データ取得成功: {len(df)}日分")
                    print(f"   期間: {df.index[0].date()} - {df.index[-1].date()}")
                    print(f"   価格範囲: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
                    
                    return df
                else:
                    print(f"❌ データが見つかりません: {data}")
                    return None
            
            elif response.status_code == 400:
                print(f"❌ 不正なリクエスト: {response.text}")
                return None
            elif response.status_code == 429:
                print("❌ レート制限に達しました。しばらく待ってから再試行してください")
                return None
            else:
                print(f"❌ API エラー ({response.status_code}): {response.text}")
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
    
    def get_sp500_data(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        S&P 500データの取得（便利メソッド）
        
        Args:
            start_date: 開始日 (YYYY-MM-DD形式)
            end_date: 終了日 (YYYY-MM-DD形式)
            
        Returns:
            DataFrame: S&P500価格データ
        """
        return self.get_series_data('SP500', start_date, end_date)
    
    def test_connection(self) -> bool:
        """API接続テスト"""
        print("🔍 FRED API接続テスト中...")
        
        if not self.api_key:
            print("❌ APIキーが設定されていません")
            return False
        
        try:
            # 最近の少量データで接続テスト
            recent_date = datetime.now().strftime('%Y-%m-%d')
            past_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            test_data = self.get_series_data('SP500', past_date, recent_date)
            
            if test_data is not None and len(test_data) > 0:
                print("✅ FRED API接続成功")
                return True
            else:
                print("❌ FRED API接続失敗: データが取得できません")
                return False
                
        except Exception as e:
            print(f"❌ FRED API接続テストエラー: {e}")
            return False
    
    def get_available_date_range(self, series_id: str) -> Optional[Dict]:
        """
        指定シリーズの利用可能日付範囲を取得
        
        Args:
            series_id: FREDシリーズID
            
        Returns:
            Dict: {'start': start_date, 'end': end_date} or None
        """
        if not self.api_key:
            return None
        
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json'
        }
        
        try:
            url = f"{self.base_url}/series"
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'seriess' in data and len(data['seriess']) > 0:
                    series_info = data['seriess'][0]
                    return {
                        'start': series_info.get('observation_start'),
                        'end': series_info.get('observation_end'),
                        'title': series_info.get('title'),
                        'frequency': series_info.get('frequency'),
                        'units': series_info.get('units')
                    }
            
            return None
            
        except Exception as e:
            print(f"エラー: {e}")
            return None

def setup_fred_api():
    """FRED API設定のガイダンス"""
    print("=== FRED API セットアップガイド ===\n")
    
    print("1. FRED APIキーの取得:")
    print("   - https://fred.stlouisfed.org/docs/api/api_key.html にアクセス")
    print("   - 無料アカウントを作成")
    print("   - APIキーを取得")
    
    print("\n2. APIキーの設定方法:")
    print("   方法A: 環境変数に設定")
    print("   export FRED_API_KEY='your_api_key_here'")
    
    print("\n   方法B: .envファイルに記載")
    print("   FRED_API_KEY=your_api_key_here")
    
    print("\n   方法C: コード内で直接指定")
    print("   client = FREDDataClient(api_key='your_api_key_here')")
    
    print("\n3. 利用制限:")
    print("   - 120 requests per 60 seconds")
    print("   - 完全無料")
    print("   - 政府機関による高信頼性データ")

def test_fred_implementation():
    """FRED実装のテスト"""
    print("=== FRED実装テスト ===\n")
    
    # FREDクライアント初期化
    client = FREDDataClient()
    
    # 接続テスト
    if not client.test_connection():
        print("❌ FRED API接続に失敗しました")
        print("\n🔧 解決方法:")
        setup_fred_api()
        return None
    
    # 1987年データ取得テスト
    print("\n📊 1987年ブラックマンデーデータ取得テスト")
    
    start_date = "1985-01-01"
    end_date = "1987-10-31"
    
    sp500_data = client.get_sp500_data(start_date, end_date)
    
    if sp500_data is not None:
        print(f"\n🎉 1987年データ取得成功!")
        
        # 1987年データの詳細分析
        data_1987 = sp500_data[sp500_data.index.year == 1987]
        print(f"   1987年データ: {len(data_1987)}日分")
        
        if len(data_1987) > 0:
            # ブラックマンデー周辺の価格変動
            october_1987 = data_1987[data_1987.index.month == 10]
            if len(october_1987) > 0:
                print(f"   1987年10月データ: {len(october_1987)}日分")
                print(f"   10月最高値: {october_1987['Close'].max():.2f}")
                print(f"   10月最安値: {october_1987['Close'].min():.2f}")
                print(f"   10月下落率: {((october_1987['Close'].iloc[-1] / october_1987['Close'].iloc[0]) - 1) * 100:.1f}%")
        
        return sp500_data
    
    else:
        print("❌ 1987年データ取得に失敗")
        return None

def main():
    """メイン実行関数"""
    print("🎯 FRED API実装・テスト開始\n")
    
    # API設定ガイド表示
    if not os.getenv('FRED_API_KEY'):
        setup_fred_api()
        print("\n" + "="*50)
        print("APIキー設定後、再度実行してください")
        return
    
    # FRED実装テスト
    data = test_fred_implementation()
    
    if data is not None:
        print(f"\n✅ FRED APIによる実市場データ取得成功")
        print(f"✅ 1987年ブラックマンデーデータ準備完了")
        print(f"✅ 実市場データでのLPPL検証が可能")
        
        print(f"\n📋 Next Steps:")
        print("1. FREDデータを使用したLPPL実市場検証の実行")
        print("2. 論文値との詳細比較")
        print("3. 実用システムでの運用テスト")
        
    else:
        print(f"\n❌ FRED API実装に問題があります")
        print("代替API検討が必要です")

if __name__ == "__main__":
    main()