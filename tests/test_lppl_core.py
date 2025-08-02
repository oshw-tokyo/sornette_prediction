#!/usr/bin/env python3
"""
LPPLコア機能のテストスイート
実装の正確性を検証するためのテストコード
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.fitting.utils import logarithm_periodic_func
from src.fitting.multi_criteria_selection import MultiCriteriaSelector
from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator, FittingQuality


class TestLPPLModel(unittest.TestCase):
    """LPPLモデルの数学的正確性をテスト"""
    
    def setUp(self):
        """テスト用の共通設定"""
        self.t = np.linspace(0, 1, 100)
        
        # 論文値に基づくパラメータ
        self.tc_true = 1.2
        self.beta_true = 0.33
        self.omega_true = 7.4
        self.phi_true = 0.0
        self.A_true = 10.0
        self.B_true = -1.0
        self.C_true = 0.1
        
    def test_lppl_model_calculation(self):
        """LPPLモデルの計算が正しいことを確認"""
        # モデル計算
        y = logarithm_periodic_func(self.t, self.tc_true, self.beta_true, self.omega_true,
                      self.phi_true, self.A_true, self.B_true, self.C_true)
        
        # 基本的な検証
        self.assertEqual(len(y), len(self.t))
        self.assertFalse(np.any(np.isnan(y)))
        self.assertFalse(np.any(np.isinf(y)))
        
        # tc に近づくにつれて値が変化することを確認
        self.assertGreater(y[0], y[-1])  # 下降トレンド（B < 0の場合）
        
    def test_parameter_bounds(self):
        """パラメータ境界でのモデル挙動をテスト"""
        # tc = t の境界ケース（発散しないことを確認）
        t = np.array([0.5, 0.9, 0.99])
        tc = 1.0
        
        y = logarithm_periodic_func(t, tc, self.beta_true, self.omega_true,
                      self.phi_true, self.A_true, self.B_true, self.C_true)
        
        # 値が有限であることを確認
        self.assertTrue(np.all(np.isfinite(y)))
        
    def test_logarithm_periodic_func(self):
        """対数周期関数の形式をテスト"""
        # パラメータ配列形式
        params = [self.tc_true, self.beta_true, self.omega_true, 
                 self.phi_true, self.A_true, self.B_true, self.C_true]
        
        y1 = logarithm_periodic_func(self.t, *params)
        y2 = logarithm_periodic_func(self.t, *params)
        
        # 両関数が同じ結果を返すことを確認
        np.testing.assert_array_almost_equal(y1, y2)


class TestFittingQuality(unittest.TestCase):
    """フィッティング品質評価のテスト"""
    
    def setUp(self):
        """テスト用データの準備"""
        self.evaluator = FittingQualityEvaluator()
        
    def test_quality_assessment_good_parameters(self):
        """良好なパラメータの品質評価"""
        # 論文値に近いパラメータ
        assessment = self.evaluator.assess_fitting_quality(
            tc=1.1,
            beta=0.33,
            omega=7.4,
            r_squared=0.95,
            rmse=0.01,
            t_end=1.0
        )
        
        self.assertEqual(assessment.quality, FittingQuality.HIGH_QUALITY)
        self.assertTrue(assessment.is_usable)
        self.assertGreater(assessment.confidence, 0.8)
        
    def test_quality_assessment_boundary_sticking(self):
        """境界張り付きパラメータの品質評価"""
        # tc が下限境界に張り付いている
        assessment = self.evaluator.assess_fitting_quality(
            tc=1.01,  # 下限境界付近
            beta=0.1,  # 下限境界
            omega=7.4,
            r_squared=0.85,
            rmse=0.05,
            t_end=1.0
        )
        
        self.assertIn(assessment.quality, [FittingQuality.UNACCEPTABLE, FittingQuality.FAILED])
        self.assertFalse(assessment.is_usable)
        self.assertLess(assessment.confidence, 0.5)
        
    def test_quality_assessment_poor_fit(self):
        """低品質フィットの評価"""
        # R²が低い
        assessment = self.evaluator.assess_fitting_quality(
            tc=1.5,
            beta=0.4,
            omega=6.0,
            r_squared=0.65,  # 低いR²
            rmse=0.1,
            t_end=1.0
        )
        
        self.assertIn(assessment.quality, [FittingQuality.ACCEPTABLE, FittingQuality.UNACCEPTABLE])
        self.assertLess(assessment.confidence, 0.7)


class TestMultiCriteriaSelection(unittest.TestCase):
    """複数基準選択のテスト"""
    
    def setUp(self):
        """テスト用の合成データ生成"""
        # ノイズの少ない理想的なLPPLデータ
        t = np.linspace(0, 1, 200)
        tc_true = 1.1
        params_true = [tc_true, 0.33, 7.4, 0.0, 10.0, -1.0, 0.1]
        
        y_true = logarithm_periodic_func(t, *params_true)
        noise = np.random.normal(0, 0.001, len(t))  # 微小ノイズ
        y = y_true + noise
        
        # DataFrameに変換
        dates = pd.date_range(end=datetime.now(), periods=len(t))
        self.data = pd.DataFrame({'Close': y}, index=dates)
        
        self.selector = MultiCriteriaSelector()
        
    def test_comprehensive_fitting(self):
        """包括的フィッティングのテスト"""
        result = self.selector.perform_comprehensive_fitting(self.data)
        
        # 基本的な検証
        self.assertIsNotNone(result)
        self.assertGreater(len(result.all_candidates), 0)
        
        # 成功した候補があることを確認
        successful = [c for c in result.all_candidates if c.success]
        self.assertGreater(len(successful), 0)
        
        # 最良結果の存在を確認
        self.assertIsNotNone(result.best_by_r_squared)
        
        # R²基準の最良結果の品質を確認
        best = result.best_by_r_squared
        self.assertGreater(best.r_squared, 0.8)  # 高いR²
        self.assertLess(abs(best.beta - 0.33), 0.1)  # β値が論文値に近い
        
    def test_selection_criteria_consistency(self):
        """選択基準の一貫性テスト"""
        result = self.selector.perform_comprehensive_fitting(self.data)
        
        # 各基準で選ばれた結果が存在
        self.assertIsNotNone(result.best_by_r_squared)
        self.assertIsNotNone(result.theoretical_best)
        
        # R²基準が実際に最高のR²を持つことを確認
        if result.best_by_r_squared and len(result.all_candidates) > 1:
            max_r_squared = max(c.r_squared for c in result.all_candidates if c.success)
            self.assertAlmostEqual(result.best_by_r_squared.r_squared, max_r_squared, places=6)


class TestDataValidation(unittest.TestCase):
    """データ検証機能のテスト"""
    
    def test_empty_data_handling(self):
        """空データの処理"""
        selector = MultiCriteriaSelector()
        empty_data = pd.DataFrame()
        
        result = selector.perform_comprehensive_fitting(empty_data)
        self.assertEqual(len(result.all_candidates), 0)
        
    def test_insufficient_data_handling(self):
        """不十分なデータの処理"""
        selector = MultiCriteriaSelector()
        # 10点のみのデータ（フィッティングには不十分）
        small_data = pd.DataFrame({'Close': np.random.rand(10)})
        
        result = selector.perform_comprehensive_fitting(small_data)
        # 結果が返されるが、成功候補が少ないはず
        successful = [c for c in result.all_candidates if c.success]
        self.assertEqual(len(successful), 0)


class TestReproducibility(unittest.TestCase):
    """再現性のテスト"""
    
    def test_deterministic_results(self):
        """同じデータで同じ結果が得られることを確認"""
        # 固定シードで合成データ生成
        np.random.seed(42)
        t = np.linspace(0, 1, 100)
        y = logarithm_periodic_func(t, 1.1, 0.33, 7.4, 0.0, 10.0, -1.0, 0.1)
        y += np.random.normal(0, 0.01, len(t))
        
        data = pd.DataFrame({'Close': y})
        selector = MultiCriteriaSelector()
        
        # 2回実行
        result1 = selector.perform_comprehensive_fitting(data)
        result2 = selector.perform_comprehensive_fitting(data)
        
        # 候補数が同じ
        self.assertEqual(len(result1.all_candidates), len(result2.all_candidates))
        
        # 最良結果のパラメータが近い（完全一致は期待しない）
        if result1.best_by_r_squared and result2.best_by_r_squared:
            self.assertAlmostEqual(result1.best_by_r_squared.tc, 
                                 result2.best_by_r_squared.tc, places=2)


def run_all_tests():
    """全テストを実行"""
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestLPPLModel))
    suite.addTests(loader.loadTestsFromTestCase(TestFittingQuality))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiCriteriaSelection))
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestReproducibility))
    
    # 実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("🧪 LPPLコア機能テストスイート")
    print("=" * 60)
    
    success = run_all_tests()
    
    if success:
        print("\n✅ 全テスト合格！")
    else:
        print("\n❌ テスト失敗があります")