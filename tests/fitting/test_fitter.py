import unittest
import numpy as np
from src.fitting.fitter import LogPeriodicFitter, FittingResult

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
        
        # ノイズ付きデータ
        np.random.seed(42)
        self.noise = np.random.normal(0, 1, len(self.t))
        self.y_noisy = self.y_ideal + self.noise

    def test_ideal_fitting(self):
        """理想的なデータでのフィッティングテスト"""
        result = self.fitter.fit_log_periodic(self.t, self.y_ideal)
        
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.99)
        self.assertAlmostEqual(result.parameters['tc'], self.tc, delta=1)
        self.assertAlmostEqual(result.parameters['m'], self.m, delta=0.1)
        self.assertAlmostEqual(result.parameters['omega'], self.omega, delta=0.1)

    def test_noisy_fitting(self):
        """ノイズを含むデータでのフィッティングテスト"""
        result = self.fitter.fit_log_periodic(self.t, self.y_noisy)
        
        self.assertTrue(result.success)
        self.assertGreater(result.r_squared, 0.8)
        self.assertTrue(0 < result.parameters['m'] < 1)
        self.assertTrue(5 <= result.parameters['omega'] <= 8)

    def test_multiple_initializations(self):
        """複数の初期値でのフィッティングテスト"""
        result = self.fitter.fit_with_multiple_initializations(
            self.t, self.y_noisy, n_tries=5
        )
        
        self.assertTrue(result.success)
        single_result = self.fitter.fit_log_periodic(self.t, self.y_noisy)
        self.assertGreaterEqual(result.r_squared, single_result.r_squared)