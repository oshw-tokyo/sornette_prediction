import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

from ..fitting.fitter import LogPeriodicFitter
from ..log_utils.analysis_logger import AnalysisLogger
from ..config.validation_settings import get_validation_settings
from .historical_crashes import CrashCase, get_crash_case

@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""
    success: bool
    parameters: Dict
    error_metrics: Dict
    statistical_tests: Dict
    original_values: Dict
    error_message: Optional[str] = None

class CrashValidator:
    def __init__(self):
        self.logger = AnalysisLogger()
        self.fitter = LogPeriodicFitter()
        
        # 検証設定の取得
        self.settings = get_validation_settings('default')
        
    def validate_crash(self, crash_case: CrashCase) -> ValidationResult:
        """クラッシュケースの再現性を検証"""
        try:
            # クラッシュケース固有の設定を取得
            case_settings = get_validation_settings(crash_case.id)
            
            # データ取得時の制限を適用
            data = self._get_market_data(
                crash_case.symbol,
                crash_case.period.start_date,
                crash_case.period.validation_end_date
            )

            # データ点数のチェック
            if len(data) < case_settings['minimum_data_points']:
                raise ValueError(
                    f"Insufficient data points: {len(data)} < "
                    f"{case_settings['minimum_data_points']}"
                )
                
            if len(data) > case_settings['maximum_data_points']:
                self.logger.warning(
                    f"Data points exceed maximum: {len(data)} > "
                    f"{case_settings['maximum_data_points']}"
                )

         
            t, prices = self.fitter.prepare_data(data['Close'].values)
            if t is None or prices is None:
                raise ValueError("Failed to prepare data")

            # 2. べき乗則フィット
            self.logger.info("Performing power law fitting...")
            power_law_result = self.fitter.fit_power_law(t, prices)
            if not power_law_result.success:
                raise ValueError("Power law fitting failed")

            # 3. 対数周期フィット
            self.logger.info("Performing log-periodic fitting...")
            log_periodic_result = self.fitter.fit_log_periodic(t, prices, power_law_result.parameters)
            if not log_periodic_result.success:
                raise ValueError("Log-periodic fitting failed")

            # 4. 結果の検証
            validation_metrics = self._validate_results(log_periodic_result, crash_case, data.index)
            
            # 5. 統計的有意性の評価
            statistical_tests = self._perform_statistical_tests(
                prices, 
                self.fitter.log_periodic_func(t, **log_periodic_result.parameters),
                log_periodic_result.statistical_significance
            )

            return ValidationResult(
                success=validation_metrics['overall_success'],
                parameters=log_periodic_result.parameters,
                error_metrics=validation_metrics['error_metrics'],
                statistical_tests=statistical_tests,
                original_values=crash_case.parameters
            )

        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return ValidationResult(
                success=False,
                parameters={},
                error_metrics={},
                statistical_tests={},
                original_values=crash_case.parameters,
                error_message=str(e)
            )

    def _get_market_data(self, symbol: str, start_date: datetime, 
                        end_date: datetime) -> pd.DataFrame:
        """市場データの取得"""
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start_date, end=end_date)
            if df.empty:
                raise ValueError(f"No data retrieved for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to download data: {str(e)}")
            return None

    def _validate_results(self, result, crash_case: CrashCase, dates) -> Dict:
        """フィッティング結果の検証"""
        # パラメータの相対誤差を計算
        errors = {
            'm': abs(result.parameters['m'] - crash_case.parameters.m),
            'omega': abs(result.parameters['omega'] - crash_case.parameters.omega),
        }

        # tcの誤差は日数で計算
        tc_date = dates[-1] + timedelta(days=int(result.parameters['tc']))
        errors['tc'] = abs((tc_date - crash_case.period.crash_date).days)

        # 許容範囲内かどうかを確認
        tolerances = getattr(crash_case, 'tolerances', self.default_tolerances)
        within_tolerance = {
            param: errors[param] <= tolerances[param]
            for param in errors.keys()
        }

        # 全体的な成功判定
        overall_success = all(within_tolerance.values())

        return {
            'overall_success': overall_success,
            'error_metrics': {
                'absolute_errors': errors,
                'within_tolerance': within_tolerance
            }
        }

    def _perform_statistical_tests(self, y_true: np.ndarray, y_pred: np.ndarray,
                                 base_tests: Dict) -> Dict:
        """追加の統計的検定を実行"""
        # 基本的な検定結果を継承
        tests = base_tests.copy()
        
        # 1. Kolmogorov-Smirnov検定（残差の分布の正規性）
        residuals = y_true - y_pred
        ks_stat, ks_pvalue = stats.kstest(
            (residuals - np.mean(residuals)) / np.std(residuals),
            'norm'
        )
        tests['ks_test'] = {
            'statistic': ks_stat,
            'p_value': ks_pvalue
        }
        
        # 2. Runs検定（残差の独立性）
        median = np.median(residuals)
        runs = np.sum(np.abs(np.diff(residuals > median))) + 1
        n1 = np.sum(residuals > median)
        n2 = len(residuals) - n1
        runs_zscore = (runs - (2*n1*n2/len(residuals) + 1)) / \
                     np.sqrt(2*n1*n2*(2*n1*n2 - len(residuals)) / \
                            (len(residuals)**2 * (len(residuals) - 1)))
        runs_pvalue = 2 * (1 - stats.norm.cdf(abs(runs_zscore)))
        tests['runs_test'] = {
            'statistic': runs_zscore,
            'p_value': runs_pvalue
        }
        
        return tests