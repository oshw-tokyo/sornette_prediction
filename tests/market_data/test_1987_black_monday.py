#!/usr/bin/env python3
"""
1987年ブラックマンデーの実市場データでのLPPL検証

目的: 論文で言及された実際の株価データでLPPLフィッティングを実行し、
     論文報告値との比較を行う。

参照論文: papers/extracted_texts/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt
重要な情報:
- クラッシュ日: 1987年10月19日
- 米国市場: 30%以上の下落
- 論文期間: クラッシュ前9ヶ月間で31.4%上昇
- 検証期間: 1980年1月-1987年9月（論文に基づく）
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.fitting.utils import logarithm_periodic_func
from scipy.optimize import curve_fit, differential_evolution

# プロット保存ディレクトリの確保
os.makedirs('plots/market_validation/', exist_ok=True)
os.makedirs('analysis_results/market_validation/', exist_ok=True)

def fetch_1987_market_data():
    """1987年ブラックマンデー前後の実市場データを取得"""
    print("=== 1987年ブラックマンデー実市場データ取得 ===\n")
    
    try:
        # 論文で言及された期間に基づく
        # 検証期間: 1980年1月-1987年9月
        start_date = "1980-01-01"
        end_date = "1987-10-01"  # クラッシュ直前まで
        
        print(f"データ取得期間: {start_date} - {end_date}")
        print("対象指数: S&P 500 (^GSPC)")
        
        # S&P 500データ取得（論文でも言及）
        ticker = "^GSPC"
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            print("❌ データ取得に失敗しました")
            return None
            
        print(f"✅ データ取得成功: {len(data)}日分")
        print(f"期間: {data.index[0].date()} - {data.index[-1].date()}")
        print(f"価格範囲: ${data['Close'].min():.2f} - ${data['Close'].max():.2f}")
        
        return data
        
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
        return None

def prepare_lppl_data(data):
    """LPPLフィッティング用にデータを準備"""
    if data is None:
        return None, None
        
    # 対数価格に変換
    log_prices = np.log(data['Close'].values)
    
    # 時間軸を正規化（tc > t の制約のため）
    dates = data.index
    t_days = (dates - dates[0]).days.values
    t_normalized = t_days / max(t_days)  # 0-1に正規化
    
    print(f"\n📊 データ準備完了:")
    print(f"- データ点数: {len(log_prices)}")
    print(f"- 時間範囲: {t_normalized[0]:.3f} - {t_normalized[-1]:.3f}")
    print(f"- 対数価格範囲: {log_prices.min():.3f} - {log_prices.max():.3f}")
    print(f"- トレンド: {((log_prices[-1] - log_prices[0]) / log_prices[0] * 100):+.1f}%")
    
    return t_normalized, log_prices

def fit_lppl_to_market_data(t, log_prices):
    """実市場データにLPPLモデルをフィッティング"""
    print("\n🔧 LPPLフィッティング実行")
    
    # 論文値に基づく初期パラメータと境界
    # tc は最後のデータポイントより少し先に設定
    tc_bounds = (t[-1] + 0.01, t[-1] + 0.2)
    
    # パラメータ境界（論文の制約を考慮）
    bounds = (
        [tc_bounds[0], 0.1, 2.0, -8*np.pi, log_prices.min()-1, log_prices.min()-1, -2.0],  # 下限
        [tc_bounds[1], 0.8, 15.0, 8*np.pi, log_prices.max()+1, log_prices.max()+1, 2.0]   # 上限
    )
    
    results = []
    
    # 複数の初期値でフィッティング
    n_trials = 10
    print(f"複数初期値でのフィッティング（{n_trials}回試行）...")
    
    for i in range(n_trials):
        try:
            # ランダムな初期値生成
            tc_init = np.random.uniform(tc_bounds[0], tc_bounds[1])
            beta_init = np.random.uniform(0.2, 0.5)  # 論文値0.33周辺
            omega_init = np.random.uniform(5.0, 9.0)  # 論文値7.4周辺
            phi_init = np.random.uniform(-np.pi, np.pi)
            A_init = np.mean(log_prices)
            B_init = np.random.uniform(-1, 1)
            C_init = np.random.uniform(-0.5, 0.5)
            
            p0 = [tc_init, beta_init, omega_init, phi_init, A_init, B_init, C_init]
            
            # Trust Region Reflective法でフィッティング
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, log_prices,
                p0=p0, bounds=bounds, method='trf',
                ftol=1e-8, xtol=1e-8, gtol=1e-8,
                max_nfev=10000
            )
            
            # フィッティング品質評価
            y_pred = logarithm_periodic_func(t, *popt)
            residuals = log_prices - y_pred
            r_squared = 1 - (np.sum(residuals**2) / np.sum((log_prices - np.mean(log_prices))**2))
            rmse = np.sqrt(np.mean(residuals**2))
            
            result = {
                'trial': i+1,
                'params': popt,
                'r_squared': r_squared,
                'rmse': rmse,
                'residuals': residuals,
                'prediction': y_pred
            }
            results.append(result)
            
            print(f"  試行 {i+1}: R²={r_squared:.6f}, RMSE={rmse:.6f}")
            
        except Exception as e:
            print(f"  試行 {i+1}: フィッティング失敗 - {str(e)[:50]}...")
            continue
    
    if not results:
        print("❌ すべてのフィッティング試行が失敗しました")
        return None
        
    # 最良の結果を選択（R²が最大）
    best_result = max(results, key=lambda x: x['r_squared'])
    print(f"\n✅ 最良フィッティング: 試行{best_result['trial']}")
    print(f"   R² = {best_result['r_squared']:.6f}")
    print(f"   RMSE = {best_result['rmse']:.6f}")
    
    return best_result, results

def analyze_fitted_parameters(result):
    """フィッティング結果のパラメータ分析"""
    if result is None:
        return
        
    params = result['params']
    tc, beta, omega, phi, A, B, C = params
    
    print(f"\n📊 フィッティング結果分析:")
    print(f"{'パラメータ':<15} {'推定値':<12} {'論文値':<12} {'誤差率':<10}")
    print("-" * 55)
    
    # 論文値との比較
    paper_beta = 0.33
    paper_omega = 7.4
    
    beta_error = abs(beta - paper_beta) / paper_beta * 100
    omega_error = abs(omega - paper_omega) / paper_omega * 100
    
    print(f"{'tc (臨界時刻)':<15} {tc:<12.4f} {'N/A':<12} {'N/A':<10}")
    print(f"{'β (臨界指数)':<15} {beta:<12.4f} {paper_beta:<12.2f} {beta_error:<10.2f}%")
    print(f"{'ω (角周波数)':<15} {omega:<12.4f} {paper_omega:<12.1f} {omega_error:<10.2f}%")
    print(f"{'φ (位相)':<15} {phi:<12.4f} {'N/A':<12} {'N/A':<10}")
    print(f"{'A (定数項)':<15} {A:<12.4f} {'N/A':<12} {'N/A':<10}")
    print(f"{'B (係数)':<15} {B:<12.4f} {'N/A':<12} {'N/A':<10}")
    print(f"{'C (振幅)':<15} {C:<12.4f} {'N/A':<12} {'N/A':<10}")
    
    # 論文との合致度評価
    print(f"\n🎯 論文値との合致度評価:")
    if beta_error < 5:
        print(f"   β値: ✅ 優秀 (誤差 {beta_error:.1f}% < 5%)")
    elif beta_error < 10:
        print(f"   β値: ⚠️ 許容 (誤差 {beta_error:.1f}% < 10%)")
    else:
        print(f"   β値: ❌ 要改善 (誤差 {beta_error:.1f}% > 10%)")
        
    if omega_error < 10:
        print(f"   ω値: ✅ 良好 (誤差 {omega_error:.1f}% < 10%)")
    else:
        print(f"   ω値: ❌ 要改善 (誤差 {omega_error:.1f}% > 10%)")
    
    return {
        'beta_error': beta_error,
        'omega_error': omega_error,
        'params_dict': {
            'tc': tc, 'beta': beta, 'omega': omega, 'phi': phi,
            'A': A, 'B': B, 'C': C
        }
    }

def plot_fitting_results(t, log_prices, result, data_dates):
    """フィッティング結果の可視化"""
    if result is None:
        return
        
    params = result['params']
    prediction = result['prediction']
    
    # メインプロット
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # 上段: 実データとフィッティング結果
    ax1.plot(data_dates, np.exp(log_prices), 'b-', linewidth=1, label='実際のS&P 500', alpha=0.7)
    ax1.plot(data_dates, np.exp(prediction), 'r-', linewidth=2, label='LPPL フィッティング')
    
    ax1.set_ylabel('価格 ($)', fontsize=12)
    ax1.set_title('1987年ブラックマンデー前のS&P 500とLPPLフィッティング', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # クラッシュ日の表示
    crash_date = datetime(1987, 10, 19)
    ax1.axvline(crash_date, color='red', linestyle='--', alpha=0.7, label='ブラックマンデー')
    
    # 下段: 残差
    residuals = result['residuals']
    ax2.plot(data_dates, residuals, 'g-', linewidth=1, alpha=0.7)
    ax2.axhline(0, color='black', linestyle='-', alpha=0.3)
    ax2.set_ylabel('残差', fontsize=12)
    ax2.set_xlabel('日付', fontsize=12)
    ax2.set_title('フィッティング残差', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 統計情報の追加
    r_sq = result['r_squared']
    rmse = result['rmse']
    tc, beta, omega = params[0], params[1], params[2]
    
    info_text = f'R² = {r_sq:.4f}\nRMSE = {rmse:.4f}\nβ = {beta:.3f}\nω = {omega:.2f}'
    ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存
    filename = 'plots/market_validation/1987_black_monday_fitting.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n📊 フィッティング結果プロット保存: {filename}")
    
    plt.show()

def save_analysis_results(result, analysis, data_info):
    """分析結果をファイルに保存"""
    if result is None:
        return
        
    # 結果サマリーの作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    summary = f"""
# 1987年ブラックマンデー実市場データ検証結果
実行日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## データ情報
- 期間: {data_info['period']}
- データ点数: {data_info['n_points']}
- 価格範囲: ${data_info['price_min']:.2f} - ${data_info['price_max']:.2f}

## フィッティング結果
- R²値: {result['r_squared']:.6f}
- RMSE: {result['rmse']:.6f}

## パラメータ推定値
"""
    
    params = result['params']
    param_names = ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
    for i, (name, value) in enumerate(zip(param_names, params)):
        summary += f"- {name}: {value:.6f}\n"
    
    if analysis:
        summary += f"""
## 論文値との比較
- β値誤差: {analysis['beta_error']:.2f}%
- ω値誤差: {analysis['omega_error']:.2f}%

## 評価
"""
        # 評価結果の追加
        if analysis['beta_error'] < 5:
            summary += "- β値: 優秀 (誤差 < 5%)\n"
        elif analysis['beta_error'] < 10:
            summary += "- β値: 許容 (誤差 < 10%)\n"
        else:
            summary += "- β値: 要改善 (誤差 > 10%)\n"
    
    # ファイル保存
    result_file = f'analysis_results/market_validation/1987_validation_{timestamp}.md'
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"📄 分析結果保存: {result_file}")

def main():
    """メイン実行関数"""
    print("🎯 1987年ブラックマンデー実市場データ検証開始\n")
    
    # 1. 実市場データ取得
    market_data = fetch_1987_market_data()
    if market_data is None:
        print("❌ データ取得に失敗したため、検証を中止します")
        return
    
    # 2. LPPLフィッティング用データ準備
    t, log_prices = prepare_lppl_data(market_data)
    if t is None:
        print("❌ データ準備に失敗しました")
        return
    
    # 3. LPPLフィッティング実行
    result, all_results = fit_lppl_to_market_data(t, log_prices)
    if result is None:
        print("❌ フィッティングに失敗しました")
        return
    
    # 4. パラメータ分析
    analysis = analyze_fitted_parameters(result)
    
    # 5. 結果可視化
    plot_fitting_results(t, log_prices, result, market_data.index)
    
    # 6. 結果保存
    data_info = {
        'period': f"{market_data.index[0].date()} - {market_data.index[-1].date()}",
        'n_points': len(market_data),
        'price_min': market_data['Close'].min(),
        'price_max': market_data['Close'].max()
    }
    save_analysis_results(result, analysis, data_info)
    
    print("\n🎉 1987年ブラックマンデー実市場データ検証完了!")
    
    # 成功評価
    if analysis and analysis['beta_error'] < 10:
        print("✅ 実市場データでの検証成功: 論文値との良好な一致を確認")
    else:
        print("⚠️ 実市場データでの検証: 更なる改善が必要")

if __name__ == "__main__":
    main()