import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

from .utils import power_law_func, logarithm_periodic_func


@dataclass
class FittingResult:
    """フィッティング結果を格納するデータクラス"""
    success: bool
    parameters: Dict[str, float]
    residuals: float
    r_squared: float
    statistical_significance: Dict
    error_message: Optional[str] = None
    is_typical_range: bool = False

class LogarithmPeriodicFitter:
    """Sornette et al. (1996)に基づく対数周期性フィッティング"""
    
    def prepare_data(self, prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sornette et al. (1996)に従ってデータを前処理
        1. 価格を最初の価格で正規化
        2. 正規化された価格を対数変換
        """
        try:
            # 1. 価格の正規化
            normalized_prices = prices / prices[0]
            
            # 2. 対数変換
            logarithm_prices = np.log(normalized_prices)
            
            # 時間軸の生成（0から1の範囲）
            t = np.linspace(0, 1, len(prices))
            
            # データの品質チェック
            if not np.all(np.isfinite(logarithm_prices)):
                print("ERROR: ", "Invalid values detected after logarithm transformation")
                return None, None
            
            print("INFO: ", f"Data preparation completed. Shape: {t.shape}")
            return t, logarithm_prices
            
        except Exception as e:
            print("ERROR: ", f"Data preparation failed: {str(e)}")
            return None, None

    def fit_with_multiple_initializations(self, t: np.ndarray, prices: np.ndarray, 
                                        n_tries: int = 5) -> FittingResult:
        """複数の初期値でフィッティングを試行"""
        best_result = None
        best_residuals = np.inf
        
        for i in range(n_tries):
            try:
                # 1. べき乗則フィット
                power_result = self.fit_power_law(t, prices)
                if not power_result.success:
                    continue
                
                # 2. 対数周期フィット
                result = self.fit_logarithm_periodic(t, prices, power_result.parameters)
                if not result.success:
                    continue
                
                if result.residuals < best_residuals:
                    best_result = result
                    best_residuals = result.residuals
                
            except Exception as e:
                print("WARNING: ", f"Fitting attempt {i+1} failed: {str(e)}")
                continue
        
        if best_result is None:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message="All fitting attempts failed"
            )
        
        return best_result

    def fit_power_law(self, t: np.ndarray, y: np.ndarray) -> FittingResult:
        """べき乗則による基本フィッティング"""
        try:
            # データを1次元配列に確実に変換
            t = np.asarray(t).ravel()
            y = np.asarray(y).ravel()
            
            # 初期パラメータ設定
            tc_init = t[-1] + (t[-1] - t[0]) * 0.2
            m_init = 0.45  # 論文での典型的な値
            A_init = np.mean(y)
            B_init = (y[-1] - y[0]) / (t[-1] - t[0])

            # パラメータをフラット化して1次元配列として渡す
            p0 = np.array([tc_init, m_init, A_init, B_init])

            # パラメータの境界設定
            bounds = (
                [t[-1], 0.1, -np.inf, -np.inf],  # 下限
                [t[-1] + (t[-1] - t[0]) * 0.3, 0.7, np.inf, np.inf]  # 上限
            )

            popt, pcov = curve_fit(
                power_law_func, t, y,
                p0=p0,
                bounds=bounds,
                maxfev=10000,
                method='trf'
            )

            # フィッティング結果の評価
            y_fit = power_law_func(t, *popt)
            residuals = np.mean((y - y_fit) ** 2)
            r_squared = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - np.mean(y)) ** 2)

            return FittingResult(
                success=True,
                parameters={
                    'tc': popt[0],
                    'm': popt[1],
                    'A': popt[2],
                    'B': popt[3]
                },
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=self._assess_statistical_significance(y, y_fit)
            )

        except Exception as e:
            print("ERROR: ", f"Power law fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )
        
    def fit_logarithm_periodic(self, t: np.ndarray, y: np.ndarray, 
                    power_law_params: Dict[str, float]) -> FittingResult:
        """対数周期フィッティング"""
        try:
            # データの1次元化
            t = np.asarray(t).ravel()
            y = np.asarray(y).ravel()
            
            p0 = [
                max(t[-1], min(t[-1] + (t[-1] - t[0]) * 0.1, power_law_params['tc'])),  # tc の制限
                max(0.1, min(0.9, power_law_params['m'])),  # m の制限
                6.36,  # omega
                0.0,  # phi
                max(-10, min(10, power_law_params['A'])),  # A の制限
                max(-10, min(10, power_law_params['B'])),  # B の制限
                0.05  # C
            ]

            bounds = (
                [t[-1], 0.1, 5.0, -2 * np.pi, -10, -10, -0.5],  # 下限
                [t[-1] + (t[-1] - t[0]) * 0.2, 0.9, 8.0, 2 * np.pi, 10, 10, 0.5]  # 上限
            )

            print("DEBUG: ", f"Initial parameters (p0): {p0}")

            print("DEBUG: ", f"Bounds: {bounds}")            
            
            # フィッティング実行
            popt, _ = curve_fit(
                logarithm_periodic_func,
                t, y,
                p0=p0,
                bounds=bounds,
                maxfev=10000,
                method='trf'
            )
            
            # 結果評価
            y_fit = logarithm_periodic_func(t, *popt)
            residuals = np.mean((y - y_fit) ** 2)
            r_squared = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - np.mean(y)) ** 2)
            
            return FittingResult(
                success=True,
                parameters={
                    'tc': popt[0],
                    'm': popt[1],
                    'omega': popt[2],
                    'phi': popt[3],
                    'A': popt[4],
                    'B': popt[5],
                    'C': popt[6]
                },
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=self._assess_statistical_significance(y, y_fit)
            )
            
        except Exception as e:
            print("ERROR: ", f"Logarithm-periodic fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )
   

    def _assess_statistical_significance(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """フィッティング結果の統計的有意性を評価"""
        residuals = y_true - y_pred
        n = len(y_true)
        p = 4  # パラメータ数

        # F検定
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        f_stat = ((ss_tot - ss_res) / (p - 1)) / (ss_res / (n - p))
        f_pvalue = 1 - stats.f.cdf(f_stat, p-1, n-p)

        # 残差の正規性検定
        normality_stat, normality_pvalue = stats.normaltest(residuals)

        # Durbin-Watson検定
        dw_stat = np.sum(np.diff(residuals) ** 2) / np.sum(residuals ** 2)

        return {
            'f_test': {
                'statistic': f_stat,
                'p_value': f_pvalue
            },
            'normality_test': {
                'statistic': normality_stat,
                'p_value': normality_pvalue
            },
            'durbin_watson': dw_stat
        }
    
    def fit(self, t: np.ndarray, y: np.ndarray) -> FittingResult:
        """統合的なフィッティングメソッド"""
        try:
            # 1. べき乗則フィッティング
            power_result = self.fit_power_law(t, y)
            if not power_result.success:
                raise ValueError("Power law fitting failed")
            
            # 2. 対数周期フィッティング
            logarithm_result = self.fit_logarithm_periodic(t, y, power_result.parameters)
            if not logarithm_result.success:
                raise ValueError("Logarithm-periodic fitting failed")
            
            return logarithm_result
        except Exception as e:
            print("ERROR: ", f"Fit process failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )
    

def check_stability(times, prices, window_size=30, step=5, data=None, symbol=None):
    """
    パラメータの安定性をチェック
    

    Returns:
    --------
    tuple:
        (tc_mean, tc_std, tc_cv, window_consistency)

    Parameters:
    -----------
    times : array-like
        時間データ
    prices : array-like
        価格データ
    window_size : int
        分析ウィンドウのサイズ（日数）
    step : int
        ウィンドウのスライド幅（日数）
    data : pandas.DataFrame
        元の株価データ（日付情報を取得するため）
    """
    tc_estimates = []
    windows = []
    
    for i in range(0, len(times) - window_size, step):
        window_times = times[i:i+window_size]
        window_prices = prices[i:i+window_size]
        
        tc_guess = window_times[-1] + 30
        
        try:
            popt, _ = LogarithmPeriodicFitter.fit_logarithm_periodic(window_times, window_prices, tc_guess)
            if popt is not None:
                tc_estimates.append(popt[0])
                windows.append(window_times[-1])
        except:
            continue
    
    if tc_estimates:
        plt.figure(figsize=(12, 6))
        plt.plot(windows, tc_estimates, 'bo-')
        plt.xlabel('ウィンドウ終了時点')
        plt.ylabel('予測された臨界時点')
        plt.title('臨界時点予測の安定性分析')
        plt.grid(True)
        
        # グラフを保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stability_{symbol}_{timestamp}.png' if symbol else f'stability_{timestamp}.png'
        
        output_dir = "analysis_results/plots"
        plt.savefig(os.path.join(output_dir, filename))
        plt.close() # プロットを閉じる
        
        # 安定性の指標を計算
        tc_std = np.std(tc_estimates)
        tc_mean = np.mean(tc_estimates)
        tc_cv = tc_std / tc_mean  # 変動係数

        # 時間窓での一貫性を計算
        window_consistency = max(0, 1 - 2 * tc_cv) if tc_cv is not None else 0
        
        print(f"\n安定性分析結果:")
        print(f"臨界時点の平均: {tc_mean:.2f}")
        print(f"臨界時点の標準偏差: {tc_std:.2f}")
        print(f"変動係数: {tc_cv:.3f}")
        print(f"予測一貫性: {window_consistency:.3f}") 
        
        # 日付での表示を追加
        if data is not None:
            mean_days_from_end = tc_mean - len(times)
            predicted_mean_date = data.index[-1] + timedelta(days=int(mean_days_from_end))
            print(f"予測される平均的な臨界時点の日付: {predicted_mean_date.strftime('%Y年%m月%d日')}")
            
            # 標準偏差を考慮した予測範囲
            earliest_date = predicted_mean_date - timedelta(days=int(tc_std))
            latest_date = predicted_mean_date + timedelta(days=int(tc_std))
            print(f"予測範囲: {earliest_date.strftime('%Y年%m月%d日')} ～ {latest_date.strftime('%Y年%m月%d日')}")
        
        return tc_mean, tc_std, tc_cv, window_consistency
    else:
        print("安定性分析に失敗しました。")
        return None, None, None, None