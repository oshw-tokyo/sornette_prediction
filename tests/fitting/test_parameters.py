import unittest
from src.fitting.parameters import FittingParameterManager, ParameterSet  # FittingParametersからFittingParameterManagerに変更

class TestParameters(unittest.TestCase):
    def setUp(self):
        self.param_manager = FittingParameterManager()
        
        # 有効なパラメータ
        is_valid, msg = self.params.validate_parameters(z=0.5, omega=6.0)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)
        
        # 無効なzパラメータ
        is_valid, msg = self.params.validate_parameters(z=1.5, omega=6.0)
        self.assertFalse(is_valid)
        self.assertIn("outside theoretical range", msg)
        
        # 無効なomegaパラメータ
        is_valid, msg = self.params.validate_parameters(z=0.5, omega=4.0)
        self.assertFalse(is_valid)
        self.assertIn("outside typical range", msg)