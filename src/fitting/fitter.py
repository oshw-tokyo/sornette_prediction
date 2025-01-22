import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from ..log_utils.analysis_logger import AnalysisLogger

# fitter.py の先頭に追加
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

class LogPeriodicFitter:
    """Sornette et al. (1996)に基づく対数周期性フィッティング"""
    
    def __init__(self):
        self.logger = AnalysisLogger()

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
            log_prices = np.log(normalized_prices)
            
            # 時間軸の生成（0から1の範囲）
            t = np.linspace(0, 1, len(prices))
            
            # データの品質チェック
            if not np.all(np.isfinite(log_prices)):
                self.logger.error("Invalid values detected after log transformation")
                return None, None
            
            self.logger.info(f"Data preparation completed. Shape: {t.shape}")
            return t, log_prices
            
        except Exception as e:
            self.logger.error(f"Data preparation failed: {str(e)}")
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
                result = self.fit_log_periodic(t, prices, power_result.parameters)
                if not result.success:
                    continue
                
                if result.residuals < best_residuals:
                    best_result = result
                    best_residuals = result.residuals
                
            except Exception as e:
                self.logger.warning(f"Fitting attempt {i+1} failed: {str(e)}")
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
            tc_init = t[-1] + (t[-1] - t[0]) * 0.1
            m_init = 0.45  # 論文での典型的な値
            A_init = np.mean(y)
            B_init = (y[-1] - y[0]) / (t[-1] - t[0])

            # パラメータをフラット化して1次元配列として渡す
            p0 = np.array([tc_init, m_init, A_init, B_init])

            # パラメータの境界設定
            bounds = (
                [t[-1], 0.33, -np.inf, -np.inf],  # 下限
                [t[-1] + (t[-1] - t[0]) * 0.2, 0.68, np.inf, np.inf]  # 上限
            )

            popt, pcov = curve_fit(
                self.power_law_func, t, y,
                p0=p0,
                bounds=bounds,
                maxfev=10000,
                method='trf'
            )

            # フィッティング結果の評価
            y_fit = self.power_law_func(t, *popt)
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
            self.logger.error(f"Power law fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )
        
    def fit_log_periodic(self, t: np.ndarray, y: np.ndarray, 
                        power_law_params: Dict[str, float]) -> FittingResult:
        """対数周期補正を含むフィッティング"""
        try:
            # べき乗則フィットのパラメータを初期値として使用
            p0 = [
                power_law_params['tc'],
                power_law_params['m'],
                6.36,  # omega（論文での典型的な値）
                0,     # phi
                power_law_params['A'],
                power_law_params['B'],
                0.1    # C
            ]

            # 境界条件（論文に基づく）
            bounds = (
                [t[-1], 0.1, 5.0, -2*np.pi, -np.inf, -np.inf, -0.5],
                [t[-1] + (t[-1] - t[0])*0.5, 0.9, 8.0, 2*np.pi, np.inf, np.inf, 0.5]
            )

            popt, pcov = curve_fit(
                self.log_periodic_func, t, y,
                p0=p0,
                bounds=bounds,
                maxfev=10000
            )

            y_fit = self.log_periodic_func(t, *popt)
            residuals = np.mean((y - y_fit) ** 2)
            r_squared = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - np.mean(y)) ** 2)

            # 統計的有意性の評価
            significance = self._assess_statistical_significance(y, y_fit)

            # パラメータが典型的な範囲内かチェック
            is_typical = (0.33 <= popt[1] <= 0.68) and (5.0 <= popt[2] <= 8.0)

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
                statistical_significance=significance,
                is_typical_range=is_typical
            )

        except Exception as e:
            self.logger.error(f"Log-periodic fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    @staticmethod
    def power_law_func(t: np.ndarray, tc: float, m: float, A: float, B: float) -> np.ndarray:
        """べき乗則のモデル関数"""
        dt = tc - t
        mask = dt > 0
        result = np.zeros_like(t)
        result[mask] = A + B * np.power(dt[mask], m)
        return result

    @staticmethod
    def log_periodic_func(t: np.ndarray, tc: float, m: float, omega: float,
                        phi: float, A: float, B: float, C: float) -> np.ndarray:
        """
        対数周期関数のモデル
        
        Parameters:
        -----------
        t : np.ndarray
            時間データ（1次元配列）
        tc : float
            臨界時点
        m : float
            べき指数（0.33-0.68の範囲）
        omega : float
            対数周期の角振動数（5-8の範囲）
        phi : float
            位相（-2π から 2π の範囲）
        A, B, C : float
            振幅パラメータ
        
        Returns:
        --------
        np.ndarray
            対数周期関数の値（1次元配列）
        """
        # データを1次元配列に変換
        t = np.asarray(t).ravel()
        
        # dtの計算とマスク生成
        dt = tc - t
        mask = dt > 0
        
        # 結果配列の初期化
        result = np.zeros_like(t, dtype=float)
        
        # マスクされた領域での計算
        valid_dt = dt[mask]
        if len(valid_dt) > 0:
            # ここで重要なのは、各要素に対して一度に計算を行うこと
            log_term = omega * np.log(valid_dt) + phi
            power_term = np.power(valid_dt, m)
            result[mask] = A + B * power_term * (1 + C * np.cos(log_term))
        
        return result

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