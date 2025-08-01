#!/usr/bin/env python3
"""
β値の系統的誤差問題のデバッグスクリプト
論文の式(54)を用いて詳細な分析を実行
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from src.fitting.utils import logarithm_periodic_func
import warnings
warnings.filterwarnings('ignore')

def generate_clean_lppl_data(params, n_points=500, noise_level=0.001):
    """ノイズの少ない高品質なLPPLデータを生成"""
    t = np.linspace(0, 1, n_points)
    
    # 論文の式(54)に従って生成
    tc, beta, omega, phi, A, B, C = params
    
    # より安定した計算
    dt = tc - t
    valid_mask = dt > 0
    
    log_prices = np.zeros_like(t)
    log_prices[valid_mask] = (A + 
                             B * np.power(dt[valid_mask], beta) +
                             C * np.power(dt[valid_mask], beta) * 
                             np.cos(omega * np.log(dt[valid_mask]) + phi))
    
    # 最小限のノイズを追加
    noise = np.random.normal(0, noise_level, len(t))
    
    return t, log_prices + noise

def test_parameter_recovery():
    """パラメータ回復テストの実行"""
    print("=== β値系統誤差の詳細分析 ===\n")
    
    # 論文の1987年クラッシュパラメータ
    true_params = {
        'tc': 1.1,
        'beta': 0.33,   # 論文値
        'omega': 7.4,   # 論文値
        'phi': 1.0,
        'A': 1.0,
        'B': -0.5,
        'C': 0.1
    }
    
    print("真のパラメータ (論文ベース):")
    for key, value in true_params.items():
        print(f"  {key}: {value:.4f}")
    
    # 複数のノイズレベルでテスト
    noise_levels = [0.0001, 0.001, 0.005, 0.01]
    
    for noise_level in noise_levels:
        print(f"\n--- ノイズレベル: {noise_level:.4f} ---")
        
        # シード設定による再現性確保
        np.random.seed(42)
        
        # データ生成
        params_list = list(true_params.values())
        t, y = generate_clean_lppl_data(params_list, n_points=1000, noise_level=noise_level)
        
        print(f"データ統計:")
        print(f"  データ点数: {len(t)}")
        print(f"  y範囲: [{y.min():.4f}, {y.max():.4f}]")
        print(f"  y標準偏差: {np.std(y):.4f}")
        
        # 複数の最適化手法でテスト
        methods = ['trf', 'lm', 'dogbox']
        
        for method in methods:
            try:
                # 初期値を真の値の近くに設定
                p0 = [
                    true_params['tc'] + np.random.normal(0, 0.01),
                    true_params['beta'] + np.random.normal(0, 0.02),
                    true_params['omega'] + np.random.normal(0, 0.5),
                    true_params['phi'] + np.random.normal(0, 0.5),
                    true_params['A'] + np.random.normal(0, 0.1),
                    true_params['B'] + np.random.normal(0, 0.1),
                    true_params['C'] + np.random.normal(0, 0.02)
                ]
                
                # 境界設定（論文の制約に基づく）
                bounds = (
                    [1.01, 0.1, 2.0, -8*np.pi, -10, -10, -2.0],
                    [1.5, 0.8, 15.0, 8*np.pi, 10, 10, 2.0]
                )
                
                # フィッティング実行
                popt, pcov = curve_fit(
                    logarithm_periodic_func, t, y,
                    p0=p0, bounds=bounds, method=method,
                    ftol=1e-8, xtol=1e-8, gtol=1e-8,
                    max_nfev=10000
                )
                
                # 結果評価
                y_fit = logarithm_periodic_func(t, *popt)
                r2 = 1 - np.sum((y - y_fit)**2) / np.sum((y - np.mean(y))**2)
                
                param_names = ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
                
                print(f"\n  {method.upper()}法の結果 (R²={r2:.6f}):")
                for i, (name, true_val, fitted_val) in enumerate(zip(param_names, params_list, popt)):
                    error = abs(fitted_val - true_val)
                    error_pct = (error / abs(true_val)) * 100 if true_val != 0 else float('inf')
                    
                    status = "✓" if error_pct < 5 else "⚠" if error_pct < 10 else "✗"
                    print(f"    {name}: {fitted_val:.4f} (真値: {true_val:.4f}, 誤差: {error_pct:.1f}%) {status}")
                
            except Exception as e:
                print(f"  {method.upper()}法 失敗: {str(e)}")

def test_differential_evolution():
    """Differential Evolution（グローバル最適化）を使用したテスト"""
    print("\n=== グローバル最適化 (Differential Evolution) テスト ===\n")
    
    # 論文パラメータ
    true_params = [1.1, 0.33, 7.4, 1.0, 1.0, -0.5, 0.1]
    param_names = ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
    
    # データ生成
    np.random.seed(42)  
    t, y = generate_clean_lppl_data(true_params, n_points=500, noise_level=0.001)
    
    # 目的関数の定義
    def objective(params):
        try:
            y_pred = logarithm_periodic_func(t, *params)
            mse = np.mean((y - y_pred)**2)
            return mse
        except:
            return 1e10
    
    # パラメータ境界（論文の制約）
    bounds = [
        (1.01, 1.5),      # tc
        (0.1, 0.8),       # beta
        (2.0, 15.0),      # omega
        (-8*np.pi, 8*np.pi), # phi
        (-10, 10),        # A
        (-10, 10),        # B
        (-2.0, 2.0)       # C
    ]
    
    print("Differential Evolution実行中...")
    
    try:
        result = differential_evolution(
            objective, bounds,
            maxiter=1000,
            popsize=15,
            seed=42,
            atol=1e-8,
            tol=1e-8
        )
        
        if result.success:
            print(f"最適化成功！ (関数評価回数: {result.nfev})")
            print(f"最終目的関数値: {result.fun:.8e}")
            
            fitted_params = result.x
            y_fit = logarithm_periodic_func(t, *fitted_params)
            r2 = 1 - np.sum((y - y_fit)**2) / np.sum((y - np.mean(y))**2)
            
            print(f"\nフィッティング結果 (R²={r2:.6f}):")
            for i, (name, true_val, fitted_val) in enumerate(zip(param_names, true_params, fitted_params)):
                error = abs(fitted_val - true_val)
                error_pct = (error / abs(true_val)) * 100 if true_val != 0 else float('inf')
                
                status = "✓" if error_pct < 5 else "⚠" if error_pct < 10 else "✗"
                print(f"  {name}: {fitted_val:.4f} (真値: {true_val:.4f}, 誤差: {error_pct:.1f}%) {status}")
                
        else:
            print(f"最適化失敗: {result.message}")
            
    except Exception as e:
        print(f"Differential Evolution エラー: {str(e)}")

def analyze_function_behavior():
    """LPPL関数の挙動分析"""
    print("\n=== LPPL関数の挙動分析 ===\n")
    
    t = np.linspace(0, 1, 1000)
    base_params = [1.1, 0.33, 7.4, 1.0, 1.0, -0.5, 0.1]
    
    # βを変化させた時の影響
    beta_values = [0.30, 0.33, 0.36, 0.40]
    
    plt.figure(figsize=(15, 10))
    
    for i, beta in enumerate(beta_values):
        params = base_params.copy()
        params[1] = beta
        
        try:
            y = logarithm_periodic_func(t, *params)
            
            plt.subplot(2, 2, i+1)
            plt.plot(t, y, 'b-', linewidth=2)
            plt.title(f'β = {beta:.2f}')
            plt.xlabel('時間 t')
            plt.ylabel('対数価格')
            plt.grid(True, alpha=0.3)
            
            # 特性を計算
            dy_dt = np.gradient(y, t)
            acceleration = np.gradient(dy_dt, t)
            
            print(f"β = {beta:.2f}:")
            print(f"  価格範囲: [{y.min():.4f}, {y.max():.4f}]")
            print(f"  最大勾配: {dy_dt.max():.4f}")
            print(f"  最大加速度: {acceleration.max():.4f}")
            
        except Exception as e:
            print(f"β = {beta:.2f}: 計算エラー - {str(e)}")
    
    plt.tight_layout()
    plt.savefig('beta_behavior_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\nプロット保存: beta_behavior_analysis.png")

if __name__ == "__main__":
    # テスト実行
    test_parameter_recovery()
    test_differential_evolution()
    analyze_function_behavior()
    
    print("\n=== 分析完了 ===")