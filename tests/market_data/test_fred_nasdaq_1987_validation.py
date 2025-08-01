#!/usr/bin/env python3
"""
FRED NASDAQ データで1987年ブラックマンデー実市場検証

目的: FRED APIのNASDAQデータを使用して、1987年ブラックマンデー前の
     実市場データでLPPLモデルの検証を実行

データソース: FRED NASDAQCOM (1971年から利用可能)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# 環境変数とパス設定
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.fitting.utils import logarithm_periodic_func
from src.data_sources.fred_data_client import FREDDataClient
from scipy.optimize import curve_fit, differential_evolution

# 出力ディレクトリ
os.makedirs('plots/market_validation/', exist_ok=True)
os.makedirs('analysis_results/market_validation/', exist_ok=True)

def get_nasdaq_1987_data():
    """FRED APIからNASDAQ 1987年データを取得"""
    print("=== FRED NASDAQ 1987年データ取得 ===\n")
    
    client = FREDDataClient()
    
    # NASDAQデータ取得（1985-1987年）
    print("📊 NASDAQ Composite データ取得中...")
    data = client.get_series_data('NASDAQCOM', '1985-01-01', '1987-10-31')
    
    if data is None:
        print("❌ データ取得に失敗しました")
        return None
    
    print(f"✅ NASDAQ データ取得成功")
    print(f"   期間: {data.index[0].date()} - {data.index[-1].date()}")
    print(f"   データ点数: {len(data)}")
    print(f"   価格範囲: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
    
    # 1987年の詳細分析
    data_1987 = data[data.index.year == 1987]
    print(f"   1987年データ: {len(data_1987)}日")
    
    if len(data_1987) > 0:
        # 年間の変動分析
        year_start = data_1987['Close'].iloc[0]
        year_high = data_1987['Close'].max()
        year_end = data_1987['Close'].iloc[-1]
        
        annual_return = ((year_end / year_start) - 1) * 100
        peak_gain = ((year_high / year_start) - 1) * 100
        
        print(f"   1987年パフォーマンス:")
        print(f"     年初: {year_start:.2f}")
        print(f"     年高値: {year_high:.2f}")
        print(f"     年末: {year_end:.2f}")
        print(f"     年間リターン: {annual_return:+.1f}%")
        print(f"     年初からピークまで: {peak_gain:+.1f}%")
        
        # ブラックマンデー前後の分析
        crash_period = data_1987[(data_1987.index.month == 10)]
        if len(crash_period) > 0:
            oct_start = crash_period['Close'].iloc[0]
            oct_low = crash_period['Close'].min()
            crash_decline = ((oct_low / oct_start) - 1) * 100
            
            print(f"   10月のクラッシュ:")
            print(f"     10月初: {oct_start:.2f}")
            print(f"     10月最安値: {oct_low:.2f}")
            print(f"     最大下落率: {crash_decline:.1f}%")
    
    return data

def prepare_lppl_fitting_data(data):
    """LPPL フィッティング用データ準備"""
    print(f"\n=== LPPL フィッティング用データ準備 ===\n")
    
    # ブラックマンデー（1987年10月19日）より前のデータを使用
    crash_date = datetime(1987, 10, 19)
    pre_crash_data = data[data.index < crash_date]
    
    if len(pre_crash_data) < 100:
        print(f"❌ フィッティング用データが不足: {len(pre_crash_data)}日分")
        return None, None, None
    
    print(f"✅ フィッティング対象期間:")
    print(f"   期間: {pre_crash_data.index[0].date()} - {pre_crash_data.index[-1].date()}")
    print(f"   データ点数: {len(pre_crash_data)}")
    
    # 対数価格変換
    log_prices = np.log(pre_crash_data['Close'].values)
    
    # 時間軸正規化（0-1）
    t = np.linspace(0, 1, len(log_prices))
    
    print(f"   対数価格範囲: {log_prices.min():.4f} - {log_prices.max():.4f}")
    print(f"   総変動率: {((np.exp(log_prices[-1]) / np.exp(log_prices[0])) - 1) * 100:+.1f}%")
    
    return t, log_prices, pre_crash_data

def fit_lppl_to_nasdaq_data(t, log_prices):
    """NASDAQ データにLPPLモデルをフィッティング"""
    print(f"=== NASDAQ データ LPPL フィッティング ===\n")
    
    # パラメータ境界設定（1987年クラッシュに特化）
    tc_bounds = (1.01, 1.15)  # クラッシュ点
    
    bounds = (
        [tc_bounds[0], 0.1, 2.0, -8*np.pi, log_prices.min()-0.5, -2.0, -1.0],  # 下限
        [tc_bounds[1], 0.8, 15.0, 8*np.pi, log_prices.max()+0.5, 2.0, 1.0]     # 上限
    )
    
    print(f"フィッティング実行中（複数初期値による最適化）...")
    
    results = []
    n_trials = 25  # 実データには多めの試行
    
    for i in range(n_trials):
        try:
            # 初期値生成
            tc_init = np.random.uniform(tc_bounds[0], tc_bounds[1])
            beta_init = np.random.uniform(0.2, 0.5)  # 論文値0.33周辺
            omega_init = np.random.uniform(5.0, 10.0)  # 論文値7.4周辺
            phi_init = np.random.uniform(-np.pi, np.pi)
            A_init = np.mean(log_prices)
            B_init = np.random.uniform(-0.8, 0.8)
            C_init = np.random.uniform(-0.3, 0.3)
            
            p0 = [tc_init, beta_init, omega_init, phi_init, A_init, B_init, C_init]
            
            # 高精度フィッティング
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, log_prices,
                p0=p0, bounds=bounds, method='trf',
                ftol=1e-12, xtol=1e-12, gtol=1e-12,
                max_nfev=25000
            )
            
            # 品質評価
            y_pred = logarithm_periodic_func(t, *popt)
            residuals = log_prices - y_pred
            r_squared = 1 - (np.sum(residuals**2) / np.sum((log_prices - np.mean(log_prices))**2))
            rmse = np.sqrt(np.mean(residuals**2))
            
            # 物理的制約チェック
            tc, beta, omega = popt[0], popt[1], popt[2]
            if tc > t[-1] and 0.1 <= beta <= 0.8 and 2.0 <= omega <= 15.0 and r_squared > 0.5:
                results.append({
                    'trial': i+1,
                    'params': popt,
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'residuals': residuals,
                    'prediction': y_pred
                })
                
                if (i+1) % 5 == 0:  # 5回に1回進捗表示
                    print(f"  試行 {i+1}: R²={r_squared:.4f}, β={beta:.3f}, ω={omega:.2f}")
        
        except Exception as e:
            continue
    
    if not results:
        print("❌ 有効なフィッティング結果がありません")
        return None
    
    # 最良結果の選択（R²値で評価）
    best_result = max(results, key=lambda x: x['r_squared'])
    
    print(f"\n✅ フィッティング完了:")
    print(f"   成功試行: {len(results)}/{n_trials}")
    print(f"   最良R²: {best_result['r_squared']:.6f}")
    print(f"   最良RMSE: {best_result['rmse']:.6f}")
    
    return best_result, results

def analyze_nasdaq_fitting_results(result):
    """NASDAQ フィッティング結果の詳細分析"""
    if result is None:
        return None
    
    params = result['params']
    tc, beta, omega, phi, A, B, C = params
    
    print(f"\n=== NASDAQ 実市場データ フィッティング分析 ===\n")
    print(f"{'パラメータ':<15} {'推定値':<12} {'論文値':<12} {'誤差率':<10} {'評価'}")
    print("-" * 65)
    
    # 論文値との詳細比較
    paper_beta = 0.33
    paper_omega = 7.4
    
    beta_error = abs(beta - paper_beta) / paper_beta * 100
    omega_error = abs(omega - paper_omega) / paper_omega * 100
    
    def get_evaluation(error_pct):
        if error_pct < 5: return "優秀 ✅"
        elif error_pct < 10: return "良好 ⚠️"  
        elif error_pct < 20: return "許容 ⚠️"
        elif error_pct < 30: return "要注意 🔶"
        else: return "要改善 ❌"
    
    print(f"{'tc (臨界時刻)':<15} {tc:<12.4f} {'~1.02':<12} {'N/A':<10} {'N/A'}")
    print(f"{'β (臨界指数)':<15} {beta:<12.4f} {paper_beta:<12.2f} {beta_error:<10.1f}% {get_evaluation(beta_error)}")
    print(f"{'ω (角周波数)':<15} {omega:<12.4f} {paper_omega:<12.1f} {omega_error:<10.1f}% {get_evaluation(omega_error)}")
    print(f"{'φ (位相)':<15} {phi:<12.4f} {'N/A':<12} {'N/A':<10} {'N/A'}")
    print(f"{'A (定数項)':<15} {A:<12.4f} {'N/A':<12} {'N/A':<10} {'N/A'}")
    print(f"{'B (パワー係数)':<15} {B:<12.4f} {'負値期待':<12} {'N/A':<10} {'N/A'}")
    print(f"{'C (振動振幅)':<15} {C:<12.4f} {'小値期待':<12} {'N/A':<10} {'N/A'}")
    
    # 実市場適用可能性の総合評価
    r_squared = result['r_squared']
    rmse = result['rmse']
    
    # 評価基準（実市場データ用に緩和）
    beta_acceptable = beta_error < 25  # 実市場では25%以内を許容
    omega_acceptable = omega_error < 30  # 実市場では30%以内を許容
    r2_acceptable = r_squared > 0.75  # 実市場では0.75以上を許容
    
    overall_success = beta_acceptable and omega_acceptable and r2_acceptable
    
    print(f"\n🎯 実市場適用可能性評価:")
    print(f"   フィッティング品質: R²={r_squared:.4f}, RMSE={rmse:.4f}")
    
    if overall_success:
        print("✅ 成功: 実市場でのLPPLモデル妥当性を確認")
        print("✅ 科学的意義: 理論が実際の市場現象を説明可能")
        print("✅ 実用価値: クラッシュ前兆パターンの検出が可能")
    else:
        print("⚠️ 部分的成功: モデル適用に課題あり")
        if not beta_acceptable:
            print(f"   🔶 β値の乖離が大きい: {beta_error:.1f}%")
        if not omega_acceptable:
            print(f"   🔶 ω値の乖離が大きい: {omega_error:.1f}%")
        if not r2_acceptable:
            print(f"   🔶 フィッティング品質が低い: R²={r_squared:.3f}")
    
    return {
        'beta_error': beta_error,
        'omega_error': omega_error,
        'r_squared': r_squared,
        'rmse': rmse,
        'overall_success': overall_success,
        'beta_acceptable': beta_acceptable,
        'omega_acceptable': omega_acceptable,
        'r2_acceptable': r2_acceptable
    }

def plot_nasdaq_validation_results(pre_crash_data, result, analysis):
    """NASDAQ 検証結果の詳細可視化"""
    if result is None:
        return
    
    params = result['params']
    prediction = result['prediction']
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. メインプロット: NASDAQ実データとLPPLフィッティング
    dates = pre_crash_data.index
    actual_prices = pre_crash_data['Close'].values
    fitted_prices = np.exp(prediction)
    
    ax1.plot(dates, actual_prices, 'b-', linewidth=1.5, alpha=0.8, label='NASDAQ実データ (FRED)')
    ax1.plot(dates, fitted_prices, 'r-', linewidth=2.5, label='LPPL フィッティング')
    
    # ブラックマンデーの位置
    crash_date = datetime(1987, 10, 19)
    ax1.axvline(crash_date, color='red', linestyle='--', alpha=0.7, label='ブラックマンデー')
    
    ax1.set_ylabel('NASDAQ Composite Index', fontsize=12)
    ax1.set_title('1987年ブラックマンデー前のNASDAQ実市場データとLPPLフィッティング\n(FRED データソース)', 
                  fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 統計情報の表示
    r_sq = result['r_squared']
    rmse = result['rmse']
    beta_est, omega_est = params[1], params[2]
    
    info_text = f'R² = {r_sq:.4f}\nRMSE = {rmse:.4f}\nβ = {beta_est:.3f}\nω = {omega_est:.2f}'
    ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    # 2. 残差分析
    residuals = result['residuals']
    ax2.plot(dates, residuals, 'green', linewidth=1, alpha=0.7)
    ax2.axhline(0, color='black', linestyle='-', alpha=0.5)
    ax2.set_ylabel('フィッティング残差', fontsize=12)
    ax2.set_title('残差分析', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. パラメータ比較
    param_names = ['β (臨界指数)', 'ω (角周波数)']
    estimated = [params[1], params[2]]
    paper_values = [0.33, 7.4]
    errors = [analysis['beta_error'], analysis['omega_error']]
    
    x_pos = np.arange(len(param_names))
    width = 0.35
    
    bars1 = ax3.bar(x_pos - width/2, estimated, width, label='推定値', 
                    alpha=0.8, color='skyblue')
    bars2 = ax3.bar(x_pos + width/2, paper_values, width, label='論文値', 
                    alpha=0.8, color='orange')
    
    ax3.set_ylabel('パラメータ値', fontsize=12)
    ax3.set_title('論文値との比較', fontsize=12)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(param_names)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 誤差率をバーに表示
    for i, (bar1, bar2, error) in enumerate(zip(bars1, bars2, errors)):
        height1 = bar1.get_height()
        ax3.text(bar1.get_x() + bar1.get_width()/2., height1 + height1*0.05,
                f'{estimated[i]:.3f}\n({error:+.1f}%)', ha='center', va='bottom', fontsize=9)
        
        height2 = bar2.get_height()
        ax3.text(bar2.get_x() + bar2.get_width()/2., height2 + height2*0.05,
                f'{paper_values[i]:.3f}', ha='center', va='bottom', fontsize=9)
    
    # 4. 総合評価サマリー
    ax4.axis('off')
    
    success = analysis['overall_success']
    
    summary_text = f"""
NASDAQ実市場データ検証結果
━━━━━━━━━━━━━━━━━━━━━━
データソース: FRED NASDAQCOM
検証期間: {dates[0].date()} - {dates[-1].date()}
データ点数: {len(dates)}

フィッティング品質
━━━━━━━━━━━━━━━━━━━━━━
R² 値: {r_sq:.4f}
RMSE: {rmse:.4f}

論文値との比較
━━━━━━━━━━━━━━━━━━━━━━
β 誤差: {analysis['beta_error']:.1f}%
ω 誤差: {analysis['omega_error']:.1f}%

総合評価
━━━━━━━━━━━━━━━━━━━━━━
{'✅ 実市場適用可能' if success else '⚠️ 要改善'}

科学的意義
━━━━━━━━━━━━━━━━━━━━━━
{'LPPLモデルの実証的妥当性確認' if success else 'モデル精度向上の必要性確認'}
"""
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', 
             bbox=dict(boxstyle='round,pad=0.5', 
                      facecolor='lightgreen' if success else 'lightyellow', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存
    filename = 'plots/market_validation/1987_nasdaq_fred_validation.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n📊 検証結果保存: {filename}")
    plt.show()

def save_validation_results(result, analysis, data_info):
    """検証結果の詳細保存"""
    if result is None:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 結果レポート作成
    params = result['params']
    
    report = f"""# NASDAQ実市場データLPPL検証結果レポート

## 実行情報
- 実行日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- データソース: FRED NASDAQCOM
- 検証期間: {data_info['start_date']} - {data_info['end_date']}
- データ点数: {data_info['data_points']}

## フィッティング結果

### パラメータ推定値
- tc (臨界時刻): {params[0]:.6f}
- β (臨界指数): {params[1]:.6f}
- ω (角周波数): {params[2]:.6f}
- φ (位相): {params[3]:.6f}
- A (定数項): {params[4]:.6f}
- B (パワー係数): {params[5]:.6f}
- C (振動振幅): {params[6]:.6f}

### 品質指標
- R²値: {result['r_squared']:.6f}
- RMSE: {result['rmse']:.6f}

### 論文値との比較
- β値論文比較: 推定{params[1]:.3f} vs 論文0.330 (誤差{analysis['beta_error']:.1f}%)
- ω値論文比較: 推定{params[2]:.3f} vs 論文7.400 (誤差{analysis['omega_error']:.1f}%)

## 評価結果

### 個別評価
- β値適合性: {'✅ 許容範囲' if analysis['beta_acceptable'] else '❌ 要改善'}
- ω値適合性: {'✅ 許容範囲' if analysis['omega_acceptable'] else '❌ 要改善'}
- フィッティング品質: {'✅ 許容範囲' if analysis['r2_acceptable'] else '❌ 要改善'}

### 総合評価
**{'✅ 成功: 実市場でのLPPLモデル適用可能性を確認' if analysis['overall_success'] else '⚠️ 部分的成功: モデル改良が必要'}**

## 科学的・実用的意義

### 成功の場合の意義
- LPPLモデルが実際の市場クラッシュ前兆を捉える能力を実証
- 1987年ブラックマンデーのような歴史的イベントの理論的説明
- 将来のクラッシュ予測システム構築への道筋

### 今後の展開
1. 他の歴史的クラッシュ事例での検証拡大
2. リアルタイム監視システムの構築
3. 予測精度向上のためのモデル改良
4. 実用トレーディングシステムへの統合

---
*このレポートは実市場データを用いたLPPLモデルの科学的検証結果です*
"""
    
    # ファイル保存
    result_file = f'analysis_results/market_validation/nasdaq_1987_validation_{timestamp}.md'
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 詳細レポート保存: {result_file}")

def main():
    """メイン実行関数"""
    print("🎯 FRED NASDAQ 1987年実市場データ検証開始\n")
    
    # 1. NASDAQデータ取得
    nasdaq_data = get_nasdaq_1987_data()
    if nasdaq_data is None:
        print("❌ データ取得に失敗しました")
        return
    
    # 2. フィッティング用データ準備
    t, log_prices, pre_crash_data = prepare_lppl_fitting_data(nasdaq_data)
    if t is None:
        print("❌ データ準備に失敗しました")
        return
    
    # 3. LPPLフィッティング実行
    result, all_results = fit_lppl_to_nasdaq_data(t, log_prices)
    if result is None:
        print("❌ フィッティングに失敗しました")
        return
    
    # 4. 結果分析
    analysis = analyze_nasdaq_fitting_results(result)
    
    # 5. 結果可視化
    plot_nasdaq_validation_results(pre_crash_data, result, analysis)
    
    # 6. 結果保存
    data_info = {
        'start_date': pre_crash_data.index[0].date(),
        'end_date': pre_crash_data.index[-1].date(),
        'data_points': len(pre_crash_data)
    }
    save_validation_results(result, analysis, data_info)
    
    # 7. 最終評価
    print(f"\n🏆 FRED NASDAQ実市場データ検証 最終結果:")
    
    if analysis and analysis['overall_success']:
        print("✅ 成功: LPPLモデルの実市場適用可能性を実証")
        print("✅ 科学的価値: 理論が実際のクラッシュ前兆を説明")
        print("✅ 実用価値: クラッシュ予測システム構築の基盤確立")
        
        print(f"\n🚀 推奨次ステップ:")
        print("1. 他の歴史的クラッシュでの検証拡大")
        print("2. S&P500等の他指数での検証")
        print("3. リアルタイム監視システムの開発")
        print("4. 実用トレーディングシステムの構築")
        
    else:
        print("⚠️ 部分的成功: 理論と実市場間のギャップを確認")
        print("🔬 研究価値: モデル改良の方向性を提示")
        
        print(f"\n🛠️ 改善提案:")
        print("1. より高精度な最適化手法の導入")
        print("2. 市場体制変化を考慮したモデル拡張")
        print("3. ノイズ除去・前処理技術の向上")
    
    print(f"\n📊 達成事項サマリー:")
    print("✅ FRED APIキーの設定・動作確認完了")
    print("✅ 1987年実市場データの取得成功")
    print("✅ 実市場データでのLPPL検証実行完了")
    print("✅ 論文値との定量的比較完了")
    print("✅ 将来実装のためのAPI基盤確立")

if __name__ == "__main__":
    main()