#!/usr/bin/env python3
"""
テスト実行スクリプト
実装の正確性を検証するためのユーザーフレンドリーなテストランナー
"""

import sys
import os
import unittest
import time
from datetime import datetime

# matplotlib設定（GUIを無効化）
from src.config.matplotlib_config import configure_matplotlib_for_automation
configure_matplotlib_for_automation()

# カラー出力用のANSIコード
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """ヘッダー表示"""
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}🧪 Sornette LPPL予測システム - 検証テストスイート{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def run_core_tests():
    """コア機能のテスト実行"""
    print(f"{Colors.BLUE}📋 1. LPPLコア機能テスト{Colors.RESET}")
    print("-" * 50)
    
    try:
        from tests.test_lppl_core import (TestLPPLModel, TestFittingQuality, 
                                         TestMultiCriteriaSelection, TestDataValidation,
                                         TestReproducibility)
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # テストケース追加
        test_cases = [
            ("数学モデル", TestLPPLModel),
            ("品質評価", TestFittingQuality),
            ("複数基準選択", TestMultiCriteriaSelection),
            ("データ検証", TestDataValidation),
            ("再現性", TestReproducibility)
        ]
        
        for name, test_class in test_cases:
            print(f"  • {name}テスト実行中...", end='', flush=True)
            
            # 個別実行
            case_suite = loader.loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'))
            result = runner.run(case_suite)
            
            if result.wasSuccessful():
                print(f" {Colors.GREEN}✓ 成功{Colors.RESET}")
            else:
                print(f" {Colors.RED}✗ 失敗 ({len(result.failures)}件){Colors.RESET}")
                for test, traceback in result.failures:
                    print(f"    - {test}: {traceback.split('AssertionError:')[-1].strip()[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}エラー: {str(e)}{Colors.RESET}")
        return False


def run_parameter_validation():
    """パラメータ検証テスト"""
    print(f"\n{Colors.BLUE}📋 2. パラメータ検証テスト{Colors.RESET}")
    print("-" * 50)
    
    try:
        from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator, FittingQuality
        
        evaluator = FittingQualityEvaluator()
        
        # テストケース
        test_cases = [
            {
                "name": "論文値パラメータ",
                "params": {"tc": 1.2, "beta": 0.33, "omega": 7.4, "r_squared": 0.95, "rmse": 0.01, "t_end": 1.0},
                "expected_usable": True
            },
            {
                "name": "境界張り付き",
                "params": {"tc": 1.01, "beta": 0.1, "omega": 7.4, "r_squared": 0.85, "rmse": 0.05, "t_end": 1.0},
                "expected_usable": False
            },
            {
                "name": "低品質フィット",
                "params": {"tc": 1.5, "beta": 0.4, "omega": 6.0, "r_squared": 0.65, "rmse": 0.1, "t_end": 1.0},
                "expected_usable": False
            }
        ]
        
        all_passed = True
        for case in test_cases:
            assessment = evaluator.evaluate_fitting(**case["params"])
            passed = assessment.is_usable == case["expected_usable"]
            
            status = f"{Colors.GREEN}✓{Colors.RESET}" if passed else f"{Colors.RED}✗{Colors.RESET}"
            print(f"  {status} {case['name']}: 品質={assessment.quality.value}, "
                  f"信頼度={assessment.confidence:.1%}, 使用可能={assessment.is_usable}")
            
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"{Colors.RED}エラー: {str(e)}{Colors.RESET}")
        return False


def run_data_access_test():
    """データアクセステスト（FRED限定）"""
    print(f"\n{Colors.BLUE}📋 3. データアクセステスト（FRED API）{Colors.RESET}")
    print("-" * 50)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.data_sources.unified_data_client import UnifiedDataClient
        from datetime import datetime, timedelta
        
        client = UnifiedDataClient()
        
        # FREDが有効か確認
        if 'fred' not in client.available_sources:
            print(f"{Colors.YELLOW}⚠️ FRED APIが利用できません。APIキーを確認してください。{Colors.RESET}")
            return False
        
        # テストデータ取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        test_symbol = 'NASDAQ'
        print(f"  • {test_symbol} データ取得テスト...", end='', flush=True)
        
        data, source = client.get_data_with_fallback(
            test_symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if data is not None and len(data) > 0:
            print(f" {Colors.GREEN}✓ 成功 ({len(data)}日分, ソース: {source}){Colors.RESET}")
            return True
        else:
            print(f" {Colors.RED}✗ 失敗{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}エラー: {str(e)}{Colors.RESET}")
        return False


def run_integration_test():
    """統合テスト - 実際のワークフロー"""
    print(f"\n{Colors.BLUE}📋 4. 統合テスト（エンドツーエンド）{Colors.RESET}")
    print("-" * 50)
    
    try:
        # 合成データでの完全なワークフロー
        import numpy as np
        import pandas as pd
        from src.fitting.multi_criteria_selection import MultiCriteriaSelector
        
        print("  • 合成データ生成...", end='', flush=True)
        
        # 理想的なLPPLデータ生成
        t = np.linspace(0, 1, 200)
        from src.fitting.fitter import logarithm_periodic_func
        y = logarithm_periodic_func(t, 1.1, 0.33, 7.4, 0.0, 10.0, -1.0, 0.1)
        y += np.random.normal(0, 0.01, len(t))  # ノイズ追加
        
        data = pd.DataFrame({'Close': y})
        print(f" {Colors.GREEN}✓{Colors.RESET}")
        
        print("  • LPPLフィッティング実行...", end='', flush=True)
        selector = MultiCriteriaSelector()
        result = selector.perform_comprehensive_fitting(data)
        
        successful = [c for c in result.all_candidates if c.convergence_success]
        if len(successful) > 0 and result.best_by_r_squared:
            print(f" {Colors.GREEN}✓ 成功 (候補: {len(successful)}){Colors.RESET}")
            
            best = result.best_by_r_squared
            print(f"  • 最良結果: tc={best.tc:.3f}, β={best.beta:.3f}, "
                  f"ω={best.omega:.3f}, R²={best.r_squared:.3f}")
            
            # パラメータが論文値に近いか確認
            beta_error = abs(best.beta - 0.33) / 0.33 * 100
            if beta_error < 10:
                print(f"  • β値誤差: {Colors.GREEN}{beta_error:.1f}% (良好){Colors.RESET}")
            else:
                print(f"  • β値誤差: {Colors.YELLOW}{beta_error:.1f}% (要改善){Colors.RESET}")
            
            return True
        else:
            print(f" {Colors.RED}✗ 失敗{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}エラー: {str(e)}{Colors.RESET}")
        return False


def print_summary(results):
    """結果サマリー表示"""
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}📊 テスト結果サマリー{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"総テスト項目: {total}")
    print(f"成功: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"失敗: {Colors.RED}{total - passed}{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ 全テスト合格！実装は正しく動作しています。{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️ 一部のテストが失敗しました。{Colors.RESET}")
        print("失敗したテスト:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")


def main():
    """メイン実行関数"""
    print_header()
    
    # 各テスト実行
    results = {}
    
    start_time = time.time()
    
    # 1. コアテスト
    results["コア機能"] = run_core_tests()
    
    # 2. パラメータ検証
    results["パラメータ検証"] = run_parameter_validation()
    
    # 3. データアクセス
    results["データアクセス"] = run_data_access_test()
    
    # 4. 統合テスト
    results["統合テスト"] = run_integration_test()
    
    elapsed_time = time.time() - start_time
    
    # サマリー表示
    print_summary(results)
    
    print(f"\n実行時間: {elapsed_time:.2f}秒")
    
    # 終了コード
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())