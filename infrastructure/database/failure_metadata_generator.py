#!/usr/bin/env python3
"""
失敗メタデータ生成器
- データ取得失敗とフィッティング失敗の詳細メタデータ生成
- 失敗原因の分類・分析に使用
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

class FailureMetadataGenerator:
    """失敗メタデータ生成クラス"""
    
    @staticmethod
    def create_data_retrieval_failure_metadata(
        api_provider: str,
        http_status: Optional[int] = None,
        response_data: Optional[Dict] = None,
        request_details: Optional[Dict] = None,
        rate_limit_info: Optional[Dict] = None,
        network_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        データ取得失敗のメタデータ生成
        
        Args:
            api_provider: APIプロバイダー (coingecko, alpha_vantage, fred)
            http_status: HTTPステータスコード
            response_data: レスポンスデータ
            request_details: リクエスト詳細
            rate_limit_info: レート制限情報
            network_error: ネットワークエラー
            
        Returns:
            dict: 失敗メタデータ
        """
        
        metadata = {
            'failure_type': 'data_retrieval',
            'api_provider': api_provider,
            'timestamp': datetime.now().isoformat(),
            'request_info': request_details or {},
            'response_info': {
                'http_status': http_status,
                'response_data': response_data or {},
                'network_error': network_error
            },
            'rate_limit_info': rate_limit_info or {},
            'recovery_suggestions': []
        }
        
        # プロバイダー別の詳細情報
        if api_provider == 'coingecko':
            api_key_exists = rate_limit_info and rate_limit_info.get('api_key') if rate_limit_info else False
            metadata['coingecko_specific'] = {
                'api_tier': 'free' if not api_key_exists else 'pro',
                'rate_limit_per_minute': 10 if not api_key_exists else 100,
                'common_issues': [
                    'Rate limit exceeded',
                    'Invalid coin ID',
                    'API maintenance'
                ]
            }
            
            # 回復提案
            if http_status == 429:  # Rate limit
                metadata['recovery_suggestions'].extend([
                    'Increase delay between requests',
                    'Consider upgrading to Pro API',
                    'Implement exponential backoff'
                ])
            elif http_status == 404:  # Not found
                metadata['recovery_suggestions'].extend([
                    'Verify coin ID mapping',
                    'Check if coin is delisted',
                    'Update symbol mapping'
                ])
        
        elif api_provider == 'alpha_vantage':
            metadata['alpha_vantage_specific'] = {
                'daily_limit': 500,
                'monthly_limit': 5000,
                'common_issues': [
                    'Daily quota exceeded',
                    'Invalid symbol',
                    'API maintenance'
                ]
            }
            
            if http_status == 200 and response_data:
                # Alpha Vantageは200でもエラーメッセージを返すことがある
                if 'Error Message' in str(response_data):
                    metadata['recovery_suggestions'].append('Check symbol validity')
                elif 'Thank you for using Alpha Vantage' in str(response_data):
                    metadata['recovery_suggestions'].extend([
                        'Daily quota exceeded',
                        'Wait until next day',
                        'Consider premium plan'
                    ])
        
        elif api_provider == 'fred':
            metadata['fred_specific'] = {
                'rate_limit': '120 requests per 60 seconds',
                'api_reliability': 'high',
                'common_issues': [
                    'Invalid series ID',
                    'Date out of range',
                    'Temporary maintenance'
                ]
            }
            
            if http_status == 400:
                metadata['recovery_suggestions'].extend([
                    'Check series ID validity',
                    'Verify date range parameters'
                ])
        
        return metadata
    
    @staticmethod
    def create_fitting_failure_metadata(
        fitting_method: str,
        optimization_algorithm: str,
        parameter_bounds: Dict[str, Any],
        attempted_iterations: int,
        convergence_status: str,
        parameter_values: Optional[Dict[str, float]] = None,
        statistical_measures: Optional[Dict[str, float]] = None,
        boundary_issues: Optional[List[str]] = None,
        data_quality_issues: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        フィッティング失敗のメタデータ生成
        
        Args:
            fitting_method: フィッティング手法
            optimization_algorithm: 最適化アルゴリズム
            parameter_bounds: パラメータ境界
            attempted_iterations: 試行回数
            convergence_status: 収束状況
            parameter_values: パラメータ値
            statistical_measures: 統計指標
            boundary_issues: 境界問題
            data_quality_issues: データ品質問題
            
        Returns:
            dict: 失敗メタデータ
        """
        
        metadata = {
            'failure_type': 'fitting_execution',
            'fitting_method': fitting_method,
            'optimization_details': {
                'algorithm': optimization_algorithm,
                'attempted_iterations': attempted_iterations,
                'convergence_status': convergence_status,
                'parameter_bounds': parameter_bounds
            },
            'parameter_analysis': {
                'final_values': parameter_values or {},
                'boundary_stuck_params': boundary_issues or [],
                'statistical_measures': statistical_measures or {}
            },
            'data_quality': {
                'issues_found': data_quality_issues or []
            },
            'timestamp': datetime.now().isoformat(),
            'recovery_suggestions': []
        }
        
        # 失敗原因の分析と提案
        if convergence_status == 'max_iterations_reached':
            metadata['recovery_suggestions'].extend([
                'Increase maximum iterations',
                'Try different initial parameters',
                'Consider alternative optimization algorithm'
            ])
        
        elif convergence_status == 'optimization_failed':
            metadata['recovery_suggestions'].extend([
                'Adjust parameter bounds',
                'Try multiple initial guesses',
                'Check data quality'
            ])
        
        if boundary_issues:
            metadata['recovery_suggestions'].append('Review parameter bounds - some parameters hit boundaries')
        
        if data_quality_issues:
            metadata['recovery_suggestions'].append('Address data quality issues before refitting')
        
        # LPPL特有の問題
        if fitting_method == 'lppl':
            metadata['lppl_specific'] = {
                'known_challenges': [
                    'tc parameter sensitive to noise',
                    'omega parameter often hits upper bound',
                    'Local minima in optimization landscape'
                ],
                'recommended_approaches': [
                    'Multi-start optimization',
                    'Parameter sweeping for tc',
                    'Quality filtering based on boundary conditions'
                ]
            }
            
            # LPPLパラメータの特定問題
            if parameter_values:
                tc = parameter_values.get('tc')
                omega = parameter_values.get('omega')
                
                if tc and tc < 1.01:
                    metadata['recovery_suggestions'].append('tc too close to 1.0 - consider data period adjustment')
                
                if omega and omega >= 19.9:
                    metadata['recovery_suggestions'].append('omega hitting upper bound - review constraints')
        
        return metadata
    
    @staticmethod
    def create_data_processing_failure_metadata(
        processing_stage: str,
        data_shape: Optional[tuple] = None,
        missing_data_count: Optional[int] = None,
        outlier_count: Optional[int] = None,
        transformation_errors: Optional[List[str]] = None,
        validation_errors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        データ処理失敗のメタデータ生成
        
        Args:
            processing_stage: 処理段階
            data_shape: データ形状
            missing_data_count: 欠損データ数
            outlier_count: 外れ値数
            transformation_errors: 変換エラー
            validation_errors: 検証エラー
            
        Returns:
            dict: 失敗メタデータ
        """
        
        metadata = {
            'failure_type': 'data_processing',
            'processing_stage': processing_stage,
            'data_diagnostics': {
                'data_shape': data_shape,
                'missing_data_count': missing_data_count,
                'outlier_count': outlier_count
            },
            'errors': {
                'transformation_errors': transformation_errors or [],
                'validation_errors': validation_errors or []
            },
            'timestamp': datetime.now().isoformat(),
            'recovery_suggestions': []
        }
        
        # データ品質に基づく提案
        if missing_data_count and missing_data_count > 0:
            metadata['recovery_suggestions'].extend([
                'Fill missing data with interpolation',
                'Extend data collection period',
                'Consider alternative data source'
            ])
        
        if outlier_count and outlier_count > 10:
            metadata['recovery_suggestions'].extend([
                'Review outlier detection threshold',
                'Consider outlier handling strategies',
                'Validate data source quality'
            ])
        
        if data_shape and len(data_shape) > 0 and data_shape[0] < 100:
            metadata['recovery_suggestions'].append('Insufficient data points for reliable fitting')
        
        return metadata
    
    @staticmethod
    def create_quality_check_failure_metadata(
        quality_score: float,
        failed_checks: List[str],
        quality_thresholds: Dict[str, float],
        statistical_values: Dict[str, float],
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        品質チェック失敗のメタデータ生成
        
        Args:
            quality_score: 品質スコア
            failed_checks: 失敗したチェック項目
            quality_thresholds: 品質閾値
            statistical_values: 統計値
            confidence_score: 信頼度スコア
            
        Returns:
            dict: 失敗メタデータ
        """
        
        metadata = {
            'failure_type': 'quality_check',
            'quality_assessment': {
                'overall_score': quality_score,
                'confidence_score': confidence_score,
                'failed_checks': failed_checks,
                'thresholds_used': quality_thresholds,
                'statistical_values': statistical_values
            },
            'timestamp': datetime.now().isoformat(),
            'recovery_suggestions': []
        }
        
        # 品質問題に基づく提案
        if 'r_squared_too_low' in failed_checks:
            metadata['recovery_suggestions'].extend([
                'Consider longer data period',
                'Review data quality',
                'Try different parameter initialization'
            ])
        
        if 'parameters_at_boundary' in failed_checks:
            metadata['recovery_suggestions'].extend([
                'Adjust parameter bounds',
                'Review optimization constraints',
                'Consider model appropriateness'
            ])
        
        if quality_score < 0.5:
            metadata['recovery_suggestions'].append('Quality too low for reliable prediction')
        
        return metadata

# 使用例の生成関数
def generate_example_metadata():
    """メタデータ生成の使用例"""
    
    print("🧪 失敗メタデータ生成例")
    print("=" * 50)
    
    # データ取得失敗の例
    print("1. データ取得失敗 (CoinGecko Rate Limit)")
    retrieval_metadata = FailureMetadataGenerator.create_data_retrieval_failure_metadata(
        api_provider='coingecko',
        http_status=429,
        request_details={'symbol': 'BTC', 'period': '365 days'},
        rate_limit_info={'requests_per_minute': 10, 'api_key': None}
    )
    print(f"   メタデータキー数: {len(retrieval_metadata)}")
    print(f"   回復提案: {retrieval_metadata['recovery_suggestions']}")
    
    # フィッティング失敗の例
    print("\\n2. フィッティング失敗 (最適化収束失敗)")
    fitting_metadata = FailureMetadataGenerator.create_fitting_failure_metadata(
        fitting_method='lppl',
        optimization_algorithm='SLSQP',
        parameter_bounds={'tc': [1.0, 3.0], 'beta': [0.1, 1.0]},
        attempted_iterations=100,
        convergence_status='max_iterations_reached',
        parameter_values={'tc': 1.001, 'beta': 0.95},
        boundary_issues=['tc_lower']
    )
    print(f"   メタデータキー数: {len(fitting_metadata)}")
    print(f"   回復提案: {fitting_metadata['recovery_suggestions']}")
    
    # データ処理失敗の例
    print("\\n3. データ処理失敗 (データ不足)")
    processing_metadata = FailureMetadataGenerator.create_data_processing_failure_metadata(
        processing_stage='validation',
        data_shape=(45,),  # 45日分のデータしかない
        missing_data_count=5,
        validation_errors=['insufficient_data_points']
    )
    print(f"   メタデータキー数: {len(processing_metadata)}")
    print(f"   回復提案: {processing_metadata['recovery_suggestions']}")
    
    # 品質チェック失敗の例
    print("\\n4. 品質チェック失敗 (R²低すぎ)")
    quality_metadata = FailureMetadataGenerator.create_quality_check_failure_metadata(
        quality_score=0.3,
        failed_checks=['r_squared_too_low', 'parameters_at_boundary'],
        quality_thresholds={'min_r_squared': 0.8},
        statistical_values={'r_squared': 0.65, 'rmse': 0.08},
        confidence_score=0.2
    )
    print(f"   メタデータキー数: {len(quality_metadata)}")
    print(f"   回復提案: {quality_metadata['recovery_suggestions']}")
    
    return retrieval_metadata, fitting_metadata, processing_metadata, quality_metadata

if __name__ == "__main__":
    generate_example_metadata()