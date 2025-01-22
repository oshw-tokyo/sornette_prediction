import unittest
from src.config.validation_settings import get_validation_settings

class TestValidationSettings(unittest.TestCase):
    def test_default_settings(self):
        """デフォルト設定の取得テスト"""
        settings = get_validation_settings('non_existent_crash')
        self.assertEqual(settings['validation_cutoff_days'], 30)
        self.assertEqual(settings['minimum_data_points'], 100)
        self.assertEqual(settings['maximum_data_points'], 1000)
    
    def test_specific_crash_settings(self):
        """特定のクラッシュケースの設定テスト"""
        settings = get_validation_settings('crash_1987')
        self.assertEqual(settings['validation_cutoff_days'], 30)
        self.assertEqual(settings['minimum_data_points'], 200)