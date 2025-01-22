import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy import stats

from src.reproducibility_validation.crash_validator import CrashValidator
from src.reproducibility_validation.crash_1987_validator import Crash1987Validator
from src.reproducibility_validation.historical_crashes import (
    CrashCase, CrashPeriod, CrashParameters, CrashMetrics,
    get_crash_case
)

class TestCrashValidator(unittest.TestCase):
    """クラッシュ検証システムの基本テスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.validator = CrashValidator()
        self.crash_case = get_crash_case('1987-10')
    
    def test_data_preparation(self):
        """データ前処理のテスト"""
        # テストデータの生成
        prices = np.exp(np.linspace(0, 1, 100))  # 指数関数的な上昇
        
        # 前処理の実行
        t, log_prices = self.validator.fitter.prepare_data(prices)
        
        # 基本的な検証
        self.assertIsNotNone(t)
        self.assertIsNotNone(log_prices)
        self.assertEqual(len(t), len(log_prices))
        
        # 正規化の検証
        self.assertAlmostEqual(log_prices[0], 0.0, places=10)
        
        # 時間軸の検証
        self.assertEqual(t[0], 0.0)
        self.assertEqual(t[-1], 1.0)
    
    def test_power_law_fitting(self):
        """べき乗則フィッティングのテスト"""
        # テストデータの生成
        t = np.linspace(0, 1, 100)
        tc = 1.1
        m = 0.33  # 論文の値を使用
        A = 1.0
        B = -0.5
        
        # べき乗則に従うデータを生成（ノイズ付き）
        prices = A + B * np.power(tc - t, m)
        prices += np.random.normal(0, 0.01, len(t))
        
        # フィッティングの実行
        result = self.validator.fitter.fit_power_law(t, prices)
        
        # 結果の検証
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.parameters['m'], m, delta=0.05)
        self.assertAlmostEqual(result.parameters['tc'], tc, delta=0.1)
        self.assertTrue(result.r_squared > 0.95)
    
    def test_log_periodic_fitting(self):
        """対数周期フィッティングのテスト"""
        # テストデータの生成
        t = np.linspace(0, 1, 200)
        tc = 1.1
        m = 0.33
        omega = 7.4  # 論文の値を使用
        phi = 2.0
        A = 1.0
        B = -0.5
        C = 0.1
        
        # 対数周期関数に従うデータを生成（ノイズ付き）
        dt = tc - t
        prices = A + B * np.power(dt, m) * (1 + C * np.cos(omega * np.log(dt) + phi))
        prices += np.random.normal(0, 0.01, len(t))
        
        # べき乗則フィットを実行
        power_result = self.validator.fitter.fit_power_law(t, prices)
        self.assertTrue(power_result.success)
        
        # 対数周期フィットを実行
        result = self.validator.fitter.fit_log_periodic(t, prices, power_result.parameters)
        
        # 結果の検証
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.parameters['m'], m, delta=0.05)
        self.assertAlmostEqual(result.parameters['omega'], omega, delta=0.3)
        self.assertTrue(result.r_squared > 0.95)

    def test_statistical_tests(self):
        """統計的検定のテスト"""
        # テストデータの生成
        n = 1000
        y_true = np.random.normal(0, 1, n)
        y_pred = y_true + np.random.normal(0, 0.1, n)
        
        # 基本的な検定結果
        base_tests = {
            'f_test': {'statistic': 1000.0, 'p_value': 0.0},
            'normality_test': {'statistic': 2.0, 'p_value': 0.3},
            'durbin_watson': 2.0
        }
        
        # 統計的検定の実行
        result = self.validator._perform_statistical_tests(y_true, y_pred, base_tests)
        
        # 結果の検証
        self.assertIn('ks_test', result)
        self.assertIn('runs_test', result)
        self.assertTrue(result['ks_test']['p_value'] > 0.05)  # 正規性の確認
    
def test_validation_metrics(self):
    """検証指標の計算テスト"""
    from src.fitting.fitter import FittingResult  # FittingResultを直接インポート
    
    # テストデータの生成
    result = FittingResult(  # self.validator.fitter.FittingResult ではなく直接 FittingResult を使用
        success=True,
        parameters={
            'm': 0.33,
            'omega': 7.4,
            'tc': 1.1
        },
        residuals=0.01,
        r_squared=0.98,
        statistical_significance={}
    )


class Test1987CrashValidator(unittest.TestCase):
    """1987年クラッシュ特化型テスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.validator = Crash1987Validator()
    
    def test_1987_specific_validation(self):
        """1987年特有の検証機能のテスト"""
        # 1987年のクラッシュケースを取得
        crash_case = get_crash_case('1987-10')
        
        # 検証の実行
        result = self.validator.validate()
        
        # 基本的な検証
        self.assertIsNotNone(result)
        self.assertIn('parameters', result.__dict__)
        self.assertIn('statistical_tests', result.__dict__)
        
        # 1987年特有のパラメータ検証
        if result.success:
            self.assertAlmostEqual(
                result.parameters.get('m', 0),
                crash_case.parameters.m,
                delta=self.validator.specific_tolerances['m']
            )
            self.assertAlmostEqual(
                result.parameters.get('omega', 0),
                crash_case.parameters.omega,
                delta=self.validator.specific_tolerances['omega']
            )

if __name__ == '__main__':
    unittest.main(verbosity=2)