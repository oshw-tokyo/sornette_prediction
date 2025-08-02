#!/usr/bin/env python3
"""
多基準フィッティング結果選択システム

複数の初期パラメータでのフィッティング結果を様々な基準で評価・選択し、
全ての結果を保持してUI上で比較可能にする。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class SelectionCriteria(Enum):
    """選択基準の種類"""
    R_SQUARED_MAX = "r_squared_max"              # R²最大化（現状）
    MULTI_CRITERIA = "multi_criteria"            # 多基準評価
    THEORETICAL_BEST = "theoretical_best"        # 理論値最適
    PRACTICAL_FOCUS = "practical_focus"          # 実用性重視
    CONSERVATIVE = "conservative"                # 保守的選択

@dataclass
class FittingCandidate:
    """個別フィッティング候補"""
    tc: float
    beta: float
    omega: float
    phi: float
    A: float
    B: float
    C: float
    r_squared: float
    rmse: float
    initial_params: List[float]
    convergence_success: bool = True
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'tc': self.tc,
            'beta': self.beta,
            'omega': self.omega,
            'phi': self.phi,
            'A': self.A,
            'B': self.B,
            'C': self.C,
            'r_squared': self.r_squared,
            'rmse': self.rmse,
            'initial_params': self.initial_params,
            'convergence_success': self.convergence_success
        }

@dataclass
class SelectionResult:
    """選択結果（全候補と各基準での選択を含む）"""
    all_candidates: List[FittingCandidate]
    selections: Dict[SelectionCriteria, FittingCandidate]
    selection_scores: Dict[SelectionCriteria, Dict[str, float]]
    default_selection: SelectionCriteria = SelectionCriteria.R_SQUARED_MAX
    
    def get_selected_result(self, criteria: SelectionCriteria = None) -> FittingCandidate:
        """指定基準での選択結果を取得"""
        criteria = criteria or self.default_selection
        return self.selections.get(criteria)
    
    def get_comparison_data(self) -> Dict[str, Any]:
        """比較用データの生成"""
        comparison = {
            'total_candidates': len(self.all_candidates),
            'successful_candidates': len([c for c in self.all_candidates if c.convergence_success]),
            'criteria_results': {}
        }
        
        for criteria, candidate in self.selections.items():
            if candidate:
                comparison['criteria_results'][criteria.value] = {
                    'selected': candidate.to_dict(),
                    'scores': self.selection_scores.get(criteria, {})
                }
        
        return comparison

class MultiCriteriaSelector:
    """多基準選択システム"""
    
    def __init__(self):
        """初期化"""
        # 理論的典型値
        self.theoretical_values = {
            'beta': 0.33,
            'omega': 6.36,
            'tc_practical_max': 1.5
        }
        
        # 多基準評価の重み
        self.multi_criteria_weights = {
            'statistical_quality': 0.4,    # R²による統計品質
            'theoretical_validity': 0.3,   # 理論値への近さ
            'practical_utility': 0.2,      # 実用性（tc値）
            'stability': 0.1               # 安定性（RMSE）
        }
    
    def perform_comprehensive_fitting(self, data: pd.DataFrame, 
                                    initial_param_sets: List[List[float]] = None) -> SelectionResult:
        """包括的フィッティングの実行"""
        
        from src.fitting.utils import logarithm_periodic_func
        from scipy.optimize import curve_fit
        
        log_prices = np.log(data['Close'].values)
        t = np.linspace(0, 1, len(data))
        
        # デフォルト初期値セット
        if initial_param_sets is None:
            initial_param_sets = self._generate_initial_param_sets(log_prices)
        
        # 全候補の生成
        all_candidates = []
        
        for i, p0 in enumerate(initial_param_sets):
            try:
                bounds = self._get_parameter_bounds(log_prices)
                
                popt, _ = curve_fit(
                    logarithm_periodic_func, t, log_prices,
                    p0=p0, bounds=bounds, method='trf',
                    maxfev=5000
                )
                
                y_pred = logarithm_periodic_func(t, *popt)
                r_squared = 1 - (np.sum((log_prices - y_pred)**2) / 
                               np.sum((log_prices - np.mean(log_prices))**2))
                rmse = np.sqrt(np.mean((log_prices - y_pred)**2))
                
                candidate = FittingCandidate(
                    tc=popt[0], beta=popt[1], omega=popt[2], phi=popt[3],
                    A=popt[4], B=popt[5], C=popt[6],
                    r_squared=r_squared, rmse=rmse,
                    initial_params=p0.copy(),
                    convergence_success=True
                )
                
                # 基本的な物理制約チェック
                if self._is_physically_valid(candidate):
                    all_candidates.append(candidate)
                    
            except Exception as e:
                # 失敗した候補も記録（convergence_success=False）
                candidate = FittingCandidate(
                    tc=0, beta=0, omega=0, phi=0, A=0, B=0, C=0,
                    r_squared=0, rmse=float('inf'),
                    initial_params=p0.copy(),
                    convergence_success=False
                )
                all_candidates.append(candidate)
        
        # 各基準での選択実行
        selections = {}
        selection_scores = {}
        
        if all_candidates:
            valid_candidates = [c for c in all_candidates if c.convergence_success]
            
            if valid_candidates:
                # R²最大化選択（現状方式）
                selections[SelectionCriteria.R_SQUARED_MAX] = self._select_by_r_squared(valid_candidates)
                selection_scores[SelectionCriteria.R_SQUARED_MAX] = {'r_squared': selections[SelectionCriteria.R_SQUARED_MAX].r_squared}
                
                # 多基準評価選択
                multi_result, multi_scores = self._select_by_multi_criteria(valid_candidates)
                selections[SelectionCriteria.MULTI_CRITERIA] = multi_result
                selection_scores[SelectionCriteria.MULTI_CRITERIA] = multi_scores
                
                # 理論値最適選択
                theo_result, theo_scores = self._select_by_theoretical_best(valid_candidates)
                selections[SelectionCriteria.THEORETICAL_BEST] = theo_result
                selection_scores[SelectionCriteria.THEORETICAL_BEST] = theo_scores
                
                # 実用性重視選択
                practical_result, practical_scores = self._select_by_practical_focus(valid_candidates)
                selections[SelectionCriteria.PRACTICAL_FOCUS] = practical_result
                selection_scores[SelectionCriteria.PRACTICAL_FOCUS] = practical_scores
                
                # 保守的選択
                conservative_result, conservative_scores = self._select_by_conservative(valid_candidates)
                selections[SelectionCriteria.CONSERVATIVE] = conservative_result
                selection_scores[SelectionCriteria.CONSERVATIVE] = conservative_scores
        
        return SelectionResult(
            all_candidates=all_candidates,
            selections=selections,
            selection_scores=selection_scores,
            default_selection=SelectionCriteria.R_SQUARED_MAX
        )
    
    def _generate_initial_param_sets(self, log_prices: np.ndarray) -> List[List[float]]:
        """初期値セットの生成"""
        param_sets = []
        
        A_base = np.mean(log_prices)
        B_base = (log_prices[-1] - log_prices[0]) / len(log_prices)
        
        # より多様な初期値セット
        tc_values = [1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 2.0]
        beta_values = [0.25, 0.33, 0.45]
        omega_values = [5.0, 6.36, 8.0]
        
        for tc in tc_values:
            for beta in beta_values:
                for omega in omega_values:
                    param_set = [
                        tc, beta, omega, 0.0,  # phi=0
                        A_base,
                        B_base,
                        0.1
                    ]
                    param_sets.append(param_set)
        
        return param_sets
    
    def _get_parameter_bounds(self, log_prices: np.ndarray) -> Tuple:
        """パラメータ境界の設定"""
        price_range = log_prices.max() - log_prices.min()
        
        lower_bounds = [
            1.001,           # tc
            0.05,            # beta
            1.0,             # omega
            -2*np.pi,        # phi
            log_prices.min() - price_range,  # A
            -price_range,    # B
            -price_range     # C
        ]
        
        upper_bounds = [
            3.0,             # tc
            1.0,             # beta
            20.0,            # omega
            2*np.pi,         # phi
            log_prices.max() + price_range,  # A
            price_range,     # B
            price_range      # C
        ]
        
        return (lower_bounds, upper_bounds)
    
    def _is_physically_valid(self, candidate: FittingCandidate) -> bool:
        """物理的妥当性チェック"""
        return (
            candidate.tc > 1.0 and
            0.05 <= candidate.beta <= 1.0 and
            1.0 <= candidate.omega <= 20.0 and
            candidate.r_squared > 0.1
        )
    
    def _select_by_r_squared(self, candidates: List[FittingCandidate]) -> FittingCandidate:
        """R²最大化選択（現状方式）"""
        return max(candidates, key=lambda c: c.r_squared)
    
    def _select_by_multi_criteria(self, candidates: List[FittingCandidate]) -> Tuple[FittingCandidate, Dict]:
        """多基準評価選択"""
        best_candidate = None
        best_score = 0
        best_scores_detail = {}
        
        for candidate in candidates:
            scores = self._calculate_multi_criteria_scores(candidate)
            total_score = sum(
                scores[criterion] * weight 
                for criterion, weight in self.multi_criteria_weights.items()
            )
            
            if total_score > best_score:
                best_score = total_score
                best_candidate = candidate
                best_scores_detail = scores.copy()
                best_scores_detail['total_score'] = total_score
        
        return best_candidate, best_scores_detail
    
    def _calculate_multi_criteria_scores(self, candidate: FittingCandidate) -> Dict[str, float]:
        """多基準スコアの計算"""
        scores = {}
        
        # 統計的品質 (R²)
        scores['statistical_quality'] = candidate.r_squared
        
        # 理論的妥当性 (β、ωの理論値への近さ)
        beta_proximity = 1.0 - min(1.0, abs(candidate.beta - self.theoretical_values['beta']) / self.theoretical_values['beta'])
        omega_proximity = 1.0 - min(1.0, abs(candidate.omega - self.theoretical_values['omega']) / self.theoretical_values['omega'])
        scores['theoretical_validity'] = (beta_proximity + omega_proximity) / 2
        
        # 実用性 (tc値の実用性)
        if candidate.tc <= 1.2:
            scores['practical_utility'] = 1.0
        elif candidate.tc <= 1.5:
            scores['practical_utility'] = 0.8
        elif candidate.tc <= 2.0:
            scores['practical_utility'] = 0.4
        else:
            scores['practical_utility'] = 0.1
        
        # 安定性 (RMSEの逆数)
        scores['stability'] = 1.0 / (1.0 + candidate.rmse)
        
        return scores
    
    def _select_by_theoretical_best(self, candidates: List[FittingCandidate]) -> Tuple[FittingCandidate, Dict]:
        """理論値最適選択"""
        best_candidate = None
        best_score = float('inf')
        
        for candidate in candidates:
            # 理論値からの距離を計算
            beta_distance = abs(candidate.beta - self.theoretical_values['beta'])
            omega_distance = abs(candidate.omega - self.theoretical_values['omega']) / self.theoretical_values['omega']
            
            # 統合距離（R²で重み付け）
            theoretical_distance = (beta_distance + omega_distance) / candidate.r_squared
            
            if theoretical_distance < best_score and candidate.r_squared > 0.5:
                best_score = theoretical_distance
                best_candidate = candidate
        
        scores = {
            'theoretical_distance': best_score,
            'beta_proximity': 1.0 - abs(best_candidate.beta - self.theoretical_values['beta']) / self.theoretical_values['beta'],
            'omega_proximity': 1.0 - abs(best_candidate.omega - self.theoretical_values['omega']) / self.theoretical_values['omega']
        }
        
        return best_candidate, scores
    
    def _select_by_practical_focus(self, candidates: List[FittingCandidate]) -> Tuple[FittingCandidate, Dict]:
        """実用性重視選択"""
        # tc <= 1.5の候補から最高R²を選択
        practical_candidates = [c for c in candidates if c.tc <= self.theoretical_values['tc_practical_max']]
        
        if not practical_candidates:
            # 実用的な候補がない場合は全体から最小tcを選択
            practical_candidates = [min(candidates, key=lambda c: c.tc)]
        
        best_candidate = max(practical_candidates, key=lambda c: c.r_squared)
        
        scores = {
            'tc_practicality': 1.0 if best_candidate.tc <= 1.5 else 0.5,
            'r_squared': best_candidate.r_squared,
            'practical_candidates_count': len(practical_candidates)
        }
        
        return best_candidate, scores
    
    def _select_by_conservative(self, candidates: List[FittingCandidate]) -> Tuple[FittingCandidate, Dict]:
        """保守的選択（高い信頼性重視）"""
        # 複数の制約を満たす候補から選択
        conservative_candidates = []
        
        for candidate in candidates:
            if (candidate.r_squared > 0.7 and
                candidate.tc <= 2.0 and
                0.2 <= candidate.beta <= 0.6 and
                4.0 <= candidate.omega <= 10.0):
                conservative_candidates.append(candidate)
        
        if not conservative_candidates:
            # 保守的候補がない場合はR²上位候補から選択
            conservative_candidates = sorted(candidates, key=lambda c: c.r_squared, reverse=True)[:3]
        
        # 保守的候補の中でバランス最優秀を選択
        best_candidate = None
        best_balance_score = 0
        
        for candidate in conservative_candidates:
            balance_score = (
                candidate.r_squared * 0.5 +
                (1.0 - abs(candidate.beta - 0.33) / 0.33) * 0.3 +
                (1.0 / (1.0 + candidate.rmse)) * 0.2
            )
            
            if balance_score > best_balance_score:
                best_balance_score = balance_score
                best_candidate = candidate
        
        scores = {
            'balance_score': best_balance_score,
            'conservative_candidates_count': len(conservative_candidates),
            'reliability_factor': best_candidate.r_squared * (1.0 / (1.0 + best_candidate.rmse))
        }
        
        return best_candidate, scores

# 使用例とテスト
def example_usage():
    """使用例の実演"""
    print("🎯 多基準フィッティング選択システム デモンストレーション")
    print("=" * 60)
    
    # サンプルデータ生成
    dates = pd.date_range('2020-01-01', periods=1000, freq='D')
    # 簡単なバブルパターン
    t = np.linspace(0, 1, 1000)
    synthetic_data = np.exp(5 + 0.5 * np.log(1.2 - t) + 0.1 * np.cos(8 * np.log(1.2 - t)) + 0.05 * np.random.randn(1000))
    
    data = pd.DataFrame({
        'Close': synthetic_data
    }, index=dates)
    
    # 多基準選択システムの実行
    selector = MultiCriteriaSelector()
    result = selector.perform_comprehensive_fitting(data)
    
    print(f"\n📊 フィッティング結果:")
    print(f"   総候補数: {len(result.all_candidates)}")
    print(f"   成功候補数: {len([c for c in result.all_candidates if c.convergence_success])}")
    
    # 各基準での選択結果比較
    print(f"\n🎯 各選択基準での結果比較:")
    for criteria, candidate in result.selections.items():
        if candidate:
            print(f"\n   {criteria.value}:")
            print(f"     tc={candidate.tc:.3f}, β={candidate.beta:.3f}, ω={candidate.omega:.2f}")
            print(f"     R²={candidate.r_squared:.4f}, RMSE={candidate.rmse:.4f}")
            
            scores = result.selection_scores.get(criteria, {})
            if scores:
                print(f"     スコア詳細: {scores}")
    
    # 比較データの生成
    comparison_data = result.get_comparison_data()
    print(f"\n📈 比較サマリー:")
    print(f"   選択可能基準数: {len(comparison_data['criteria_results'])}")
    
    # デフォルト結果の取得
    default_result = result.get_selected_result()
    print(f"\n✅ デフォルト選択 ({result.default_selection.value}):")
    print(f"   tc={default_result.tc:.3f}, 予測精度=R²{default_result.r_squared:.4f}")
    
    print(f"\n🎉 多基準選択システム デモ完了")

if __name__ == "__main__":
    example_usage()