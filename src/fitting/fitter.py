import numpy as np
from scipy.optimize import curve_fit

import warnings
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

from ..logging.analysis_logger import AnalysisLogger

@dataclass
class FittingResult:
    """フィッティング結果を格納するデータクラス"""
    success: bool
    parameters: Dict[str, float]
    residuals: float
    r_squared: float
    error_message: Optional[str] = None
    is_typical_range: bool = False


class LogPeriodicFitter:
    """対数周期性のフィッティングを行うクラス"""
    
    def __init__(self):
        self.params = FittingParameters()
        self.logger = AnalysisLogger()        
        
    @staticmethod
    def log_periodic_func(t: np.ndarray, tc: float, m: float, omega: float, 
                         phi: float, A: float, B: float, C: float) -> np.ndarray:
        """対数周期関数のモデル"""
        dt = tc - t
        return A + B * np.power(dt, m) * (1 + C * np.cos(omega * np.log(dt) + phi))

    def fit_log_periodic(self, t: np.ndarray, y: np.ndarray, 
                        initial_params: Optional[Dict[str, float]] = None) -> FittingResult:
        """対数周期関数のフィッティングを実行"""
        # デバッグ出力を追加
        self.logger.info(f"Starting fit with data shape: t={t.shape}, y={y.shape}")
        
        # データの検証
        if len(t) == 0 or len(y) == 0:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message="Empty input data"
            )
        
        if len(t) != len(y):
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message="Input arrays must have the same length"
            )
        
        # デフォルトの初期パラメータ
        default_params = {
            'tc': t[-1] + (t[-1] - t[0]) * 0.1,
            'm': 0.45,
            'omega': 6.5,
            'phi': 0,
            'A': np.mean(y),
            'B': (y[-1] - y[0]) / (t[-1] - t[0]),
            'C': 0.1
        }
        
        # 初期パラメータの設定
        params = {**default_params, **(initial_params or {})}
        self.logger.info(f"Initial parameters: {params}")
        
        try:
            # 境界条件の調整
            bounds = (
                [t[-1], self.params.Z_MIN, self.params.OMEGA_MIN, -2*np.pi, -np.inf, -np.inf, -0.5],  # Cの下限を調整
                [t[-1] + (t[-1] - t[0])*0.5, self.params.Z_MAX, self.params.OMEGA_MAX, 2*np.pi, np.inf, np.inf, 0.5]   # Cの上限を調整
            )
            self.logger.info(f"Bounds: {bounds}")

            # フィッティングの実行
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                popt, pcov = curve_fit(
                    self.log_periodic_func, t, y,
                    p0=[params['tc'], params['m'], params['omega'], 
                        params['phi'], params['A'], params['B'], params['C']],
                    bounds=bounds,
                    maxfev=50000,
                    ftol=1e-8,
                    xtol=1e-8,
                    method='trf'
                )
            
            # フィッティング結果のパラメータを取得
            fitted_params = {
                'tc': popt[0], 'm': popt[1], 'omega': popt[2],
                'phi': popt[3], 'A': popt[4], 'B': popt[5], 'C': popt[6]
            }
            self.logger.info(f"Fitted parameters: {fitted_params}")
            
            # パラメータの検証
            is_valid, error_msg = self.params.validate_parameters(
                z=fitted_params['m'], 
                omega=fitted_params['omega']
            )
            
            if not is_valid:
                self.logger.warning(f"Parameter validation failed: {error_msg}")
                return FittingResult(
                    success=False,
                    parameters=fitted_params,
                    residuals=np.inf,
                    r_squared=0,
                    error_message=error_msg
                )
            
            # フィッティング品質の評価
            y_fit = self.log_periodic_func(t, *popt)
            residuals = np.mean((y - y_fit) ** 2)
            r_squared = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - np.mean(y)) ** 2)
            self.logger.info(f"Fit quality: residuals={residuals}, R²={r_squared}")
            
            # 品質チェックの閾値を調整
            if residuals > self.params.MAX_RESIDUAL or r_squared < self.params.MIN_R_SQUARED:
                self.logger.warning(f"Poor fit quality: residuals={residuals}, R²={r_squared}")
                return FittingResult(
                    success=False,
                    parameters=fitted_params,
                    residuals=residuals,
                    r_squared=r_squared,
                    error_message="Poor fit quality"
                )
            
            # 典型的な範囲内かどうかのチェック
            is_typical, _ = self.params.is_typical_range(
                z=fitted_params['m'], 
                omega=fitted_params['omega']
            )
            
            return FittingResult(
                success=True,
                parameters=fitted_params,
                residuals=residuals,
                r_squared=r_squared,
                is_typical_range=is_typical
            )
                
        except Exception as e:
            self.logger.error(f"Fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message=str(e)
            )

    def fit_with_multiple_initializations(self, t: np.ndarray, y: np.ndarray, 
                                        n_tries: int = 5) -> FittingResult:
        """
        複数の初期値でフィッティングを試行し、最良の結果を返す
        
        Args:
            t: 時間データ
            y: 価格データ
            n_tries: 試行回数
            
        Returns:
            FittingResult: 最良のフィッティング結果
        """
        best_result = FittingResult(success=False, parameters={}, residuals=np.inf, r_squared=0)
        
        for i in range(n_tries):
            # ランダムな初期パラメータの生成
            initial_params = {
                'tc': t[-1] + (t[-1] - t[0]) * np.random.uniform(0.05, 0.15),
                'm': np.random.uniform(self.params.Z_TYPICAL_MIN, self.params.Z_TYPICAL_MAX),
                'omega': np.random.uniform(self.params.OMEGA_MIN, self.params.OMEGA_MAX),
                'phi': np.random.uniform(-np.pi, np.pi),
                'A': np.mean(y) + np.random.normal(0, np.std(y) * 0.1),
                'B': (y[-1] - y[0]) / (t[-1] - t[0]) * (1 + np.random.normal(0, 0.1)),
                'C': np.random.uniform(0.05, 0.15)
            }
            
            result = self.fit_log_periodic(t, y, initial_params)
            
            if result.success and result.residuals < best_result.residuals:
                best_result = result
                
        return best_result


@dataclass
class FittingParameters:
    """Sornette model fitting parameters with theoretical constraints"""
    
    # Theoretical constraints
    Z_MIN: float = 0.0
    Z_MAX: float = 1.0
    Z_TYPICAL_MIN: float = 0.33
    Z_TYPICAL_MAX: float = 0.68
    
    OMEGA_MIN: float = 5.0
    OMEGA_MAX: float = 8.0
    
    # Fitting quality thresholds
    MAX_RESIDUAL: float = 1.0  # Maximum acceptable residual for good fit
    MIN_R_SQUARED: float = 0.95  # Minimum R-squared for acceptable fit # Initially 0.95
    
    @classmethod
    def validate_parameters(cls, z: float, omega: float) -> Tuple[bool, Optional[str]]:
        """
        Validate if parameters are within theoretical constraints
        
        Args:
            z: Power law exponent
            omega: Log-periodic angular frequency
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not cls.Z_MIN < z < cls.Z_MAX:
            return False, f"z parameter {z} outside theoretical range ({cls.Z_MIN}, {cls.Z_MAX})"
            
        if not cls.OMEGA_MIN <= omega <= cls.OMEGA_MAX:
            return False, f"omega parameter {omega} outside typical range ({cls.OMEGA_MIN}, {cls.OMEGA_MAX})"
            
        return True, None
    
    @classmethod
    def is_typical_range(cls, z: float, omega: float) -> Tuple[bool, Optional[str]]:
        """
        Check if parameters are within typical ranges observed in empirical studies
        
        Args:
            z: Power law exponent
            omega: Log-periodic angular frequency
            
        Returns:
            Tuple of (is_typical: bool, message: Optional[str])
        """
        if not cls.Z_TYPICAL_MIN <= z <= cls.Z_TYPICAL_MAX:
            return False, f"z parameter {z} outside typical range ({cls.Z_TYPICAL_MIN}, {cls.Z_TYPICAL_MAX})"
            
        if not cls.OMEGA_MIN <= omega <= cls.OMEGA_MAX:
            return False, f"omega parameter {omega} outside typical range ({cls.OMEGA_MIN}, {cls.OMEGA_MAX})"
            
        return True, None

    @classmethod
    def get_parameter_ranges(cls) -> dict:
        """
        Get the recommended parameter ranges for fitting
        
        Returns:
            Dictionary containing parameter ranges
        """
        return {
            'z': {
                'min': cls.Z_MIN,
                'max': cls.Z_MAX,
                'typical_min': cls.Z_TYPICAL_MIN,
                'typical_max': cls.Z_TYPICAL_MAX
            },
            'omega': {
                'min': cls.OMEGA_MIN,
                'max': cls.OMEGA_MAX
            }
        }



