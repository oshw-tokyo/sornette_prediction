import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import os
from ..fitting.fitter import LogPeriodicFitter

def plot_fitting_results(times, prices, fitting_result, symbol, stock_data):
    """フィッティング結果をプロット"""
    tc = fitting_result.parameters['tc']
    
    # フィッティング曲線の生成
    t_fit = np.linspace(min(times), tc-1, 1000)
    price_fit = LogPeriodicFitter.log_periodic_func(
        t_fit, 
        tc=fitting_result.parameters['tc'],
        m=fitting_result.parameters['m'],
        omega=fitting_result.parameters['omega'],
        phi=fitting_result.parameters['phi'],
        A=fitting_result.parameters['A'],
        B=fitting_result.parameters['B'],
        C=fitting_result.parameters['C']
    )
    
    plt.figure(figsize=(15, 10))
    
    # 実データのプロット
    plt.plot(times, prices, 'ko', label='実データ', markersize=2)
    
    # フィッティング曲線のプロット
    plt.plot(t_fit, price_fit, 'r-', label='予測モデル')
    
    # 臨界時点の表示
    plt.axvline(x=tc, color='g', linestyle='--', label='予測される臨界時点')
    
    # 日付ラベルの設定
    dates = stock_data.index
    plt.xticks(
        [0, len(times)-1, tc],
        [dates[0].strftime('%Y-%m-01'),
         dates[-1].strftime('%Y-%m-%d'),
         (dates[-1] + timedelta(days=int(tc - len(times)))).strftime('%Y-%m-%d')],
        rotation=45
    )
    
    plt.xlabel('日付')
    plt.ylabel('価格')
    plt.title(f'{symbol}の対数周期性分析')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    # グラフを保存
    output_dir = ensure_output_dir(dir_name="analysis_results/plots")
    plt.savefig(os.path.join(output_dir, f'{symbol}_analysis.png'))
    plt.close()


def plot_stability_analysis(windows, tc_estimates, symbol):
    """
    安定性分析の結果をプロット

    Parameters:
    -----------
    windows : array-like
        分析ウィンドウの終了時点
    tc_estimates : array-like
        各ウィンドウでの臨界時点の予測値
    symbol : str
        分析対象の銘柄コード
    """
    plt.figure(figsize=(12, 6))
    
    # メインのプロット
    plt.plot(windows, tc_estimates, 'bo-', label='臨界時点予測', markersize=4)
    
    # 平均値と標準偏差の範囲を表示
    tc_mean = np.mean(tc_estimates)
    tc_std = np.std(tc_estimates)
    plt.axhline(y=tc_mean, color='r', linestyle='--', label='平均値')
    plt.fill_between(windows, 
                    tc_mean - tc_std, tc_mean + tc_std, 
                    color='r', alpha=0.2, label='±1標準偏差')
    
    # プロットの装飾
    plt.xlabel('ウィンドウ終了時点（データポイント）')
    plt.ylabel('予測された臨界時点（データポイント）')
    plt.title(f'{symbol} - 臨界時点予測の安定性分析')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # y軸の範囲を適切に設定
    y_margin = tc_std * 2
    plt.ylim(min(tc_estimates) - y_margin, max(tc_estimates) + y_margin)
    
    # 変動係数（CV）を計算して表示
    cv = tc_std / tc_mean if tc_mean != 0 else float('inf')
    plt.text(0.02, 0.98, 
             f'変動係数 (CV): {cv:.3f}\n標準偏差: {tc_std:.1f}',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # グラフを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = ensure_output_dir(dir_name="analysis_results/plots")
    plt.savefig(os.path.join(output_dir, f'stability_{symbol}_{timestamp}.png'))
    plt.close()


def ensure_output_dir(dir_name='analysis_results/temp'):
    """出力ディレクトリが存在しない場合は作成"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name