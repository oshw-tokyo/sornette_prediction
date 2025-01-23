import unittest
from datetime import datetime, timedelta

from src.reproducibility_validation.historical_crashes import (
    CrashCase, CrashPeriod, CrashParameters, CrashMetrics,
    get_crash_case, list_available_crashes
)

class TestHistoricalCrashes(unittest.TestCase):
    """Historical Crashes モジュールのテスト"""
    
    def test_crash_case_retrieval(self):
        """クラッシュケースの取得テスト"""
        # 1987年のクラッシュケースを取得
        crash_case = get_crash_case('1987-10')
        
        # 基本的な属性の検証
        self.assertEqual(crash_case.id, '1987-10')
        self.assertEqual(crash_case.symbol, '^GSPC')
        self.assertEqual(crash_case.period.crash_date, 
                        datetime(1987, 10, 19))
        
        # パラメータの検証
        self.assertAlmostEqual(crash_case.parameters.m, 0.33, places=2)
        self.assertAlmostEqual(crash_case.parameters.omega, 7.4, places=1)
        
        # メトリクスの検証
        self.assertAlmostEqual(crash_case.metrics.price_drop_percentage, 
                             22.6, places=1)
    
    def test_invalid_crash_id(self):
        """無効なクラッシュIDの処理テスト"""
        with self.assertRaises(KeyError):
            get_crash_case('invalid-id')
    
    def test_list_available_crashes(self):
        """利用可能なクラッシュ一覧のテスト"""
        crashes = list_available_crashes()
        
        # 基本的な検証
        self.assertIsInstance(crashes, list)
        self.assertTrue(len(crashes) > 0)
        
        # 1987年のクラッシュが含まれているか確認
        crash_1987 = next(
            (crash for crash in crashes if crash['id'] == '1987-10'),
            None
        )
        self.assertIsNotNone(crash_1987)
        self.assertEqual(crash_1987['market'], '^GSPC')
    
    def test_crash_period_validation(self):
        crash_case = get_crash_case('1987-10')
        
        self.assertLess(
            crash_case.period.start_date,
            crash_case.period.crash_date,
            "start_date should be before crash_date"
        )
        
        calculated_end_date = crash_case.period.end_date
        expected_end_date = (crash_case.period.crash_date - 
                            timedelta(days=crash_case.period.validation_cutoff_days))
        
        self.assertEqual(
            calculated_end_date,
            expected_end_date,
            "end_date should be validation_cutoff_days before crash_date"
        )

    def test_crash_parameters_validation(self):
        """クラッシュパラメータの妥当性検証"""
        crash_case = get_crash_case('1987-10')
        
        # パラメータの範囲を検証
        self.assertTrue(0 < crash_case.parameters.m < 1)
        self.assertTrue(5 <= crash_case.parameters.omega <= 8)
        
        # 許容誤差の妥当性を検証
        self.assertTrue(0 < crash_case.parameters.tolerance_m < 0.1)
        self.assertTrue(0 < crash_case.parameters.tolerance_omega < 0.5)
    
    def test_crash_metrics_validation(self):
        """クラッシュメトリクスの妥当性検証"""
        crash_case = get_crash_case('1987-10')
        
        # メトリクスの範囲を検証
        self.assertTrue(0 < crash_case.metrics.price_drop_percentage < 100)
        self.assertTrue(crash_case.metrics.duration_days > 0)
        self.assertTrue(
            crash_case.metrics.post_crash_bottom <
            crash_case.metrics.pre_crash_peak
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)