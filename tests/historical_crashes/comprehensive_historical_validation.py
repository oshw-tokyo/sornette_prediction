#!/usr/bin/env python3
"""
包括的歴史的クラッシュ検証システム

目的: 複数の歴史的クラッシュを体系的に検証し、LPPLモデルの汎用性を評価
"""

import sys
import os
from datetime import datetime
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from tests.historical_crashes.base_crash_validator import ReproducibleTestCase
from tests.historical_crashes.black_monday_1987_validator import run_black_monday_reproduction_test
from tests.historical_crashes.dotcom_bubble_2000_validator import run_dotcom_bubble_test

class ComprehensiveHistoricalValidator:
    """包括的歴史的検証システム"""
    
    def __init__(self):
        self.test_cases = {}
        self.validation_results = {}
        self.setup_test_cases()
    
    def setup_test_cases(self):
        """再現可能なテストケースの設定"""
        
        # 1987年ブラックマンデー（実証済み基準）
        self.test_cases['black_monday_1987'] = ReproducibleTestCase(
            test_name="1987年ブラックマンデー再現検証",
            test_function=run_black_monday_reproduction_test,
            expected_score_range=(90, 100)  # 実証済みなので高いスコアを期待
        )
        
        # 2000年ドットコムバブル（新規検証）
        self.test_cases['dotcom_bubble_2000'] = ReproducibleTestCase(
            test_name="2000年ドットコムバブル崩壊検証",
            test_function=run_dotcom_bubble_test,
            expected_score_range=(60, 100)  # 技術株特有の高ボラティリティを期待
        )
    
    def run_all_validations(self):
        """全ての歴史的検証を実行"""
        print("🎯 包括的歴史的クラッシュ検証システム開始\n")
        print("=" * 60)
        
        results_summary = {
            'execution_timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_cases),
            'successful_tests': 0,
            'failed_tests': 0,
            'test_results': {}
        }
        
        for test_id, test_case in self.test_cases.items():
            print(f"\n{'='*60}")
            print(f"🧪 実行中: {test_case.test_name}")
            print(f"{'='*60}")
            
            try:
                success = test_case.run_test()
                result = test_case.get_last_result()
                
                if success and result:
                    results_summary['successful_tests'] += 1
                    results_summary['test_results'][test_id] = {
                        'status': 'success',
                        'prediction_score': result.get('prediction_score', 0),
                        'adjusted_score': result.get('adjusted_prediction_score', result.get('prediction_score', 0)),
                        'crash_date': result.get('crash_date'),
                        'data_points': result.get('data_points', 0),
                        'validation_type': result.get('validation_type', test_id)
                    }
                else:
                    results_summary['failed_tests'] += 1
                    results_summary['test_results'][test_id] = {
                        'status': 'failed',
                        'error': 'Test execution failed or returned invalid result'
                    }
                
                # 結果保存
                self.validation_results[test_id] = result
                
            except Exception as e:
                print(f"❌ テスト実行エラー: {e}")
                results_summary['failed_tests'] += 1
                results_summary['test_results'][test_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # 総合分析の実行
        self.analyze_comprehensive_results(results_summary)
        
        # 結果の保存
        self.save_results(results_summary)
        
        return results_summary
    
    def analyze_comprehensive_results(self, results_summary):
        """包括的結果の分析"""
        print(f"\n{'='*60}")
        print("📊 包括的歴史的検証 総合分析")
        print(f"{'='*60}")
        
        total_tests = results_summary['total_tests']
        successful_tests = results_summary['successful_tests']
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 実行サマリー:")
        print(f"   総テスト数: {total_tests}")
        print(f"   成功テスト: {successful_tests}")
        print(f"   失敗テスト: {results_summary['failed_tests']}")
        print(f"   成功率: {success_rate:.1f}%")
        
        # 成功したテストの詳細分析
        successful_results = [
            result for result in results_summary['test_results'].values()
            if result['status'] == 'success'
        ]
        
        if successful_results:
            print(f"\n📈 成功テスト詳細分析:")
            
            scores = [r['prediction_score'] for r in successful_results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            print(f"   平均予測スコア: {avg_score:.1f}/100")
            print(f"   最高スコア: {max_score}/100")
            print(f"   最低スコア: {min_score}/100")
            
            # 個別結果の詳細
            print(f"\n📋 個別テスト結果:")
            for test_id, result in results_summary['test_results'].items():
                if result['status'] == 'success':
                    score = result['prediction_score']
                    adjusted = result.get('adjusted_score', score)
                    points = result.get('data_points', 'N/A')
                    
                    print(f"   {test_id}:")
                    print(f"     予測スコア: {score}/100")
                    if adjusted != score:
                        print(f"     調整後スコア: {adjusted}/100")
                    print(f"     データ点数: {points}日")
                    print(f"     評価: {'✅ 優秀' if score >= 80 else '⚠️ 良好' if score >= 60 else '🔶 要改善'}")
        
        # LPPLモデル汎用性の評価
        print(f"\n🔬 LPPLモデル汎用性評価:")
        
        if success_rate >= 80:
            print("✅ 優秀: LPPLモデルは複数の歴史的クラッシュで高い予測能力を実証")
            print("✅ 科学的価値: 理論の汎用性と実用性を確認")
            print("✅ 実用価値: 様々な市場状況での予測システム構築が可能")
        elif success_rate >= 60:
            print("⚠️ 良好: LPPLモデルは概ね有効だが改善の余地あり")
            print("🔬 研究価値: 特定の市場条件での予測精度向上が課題")
        else:
            print("🔶 要改善: LPPLモデルの汎用性に課題あり")
            print("🛠️ 改善必要: モデル精度向上のための手法改良が急務")
        
        # 今後の展開提案
        print(f"\n🚀 今後の展開提案:")
        
        if success_rate >= 80:
            print("1. リアルタイム監視システムの開発")
            print("2. 商用予測サービスの構築")
            print("3. 金融機関との連携強化")
            print("4. 国際市場への展開")
        else:
            print("1. 失敗テストケースの詳細分析")
            print("2. モデル精度向上手法の研究")
            print("3. データ前処理手法の改良")
            print("4. 追加の検証データセット収集")
    
    def save_results(self, results_summary):
        """結果の保存"""
        # JSON形式での詳細結果保存
        results_dir = 'analysis_results/historical_validation'
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 詳細結果JSON
        json_file = f"{results_dir}/comprehensive_validation_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results_summary, f, indent=2, ensure_ascii=False, default=str)
        
        # レポート形式のマークダウン
        report_file = f"{results_dir}/validation_report_{timestamp}.md"
        self.generate_markdown_report(results_summary, report_file)
        
        print(f"\n📄 結果保存:")
        print(f"   詳細JSON: {json_file}")
        print(f"   レポート: {report_file}")
    
    def generate_markdown_report(self, results_summary, report_file):
        """マークダウンレポートの生成"""
        
        total_tests = results_summary['total_tests']
        successful_tests = results_summary['successful_tests']
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        successful_results = [
            result for result in results_summary['test_results'].values()
            if result['status'] == 'success'
        ]
        
        avg_score = 0
        if successful_results:
            scores = [r['prediction_score'] for r in successful_results]
            avg_score = sum(scores) / len(scores)
        
        report_content = f"""# 包括的歴史的クラッシュ検証レポート

## 実行概要

- **実行日時**: {results_summary['execution_timestamp']}
- **総テスト数**: {total_tests}
- **成功テスト**: {successful_tests}
- **成功率**: {success_rate:.1f}%
- **平均予測スコア**: {avg_score:.1f}/100

## 検証結果詳細

"""
        
        for test_id, result in results_summary['test_results'].items():
            if result['status'] == 'success':
                score = result['prediction_score']
                status_icon = '✅' if score >= 80 else '⚠️' if score >= 60 else '🔶'
                
                report_content += f"""### {test_id.replace('_', ' ').title()}

- **予測スコア**: {score}/100 {status_icon}
- **データ点数**: {result.get('data_points', 'N/A')}日
- **クラッシュ日**: {result.get('crash_date', 'N/A')}
- **検証タイプ**: {result.get('validation_type', 'N/A')}

"""
            else:
                report_content += f"""### {test_id.replace('_', ' ').title()}

- **ステータス**: ❌ 失敗
- **エラー**: {result.get('error', 'Unknown error')}

"""
        
        # 総合評価
        if success_rate >= 80:
            overall_status = "✅ 優秀"
            evaluation = "LPPLモデルは複数の歴史的クラッシュで高い予測能力を実証"
        elif success_rate >= 60:
            overall_status = "⚠️ 良好" 
            evaluation = "LPPLモデルは概ね有効だが改善の余地あり"
        else:
            overall_status = "🔶 要改善"
            evaluation = "LPPLモデルの汎用性に課題あり"
        
        report_content += f"""
## 総合評価

**{overall_status}**: {evaluation}

## 科学的・実用的意義

- **理論検証**: 複数の歴史的イベントでの理論適用性評価
- **汎用性確認**: 異なる市場条件でのモデル有効性検証  
- **実用価値**: 将来の予測システム構築への指針提供

---

*Generated by Claude Code - Comprehensive Historical Validation System*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

def main():
    """メイン実行関数"""
    validator = ComprehensiveHistoricalValidator()
    results = validator.run_all_validations()
    
    print(f"\n🏆 包括的歴史的検証完了")
    print(f"成功率: {(results['successful_tests']/results['total_tests'])*100:.1f}%")
    
    return results

if __name__ == "__main__":
    main()