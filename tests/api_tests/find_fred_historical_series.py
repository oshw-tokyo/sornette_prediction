#!/usr/bin/env python3
"""
FRED API で利用可能な歴史的株価シリーズの探索

目的: 1987年のデータが利用可能なシリーズを特定
"""

import sys
import os
from dotenv import load_dotenv
import requests
import json

# 環境変数読み込み
load_dotenv()

def search_fred_series():
    """FRED で利用可能な株価関連シリーズを検索"""
    print("=== FRED 歴史的株価シリーズ探索 ===\n")
    
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("❌ APIキーが設定されていません")
        return
    
    base_url = "https://api.stlouisfed.org/fred"
    
    # 候補となるシリーズID
    candidate_series = [
        'SP500',           # S&P 500 (確認済み：2015年から)
        'SPASTT01USM661N', # S&P 500 月次
        'NASDAQCOM',       # NASDAQ Composite
        'DJIA',            # Dow Jones Industrial Average
        'SPASTT01USQ661N', # S&P 500 quarterly
        'DEXUSUK',         # USD/GBP 為替レート（参考）
        'GOLDAMGBD228NLBM', # 金価格（参考）
        'WILLREITIND',     # Wilshire US REIT Price Index
        'WILL5000IND',     # Wilshire 5000 Total Market Index
        'SPCS20RSA',       # S&P/Case-Shiller 20-City Home Price Index
    ]
    
    valid_1987_series = []
    
    for series_id in candidate_series:
        print(f"🔍 {series_id} を調査中...")
        
        # シリーズ情報を取得
        params = {
            'series_id': series_id,
            'api_key': api_key,
            'file_type': 'json'
        }
        
        url = f"{base_url}/series"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'seriess' in data and len(data['seriess']) > 0:
                    series_info = data['seriess'][0]
                    
                    title = series_info.get('title', 'N/A')
                    start_date = series_info.get('observation_start', 'N/A')
                    end_date = series_info.get('observation_end', 'N/A')
                    frequency = series_info.get('frequency', 'N/A')
                    units = series_info.get('units', 'N/A')
                    
                    print(f"   📊 {title}")
                    print(f"   📅 期間: {start_date} - {end_date}")
                    print(f"   📈 頻度: {frequency}")
                    print(f"   📋 単位: {units}")
                    
                    # 1987年がカバーされているかチェック
                    if start_date and start_date <= '1987-12-31' and end_date and end_date >= '1987-01-01':
                        print(f"   ✅ 1987年データ利用可能")
                        valid_1987_series.append({
                            'id': series_id,
                            'title': title,
                            'start': start_date,
                            'end': end_date,
                            'frequency': frequency,
                            'units': units
                        })
                    else:
                        print(f"   ❌ 1987年データ利用不可")
                
                else:
                    print(f"   ❌ シリーズ情報取得失敗")
            else:
                print(f"   ❌ HTTPエラー ({response.status_code})")
                
        except Exception as e:
            print(f"   ❌ リクエストエラー: {e}")
        
        print()
    
    return valid_1987_series

def test_series_data(series_id, title):
    """特定のシリーズの1987年データをテスト"""
    print(f"=== {title} ({series_id}) データテスト ===\n")
    
    api_key = os.getenv('FRED_API_KEY')
    base_url = "https://api.stlouisfed.org/fred"
    
    # 1987年データを取得
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': '1985-01-01',
        'observation_end': '1987-10-31',
        'sort_order': 'asc'
    }
    
    url = f"{base_url}/series/observations"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'observations' in data:
                observations = data['observations']
                
                if len(observations) > 0:
                    # 有効データをフィルタ
                    valid_data = [obs for obs in observations if obs.get('value') != '.']
                    
                    print(f"📊 データ取得結果:")
                    print(f"   総観測数: {len(observations)}")
                    print(f"   有効データ: {len(valid_data)}")
                    
                    if len(valid_data) > 0:
                        first_valid = valid_data[0]
                        last_valid = valid_data[-1]
                        
                        print(f"   📅 有効期間: {first_valid['date']} - {last_valid['date']}")
                        print(f"   💰 値の範囲: {first_valid['value']} - {last_valid['value']}")
                        
                        # 1987年のデータを確認
                        data_1987 = [obs for obs in valid_data if obs['date'].startswith('1987')]
                        print(f"   🎯 1987年データ: {len(data_1987)}個")
                        
                        if len(data_1987) > 0:
                            print(f"   📋 1987年サンプル:")
                            for obs in data_1987[:5]:
                                print(f"     {obs['date']}: {obs['value']}")
                        
                        return True
                    else:
                        print(f"   ❌ 有効データなし")
                        return False
                else:
                    print(f"   ❌ 観測データなし")
                    return False
            else:
                print(f"   ❌ observations キーなし")
                return False
        else:
            print(f"   ❌ HTTPエラー ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ リクエストエラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🔍 FRED 歴史的株価シリーズ探索開始\n")
    
    # 1. 利用可能なシリーズを探索
    valid_series = search_fred_series()
    
    print(f"🎯 1987年データ利用可能シリーズ: {len(valid_series)}個\n")
    
    if len(valid_series) > 0:
        print("✅ 利用可能シリーズ一覧:")
        for series in valid_series:
            print(f"   {series['id']}: {series['title']} ({series['start']} - {series['end']})")
        
        print(f"\n📊 データ品質テスト:")
        
        # 2. 各シリーズのデータ品質をテスト
        successful_series = []
        
        for series in valid_series:
            print(f"\n" + "="*60)
            if test_series_data(series['id'], series['title']):
                successful_series.append(series)
        
        print(f"\n🏆 最終結果:")
        print(f"   検索対象: {len(candidate_series)}シリーズ")
        print(f"   1987年対応: {len(valid_series)}シリーズ")
        print(f"   データ取得成功: {len(successful_series)}シリーズ")
        
        if len(successful_series) > 0:
            print(f"\n✅ 推奨シリーズ:")
            for series in successful_series:
                print(f"   {series['id']}: {series['title']}")
                print(f"     期間: {series['start']} - {series['end']}")
                print(f"     頻度: {series['frequency']}")
        else:
            print(f"\n❌ 1987年データが利用可能なシリーズが見つかりませんでした")
            
    else:
        print("❌ 1987年データが利用可能なシリーズが見つかりませんでした")
        print("\n💡 代替案:")
        print("1. Alpha Vantage API の利用")
        print("2. 他の金融データプロバイダーの検討")
        print("3. 歴史的データの手動取得")

if __name__ == "__main__":
    # 候補シリーズリストをグローバルに定義
    candidate_series = [
        'SP500', 'SPASTT01USM661N', 'NASDAQCOM', 'DJIA', 'SPASTT01USQ661N',
        'DEXUSUK', 'GOLDAMGBD228NLBM', 'WILLREITIND', 'WILL5000IND', 'SPCS20RSA'
    ]
    
    main()