#!/usr/bin/env python3
"""
2016-2019年tc値の簡易分析

目的: タイムアウトを避けつつtc値の実際の値を確認
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# Environment setup
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.fitting.utils import logarithm_periodic_func
from src.data_sources.fred_data_client import FREDDataClient
from scipy.optimize import curve_fit

def quick_tc_analysis():
    """簡易tc分析"""
    
    print("🔍 2016-2019年tc値簡易分析")
    print("=" * 40)
    
    # データ取得
    client = FREDDataClient()
    data = client.get_series_data('NASDAQCOM', '2016-01-01', '2019-12-31')
    
    if data is None:
        print("❌ データ取得失敗")
        return None
    
    print(f"✅ データ取得: {len(data)}日分")
    
    # データ準備
    log_prices = np.log(data['Close'].values)
    t = np.linspace(0, 1, len(data))
    
    # 簡易フィッティング（5回のみ）
    print("\n🔬 簡易フィッティング実行（5回試行）...")
    
    successful_fits = []
    
    # 固定初期値での試行
    initial_sets = [
        {'tc': 1.1, 'beta': 0.33, 'omega': 6.0},
        {'tc': 1.2, 'beta': 0.35, 'omega': 7.0},
        {'tc': 1.15, 'beta': 0.3, 'omega': 8.0},
        {'tc': 1.25, 'beta': 0.4, 'omega': 5.5},
        {'tc': 1.3, 'beta': 0.37, 'omega': 6.5}
    ]
    
    for i, init_set in enumerate(initial_sets):
        try:
            # 初期値設定
            A_init = np.mean(log_prices)
            B_init = (log_prices[-1] - log_prices[0]) / (len(log_prices) - 1)
            
            p0 = [
                init_set['tc'], init_set['beta'], init_set['omega'],
                0.0, A_init, B_init, 0.1
            ]
            
            # 境界設定
            bounds = (
                [1.01, 0.1, 3.0, -8*np.pi, -10, -10, -2.0],
                [2.0, 0.8, 15.0, 8*np.pi, 10, 10, 2.0]
            )
            
            # フィッティング実行
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, log_prices,
                p0=p0, bounds=bounds, method='trf',
                maxfev=5000  # 軽量化
            )
            
            # 評価
            y_pred = logarithm_periodic_func(t, *popt)
            r_squared = 1 - (np.sum((log_prices - y_pred)**2) / 
                           np.sum((log_prices - np.mean(log_prices))**2))
            
            if r_squared > 0.5:  # 最低品質
                successful_fits.append({
                    'trial': i,
                    'tc': popt[0],
                    'beta': popt[1],
                    'omega': popt[2],
                    'r_squared': r_squared
                })
                
                print(f"   試行{i+1}: R²={r_squared:.4f}, tc={popt[0]:.4f}")
        
        except Exception as e:
            print(f"   試行{i+1}: 失敗")
            continue
    
    if not successful_fits:
        print("❌ 全試行失敗")
        return None
    
    # tc値分析
    print(f"\n📊 tc値分析結果:")
    tc_values = [fit['tc'] for fit in successful_fits]
    r2_values = [fit['r_squared'] for fit in successful_fits]
    
    print(f"   成功フィット数: {len(successful_fits)}")
    print(f"   tc値範囲: [{min(tc_values):.4f}, {max(tc_values):.4f}]")
    print(f"   tc値平均: {np.mean(tc_values):.4f}")
    print(f"   最良R²: {max(r2_values):.4f}")
    
    # 予測日計算
    observation_start = data.index[0]
    observation_end = data.index[-1]
    observation_days = (observation_end - observation_start).days
    
    print(f"\n📅 予測時期分析:")
    print(f"   観測期間: {observation_start.date()} - {observation_end.date()}")
    print(f"   観測日数: {observation_days}日")
    
    for fit in successful_fits:
        tc = fit['tc']
        days_to_critical = (tc - 1.0) * observation_days
        predicted_date = observation_end + timedelta(days=days_to_critical)
        
        print(f"   試行{fit['trial']+1}: tc={tc:.4f} → {predicted_date.date()} (R²={fit['r_squared']:.4f})")
    
    # 平均予測日
    mean_tc = np.mean(tc_values)
    mean_days_to_critical = (mean_tc - 1.0) * observation_days
    mean_predicted_date = observation_end + timedelta(days=mean_days_to_critical)
    
    print(f"\n🎯 平均予測日: {mean_predicted_date.date()}")
    
    # 実際のイベントとの比較
    major_events = {
        'コロナショック': datetime(2020, 3, 23),
        '2021年急騰ピーク': datetime(2021, 2, 16),
    }
    
    print(f"\n🔍 実際のイベントとの比較:")
    for event_name, event_date in major_events.items():
        days_diff = abs((event_date - mean_predicted_date).days)
        print(f"   {event_name}: {event_date.date()} (差: {days_diff}日)")
    
    # 解釈
    print(f"\n🧠 簡易解釈:")
    if mean_tc <= 1.5:
        print("   ✅ 現実的な予測時期 - バブル特性検出の可能性")
    elif mean_tc <= 2.0:
        print("   ⚠️ やや遠い予測 - 長期トレンド捕捉の可能性")
    else:
        print("   📊 非現実的な予測 - 単純な数学的フィット")
    
    return {
        'successful_fits': successful_fits,
        'tc_statistics': {
            'mean': np.mean(tc_values),
            'min': min(tc_values),
            'max': max(tc_values),
            'std': np.std(tc_values)
        },
        'mean_predicted_date': mean_predicted_date,
        'best_r2': max(r2_values)
    }

if __name__ == "__main__":
    result = quick_tc_analysis()
    
    if result:
        print(f"\n🎯 簡易分析完了")
        print(f"   平均tc: {result['tc_statistics']['mean']:.4f}")
        print(f"   予測日: {result['mean_predicted_date'].date()}")
        print(f"   最良R²: {result['best_r2']:.4f}")
    else:
        print("❌ 分析失敗")