import unittest
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any  # 追加
from src.stock_analysis import (
    LogPeriodicFitter, 
    FittingParameters,
    FittingResult
)

class TestLogPeriodicFitter(unittest.TestCase):
    def setUp(self):
        """テストの前準備"""
        self.fitter = LogPeriodicFitter()
        
        # テストデータの生成
        self.t = np.linspace(0, 100, 200)
        # 既知のパラメータでテストデータを生成
        self.tc = 120
        self.m = 0.45
        self.omega = 6.5
        self.phi = 0.5
        self.A = 100
        self.B = 10
        self.C = 0.1
        
        # ノイズなしの理想的なデータ
        self.y_ideal = self.fitter.log_periodic_func(
            self.t, self.tc, self.m, self.omega, 
            self.phi, self.A, self.B, self.C
        )
        
        # 実際のデータを模擬するためにノイズを追加
        np.random.seed(42)  # 再現性のため
        self.noise = np.random.normal(0, 1, len(self.t))
        self.y_noisy = self.y_ideal + self.noise

    def test_parameter_validation(self):
        """パラメータ検証機能のテスト"""
        params = FittingParameters()
        
        # 有効なパラメータ
        is_valid, msg = params.validate_parameters(z=0.5, omega=6.0)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)
        
        # 無効なzパラメータ
        is_valid, msg = params.validate_parameters(z=1.5, omega=6.0)
        self.assertFalse(is_valid)
        self.assertIn("outside theoretical range", msg)
        
        # 無効なomegaパラメータ
        is_valid, msg = params.validate_parameters(z=0.5, omega=4.0)
        self.assertFalse(is_valid)
        self.assertIn("outside typical range", msg)

    def test_ideal_fitting(self):
        """理想的なデータでのフィッティングテスト"""
        result = self.fitter.fit_log_periodic(self.t, self.y_ideal)
        
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.99)  # 理想的なデータなので非常に高いR²を期待
        
        # パラメータが元の値に近いことを確認
        self.assertAlmostEqual(result.parameters['tc'], self.tc, delta=1)
        self.assertAlmostEqual(result.parameters['m'], self.m, delta=0.1)
        self.assertAlmostEqual(result.parameters['omega'], self.omega, delta=0.1)

    def test_noisy_fitting(self):
        """ノイズを含むデータでのフィッティングテスト"""
        result = self.fitter.fit_log_periodic(self.t, self.y_noisy)
        
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.8)  # ノイズがあるのでやや低いR²を許容
        
        # パラメータが妥当な範囲内にあることを確認
        self.assertTrue(0 < result.parameters['m'] < 1)
        self.assertTrue(5 <= result.parameters['omega'] <= 8)

    def test_multiple_initializations(self):
        """複数の初期値でのフィッティングテスト"""
        result = self.fitter.fit_with_multiple_initializations(
            self.t, self.y_noisy, n_tries=5
        )
        
        self.assertTrue(result.success)
        # 最良の結果が単一のフィッティングより良いことを期待
        single_result = self.fitter.fit_log_periodic(self.t, self.y_noisy)
        self.assertGreaterEqual(result.r_squared, single_result.r_squared)

def fit_log_periodic(self, t: np.ndarray, y: np.ndarray, 
                    initial_params: Optional[Dict[str, float]] = None) -> FittingResult:
    """対数周期関数のフィッティングを実行"""
    # 入力データの検証を追加
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
        
    # NaNチェックを追加
    if np.any(np.isnan(t)) or np.any(np.isnan(y)):
        return FittingResult(
            success=False,
            parameters={},
            residuals=np.inf,
            r_squared=0,
            error_message="Input data contains NaN values"
        )

if __name__ == '__main__':
    unittest.main()