import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import os
from ..fitting.utils import logarithm_periodic_func

def plot_fitting_results(times, prices, fitting_result, symbol=None, stock_data=None, save_dir="analysis_results/plots"):
    """フィッティング結果をプロット"""
    tc = fitting_result.parameters['tc']
    
    # フィッティング曲線の生成
    t_fit = np.linspace(min(times), tc-1, 1000)
    price_fit = logarithm_periodic_func(
        t_fit, 
        **fitting_result.parameters
    )
    
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # 実データのプロット
    ax.plot(times, prices, 'ko', label='実データ', markersize=2)
    ax.plot(t_fit, price_fit, 'r-', label='予測モデル')
    ax.axvline(x=tc, color='g', linestyle='--', label='予測される臨界時点')
    
    # 日付ラベルの設定
    if stock_data is not None:
        dates = stock_data.index
        ax.set_xticks([0, len(times)-1, tc])
        ax.set_xticklabels([
            dates[0].strftime('%Y-%m-%d'),
            dates[-1].strftime('%Y-%m-%d'),
            (dates[-1] + timedelta(days=int(tc - len(times)))).strftime('%Y-%m-%d')
        ], rotation=45)
    
    ax.set_xlabel('日付')
    ax.set_ylabel('価格')
    ax.set_title(f'{symbol or ""}の対数周期性分析')
    ax.legend()
    ax.grid(True)
    
    plt.tight_layout()
    
    if symbol and save_dir:
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, f'{symbol}_analysis.png')
        plt.savefig(filename)
        plt.close()
    else:
        plt.show()

def plot_stability_analysis(windows, tc_estimates, symbol=None, data=None, save_dir="analysis_results/plots"):
    """安定性分析の結果をプロット"""
    tc_mean = np.mean(tc_estimates)
    tc_std = np.std(tc_estimates)
    tc_cv = tc_std / tc_mean
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(windows, tc_estimates, 'bo-', label='臨界時点予測', markersize=4)
    ax.axhline(y=tc_mean, color='r', linestyle='--', label='平均値')
    ax.fill_between(windows, tc_mean - tc_std, tc_mean + tc_std, 
                   color='r', alpha=0.2, label='±1標準偏差')
    
    y_margin = tc_std * 2
    ax.set_ylim(min(tc_estimates) - y_margin, max(tc_estimates) + y_margin)
    
    ax.set_xlabel('ウィンドウ終了時点')
    ax.set_ylabel('予測された臨界時点')
    ax.set_title(f'{symbol or ""}の安定性分析')
    ax.grid(True)
    ax.legend()
    
    # 統計情報の表示
    stats_text = f'変動係数 (CV): {tc_cv:.3f}\n標準偏差: {tc_std:.1f}'
    if data is not None:
        mean_days = int(tc_mean - len(windows))
        pred_date = data.index[-1] + timedelta(days=mean_days)
        stats_text += f'\n予測日: {pred_date.strftime("%Y-%m-%d")}'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', bbox=dict(boxstyle='round', 
            facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    if symbol and save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(save_dir, f'stability_{symbol}_{timestamp}.png')
        plt.savefig(filename)
        plt.close()
    else:
        plt.show()

def ensure_output_dir(dir_name='analysis_results/temp'):
    """出力ディレクトリが存在しない場合は作成"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name