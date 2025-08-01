import numpy as np
from scipy import stats  
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error

import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import os



def power_law_func(t: np.ndarray, tc: float, beta: float, A: float, B: float) -> np.ndarray:
    """べき乗則のモデル関数"""
    dt = tc - t
    mask = dt > 0
    result = np.zeros_like(t)
    result[mask] = A + B * np.power(dt[mask], beta)
    return result


def logarithm_periodic_func(t: np.ndarray, tc: float, beta: float, omega: float,
                     phi: float, A: float, B: float, C: float) -> np.ndarray:
    """
    対数周期パワー法則モデル (LPPL)
    
    参照論文: papers/extracted_texts/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt
    数式: 式(54)
    I(t) = A + B(tc - t)^β + C(tc - t)^β cos(ω ln(tc - t) - φ)
    
    理論値: β = 0.33 ± 0.03, ω = 6-8 (Sornette, 2004)
    """
    # # 入力の形状を確認
    # print(f"\nFunction call info:")
    # print(f"Input t type: {type(t)}")
    # print(f"Input t dtype: {t.dtype}")
    # print(f"Input parameters: tc={tc}, beta={beta}, omega={omega}")
    
    t = np.asarray(t).ravel()
    dt = (tc - t).ravel()
    mask = dt > 0
    result = np.zeros_like(t, dtype=float)
    
    valid_dt = dt[mask]
    if len(valid_dt) > 0:
        # 中間計算結果を確認
        power_term = np.power(valid_dt, beta).ravel()
        log_term = np.log(valid_dt).ravel()
        cos_term = np.cos(omega * log_term + phi).ravel()
        oscillation = (C * power_term * cos_term).ravel()
        
        # print(f"Intermediate values:")
        # print(f"power_term: min={power_term.min():.3e}, max={power_term.max():.3e}")
        # print(f"cos_term: min={cos_term.min():.3e}, max={cos_term.max():.3e}")
        
        # 各ステップの結果を個別に計算
        base = (A + B * power_term).ravel()
        # print(f"Before assignment: base shape: {base.shape}, oscillation shape: {oscillation.shape}")
        # print(f"Result shape before: {result.shape}")
        result[mask] = (base + oscillation).ravel()
        # print(f"Result shape after assignment: {result.shape}")
    
    # 戻り値の形状を確認
    final_result = result.ravel()
    # print(f"Output shape: {final_result.shape}")
    # print(f"Output type: {type(final_result)}")
    # print(f"Output range: [{final_result.min():.3e}, {final_result.max():.3e}]")
    
    return final_result.ravel()

def assess_statistical_significance(y_true: np.ndarray, y_pred: np.ndarray, num_params: int = 7) -> dict:
    """統計的有意性の評価"""
    residuals = y_true - y_pred
    n = len(y_true)
    
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    f_stat = ((ss_tot - ss_res) / (num_params - 1)) / (ss_res / (n - num_params))
    f_pvalue = 1 - stats.f.cdf(f_stat, num_params-1, n-num_params)
    
    normality_stat, normality_pvalue = stats.normaltest(residuals)
    dw_stat = np.sum(np.diff(residuals) ** 2) / np.sum(residuals ** 2)
    
    return {
        'f_test': {'statistic': f_stat, 'p_value': f_pvalue},
        'normality_test': {'statistic': normality_stat, 'p_value': normality_pvalue},
        'durbin_watson': dw_stat
    }

def calculate_fit_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple:
    """フィッティングの評価指標を計算"""
    residuals = np.mean((y_true - y_pred) ** 2)
    r_squared = 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)
    return residuals, r_squared

def validate_fit_quality(times, prices, popt, plot=True, symbol=None):
    """
    フィッティングの品質を評価
    """
    # 入力データを1次元配列に確実に変換
    times = np.asarray(times).ravel()
    prices = np.asarray(prices).ravel()
    
    # モデルによる予測値の計算
    predicted_prices = logarithm_periodic_func(times, *popt)
    
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
        
        output_dir = "analysis_results/plots"
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