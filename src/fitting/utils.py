import numpy as np
from scipy import stats  
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error

import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import os

from ..log_utils.analysis_logger import AnalysisLogger


def power_law_func(t: np.ndarray, tc: float, m: float, A: float, B: float) -> np.ndarray:
    """べき乗則のモデル関数"""
    t = np.asarray(t).ravel()
    dt = tc - t
    mask = dt > 0
    result = np.zeros_like(t)
    result[mask] = A + B * np.power(dt[mask], m)
    return result

def log_periodic_func(t: np.ndarray, tc: float, m: float, omega: float,
                    phi: float, A: float, B: float, C: float) -> np.ndarray:
    """対数周期関数のモデル関数"""
    # 入力配列の次元チェックと変換
    t = np.asarray(t)
    original_shape = t.shape
    t = t.ravel()
    
    # 計算
    dt = tc - t
    mask = dt > 0
    result = np.zeros_like(t, dtype=float)
    valid_dt = dt[mask]
    
    if len(valid_dt) > 0:
        log_term = omega * np.log(valid_dt) + phi
        power_term = np.power(valid_dt, m)
        result[mask] = A + B * power_term * (1 + C * np.cos(log_term))
    
    return result.reshape(original_shape) if len(original_shape) > 1 else result



def validate_fit_quality(times, prices, popt, plot=True, symbol=None):
    """
    フィッティングの品質を評価
    """
    # 入力データを1次元配列に確実に変換
    times = np.asarray(times).ravel()
    prices = np.asarray(prices).ravel()
    
    # モデルによる予測値の計算
    predicted_prices = log_periodic_func(times, *popt)
    
    # 評価指標の計算
    r2 = r2_score(prices, predicted_prices)
    rmse = np.sqrt(mean_squared_error(prices, predicted_prices))
    
    # 残差の計算と1次元配列への変換
    residuals = (prices - predicted_prices).ravel()
    
    # 残差の正規性検定
    _, normality_p_value = stats.normaltest(residuals)
    
    # 残差から無限大やNaNを除去
    residuals = residuals[np.isfinite(residuals)]
    
    # 自己相関の計算（残差が空でないことを確認）
    if len(residuals) > 0:
        # 残差の分散が0でないことを確認
        variance = np.var(residuals)
        if variance > 0:
            autocorr = np.correlate(residuals, residuals, mode='full') / (len(residuals) * variance)
            autocorr = autocorr[len(autocorr)//2:]
        else:
            print("警告: 残差の分散が0です")
            autocorr = np.zeros(len(residuals))
    else:
        print("警告: 有効な残差データがありません")
        autocorr = np.array([])
    
    if plot:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 実データvs予測値プロット
        axes[0,0].scatter(prices, predicted_prices, alpha=0.5)
        axes[0,0].plot([min(prices), max(prices)], [min(prices), max(prices)], 'r--')
        axes[0,0].set_xlabel('実際の価格')
        axes[0,0].set_ylabel('予測価格')
        axes[0,0].set_title('実際の価格 vs 予測価格')
        
        # 2. 残差プロット
        axes[0,1].scatter(times, residuals, alpha=0.5)
        axes[0,1].axhline(y=0, color='r', linestyle='--')
        axes[0,1].set_xlabel('時間')
        axes[0,1].set_ylabel('残差')
        axes[0,1].set_title('残差の時系列プロット')
        
        # 3. 残差のヒストグラム
        if len(residuals) > 0:
            axes[1,0].hist(residuals, bins=30, density=True, alpha=0.7)
            xmin, xmax = axes[1,0].get_xlim()
            x = np.linspace(xmin, xmax, 100)
            axes[1,0].plot(x, stats.norm.pdf(x, np.mean(residuals), np.std(residuals)), 'r-', lw=2)
            axes[1,0].set_xlabel('残差')
            axes[1,0].set_ylabel('頻度')
            axes[1,0].set_title('残差の分布')
        
        # 4. 自己相関プロット
        if len(autocorr) > 0:
            lags = np.arange(len(autocorr))
            axes[1,1].plot(lags, autocorr)
            axes[1,1].axhline(y=0, color='r', linestyle='--')
            axes[1,1].axhline(y=1.96/np.sqrt(len(times)), color='r', linestyle=':')
            axes[1,1].axhline(y=-1.96/np.sqrt(len(times)), color='r', linestyle=':')
            axes[1,1].set_xlabel('ラグ')
            axes[1,1].set_ylabel('自己相関')
            axes[1,1].set_title('残差の自己相関')
        
        plt.tight_layout()
        
        
        # ファイルを保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'fit_quality_{symbol}_{timestamp}.png' if symbol else f'fit_quality_{timestamp}.png'
        
        output_dir = AnalysisLogger.ensure_output_dir(dir_name="analysis_results/plots")
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()

    
    # 最大自己相関の計算（自己相関が存在する場合のみ）
    max_autocorr = np.max(np.abs(autocorr[1:])) if len(autocorr) > 1 else 0
    
    return {
        'R2': r2,
        'RMSE': rmse,
        'Residuals_normality_p': normality_p_value,
        'Max_autocorr': max_autocorr
    }




def calculate_residuals(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """残差計算"""
    return np.mean((y_true - y_pred) ** 2)

def calculate_r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """決定係数計算"""
    return 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2)

# その他のユーティリティ関数