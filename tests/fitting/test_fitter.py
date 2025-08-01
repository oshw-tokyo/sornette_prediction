# tests/fitting/test_fitter.py

import unittest
import numpy as np
from src.fitting.fitter import LogarithmPeriodicFitter

# tests/fitting/test_fitter.py
class TestLogarithmPeriodicFitter(unittest.TestCase):
    def setUp(self):
        self.fitter = LogarithmPeriodicFitter()
        self.t = np.linspace(0, 0.8, 200)  # tcまでの範囲を確保
        tc = 1.0  # 論文の標準化に合わせる
        m = 0.33  # 論文値 # 要修正
        omega = 7.4  # 論文値 # 要修正
        phi = 0
        A = 1.0
        B = -0.5
        C = 0.1
        
        dt = tc - self.t
        self.y_power_law = A + B * np.power(dt, m)
        self.y_ideal = A + B * np.power(dt, m) * (1 + C * np.cos(omega * np.log(dt) + phi))
        self.y_noisy = self.y_ideal + np.random.normal(0, 0.01, len(self.t))
    
    def test_fit_integration(self):
        result = self.fitter.fit(self.t, self.y_ideal)
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.95)

    def test_power_law_fitting(self):
        """べき乗則フィッティングのテスト"""
        result = self.fitter.fit_power_law(self.t, self.y_power_law)
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.95)
        
    def test_logarithm_periodic_fitting(self):
        """対数周期フィッティングのテスト"""
        # まずべき乗則フィット
        power_law_result = self.fitter.fit_power_law(self.t, self.y_ideal)
        self.assertTrue(power_law_result.success)
        
        # 次に対数周期フィット
        result = self.fitter.fit_logarithm_periodic(self.t, self.y_ideal, power_law_result.parameters)
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.95)

    def test_noisy_fitting(self):
        """ノイズを含むデータでのフィッティングテスト"""
        # べき乗則フィット
        power_law_result = self.fitter.fit_power_law(self.t, self.y_noisy)
        self.assertTrue(power_law_result.success)
        
        # 対数周期フィット
        result = self.fitter.fit_logarithm_periodic(self.t, self.y_noisy, power_law_result.parameters)
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.90)  # ノイズがあるので閾値を下げる

    def test_fit_integration(self):
        """統合フィッティングのテスト"""
        result = self.fitter.fit(self.t, self.y_ideal)
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.95)