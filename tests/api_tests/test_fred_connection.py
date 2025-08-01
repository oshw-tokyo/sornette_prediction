#!/usr/bin/env python3
"""
FRED API接続テスト

目的: 取得したFRED APIキーの動作確認と1987年データの取得テスト
"""

import sys
import os
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.data_sources.fred_data_client import FREDDataClient

def test_fred_api_connection():
    """FRED API接続の基本テスト"""
    print("=== FRED API 接続テスト ===\n")
    
    # APIキーの確認
    api_key = os.getenv('FRED_API_KEY')
    if api_key:
        print(f"✅ APIキー確認: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("❌ APIキーが環境変数に設定されていません")
        return False
    
    # FREDクライアント初期化
    client = FREDDataClient()
    
    # 基本接続テスト
    print("🔍 FRED API基本接続テスト中...")
    if client.test_connection():
        print("✅ FRED API接続成功!")
        return True
    else:
        print("❌ FRED API接続失敗")
        return False

def test_sp500_data_retrieval():
    """S&P500データ取得テスト"""
    print("\n=== S&P500 データ取得テスト ===\n")
    
    client = FREDDataClient()
    
    # 最近のデータ取得テスト
    print("📊 最近のS&P500データ取得テスト...")
    recent_data = client.get_sp500_data("2023-01-01", "2023-12-31")
    
    if recent_data is not None and len(recent_data) > 0:
        print(f"✅ 最近データ取得成功: {len(recent_data)}日分")
        print(f"   期間: {recent_data.index[0].date()} - {recent_data.index[-1].date()}")
        print(f"   価格範囲: {recent_data['Close'].min():.2f} - {recent_data['Close'].max():.2f}")
        
        # データサンプル表示
        print(f"\n📋 データサンプル（最新5日）:")
        for idx, row in recent_data.tail().iterrows():
            print(f"   {idx.date()}: {row['Close']:.2f}")
        
        return True
    else:
        print("❌ 最近データ取得失敗")
        return False

def test_1987_black_monday_data():
    """1987年ブラックマンデーデータ取得テスト"""
    print("\n=== 1987年ブラックマンデー データ取得テスト ===\n")
    
    client = FREDDataClient()
    
    # 1987年前後のデータ取得
    print("📊 1987年前後のS&P500データ取得中...")
    data_1987 = client.get_sp500_data("1985-01-01", "1987-10-31")
    
    if data_1987 is not None and len(data_1987) > 0:
        print(f"✅ 1987年データ取得成功: {len(data_1987)}日分")
        print(f"   全期間: {data_1987.index[0].date()} - {data_1987.index[-1].date()}")
        
        # 1987年データの詳細分析
        data_1987_year = data_1987[data_1987.index.year == 1987]
        if len(data_1987_year) > 0:
            print(f"   1987年データ: {len(data_1987_year)}日分")
            
            # 1987年10月の分析（ブラックマンデー）
            october_1987 = data_1987_year[data_1987_year.index.month == 10]
            if len(october_1987) > 0:
                print(f"   1987年10月: {len(october_1987)}日分")
                
                oct_start = october_1987['Close'].iloc[0]
                oct_end = october_1987['Close'].iloc[-1]
                oct_change = ((oct_end / oct_start) - 1) * 100
                
                print(f"   10月価格変動: {oct_change:.1f}%")
                print(f"   10月最高値: {october_1987['Close'].max():.2f}")
                print(f"   10月最安値: {october_1987['Close'].min():.2f}")
                
                # 具体的な日付のデータ確認
                print(f"\n📅 1987年10月の主要日付:")
                for idx, row in october_1987.head(10).iterrows():
                    print(f"   {idx.date()}: {row['Close']:.2f}")
        
        return data_1987
    else:
        print("❌ 1987年データ取得失敗")
        return None

def test_data_quality():
    """データ品質の詳細テスト"""
    print("\n=== データ品質テスト ===\n")
    
    client = FREDDataClient()
    
    # テスト期間のデータ取得
    test_data = client.get_sp500_data("1980-01-01", "1990-12-31")
    
    if test_data is None:
        print("❌ テストデータ取得失敗")
        return False
    
    print(f"📊 データ品質分析（1980-1990年）:")
    print(f"   総データ点数: {len(test_data)}")
    print(f"   期間: {test_data.index[0].date()} - {test_data.index[-1].date()}")
    
    # 欠損値チェック
    missing_values = test_data['Close'].isnull().sum()
    print(f"   欠損値: {missing_values}個 ({missing_values/len(test_data)*100:.2f}%)")
    
    # データの連続性チェック
    date_gaps = []
    for i in range(1, len(test_data)):
        gap = (test_data.index[i] - test_data.index[i-1]).days
        if gap > 5:  # 5日以上の間隔
            date_gaps.append((test_data.index[i-1], test_data.index[i], gap))
    
    print(f"   大きな日付ギャップ: {len(date_gaps)}個")
    if len(date_gaps) > 0:
        print(f"   最大ギャップ: {max(date_gaps, key=lambda x: x[2])[2]}日")
    
    # 価格の妥当性チェック
    price_range = test_data['Close'].max() - test_data['Close'].min()
    print(f"   価格範囲: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")
    print(f"   価格変動幅: {price_range:.2f}")
    
    # 異常値チェック
    daily_returns = test_data['Close'].pct_change().dropna()
    extreme_returns = daily_returns[abs(daily_returns) > 0.1]  # 10%以上の変動
    
    print(f"   極端な日次変動（>10%）: {len(extreme_returns)}回")
    if len(extreme_returns) > 0:
        print(f"   最大日次変動: {extreme_returns.abs().max()*100:.1f}%")
    
    return True

def main():
    """メインテスト実行"""
    print("🎯 FRED API 完全テスト開始\n")
    
    success_count = 0
    total_tests = 4
    
    # 1. 基本接続テスト
    if test_fred_api_connection():
        success_count += 1
    
    # 2. S&P500データ取得テスト
    if test_sp500_data_retrieval():
        success_count += 1
    
    # 3. 1987年データテスト
    data_1987 = test_1987_black_monday_data()
    if data_1987 is not None:
        success_count += 1
    
    # 4. データ品質テスト
    if test_data_quality():
        success_count += 1
    
    # 最終結果
    print(f"\n🏆 テスト結果サマリー:")
    print(f"   成功: {success_count}/{total_tests}")
    print(f"   成功率: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\n✅ FRED API完全セットアップ成功!")
        print("✅ 1987年ブラックマンデーデータ取得可能")
        print("✅ 実市場データでのLPPL検証準備完了")
        
        print(f"\n🚀 次のステップ:")
        print("1. 実市場データLPPL検証の実行")
        print("2. 論文値との詳細比較")
        print("3. 実用システム構築")
        
        return True
    else:
        print("\n⚠️ 一部のテストで問題が発生しました")
        print("🔧 問題の詳細を確認し、設定を見直してください")
        
        return False

if __name__ == "__main__":
    main()