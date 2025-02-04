import numpy as np
from scipy.optimize import curve_fit
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from .utils import (power_law_func, logarithm_periodic_func, 
                   assess_statistical_significance, calculate_fit_metrics)

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
    """Critical Market Crashes の式(54)に基づく対数周期性フィッティング"""
    
    def prepare_data(self, prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """データの前処理"""
        try:
            log_prices = np.log(prices)
            normalized_log_prices = log_prices - log_prices[0]
            t = np.linspace(0, 1, len(prices))
            
            return t, normalized_log_prices
            
        except Exception as e:
            print(f"ERROR: Data preparation failed: {str(e)}")
            return None, None

    def fit_power_law(self, t: np.ndarray, y: np.ndarray) -> FittingResult:
        """第1段階: べき乗則フィッティング"""
        try:

            # データのシェイプを統一
            t = np.asarray(t).ravel()
            y = np.asarray(y).ravel()
            # デバッグ情報
            print(f"Input check:")
            print(f"t shape: {t.shape}, y shape: {y.shape}")
            print(f"t range: [{t.min()}, {t.max()}]")
            print(f"y range: [{y.min()}, {y.max()}]")

            # データの有効性チェック
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                raise ValueError("Invalid values in data")

                   # 初期値の設定 - Aについては対数空間で設定
            p0 = [1.1, 0.45, np.log(np.mean(y)), (y[-1]-y[0])/(t[-1]-t[0])]
            bounds = ([1.01, 0.2, -np.inf, -np.inf],
                     [1.2, 0.5, np.inf, np.inf])
            
            popt, _ = curve_fit(power_law_func, t, y, p0=p0, bounds=bounds, maxfev=10000, method='trf')
            
            y_fit = power_law_func(t, *popt)
            residuals, r_squared = calculate_fit_metrics(y, y_fit)

            print(f"Fitted parameters: tc={popt[0]}, beta={popt[1]}")

            return FittingResult(
                success=True,
                parameters={'tc': popt[0], 'beta': popt[1], 
                            'A': np.exp(popt[2]), 'B': popt[3]},
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=assess_statistical_significance(y, y_fit)
            )
            
        except Exception as e:
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
        """第2段階: 対数周期項を含む完全なフィッティング"""
        try:
            # べき乗則フィットの残差を計算
            y_power = power_law_func(t, **power_law_params)
            residuals = y - y_power
            
            # デバッグ情報
            print(f"Power law residuals range: [{residuals.min():.3e}, {residuals.max():.3e}]")

            p0 = [
                power_law_params['tc'],
                power_law_params['beta'],
                6.36,  # omega
                0.0,   # phi
                np.log(power_law_params['A']),  # 対数空間に変換
                power_law_params['B'],
                0.1    # C
            ]
            
            bounds = ([
                p0[0]*0.9, p0[1]*0.8,  # より広い範囲
                2.0, -8*np.pi, -np.inf, -np.inf, -2.0
            ], [
                p0[0]*1.1, p0[1]*1.2,
                15.0, 8*np.pi, np.inf, np.inf, 2.0
            ])

            popt, _ = curve_fit(logarithm_periodic_func, t, y, p0=p0, bounds=bounds, maxfev=10000)     
            
            y_fit = logarithm_periodic_func(t, *popt)
            residuals, r_squared = calculate_fit_metrics(y, y_fit)

            return FittingResult(
                success=True,
                parameters={
                    'tc': popt[0],
                    'beta': popt[1],
                    'omega': popt[2],
                    'phi': popt[3],
                    'A': np.exp(popt[4]),  # 元の空間に戻す
                    'B': popt[5],
                    'C': popt[6]
                },
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=assess_statistical_significance(y, y_fit)
            )

        except Exception as e:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    def fit(self, t: np.ndarray, y: np.ndarray) -> FittingResult:
        """2段階フィッティングの実行"""
        try:
            power_result = self.fit_power_law(t, y)
            if not power_result.success:
                raise ValueError("Power law fitting failed")
            
            full_result = self.fit_logarithm_periodic(t, y, power_result.parameters)
            if not full_result.success:
                raise ValueError("Logarithm periodic fitting failed")
            
            return full_result

        except Exception as e:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    def check_stability(self, times, prices, window_size=30, step=5, data=None, symbol=None):
        """パラメータの安定性分析"""
        tc_estimates = []
        windows = []
        
        for i in range(0, len(times) - window_size, step):
            window_times = times[i:i+window_size]
            window_prices = prices[i:i+window_size]
            
            try:
                result = self.fit(window_times, window_prices)
                if result.success:
                    tc_estimates.append(result.parameters['tc'])
                    windows.append(window_times[-1])
            except Exception as e:
                print(f"Window {i} fitting failed: {str(e)}")
                continue
        
        if not tc_estimates:
            print("No successful fits in stability analysis")
            return None, None, None, None
            
        tc_mean = np.mean(tc_estimates)
        tc_std = np.std(tc_estimates)
        tc_cv = tc_std / tc_mean
        window_consistency = max(0, 1 - 2 * tc_cv)
        
        return tc_mean, tc_std, tc_cv, window_consistency