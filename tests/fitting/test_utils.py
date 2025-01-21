import unittest
import numpy as np
from src.fitting.utils import calculate_residuals, calculate_r_squared

class TestFittingUtils(unittest.TestCase):
    def setUp(self):
        """テストデータの準備"""
        self.y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        self.y_pred = np.array([1.1, 2.1, 2.9, 4.0, 5.1])

    def test_calculate_residuals(self):
        """残差計算のテスト"""
        residuals = calculate_residuals(self.y_true, self.y_pred)
        self.assertIsInstance(residuals, float)
        self.assertGreaterEqual(residuals, 0)

    def test_calculate_r_squared(self):
        """決定係数計算のテスト"""
        r2 = calculate_r_squared(self.y_true, self.y_pred)
        self.assertIsInstance(r2, float)
        self.assertLessEqual(r2, 1.0)
        self.assertGreaterEqual(r2, 0.0)