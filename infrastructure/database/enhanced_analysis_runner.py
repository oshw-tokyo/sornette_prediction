#!/usr/bin/env python3
"""
強化された分析実行器
- フィッティング失敗追跡システム統合
- データ取得失敗とフィッティング失敗の詳細記録
- 重複排除システム統合
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import json
import traceback

# プロジェクトルートのパスを追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.fitting_failure_tracker import FittingFailureTracker
from infrastructure.database.failure_metadata_generator import FailureMetadataGenerator

class EnhancedAnalysisRunner:
    """強化された分析実行器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.failure_tracker = FittingFailureTracker(db_path)
        self.metadata_generator = FailureMetadataGenerator()
    
    def run_symbol_analysis(self, symbol: str, analysis_basis_date: str,
                          schedule_name: str = None, backfill_batch_id: str = None,
                          force_retry: bool = False) -> Dict[str, Any]:
        """
        銘柄分析の実行（失敗追跡機能付き）
        
        Args:
            symbol: 銘柄シンボル
            analysis_basis_date: 分析基準日
            schedule_name: スケジュール名
            backfill_batch_id: バックフィルバッチID
            force_retry: 強制リトライ
            
        Returns:
            dict: 実行結果
        """
        
        # 1. 重複チェック
        if not force_retry:
            check_result = self.failure_tracker.check_analysis_needed(
                symbol, analysis_basis_date, schedule_name
            )
            
            if not check_result['needed']:
                return {
                    'status': 'skipped',
                    'reason': check_result['reason'],
                    'symbol': symbol,
                    'analysis_basis_date': analysis_basis_date
                }
        
        # 2. 解析開始記録
        status_id = self.failure_tracker.start_analysis(
            symbol, analysis_basis_date, schedule_name
        )
        
        print(f"🔄 {symbol} ({analysis_basis_date}) 解析開始")
        
        try:
            # 3. データ取得段階
            data_result = self._retrieve_market_data(symbol, analysis_basis_date)
            
            if not data_result['success']:
                # データ取得失敗
                self._record_data_retrieval_failure(
                    status_id, symbol, analysis_basis_date, data_result, 
                    schedule_name, backfill_batch_id
                )
                return {
                    'status': 'failed',
                    'stage': 'data_retrieval',
                    'reason': data_result['error'],
                    'symbol': symbol,
                    'analysis_basis_date': analysis_basis_date
                }
            
            # 4. データ取得成功記録
            data_info = data_result['data_info']
            self.failure_tracker.record_data_retrieval(
                status_id, data_info['source'], data_info['points'],
                data_info['start_date'], data_info['end_date']
            )
            
            # 5. データ処理段階
            processing_result = self._process_market_data(data_result['data'])
            
            if not processing_result['success']:
                # データ処理失敗
                self._record_data_processing_failure(
                    status_id, symbol, analysis_basis_date, processing_result, 
                    data_info, schedule_name, backfill_batch_id
                )
                return {
                    'status': 'failed',
                    'stage': 'data_processing',
                    'reason': processing_result['error'],
                    'symbol': symbol,
                    'analysis_basis_date': analysis_basis_date
                }
            
            # 6. LPPL フィッティング段階
            fitting_result = self._execute_lppl_fitting(
                processing_result['processed_data'], symbol, analysis_basis_date
            )
            
            if not fitting_result['success']:
                # フィッティング失敗
                self._record_fitting_failure(
                    status_id, symbol, analysis_basis_date, fitting_result,
                    data_info, schedule_name, backfill_batch_id
                )
                return {
                    'status': 'failed',
                    'stage': 'fitting_execution',
                    'reason': fitting_result['error'],
                    'symbol': symbol,
                    'analysis_basis_date': analysis_basis_date
                }
            
            # 7. 品質チェック段階
            quality_result = self._check_fitting_quality(fitting_result['fit_result'])
            
            if not quality_result['success']:
                # 品質チェック失敗
                self._record_quality_check_failure(
                    status_id, symbol, analysis_basis_date, quality_result,
                    data_info, schedule_name, backfill_batch_id
                )
                return {
                    'status': 'failed',
                    'stage': 'quality_check',
                    'reason': quality_result['error'],
                    'symbol': symbol,
                    'analysis_basis_date': analysis_basis_date
                }
            
            # 8. データベース保存
            result_id = self._save_analysis_result(
                fitting_result['fit_result'], data_info, schedule_name, backfill_batch_id
            )
            
            # 9. 成功記録
            self.failure_tracker.record_success(status_id, result_id)
            
            print(f"✅ {symbol} ({analysis_basis_date}) 解析成功")
            
            return {
                'status': 'success',
                'result_id': result_id,
                'symbol': symbol,
                'analysis_basis_date': analysis_basis_date,
                'quality_score': quality_result['quality_score']
            }
            
        except Exception as e:
            # 予期しないエラー
            error_details = {
                'exception_type': type(e).__name__,
                'exception_message': str(e),
                'traceback': traceback.format_exc()
            }
            
            self.failure_tracker.record_failure(
                status_id, symbol, analysis_basis_date, 'unknown',
                'unexpected_error', 'system_error', str(e),
                error_details, None, {}, schedule_name, backfill_batch_id
            )
            
            print(f"❌ {symbol} ({analysis_basis_date}) 予期しないエラー: {str(e)}")
            
            return {
                'status': 'failed',
                'stage': 'unexpected_error',
                'reason': str(e),
                'symbol': symbol,
                'analysis_basis_date': analysis_basis_date
            }
    
    def _retrieve_market_data(self, symbol: str, analysis_basis_date: str) -> Dict[str, Any]:
        """マーケットデータ取得（モックアップ）"""
        
        print(f"   📊 データ取得中: {symbol}")
        
        # 実際の実装では unified_data_client を使用
        try:
            # モックアップ: 実際のデータ取得ロジックをここに実装
            # from infrastructure.data_sources.unified_data_client import UnifiedDataClient
            # client = UnifiedDataClient()
            # data, source = client.get_data_with_fallback(symbol, start_date, end_date)
            
            # テスト用の成功ケース
            if symbol in ['TEST_SUCCESS', 'BTC', 'ETH']:
                return {
                    'success': True,
                    'data': {'mock': 'data'},  # 実際のDataFrameが入る
                    'data_info': {
                        'source': 'coingecko',
                        'points': 365,
                        'start_date': '2024-08-10',
                        'end_date': '2025-08-10'
                    }
                }
            
            # テスト用の失敗ケース  
            elif symbol == 'TEST_RATE_LIMIT':
                return {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'http_status': 429,
                    'api_provider': 'coingecko',
                    'request_details': {'symbol': symbol, 'period': '365 days'}
                }
            
            elif symbol == 'TEST_NOT_FOUND':
                return {
                    'success': False,
                    'error': 'Symbol not found',
                    'http_status': 404,
                    'api_provider': 'coingecko'
                }
            
            else:
                # デフォルト成功
                return {
                    'success': True,
                    'data': {'mock': 'data'},
                    'data_info': {
                        'source': 'mock',
                        'points': 200,
                        'start_date': '2024-08-10',
                        'end_date': '2025-08-10'
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'network_error': str(e)
            }
    
    def _process_market_data(self, data: Any) -> Dict[str, Any]:
        """マーケットデータ処理（モックアップ）"""
        
        print(f"   🔧 データ処理中")
        
        # 実際の実装では data validation, transformation等
        try:
            # テスト用: 常に成功
            return {
                'success': True,
                'processed_data': data  # 実際の処理済みデータが入る
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Data processing failed: {str(e)}',
                'processing_stage': 'validation',
                'data_shape': getattr(data, 'shape', None),
                'validation_errors': [str(e)]
            }
    
    def _execute_lppl_fitting(self, data: Any, symbol: str, 
                            analysis_basis_date: str) -> Dict[str, Any]:
        """LPPLフィッティング実行（モックアップ）"""
        
        print(f"   🎯 LPPLフィッティング実行")
        
        # 実際の実装では core.fitting.fitter を使用
        try:
            # テスト用の成功ケース
            if symbol in ['TEST_SUCCESS', 'BTC', 'ETH']:
                return {
                    'success': True,
                    'fit_result': {
                        'parameters': {
                            'tc': 1.5, 'beta': 0.8, 'omega': 12.0, 
                            'phi': 2.1, 'A': 5.2, 'B': -0.3, 'C': 0.02
                        },
                        'statistics': {'r_squared': 0.92, 'rmse': 0.015},
                        'predictions': {'crash_date': '2025-12-15', 'days_to_crash': 127}
                    }
                }
            
            # テスト用の失敗ケース
            elif symbol == 'TEST_OPTIMIZATION_FAIL':
                return {
                    'success': False,
                    'error': 'Optimization failed to converge',
                    'optimization_details': {
                        'algorithm': 'SLSQP',
                        'iterations': 100,
                        'convergence_status': 'max_iterations_reached'
                    },
                    'parameter_values': {'tc': 1.001, 'beta': 0.95},
                    'boundary_issues': ['tc_lower']
                }
            
            else:
                # デフォルト成功（低品質）
                return {
                    'success': True,
                    'fit_result': {
                        'parameters': {
                            'tc': 1.01, 'beta': 0.1, 'omega': 20.0, 
                            'phi': -3.14, 'A': 8.8, 'B': -0.29, 'C': 0.01
                        },
                        'statistics': {'r_squared': 0.65, 'rmse': 0.08},
                        'predictions': {'crash_date': '2025-09-01', 'days_to_crash': 22}
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Fitting execution error: {str(e)}',
                'fitting_method': 'lppl',
                'exception_details': {'type': type(e).__name__, 'message': str(e)}
            }
    
    def _check_fitting_quality(self, fit_result: Dict[str, Any]) -> Dict[str, Any]:
        """フィッティング品質チェック（モックアップ）"""
        
        print(f"   ✅ 品質チェック実行")
        
        try:
            statistics = fit_result['statistics']
            r_squared = statistics.get('r_squared', 0)
            parameters = fit_result['parameters']
            
            # 簡単な品質チェック
            failed_checks = []
            
            if r_squared < 0.8:
                failed_checks.append('r_squared_too_low')
            
            if parameters.get('tc', 0) < 1.05:
                failed_checks.append('tc_too_close_to_one')
            
            if parameters.get('omega', 0) >= 19.9:
                failed_checks.append('omega_at_upper_bound')
            
            quality_score = max(0, 1.0 - len(failed_checks) * 0.3)
            
            if quality_score < 0.5:
                return {
                    'success': False,
                    'error': 'Quality score too low',
                    'quality_score': quality_score,
                    'failed_checks': failed_checks,
                    'thresholds': {'min_r_squared': 0.8, 'min_quality': 0.5}
                }
            
            return {
                'success': True,
                'quality_score': quality_score,
                'passed_checks': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Quality check error: {str(e)}',
                'quality_assessment': 'failed_to_evaluate'
            }
    
    def _save_analysis_result(self, fit_result: Dict[str, Any], 
                            data_info: Dict[str, Any], schedule_name: str,
                            backfill_batch_id: str) -> int:
        """分析結果の保存（モックアップ）"""
        
        print(f"   💾 結果保存")
        
        # 実際の実装では analysis_results テーブルに保存
        # モックアップでは仮のIDを返す
        return 12345
    
    def _record_data_retrieval_failure(self, status_id: int, symbol: str,
                                     analysis_basis_date: str, data_result: Dict[str, Any],
                                     schedule_name: str, backfill_batch_id: str):
        """データ取得失敗の記録"""
        
        metadata = self.metadata_generator.create_data_retrieval_failure_metadata(
            api_provider=data_result.get('api_provider', 'unknown'),
            http_status=data_result.get('http_status'),
            request_details=data_result.get('request_details', {}),
            network_error=data_result.get('network_error')
        )
        
        self.failure_tracker.record_failure(
            status_id, symbol, analysis_basis_date,
            data_result.get('api_provider', 'unknown'),
            'data_retrieval', 'api_failure', data_result['error'],
            data_result, metadata, {'retrieval_success': False},
            schedule_name, backfill_batch_id
        )
    
    def _record_data_processing_failure(self, status_id: int, symbol: str,
                                      analysis_basis_date: str, processing_result: Dict[str, Any],
                                      data_info: Dict[str, Any], schedule_name: str,
                                      backfill_batch_id: str):
        """データ処理失敗の記録"""
        
        metadata = self.metadata_generator.create_data_processing_failure_metadata(
            processing_stage=processing_result.get('processing_stage', 'unknown'),
            data_shape=processing_result.get('data_shape'),
            validation_errors=processing_result.get('validation_errors', [])
        )
        
        self.failure_tracker.record_failure(
            status_id, symbol, analysis_basis_date, data_info['source'],
            'data_processing', 'insufficient_data', processing_result['error'],
            processing_result, metadata, data_info, schedule_name, backfill_batch_id
        )
    
    def _record_fitting_failure(self, status_id: int, symbol: str,
                              analysis_basis_date: str, fitting_result: Dict[str, Any],
                              data_info: Dict[str, Any], schedule_name: str,
                              backfill_batch_id: str):
        """フィッティング失敗の記録"""
        
        opt_details = fitting_result.get('optimization_details', {})
        
        metadata = self.metadata_generator.create_fitting_failure_metadata(
            fitting_method='lppl',
            optimization_algorithm=opt_details.get('algorithm', 'unknown'),
            parameter_bounds={'tc': [1.0, 3.0], 'beta': [0.1, 1.0]},  # 実際の値を使用
            attempted_iterations=opt_details.get('iterations', 0),
            convergence_status=opt_details.get('convergence_status', 'failed'),
            parameter_values=fitting_result.get('parameter_values'),
            boundary_issues=fitting_result.get('boundary_issues', [])
        )
        
        self.failure_tracker.record_failure(
            status_id, symbol, analysis_basis_date, data_info['source'],
            'fitting_execution', 'optimization_failed', fitting_result['error'],
            fitting_result, metadata, data_info, schedule_name, backfill_batch_id
        )
    
    def _record_quality_check_failure(self, status_id: int, symbol: str,
                                    analysis_basis_date: str, quality_result: Dict[str, Any],
                                    data_info: Dict[str, Any], schedule_name: str,
                                    backfill_batch_id: str):
        """品質チェック失敗の記録"""
        
        metadata = self.metadata_generator.create_quality_check_failure_metadata(
            quality_score=quality_result.get('quality_score', 0),
            failed_checks=quality_result.get('failed_checks', []),
            quality_thresholds=quality_result.get('thresholds', {}),
            statistical_values={}
        )
        
        self.failure_tracker.record_failure(
            status_id, symbol, analysis_basis_date, data_info['source'],
            'quality_check', 'quality_rejected', quality_result['error'],
            quality_result, metadata, data_info, schedule_name, backfill_batch_id
        )

def test_enhanced_runner():
    """強化された分析実行器のテスト"""
    
    print("🧪 強化された分析実行器テスト")
    print("=" * 60)
    
    runner = EnhancedAnalysisRunner()
    
    test_cases = [
        ('TEST_SUCCESS', '2025-08-10', '成功ケース'),
        ('TEST_RATE_LIMIT', '2025-08-10', 'レート制限エラー'),
        ('TEST_NOT_FOUND', '2025-08-10', 'シンボル未発見'),
        ('TEST_OPTIMIZATION_FAIL', '2025-08-10', '最適化失敗'),
        ('TEST_LOW_QUALITY', '2025-08-10', '品質不良')
    ]
    
    results = []
    
    for symbol, date, description in test_cases:
        print(f"\\n🧪 テストケース: {description}")
        print("-" * 40)
        
        result = runner.run_symbol_analysis(
            symbol, date, 'test_schedule', 'test_batch_001'
        )
        
        results.append((symbol, result['status'], description))
        print(f"結果: {result['status']} - {result.get('reason', '成功')}")
    
    # 結果サマリー
    print(f"\\n" + "=" * 60)
    print("🧪 テスト結果サマリー")
    print("=" * 60)
    
    for symbol, status, description in results:
        status_emoji = "✅" if status == "success" else "❌"
        print(f"{status_emoji} {description:20}: {status}")
    
    # 失敗統計確認
    stats = runner.failure_tracker.get_failure_statistics('test_schedule')
    print(f"\\n📊 失敗統計:")
    print(f"  失敗カテゴリ別: {stats['failure_by_category']}")
    print(f"  失敗段階別: {stats['failure_by_stage']}")
    
    return results

if __name__ == "__main__":
    test_enhanced_runner()