#!/usr/bin/env python3
"""
多基準選択システム統合テスト

R²最大化と複数基準選択の結果を比較し、
データベース保存とUI表示機能をテスト
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# パス設定
sys.path.append('.')

def main():
    print("🎯 多基準選択システム統合テスト")
    print("=" * 50)
    
    # 1. 合成データ生成
    print("\n📊 Step 1: 合成LPPLデータ生成...")
    data = generate_synthetic_lppl_data()
    print(f"✅ データ生成完了: {len(data)}点")
    
    # 2. 多基準選択システムテスト
    print("\n🎯 Step 2: 多基準選択システムテスト...")
    test_multi_criteria_selection(data)
    
    # 3. データベース保存テスト
    print("\n💾 Step 3: データベース保存テスト...")
    test_database_storage(data)
    
    # 4. 比較分析テスト
    print("\n📊 Step 4: 比較分析テスト...")
    test_comparison_analysis()
    
    print("\n🎉 統合テスト完了")

def generate_synthetic_lppl_data():
    """合成LPPLデータの生成"""
    
    # LPPLパラメータ（論文典型値）
    tc = 1.2
    beta = 0.33
    omega = 6.28
    phi = 0.1
    A = 5.0
    B = 0.5
    C = 0.1
    
    # 時系列生成
    n_points = 800
    t = np.linspace(0, 1, n_points)
    
    # LPPL関数
    log_prices = (A + B * (tc - t)**beta * 
                 (1 + C * np.cos(omega * np.log(tc - t) + phi)))
    
    # ノイズ追加
    noise = np.random.normal(0, 0.02, n_points)
    log_prices += noise
    
    # 価格に変換
    prices = np.exp(log_prices)
    
    # データフレーム作成
    dates = pd.date_range('2020-01-01', periods=n_points, freq='D')
    data = pd.DataFrame({
        'Close': prices
    }, index=dates)
    
    return data

def test_multi_criteria_selection(data):
    """多基準選択システムのテスト"""
    
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    selector = MultiCriteriaSelector()
    result = selector.perform_comprehensive_fitting(data)
    
    print(f"   総候補数: {len(result.all_candidates)}")
    print(f"   成功候補数: {len([c for c in result.all_candidates if c.convergence_success])}")
    print(f"   選択基準数: {len(result.selections)}")
    
    # 各基準での結果比較
    print(f"\n   🎯 各選択基準での結果:")
    for criteria, candidate in result.selections.items():
        if candidate:
            print(f"     {criteria.value}:")
            print(f"       tc={candidate.tc:.3f}, β={candidate.beta:.3f}, ω={candidate.omega:.2f}")
            print(f"       R²={candidate.r_squared:.4f}, RMSE={candidate.rmse:.4f}")
            
            # 理論値との比較
            beta_diff = abs(candidate.beta - 0.33)
            omega_diff = abs(candidate.omega - 6.28)
            print(f"       理論値差: β±{beta_diff:.3f}, ω±{omega_diff:.2f}")
    
    # デフォルト選択の確認
    default = result.get_selected_result()
    print(f"\n   📌 デフォルト選択 ({result.default_selection.value}):")
    print(f"     tc={default.tc:.3f}, R²={default.r_squared:.4f}")
    
    return result

def test_database_storage(data):
    """データベース保存のテスト"""
    
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    from src.data_management.prediction_database import PredictionDatabase
    
    # データベース初期化
    db = PredictionDatabase("test_multi_criteria.db")
    
    # 多基準選択実行
    selector = MultiCriteriaSelector()
    selection_result = selector.perform_comprehensive_fitting(data)
    
    # データベース保存
    session_id = db.save_multi_criteria_results(
        selection_result,
        "TEST_MARKET",
        730,
        data.index[0],
        data.index[-1]
    )
    
    print(f"   ✅ セッション保存: {session_id}")
    
    # 保存データの検証
    multi_results = db.get_multi_criteria_results(
        market="TEST_MARKET",
        window_days=730,
        days_back=1
    )
    
    if multi_results['status'] == 'success':
        print(f"   ✅ データ取得成功: {multi_results['sessions_count']}セッション")
        
        # 各基準の結果確認
        for session_id, session_data in multi_results['sessions'].items():
            print(f"     セッション: {session_id[:8]}...")
            print(f"       選択基準数: {len(session_data['selections'])}")
            
            for criteria, result in session_data['selections'].items():
                print(f"         {criteria}: tc={result['tc']:.3f}")
    
    # クリーンアップ
    try:
        os.remove("test_multi_criteria.db")
        print(f"   🧹 テストDB削除完了")
    except:
        pass

def test_comparison_analysis():
    """比較分析のテスト"""
    
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector, SelectionCriteria
    
    print("   🔍 選択基準の特性分析...")
    
    # 複数のデータセットで各基準の特性をテスト
    test_cases = [
        {"name": "理論値データ", "tc": 1.15, "beta": 0.33, "omega": 6.36},
        {"name": "高tc値データ", "tc": 2.5, "beta": 0.45, "omega": 8.2},
        {"name": "ノイジーデータ", "tc": 1.3, "beta": 0.28, "omega": 5.8}
    ]
    
    selector = MultiCriteriaSelector()
    comparison_results = []
    
    for test_case in test_cases:
        # テストデータ生成
        data = generate_test_data_with_params(test_case)
        
        # 多基準選択実行
        result = selector.perform_comprehensive_fitting(data)
        
        # 各基準での選択結果を記録
        case_results = {"test_case": test_case["name"]}
        for criteria, candidate in result.selections.items():
            if candidate:
                case_results[criteria.value] = {
                    'tc': candidate.tc,
                    'r_squared': candidate.r_squared,
                    'theory_distance': abs(candidate.beta - 0.33) + abs(candidate.omega - 6.36)/6.36
                }
        
        comparison_results.append(case_results)
    
    # 結果表示
    for result in comparison_results:
        print(f"\n     📋 {result['test_case']}:")
        for criteria_key in ['r_squared_max', 'multi_criteria', 'theoretical_best', 'practical_focus']:
            if criteria_key in result:
                data = result[criteria_key]
                print(f"       {criteria_key}: tc={data['tc']:.3f}, R²={data['r_squared']:.3f}")

def generate_test_data_with_params(params):
    """指定パラメータでのテストデータ生成"""
    
    tc = params['tc']
    beta = params['beta']
    omega = params['omega']
    phi = 0.0
    A = 5.0
    B = 0.5
    C = 0.1
    
    n_points = 500
    t = np.linspace(0.1, 0.99, n_points)  # tc未到達範囲
    
    # LPPL関数
    log_prices = (A + B * (tc - t)**beta * 
                 (1 + C * np.cos(omega * np.log(tc - t) + phi)))
    
    # ノイズレベル調整
    if "ノイジー" in params.get('name', ''):
        noise_level = 0.05
    else:
        noise_level = 0.02
    
    noise = np.random.normal(0, noise_level, n_points)
    log_prices += noise
    
    prices = np.exp(log_prices)
    
    dates = pd.date_range('2020-01-01', periods=n_points, freq='D')
    return pd.DataFrame({'Close': prices}, index=dates)

if __name__ == "__main__":
    main()