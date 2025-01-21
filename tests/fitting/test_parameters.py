import unittest
from src.fitting.parameters import FittingParameters

class TestFittingParameters(unittest.TestCase):
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