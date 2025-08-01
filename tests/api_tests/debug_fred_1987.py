#!/usr/bin/env python3
"""
FRED API 1987年データ取得デバッグ

目的: 1987年データ取得の問題を特定・解決
"""

import sys
import os
from dotenv import load_dotenv
import json

# 環境変数読み込み
load_dotenv()

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import requests

def debug_fred_api_raw():
    """FRED APIの生レスポンスをデバッグ"""
    print("=== FRED API 生レスポンス デバッグ ===\n")
    
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("❌ APIキーが設定されていません")
        return
    
    base_url = "https://api.stlouisfed.org/fred"
    
    # 1987年データのリクエスト
    params = {
        'series_id': 'SP500',
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': '1985-01-01',
        'observation_end': '1987-10-31',
        'sort_order': 'asc'
    }
    
    url = f"{base_url}/series/observations"
    
    print(f"📡 リクエストURL: {url}")
    print(f"📋 パラメータ: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        print(f"\n📊 レスポンス情報:")
        print(f"   ステータスコード: {response.status_code}")
        print(f"   ヘッダー: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📋 レスポンス構造:")
            print(f"   キー: {list(data.keys())}")
            
            if 'observations' in data:
                observations = data['observations']
                print(f"   観測データ数: {len(observations)}")
                
                if len(observations) > 0:
                    print(f"\n📊 最初の5件のデータ:")
                    for i, obs in enumerate(observations[:5]):
                        print(f"   {i+1}: {obs}")
                    
                    print(f"\n📊 最後の5件のデータ:")
                    for i, obs in enumerate(observations[-5:]):
                        print(f"   {len(observations)-4+i}: {obs}")
                        
                    # データの種類を分析
                    values = [obs.get('value', '') for obs in observations]
                    valid_values = [v for v in values if v != '.' and v != '']
                    invalid_values = [v for v in values if v == '.' or v == '']
                    
                    print(f"\n📈 データ品質分析:")
                    print(f"   総データ数: {len(values)}")
                    print(f"   有効データ: {len(valid_values)}")
                    print(f"   無効データ: {len(invalid_values)}")
                    
                    if len(valid_values) > 0:
                        print(f"   有効データサンプル: {valid_values[:5]}")
                    
                    if len(invalid_values) > 0:
                        print(f"   無効データサンプル: {invalid_values[:5]}")
                else:
                    print("❌ 観測データが空です")
            else:
                print("❌ 'observations' キーが見つかりません")
                
        else:
            print(f"❌ HTTPエラー: {response.text}")
            
    except Exception as e:
        print(f"❌ リクエストエラー: {e}")

def debug_series_info():
    """SP500シリーズの詳細情報を取得"""
    print("\n=== SP500 シリーズ情報デバッグ ===\n")
    
    api_key = os.getenv('FRED_API_KEY')
    base_url = "https://api.stlouisfed.org/fred"
    
    # シリーズ情報の取得
    params = {
        'series_id': 'SP500',
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
                
                print(f"📊 SP500 シリーズ詳細:")
                print(f"   ID: {series_info.get('id')}")
                print(f"   タイトル: {series_info.get('title')}")
                print(f"   開始日: {series_info.get('observation_start')}")
                print(f"   終了日: {series_info.get('observation_end')}")
                print(f"   頻度: {series_info.get('frequency')}")
                print(f"   単位: {series_info.get('units')}")
                print(f"   最終更新: {series_info.get('last_updated')}")
                
                # 1987年がカバーされているかチェック
                start_date = series_info.get('observation_start')
                end_date = series_info.get('observation_end')
                
                if start_date and end_date:
                    print(f"\n🔍 1987年データ可用性:")
                    if start_date <= '1987-12-31' and end_date >= '1987-01-01':
                        print(f"   ✅ 1987年データは利用可能")
                    else:
                        print(f"   ❌ 1987年データは範囲外")
            else:
                print("❌ シリーズ情報が取得できません")
        else:
            print(f"❌ シリーズ情報取得エラー: {response.text}")
            
    except Exception as e:
        print(f"❌ シリーズ情報取得エラー: {e}")

def test_alternative_date_ranges():
    """異なる日付範囲でのテスト"""
    print("\n=== 異なる日付範囲でのテスト ===\n")
    
    api_key = os.getenv('FRED_API_KEY')
    base_url = "https://api.stlouisfed.org/fred"
    
    test_ranges = [
        ("1987-01-01", "1987-12-31", "1987年のみ"),
        ("1986-01-01", "1988-12-31", "1986-1988年"),
        ("1980-01-01", "1989-12-31", "1980年代"),
    ]
    
    for start_date, end_date, description in test_ranges:
        print(f"📊 {description} ({start_date} - {end_date}):")
        
        params = {
            'series_id': 'SP500',
            'api_key': api_key,
            'file_type': 'json',
            'observation_start': start_date,
            'observation_end': end_date,
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
                        # 有効データをカウント
                        valid_data = [obs for obs in observations if obs.get('value') != '.']
                        
                        print(f"   ✅ 総データ: {len(observations)}, 有効データ: {len(valid_data)}")
                        
                        if len(valid_data) > 0:
                            first_valid = valid_data[0]
                            last_valid = valid_data[-1]
                            print(f"   📅 有効期間: {first_valid['date']} - {last_valid['date']}")
                            print(f"   💰 価格範囲: {first_valid['value']} - {last_valid['value']}")
                    else:
                        print(f"   ❌ データなし")
                else:
                    print(f"   ❌ observations キーなし")
            else:
                print(f"   ❌ HTTPエラー ({response.status_code})")
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
        
        print()

def main():
    """メインデバッグ実行"""
    print("🔍 FRED API 1987年データ取得デバッグ開始\n")
    
    # 1. 生レスポンスのデバッグ
    debug_fred_api_raw()
    
    # 2. シリーズ情報の確認
    debug_series_info()
    
    # 3. 異なる日付範囲でのテスト
    test_alternative_date_ranges()
    
    print("🏁 デバッグ完了")

if __name__ == "__main__":
    main()