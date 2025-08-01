#!/usr/bin/env python3
"""
現在の実装でのフィッティング結果を確認するためのテストスクリプト
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd

from src.fitting.fitter import LogarithmPeriodicFitter
from src.fitting.utils import logarithm_periodic_func, power_law_func
from src.reproducibility_validation.historical_crashes import get_crash_case

def generate_synthetic_crash_data():
    """論文の典型的なパラメータで合成データを生成"""
    # 論文で報告されている1987年クラッシュの典型的なパラメータ
    tc = 1.1
    beta = 0.33  # 論文の典型値
    omega = 7.4  # 論文の典型値
    phi = 2.0
    A = 1.0
    B = -0.5
    C = 0.1
    
    # 時間軸
    t = np.linspace(0, 1, 500)
    
    # 対数周期関数による価格生成
    dt = tc - t
    log_prices = A + B * np.power(dt, beta) * (1 + C * np.cos(omega * np.log(dt) + phi))
    
    # ノイズを追加
    noise = np.random.normal(0, 0.01, len(t))
    log_prices_noisy = log_prices + noise
    
    return t, log_prices_noisy, {
        'tc': tc, 'beta': beta, 'omega': omega, 'phi': phi,
        'A': A, 'B': B, 'C': C
    }

def test_current_fitting():
    """現在の実装でフィッティングをテスト"""
    print("=== Current Implementation Fitting Test ===\n")
    
    # 合成データの生成
    print("1. Generating synthetic crash data based on 1987 crash parameters...")
    t, log_prices, true_params = generate_synthetic_crash_data()
    print(f"   Data points: {len(t)}")
    print(f"   True parameters:")
    for key, value in true_params.items():
        print(f"     {key}: {value:.4f}")
    
    # フィッター初期化
    fitter = LogarithmPeriodicFitter()
    
    # フィッティング実行
    print("\n2. Performing fitting with current implementation...")
    try:
        # 複数初期値でのフィッティング
        result = fitter.fit_with_multiple_initializations(t, log_prices, n_tries=5)
        
        if result.success:
            print("\n3. Fitting Results:")
            print("   Status: SUCCESS")
            print("   Fitted parameters:")
            for key, value in result.parameters.items():
                true_val = true_params.get(key, 'N/A')
                if isinstance(true_val, (int, float)):
                    error = abs(value - true_val)
                    error_pct = (error / abs(true_val)) * 100 if true_val != 0 else 'N/A'
                    print(f"     {key}: {value:.4f} (true: {true_val:.4f}, error: {error:.4f}, {error_pct:.1f}%)")
                else:
                    print(f"     {key}: {value:.4f}")
            
            print(f"\n   Quality metrics:")
            print(f"     R-squared: {result.r_squared:.6f}")
            print(f"     Residuals (MSE): {result.residuals:.6e}")
            
            # プロット作成
            create_fitting_plots(t, log_prices, result, true_params)
            
        else:
            print("\n3. Fitting Results:")
            print("   Status: FAILED")
            print(f"   Error: {result.error_message}")
            
    except Exception as e:
        print(f"\n3. Fitting Results:")
        print(f"   Status: ERROR")
        print(f"   Exception: {str(e)}")
        import traceback
        traceback.print_exc()

def create_fitting_plots(t, log_prices, result, true_params):
    """フィッティング結果のプロット作成"""
    try:
        # フィッティング結果による予測値を計算
        fitted_prices = logarithm_periodic_func(t, **result.parameters)
        true_prices = logarithm_periodic_func(t, **true_params)
        
        # プロット作成
        plt.figure(figsize=(12, 8))
        
        # メインプロット
        plt.subplot(2, 2, 1)
        plt.plot(t, log_prices, 'b.', alpha=0.6, label='Noisy Data', markersize=2)
        plt.plot(t, true_prices, 'g-', linewidth=2, label='True Function')
        plt.plot(t, fitted_prices, 'r--', linewidth=2, label='Fitted Function')
        plt.xlabel('Normalized Time')
        plt.ylabel('Log Price')
        plt.title('Log-Periodic Power Law Fitting')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 残差プロット
        plt.subplot(2, 2, 2)
        residuals = log_prices - fitted_prices
        plt.plot(t, residuals, 'k.', alpha=0.6, markersize=2)
        plt.axhline(y=0, color='r', linestyle='--', alpha=0.7)
        plt.xlabel('Normalized Time')
        plt.ylabel('Residuals')
        plt.title('Fitting Residuals')
        plt.grid(True, alpha=0.3)
        
        # パラメータ比較
        plt.subplot(2, 2, 3)
        params_to_compare = ['beta', 'omega', 'tc']
        true_values = [true_params[p] for p in params_to_compare]
        fitted_values = [result.parameters[p] for p in params_to_compare]
        
        x_pos = np.arange(len(params_to_compare))
        width = 0.35
        
        plt.bar(x_pos - width/2, true_values, width, label='True', alpha=0.7)
        plt.bar(x_pos + width/2, fitted_values, width, label='Fitted', alpha=0.7)
        plt.xlabel('Parameters')
        plt.ylabel('Values')
        plt.title('Parameter Comparison')
        plt.xticks(x_pos, params_to_compare)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # エラー分布
        plt.subplot(2, 2, 4)
        plt.hist(residuals, bins=30, alpha=0.7, density=True)
        plt.xlabel('Residual Value')
        plt.ylabel('Density')
        plt.title('Residual Distribution')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('current_fitting_results.png', dpi=300, bbox_inches='tight')
        print(f"\n4. Plot saved as 'current_fitting_results.png'")
        
    except Exception as e:
        print(f"\n4. Plot creation failed: {str(e)}")

if __name__ == "__main__":
    # 再現性のためのシード設定
    np.random.seed(42)
    
    test_current_fitting()
    
    print("\n=== Test completed ===")