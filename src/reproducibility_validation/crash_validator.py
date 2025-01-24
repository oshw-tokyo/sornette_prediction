import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

from ..fitting.fitter import LogarithmPeriodicFitter
from ..fitting.utils import power_law_func, logarithm_periodic_func
from ..config.validation_settings import get_validation_settings
from .historical_crashes import CrashCase

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
        super().__init__()
        self.default_tolerances = {
            'tc': 5,  # 日数での許容誤差
            'm': 0.05,
            'omega': 0.5,
            'phi': 0.5
        }
        self.fitter = LogarithmPeriodicFitter()
        
        # 検証設定の取得
        self.settings = get_validation_settings('default')
        
    def validate_crash(self, crash_case: CrashCase) -> ValidationResult:
        """クラッシュケースの再現性を検証"""
        try:
            # クラッシュケース固有の設定を取得
            case_settings = get_validation_settings(crash_case.id)
            
            data = self._get_market_data(
                crash_case.symbol,
                crash_case.period.start_date,
                crash_case.period.end_date
            )

            if data is None:
                raise ValueError("Failed to retrieve market data")
            
            # 取得データの概要をログ出力
            print("INFO: ", f"Retrieved data for {crash_case.symbol} from {crash_case.period.start_date} to {crash_case.period.end_date}")
            print("ERROR ", f"Data preview:\n{data.head()}")            

            # データ点数のチェック
            if len(data) < case_settings['minimum_data_points']:
                raise ValueError(
                    f"Insufficient data points: {len(data)} < "
                    f"{case_settings['minimum_data_points']}"
                )

            t, prices = self.fitter.prepare_data(data['Close'].values)
            if t is None or prices is None:
                raise ValueError("Failed to prepare data")

            # 2. べき乗則フィット
            print("INFO: ", "Performing power law fitting...")
            power_law_result = self.fitter.fit_power_law(t, prices)
            if not power_law_result.success:
                raise ValueError("Power law fitting failed")

            # 3. 対数周期フィット
            print("INFO: ", "Performing logarithm-periodic fitting...")
            logarithm_periodic_result = self.fitter.fit_logarithm_periodic(t, prices, power_law_result.parameters)
            if not logarithm_periodic_result.success:
                raise ValueError("Logarithm-periodic fitting failed")

            # 4. 結果の検証
            validation_metrics = self._validate_results(logarithm_periodic_result, crash_case, data.index)
            
            # 5. 統計的有意性の評価
            statistical_tests = self._perform_statistical_tests(
                prices, 
                logarithm_periodic_func(t, **logarithm_periodic_result.parameters),
                logarithm_periodic_result.statistical_significance
            )

            return ValidationResult(
                success=validation_metrics['overall_success'],
                parameters=logarithm_periodic_result.parameters,
                error_metrics=validation_metrics['error_metrics'],
                statistical_tests=statistical_tests,
                original_values=crash_case.parameters
            )

        except Exception as e:
            error_message = f"Validation failed due to error: {str(e)}"
            print("ERROR ", error_message)
            return ValidationResult(
                success=False,
                parameters={},
                error_metrics={},
                statistical_tests={},
                original_values=crash_case.parameters,
                error_message=error_message  # エラーメッセージを適切に設定
            )


    def _get_market_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """市場データの取得"""
        try:
            import yfinance as yf
            print("INFO: ", f"Downloading market data for {symbol} from {start_date} to {end_date}...")
            df = yf.download(symbol, start=start_date, end=end_date)
            if df.empty:
                raise ValueError(f"No data retrieved for {symbol}")

            # ダウンロード結果のログ出力
            print("INFO: ", f"Market data downloaded: {len(df)} rows")
            print("ERROR ", f"Data columns: {list(df.columns)}")
            print("ERROR ", f"First 5 rows of data:\n{df.head().to_string()}")  # 詳細なデータ内容を表示
            
            return df
        except Exception as e:
            print("ERROR ", f"Failed to download data: {str(e)}")
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
        tests = base_tests.copy()

        try:
            residuals = y_true - y_pred
            median = np.median(residuals)
            runs = np.sum(np.abs(np.diff(residuals > median))) + 1
            n1 = np.sum(residuals > median)
            n2 = len(residuals) - n1

            # デバッグ用ログ
            print("ERROR ", f"Residuals: mean={np.mean(residuals)}, std={np.std(residuals)}, len={len(residuals)}")
            print("ERROR ", f"Runs test inputs: n1={n1}, n2={n2}, len(residuals)={len(residuals)}")

            if len(residuals) <= 1 or n1 == 0 or n2 == 0:
                raise ValueError(f"Invalid residuals for Runs test calculation: len={len(residuals)}, n1={n1}, n2={n2}")

            numerator = runs - (2 * n1 * n2 / len(residuals) + 1)
            denominator = np.sqrt(abs(2 * n1 * n2 * (2 * n1 * n2 - len(residuals)) /
                                    (len(residuals)**2 * (len(residuals) - 1))))

            if denominator == 0 or np.isinf(denominator):
                raise ValueError(f"Invalid denominator in Runs test calculation: numerator={numerator}, denominator={denominator}")

            runs_zscore = numerator / denominator
            runs_pvalue = 2 * (1 - stats.norm.cdf(abs(runs_zscore)))
            tests['runs_test'] = {
                'statistic': runs_zscore,
                'p_value': runs_pvalue
            }
        except Exception as e:
            print("ERROR ", f"Statistical tests failed: {str(e)}")
            tests['runs_test'] = {
                'statistic': None,
                'p_value': None,
                'error': str(e)
            }
        return tests
