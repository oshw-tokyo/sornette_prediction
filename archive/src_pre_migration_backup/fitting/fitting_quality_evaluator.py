#!/usr/bin/env python3
"""
フィッティング品質評価システム

パラメータ境界張り付きやその他の異常を検出し、
フィッティング結果の品質を評価・分類する
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class FittingQuality(Enum):
    """フィッティング品質の分類"""
    HIGH_QUALITY = "high_quality"              # 高品質フィット
    ACCEPTABLE = "acceptable"                  # 許容可能
    BOUNDARY_STUCK = "boundary_stuck"          # 境界張り付き
    POOR_CONVERGENCE = "poor_convergence"      # 収束不良
    OVERFITTING = "overfitting"               # 過学習疑い
    UNSTABLE = "unstable"                     # 不安定
    FAILED = "failed"                         # 失敗
    CRITICAL_PROXIMITY = "critical_proximity"  # 臨界点極近（実際のクラッシュ直前）


@dataclass
class QualityAssessment:
    """品質評価結果"""
    quality: FittingQuality
    confidence: float  # 0-1の信頼度
    issues: List[str]  # 検出された問題のリスト
    metadata: Dict[str, Any]  # 追加メタ情報
    is_usable: bool  # 予測に使用可能か
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'quality': self.quality.value,
            'confidence': self.confidence,
            'issues': self.issues,
            'metadata': self.metadata,
            'is_usable': self.is_usable
        }


class FittingQualityEvaluator:
    """フィッティング品質評価クラス"""
    
    def __init__(self):
        """初期化"""
        # パラメータの理論的範囲
        self.parameter_ranges = {
            'tc': {'min': 1.01, 'max': 3.0, 'theoretical_min': 1.05, 'theoretical_max': 2.0},
            'beta': {'min': 0.05, 'max': 1.0, 'theoretical_min': 0.2, 'theoretical_max': 0.7},
            'omega': {'min': 1.0, 'max': 20.0, 'theoretical_min': 3.0, 'theoretical_max': 15.0},
            'A': {'min': -10, 'max': 10},
            'B': {'min': -10, 'max': 10},
            'C': {'min': -1.0, 'max': 1.0},
            'phi': {'min': -2*np.pi, 'max': 2*np.pi}
        }
        
        # 境界張り付き判定の閾値
        self.boundary_tolerance = 0.001  # 境界からこの範囲内なら張り付きと判定
        
        # 品質判定の閾値
        self.quality_thresholds = {
            'r_squared': {'high': 0.9, 'acceptable': 0.7, 'poor': 0.5},
            'rmse': {'high': 0.05, 'acceptable': 0.1, 'poor': 0.2},
            'parameter_stability': {'high': 0.9, 'acceptable': 0.7, 'poor': 0.5}
        }
    
    def evaluate_fitting(self, 
                        parameters: Dict[str, float],
                        statistics: Dict[str, float],
                        bounds: Optional[Tuple] = None,
                        initial_params: Optional[List[float]] = None,
                        convergence_info: Optional[Dict] = None) -> QualityAssessment:
        """
        フィッティング結果の総合評価
        
        Args:
            parameters: フィッティングパラメータ (tc, beta, omega等)
            statistics: 統計量 (r_squared, rmse等)
            bounds: 使用された境界条件
            initial_params: 初期パラメータ
            convergence_info: 収束情報
        
        Returns:
            QualityAssessment: 品質評価結果
        """
        
        issues = []
        metadata = {}
        quality_scores = []
        
        # 1. 境界張り付きチェック
        boundary_check = self._check_boundary_sticking(parameters, bounds)
        if boundary_check['has_boundary_issues']:
            issues.extend(boundary_check['issues'])
            metadata['boundary_stuck_params'] = boundary_check['stuck_params']
        quality_scores.append(boundary_check['score'])
        
        # 2. パラメータ妥当性チェック
        param_check = self._check_parameter_validity(parameters)
        if param_check['has_issues']:
            issues.extend(param_check['issues'])
            metadata['parameter_warnings'] = param_check['warnings']
        quality_scores.append(param_check['score'])
        
        # 3. 統計的品質チェック
        stat_check = self._check_statistical_quality(statistics)
        if stat_check['has_issues']:
            issues.extend(stat_check['issues'])
            metadata['statistical_metrics'] = stat_check['metrics']
        quality_scores.append(stat_check['score'])
        
        # 4. 過学習チェック
        overfit_check = self._check_overfitting(parameters, statistics)
        if overfit_check['is_overfitted']:
            issues.append("過学習の疑い")
            metadata['overfitting_indicators'] = overfit_check['indicators']
        quality_scores.append(overfit_check['score'])
        
        # 5. 収束品質チェック（情報がある場合）
        if convergence_info:
            conv_check = self._check_convergence_quality(convergence_info)
            if conv_check['has_issues']:
                issues.extend(conv_check['issues'])
                metadata['convergence_metrics'] = conv_check['metrics']
            quality_scores.append(conv_check['score'])
        
        # 総合評価
        overall_score = np.mean(quality_scores)
        quality = self._determine_quality_level(overall_score, issues, boundary_check)
        confidence = self._calculate_confidence(overall_score, quality, issues)
        is_usable = self._determine_usability(quality, parameters, statistics)
        
        # 特殊ケースのメタデータ追加
        if quality == FittingQuality.CRITICAL_PROXIMITY:
            metadata.update({
                'fitting_error_warning': True,
                'interpretation': 'フィッティングエラー：tc下限境界張り付き',
                'primary_cause': 'パラメータ最適化の数値的問題',
                'usage_note': '予測には使用不可：フィッティング失敗',
                'recommended_action': '異なる初期値・期間・手法での再試行',
                'rare_possibility': '極稀に実際の臨界点極近の可能性もあるが、通常はフィッティングエラー'
            })
        
        # メタデータ追加
        metadata.update({
            'overall_score': overall_score,
            'individual_scores': quality_scores,
            'parameter_values': parameters,
            'statistical_values': statistics
        })
        
        return QualityAssessment(
            quality=quality,
            confidence=confidence,
            issues=issues,
            metadata=metadata,
            is_usable=is_usable
        )
    
    def _check_boundary_sticking(self, parameters: Dict[str, float], 
                                bounds: Optional[Tuple] = None) -> Dict:
        """境界張り付きのチェック"""
        
        if bounds is None:
            # デフォルト境界を使用
            lower_bounds = [self.parameter_ranges[p]['min'] for p in ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']]
            upper_bounds = [self.parameter_ranges[p]['max'] for p in ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']]
        else:
            lower_bounds, upper_bounds = bounds
        
        stuck_params = []
        issues = []
        
        param_order = ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
        
        for i, param_name in enumerate(param_order):
            if param_name in parameters:
                value = parameters[param_name]
                lower = lower_bounds[i] if i < len(lower_bounds) else self.parameter_ranges[param_name]['min']
                upper = upper_bounds[i] if i < len(upper_bounds) else self.parameter_ranges[param_name]['max']
                
                # 境界との距離を計算
                lower_distance = abs(value - lower)
                upper_distance = abs(value - upper)
                range_size = upper - lower
                
                # 相対的な距離で判定
                relative_tolerance = self.boundary_tolerance * range_size
                
                if lower_distance < relative_tolerance:
                    stuck_params.append(f"{param_name}_lower")
                    issues.append(f"{param_name}が下限に張り付き ({value:.6f} ≈ {lower})")
                elif upper_distance < relative_tolerance:
                    stuck_params.append(f"{param_name}_upper")
                    issues.append(f"{param_name}が上限に張り付き ({value:.6f} ≈ {upper})")
        
        # スコア計算（張り付きパラメータ数に基づく）
        score = 1.0 - (len(stuck_params) / len(param_order))
        
        # tc張り付きは特に問題
        if any('tc' in sp for sp in stuck_params):
            score *= 0.5
            issues.insert(0, "⚠️ tc値の境界張り付きは深刻な問題")
        
        return {
            'has_boundary_issues': len(stuck_params) > 0,
            'stuck_params': stuck_params,
            'issues': issues,
            'score': score
        }
    
    def _check_parameter_validity(self, parameters: Dict[str, float]) -> Dict:
        """パラメータの妥当性チェック"""
        
        issues = []
        warnings = []
        validity_scores = []
        
        for param_name, value in parameters.items():
            if param_name in self.parameter_ranges:
                ranges = self.parameter_ranges[param_name]
                
                # 理論的範囲チェック
                if 'theoretical_min' in ranges and 'theoretical_max' in ranges:
                    if value < ranges['theoretical_min'] or value > ranges['theoretical_max']:
                        warnings.append(f"{param_name}={value:.3f}が理論的範囲外")
                        validity_scores.append(0.5)
                    else:
                        # 理論的範囲内での相対位置
                        theoretical_range = ranges['theoretical_max'] - ranges['theoretical_min']
                        distance_from_center = abs(value - (ranges['theoretical_min'] + ranges['theoretical_max']) / 2)
                        validity_scores.append(1.0 - (distance_from_center / theoretical_range))
        
        # 特殊なチェック
        if 'tc' in parameters:
            if parameters['tc'] > 2.5:
                issues.append("tc値が非現実的に大きい（> 2.5）")
            elif parameters['tc'] < 1.02:
                issues.append("tc値が非現実的に小さい（< 1.02）")
        
        if 'omega' in parameters:
            if parameters['omega'] < 2.0:
                warnings.append("ω値が異常に小さい（< 2.0）")
            elif parameters['omega'] > 15.0:
                warnings.append("ω値が異常に大きい（> 15.0）")
        
        score = np.mean(validity_scores) if validity_scores else 0.8
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'warnings': warnings,
            'score': score
        }
    
    def _check_statistical_quality(self, statistics: Dict[str, float]) -> Dict:
        """統計的品質のチェック"""
        
        issues = []
        metrics = {}
        scores = []
        
        # R²チェック
        if 'r_squared' in statistics:
            r2 = statistics['r_squared']
            metrics['r_squared'] = r2
            
            if r2 < self.quality_thresholds['r_squared']['poor']:
                issues.append(f"R²が非常に低い ({r2:.3f})")
                scores.append(0.2)
            elif r2 < self.quality_thresholds['r_squared']['acceptable']:
                issues.append(f"R²が低い ({r2:.3f})")
                scores.append(0.5)
            elif r2 < self.quality_thresholds['r_squared']['high']:
                scores.append(0.8)
            else:
                scores.append(1.0)
        
        # RMSEチェック
        if 'rmse' in statistics:
            rmse = statistics['rmse']
            metrics['rmse'] = rmse
            
            if rmse > self.quality_thresholds['rmse']['poor']:
                issues.append(f"RMSEが非常に高い ({rmse:.3f})")
                scores.append(0.2)
            elif rmse > self.quality_thresholds['rmse']['acceptable']:
                issues.append(f"RMSEが高い ({rmse:.3f})")
                scores.append(0.5)
            elif rmse > self.quality_thresholds['rmse']['high']:
                scores.append(0.8)
            else:
                scores.append(1.0)
        
        score = np.mean(scores) if scores else 0.5
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'metrics': metrics,
            'score': score
        }
    
    def _check_overfitting(self, parameters: Dict[str, float], 
                          statistics: Dict[str, float]) -> Dict:
        """過学習のチェック"""
        
        indicators = []
        is_overfitted = False
        
        # 高R²と異常なパラメータの組み合わせ
        if 'r_squared' in statistics and statistics['r_squared'] > 0.95:
            # tc境界張り付き
            if 'tc' in parameters and parameters['tc'] <= 1.01:
                indicators.append("高R²とtc境界張り付きの組み合わせ")
                is_overfitted = True
            
            # 極端なβ値
            if 'beta' in parameters and (parameters['beta'] < 0.1 or parameters['beta'] > 0.9):
                indicators.append("高R²と極端なβ値の組み合わせ")
                is_overfitted = True
        
        # パラメータ数と比較してデータ点数が少ない場合の判定は別途必要
        
        score = 0.2 if is_overfitted else 0.9
        
        return {
            'is_overfitted': is_overfitted,
            'indicators': indicators,
            'score': score
        }
    
    def _check_convergence_quality(self, convergence_info: Dict) -> Dict:
        """収束品質のチェック"""
        
        issues = []
        metrics = {}
        
        # 収束回数
        if 'iterations' in convergence_info:
            iterations = convergence_info['iterations']
            metrics['iterations'] = iterations
            
            if iterations > 900:
                issues.append(f"収束に多くの反復が必要 ({iterations}回)")
        
        # 収束判定
        if 'converged' in convergence_info and not convergence_info['converged']:
            issues.append("収束基準を満たさず終了")
        
        score = 0.5 if issues else 1.0
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'metrics': metrics,
            'score': score
        }
    
    def _determine_quality_level(self, overall_score: float, issues: List[str], 
                               boundary_check: Dict) -> FittingQuality:
        """品質レベルの決定"""
        
        # 境界張り付きがある場合の詳細判定
        if boundary_check['has_boundary_issues'] and 'tc' in str(boundary_check['stuck_params']):
            # tc下限張り付きの場合、臨界点極近の可能性を考慮
            if 'tc_lower' in boundary_check['stuck_params']:
                return FittingQuality.CRITICAL_PROXIMITY
            else:
                return FittingQuality.BOUNDARY_STUCK
        
        # スコアベースの判定
        if overall_score >= 0.9 and len(issues) == 0:
            return FittingQuality.HIGH_QUALITY
        elif overall_score >= 0.7 and len(issues) <= 2:
            return FittingQuality.ACCEPTABLE
        elif overall_score >= 0.5:
            if any("収束" in issue for issue in issues):
                return FittingQuality.POOR_CONVERGENCE
            elif any("過学習" in issue for issue in issues):
                return FittingQuality.OVERFITTING
            else:
                return FittingQuality.UNSTABLE
        else:
            return FittingQuality.FAILED
    
    def _calculate_confidence(self, overall_score: float, 
                            quality: FittingQuality, issues: List[str]) -> float:
        """信頼度の計算"""
        
        base_confidence = overall_score
        
        # 品質レベルによる調整
        quality_multipliers = {
            FittingQuality.HIGH_QUALITY: 1.0,
            FittingQuality.ACCEPTABLE: 0.8,
            FittingQuality.BOUNDARY_STUCK: 0.3,
            FittingQuality.POOR_CONVERGENCE: 0.4,
            FittingQuality.OVERFITTING: 0.2,
            FittingQuality.UNSTABLE: 0.3,
            FittingQuality.FAILED: 0.1,
            FittingQuality.CRITICAL_PROXIMITY: 0.95  # 高信頼度だが特殊ケース
        }
        
        confidence = base_confidence * quality_multipliers.get(quality, 0.5)
        
        # 問題数による追加減算
        confidence *= (1.0 - 0.05 * len(issues))
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_usability(self, quality: FittingQuality, 
                           parameters: Dict[str, float],
                           statistics: Dict[str, float]) -> bool:
        """予測使用可能性の判定"""
        
        # 通常使用不可の品質レベル
        unusable_qualities = [
            FittingQuality.BOUNDARY_STUCK,
            FittingQuality.FAILED,
            FittingQuality.OVERFITTING
        ]
        
        # CRITICAL_PROXIMITYは特殊処理：高信頼度だが予測としては使用不可
        if quality == FittingQuality.CRITICAL_PROXIMITY:
            return False  # 臨界点極近は予測に使用不可（但し重要な情報）
        
        if quality in unusable_qualities:
            return False
        
        # 最低限の統計的品質
        if 'r_squared' in statistics and statistics['r_squared'] < 0.5:
            return False
        
        # tc値の妥当性
        if 'tc' in parameters and (parameters['tc'] <= 1.01 or parameters['tc'] > 3.0):
            return False
        
        return True


# 使用例とテスト
def example_usage():
    """使用例"""
    evaluator = FittingQualityEvaluator()
    
    # テストケース1: 境界張り付き
    print("🔍 テストケース1: 境界張り付き")
    params1 = {
        'tc': 1.001,  # 下限に張り付き
        'beta': 0.35,
        'omega': 6.5,
        'phi': 0.0,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats1 = {'r_squared': 0.95, 'rmse': 0.03}
    
    assessment1 = evaluator.evaluate_fitting(params1, stats1)
    print(f"   品質: {assessment1.quality.value}")
    print(f"   信頼度: {assessment1.confidence:.2%}")
    print(f"   使用可能: {assessment1.is_usable}")
    print(f"   問題: {assessment1.issues}")
    if assessment1.quality == FittingQuality.CRITICAL_PROXIMITY:
        print(f"   ⚠️ 解釈: {assessment1.metadata.get('interpretation', '')}")
        print(f"   原因: {assessment1.metadata.get('primary_cause', '')}")
    
    # テストケース2: 高品質フィット
    print("\n🔍 テストケース2: 高品質フィット")
    params2 = {
        'tc': 1.25,
        'beta': 0.33,
        'omega': 6.36,
        'phi': 0.1,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats2 = {'r_squared': 0.92, 'rmse': 0.04}
    
    assessment2 = evaluator.evaluate_fitting(params2, stats2)
    print(f"   品質: {assessment2.quality.value}")
    print(f"   信頼度: {assessment2.confidence:.2%}")
    print(f"   使用可能: {assessment2.is_usable}")
    print(f"   問題: {assessment2.issues}")
    
    # テストケース3: 過学習疑い
    print("\n🔍 テストケース3: 過学習疑い")
    params3 = {
        'tc': 1.01,
        'beta': 0.95,  # 極端な値
        'omega': 18.0,  # 極端な値
        'phi': 0.0,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats3 = {'r_squared': 0.98, 'rmse': 0.02}
    
    assessment3 = evaluator.evaluate_fitting(params3, stats3)
    print(f"   品質: {assessment3.quality.value}")
    print(f"   信頼度: {assessment3.confidence:.2%}")
    print(f"   使用可能: {assessment3.is_usable}")
    print(f"   問題: {assessment3.issues}")


if __name__ == "__main__":
    example_usage()