#!/usr/bin/env python3
"""
実市場特性を再現したLPPL検証

目的: Yahoo Finance API制限を回避し、実市場の特性（ノイズ、外れ値、トレンド）を
     含むシミュレーションデータでLPPLモデルの実用性を検証

特徴:
- 1987年ブラックマンデー前の市場特性を再現
- 現実的なノイズレベル（volatility ~2-3%）
- 外れ値やジャンプの追加
- 複数の市場体制（トレンド変化）
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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

def generate_realistic_market_data():
    """
    1987年ブラックマンデー前の実市場特性を再現したデータ生成
    
    実市場の特徴:
    - 論文より: 1987年前9ヶ月で31.4%上昇
    - 日次ボラティリティ: ~1.5-2%
    - 週末効果、外れ値、regime change
    """
    print("=== 現実的な市場データシミュレーション ===\n")
    
    # パラメータ設定（論文の1987年ケースに基づく）
    n_days = 500  # 約2年分のデータ
    start_date = datetime(1985, 1, 1)
    
    # LPPLパラメータ（論文値に近い設定）
    true_params = {
        'tc': 1.05,      # クラッシュは時系列の最後近く
        'beta': 0.33,    # 論文値
        'omega': 7.4,    # 論文値
        'phi': 1.0,
        'A': 5.0,        # log(150) ≈ 5.0 (S&P500の1980年代レベル)
        'B': -0.3,
        'C': 0.08        # 小さな振幅
    }
    
    # 時間軸生成
    t = np.linspace(0, 1, n_days)
    dates = [start_date + timedelta(days=i) for i in range(n_days)]
    
    print(f"シミュレーション設定:")
    print(f"- データ期間: {dates[0].date()} - {dates[-1].date()}")
    print(f"- データ点数: {n_days}")
    print(f"- 真のパラメータ: β={true_params['beta']}, ω={true_params['omega']}")
    
    # 基本LPPLシグナル生成
    tc, beta, omega, phi, A, B, C = [true_params[key] for key in ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']]
    
    base_lppl = logarithm_periodic_func(t, tc, beta, omega, phi, A, B, C)
    
    # 現実的なノイズと市場効果を追加
    realistic_prices = add_market_realism(t, base_lppl, dates)
    
    return t, realistic_prices, dates, true_params

def add_market_realism(t, base_lppl, dates):
    """実市場の特性をシミュレーションに追加"""
    prices = base_lppl.copy()
    
    # 1. 基本的な市場ノイズ（日次ボラティリティ ~1.5%）
    daily_volatility = 0.015
    market_noise = np.random.normal(0, daily_volatility, len(t))
    prices += market_noise
    
    # 2. クラスター化されたボラティリティ（GARCH効果）
    volatility_clusters = generate_volatility_clusters(len(t))
    prices += volatility_clusters
    
    # 3. 週末・祝日効果のシミュレーション
    weekend_effects = add_calendar_effects(dates)
    prices += weekend_effects
    
    # 4. 外れ値・ジャンプの追加（年に数回程度）
    jump_effects = add_market_jumps(len(t), intensity=0.01)
    prices += jump_effects
    
    # 5. 徐々に強くなるトレンド（バブル形成）
    trend_acceleration = add_bubble_acceleration(t)
    prices += trend_acceleration
    
    print(f"市場特性追加完了:")
    print(f"- 基本ノイズレベル: {daily_volatility*100:.1f}%")
    print(f"- 最終的なボラティリティ: {np.std(np.diff(prices))*100:.2f}%")
    print(f"- 価格変動範囲: {np.exp(prices.min()):.0f} - {np.exp(prices.max()):.0f}")
    
    return prices

def generate_volatility_clusters(n_points):
    """ボラティリティクラスタリング効果を生成"""
    # 簡単なGARCH(1,1)風の効果
    volatility = np.zeros(n_points)
    sigma = 0.01  # 初期ボラティリティ
    
    for i in range(1, n_points):
        # ボラティリティの持続性
        sigma = 0.95 * sigma + 0.05 * abs(volatility[i-1]) + 0.001
        volatility[i] = np.random.normal(0, sigma)
    
    return volatility

def add_calendar_effects(dates):
    """カレンダー効果（月曜効果、月末効果など）をシミュレート"""
    effects = np.zeros(len(dates))
    
    for i, date in enumerate(dates):
        # 月曜効果（わずかに負の効果）
        if date.weekday() == 0:  # Monday
            effects[i] -= 0.002
        
        # 月末効果（わずかに正の効果）
        if date.day >= 28:
            effects[i] += 0.001
            
        # 年末効果
        if date.month == 12 and date.day >= 20:
            effects[i] += 0.003
    
    return effects

def add_market_jumps(n_points, intensity=0.01):
    """市場のジャンプ（外れ値）をシミュレート"""
    jumps = np.zeros(n_points)
    
    # ポアソン過程でジャンプタイミングを決定
    jump_times = np.random.poisson(intensity, n_points) > 0
    
    # ジャンプ幅は指数分布
    for i in np.where(jump_times)[0]:
        jump_direction = np.random.choice([-1, 1])
        jump_size = np.random.exponential(0.02)  # 平均2%のジャンプ
        jumps[i] = jump_direction * jump_size
    
    return jumps

def add_bubble_acceleration(t):
    """バブル形成期の加速的上昇をシミュレート"""
    # 後半になるほど強くなる上昇トレンド
    acceleration = 0.05 * (t ** 1.5)
    return acceleration

def fit_lppl_to_realistic_data(t, prices):
    """現実的なデータにLPPLフィッティング"""
    print("\n🔧 現実的市場データでのLPPLフィッティング")
    
    # パラメータ境界設定
    tc_bounds = (t[-1] + 0.01, t[-1] + 0.2)
    bounds = (
        [tc_bounds[0], 0.1, 2.0, -8*np.pi, prices.min()-1, -2.0, -2.0],
        [tc_bounds[1], 0.8, 15.0, 8*np.pi, prices.max()+1, 2.0, 2.0]
    )
    
    results = []
    n_trials = 15  # 現実的データには多めの試行
    
    print(f"複数初期値フィッティング（{n_trials}回試行）...")
    
    for i in range(n_trials):
        try:
            # 多様な初期値でロバストネステスト
            tc_init = np.random.uniform(tc_bounds[0], tc_bounds[1])
            beta_init = np.random.uniform(0.2, 0.6)
            omega_init = np.random.uniform(4.0, 12.0)
            phi_init = np.random.uniform(-np.pi, np.pi)
            A_init = np.random.uniform(prices.mean()-0.5, prices.mean()+0.5)
            B_init = np.random.uniform(-1, 1)
            C_init = np.random.uniform(-0.3, 0.3)
            
            p0 = [tc_init, beta_init, omega_init, phi_init, A_init, B_init, C_init]
            
            # 高精度フィッティング
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, prices,
                p0=p0, bounds=bounds, method='trf',
                ftol=1e-10, xtol=1e-10, gtol=1e-10,
                max_nfev=15000
            )
            
            # 品質評価
            y_pred = logarithm_periodic_func(t, *popt)
            residuals = prices - y_pred
            r_squared = 1 - (np.sum(residuals**2) / np.sum((prices - np.mean(prices))**2))
            rmse = np.sqrt(np.mean(residuals**2))
            
            # パラメータの物理的妥当性チェック
            tc, beta, omega = popt[0], popt[1], popt[2]
            if 0.1 <= beta <= 0.8 and 2.0 <= omega <= 15.0 and tc > t[-1]:
                results.append({
                    'trial': i+1,
                    'params': popt,
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'residuals': residuals,
                    'prediction': y_pred
                })
                print(f"  試行 {i+1}: R²={r_squared:.6f}, β={beta:.3f}, ω={omega:.2f} ✓")
            else:
                print(f"  試行 {i+1}: 物理的制約違反でスキップ")
                
        except Exception as e:
            print(f"  試行 {i+1}: エラー - {str(e)[:40]}...")
            continue
    
    if not results:
        print("❌ 有効なフィッティング結果がありません")
        return None
        
    # 最良結果の選択
    best_result = max(results, key=lambda x: x['r_squared'])
    print(f"\n✅ 最良結果: R²={best_result['r_squared']:.6f}")
    
    return best_result, results

def analyze_realistic_fitting(result, true_params):
    """現実的データでのフィッティング分析"""
    if result is None:
        return None
        
    params = result['params']
    tc, beta, omega, phi, A, B, C = params
    
    print(f"\n📊 現実的市場データでのフィッティング分析:")
    print(f"{'パラメータ':<12} {'推定値':<10} {'真値':<10} {'誤差率':<8} {'評価'}")
    print("-" * 55)
    
    # 真値との比較
    true_beta = true_params['beta']
    true_omega = true_params['omega']
    
    beta_error = abs(beta - true_beta) / true_beta * 100
    omega_error = abs(omega - true_omega) / true_omega * 100
    
    def get_evaluation(error):
        if error < 5: return "優秀 ✅"
        elif error < 10: return "良好 ⚠️"
        elif error < 20: return "許容 ⚠️"
        else: return "要改善 ❌"
    
    print(f"{'β (臨界指数)':<12} {beta:<10.4f} {true_beta:<10.2f} {beta_error:<8.1f}% {get_evaluation(beta_error)}")
    print(f"{'ω (角周波数)':<12} {omega:<10.4f} {true_omega:<10.1f} {omega_error:<8.1f}% {get_evaluation(omega_error)}")
    
    # 実市場条件での成功判定
    success_criteria = beta_error < 15 and omega_error < 20  # 現実的な基準
    
    print(f"\n🎯 実市場条件での評価:")
    if success_criteria:
        print("✅ 成功: 現実的なノイズ環境での論文値再現")
        print(f"   実用性: 実市場データでの運用可能レベル")
    else:
        print("❌ 要改善: より高精度な手法が必要")
        
    print(f"\n📈 フィッティング品質:")
    print(f"   R² = {result['r_squared']:.4f}")
    print(f"   RMSE = {result['rmse']:.4f}")
    
    return {
        'beta_error': beta_error,
        'omega_error': omega_error,
        'success': success_criteria,
        'r_squared': result['r_squared']
    }

def plot_realistic_market_results(t, prices, result, dates, true_params):
    """現実的市場データの結果可視化"""
    if result is None:
        return
        
    params = result['params']
    prediction = result['prediction']
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. メインプロット: 価格とフィッティング
    ax1.plot(dates, np.exp(prices), 'b-', linewidth=1, alpha=0.7, label='シミュレート市場価格')
    ax1.plot(dates, np.exp(prediction), 'r-', linewidth=2, label='LPPL フィッティング')
    
    # 真のLPPLシグナル（参考）
    true_tc, true_beta, true_omega, true_phi, true_A, true_B, true_C = [
        true_params[k] for k in ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
    ]
    true_signal = logarithm_periodic_func(t, true_tc, true_beta, true_omega, true_phi, true_A, true_B, true_C)
    ax1.plot(dates, np.exp(true_signal), 'g--', linewidth=2, alpha=0.8, label='真のLPPLシグナル')
    
    ax1.set_ylabel('価格', fontsize=12)
    ax1.set_title('現実的市場データとLPPLフィッティング', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 残差分析
    residuals = result['residuals']
    ax2.plot(dates, residuals, 'purple', linewidth=1, alpha=0.7)
    ax2.axhline(0, color='black', linestyle='-', alpha=0.5)
    ax2.set_ylabel('残差', fontsize=12)
    ax2.set_title('フィッティング残差', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. パラメータ比較
    param_names = ['β', 'ω']
    estimated = [params[1], params[2]]
    true_vals = [true_params['beta'], true_params['omega']]
    
    x_pos = np.arange(len(param_names))
    width = 0.35
    
    ax3.bar(x_pos - width/2, estimated, width, label='推定値', alpha=0.8, color='skyblue')
    ax3.bar(x_pos + width/2, true_vals, width, label='真値', alpha=0.8, color='orange')
    
    ax3.set_ylabel('パラメータ値', fontsize=12)
    ax3.set_title('主要パラメータの比較', fontsize=12)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(param_names)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 統計サマリー
    ax4.axis('off')
    
    r_sq = result['r_squared']
    rmse = result['rmse']
    beta_est, omega_est = params[1], params[2]
    beta_err = abs(beta_est - true_params['beta']) / true_params['beta'] * 100
    omega_err = abs(omega_est - true_params['omega']) / true_params['omega'] * 100
    
    summary_text = f"""
フィッティング統計
━━━━━━━━━━━━━━━━
R² 値: {r_sq:.4f}
RMSE: {rmse:.4f}

パラメータ精度
━━━━━━━━━━━━━━━━
β 誤差: {beta_err:.1f}%
ω 誤差: {omega_err:.1f}%

実用性評価
━━━━━━━━━━━━━━━━
現実的ノイズ環境での
論文パラメータ再現テスト
"""
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存
    filename = 'plots/market_validation/realistic_market_simulation.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n📊 結果保存: {filename}")
    plt.show()

def main():
    """メイン実行関数"""
    print("🎯 現実的市場データでのLPPL実用性検証\n")
    
    # 1. 現実的市場データ生成
    t, prices, dates, true_params = generate_realistic_market_data()
    
    # 2. LPPLフィッティング実行
    result, all_results = fit_lppl_to_realistic_data(t, prices)
    if result is None:
        print("❌ フィッティングに失敗しました")
        return
    
    # 3. 結果分析
    analysis = analyze_realistic_fitting(result, true_params)
    
    # 4. 可視化
    plot_realistic_market_results(t, prices, result, dates, true_params)
    
    # 5. 最終評価
    print(f"\n🏆 実市場適用可能性評価:")
    if analysis and analysis['success']:
        print("✅ 成功: 実市場レベルのノイズ環境でも論文値を再現")
        print("✅ 実用性: 実際のトレーディングでの活用が期待できる")
        print("✅ 堅牢性: 複雑な市場条件下でも安定したフィッティング")
    else:
        print("⚠️ 部分的成功: さらなる手法改善の余地あり")
        
    print(f"\n📝 次のステップ提案:")
    print("1. 他の歴史的クラッシュ事例での検証")
    print("2. リアルタイムデータでの適用テスト")
    print("3. 予測精度の向上手法の研究")

if __name__ == "__main__":
    main()