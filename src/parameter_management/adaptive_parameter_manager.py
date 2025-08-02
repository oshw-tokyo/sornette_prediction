#!/usr/bin/env python3
"""
リアルタイム監視システム向け適応的パラメータマネージャー

1987年・2000年検証の成功事例から抽出したパラメータ管理戦略を実装
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime, timedelta

class BubbleType(Enum):
    """バブルタイプ分類"""
    TECH_BUBBLE = "tech_bubble"
    FINANCIAL_CRISIS = "financial_crisis"
    COMMODITY_BUBBLE = "commodity_bubble"
    UNKNOWN = "unknown"

class FittingStrategy(Enum):
    """フィッティング戦略"""
    CONSERVATIVE = "conservative"    # 日常監視用
    EXTENSIVE = "extensive"         # 詳細分析用
    EMERGENCY = "emergency"         # 危機検出用

@dataclass
class ParameterRange:
    """パラメータ範囲定義"""
    min_val: float
    max_val: float
    preferred_center: Optional[float] = None
    
    def contains(self, value: float) -> bool:
        return self.min_val <= value <= self.max_val
    
    def get_center(self) -> float:
        return self.preferred_center or (self.min_val + self.max_val) / 2

@dataclass
class MarketCharacteristics:
    """市場特性パラメータ"""
    data_period_days: int
    volatility: float
    bubble_magnitude: float
    bubble_type: BubbleType
    data_quality_score: float

class AdaptiveParameterManager:
    """適応的パラメータマネージャー"""
    
    def __init__(self):
        """初期化とパラメータテーブルの設定"""
        self._setup_parameter_tables()
        self._setup_strategies()
        self.history = []
    
    def _setup_parameter_tables(self):
        """パラメータテーブルの初期設定"""
        
        # 固定パラメータ（全ケースで共通）
        self.fixed_params = {
            'phi': 0.0,      # 位相は0固定
            'C': 0.1,        # 振動振幅は小さい固定値
        }
        
        # 適応パラメータ（コア範囲 - 理論値重視）
        self.core_ranges = {
            'tc': ParameterRange(1.01, 1.3, 1.15),
            'beta': ParameterRange(0.25, 0.50, 0.33),  # Sornette理論値中心
            'omega': ParameterRange(5.0, 9.0, 6.36),   # 論文典型値
        }
        
        # 拡張パラメータ（広域探索用）
        self.extended_ranges = {
            'tc': ParameterRange(1.001, 1.5, 1.15),
            'beta': ParameterRange(0.1, 0.7, 0.33),
            'omega': ParameterRange(3.0, 15.0, 6.36),
        }
        
        # 最大パラメータ（緊急時用）
        self.maximum_ranges = {
            'tc': ParameterRange(1.001, 2.0, 1.15),
            'beta': ParameterRange(0.05, 1.0, 0.33),
            'omega': ParameterRange(1.0, 20.0, 6.36),
        }
        
        # バブルタイプ別調整
        self.bubble_type_adjustments = {
            BubbleType.TECH_BUBBLE: {
                'beta': ParameterRange(0.3, 0.4, 0.35),
                'omega': ParameterRange(6.0, 8.0, 7.0),
                'tc_extension_factor': 1.1
            },
            BubbleType.FINANCIAL_CRISIS: {
                'beta': ParameterRange(0.2, 0.6, 0.33),
                'omega': ParameterRange(4.0, 10.0, 6.5),
                'tc_extension_factor': 1.0
            },
            BubbleType.COMMODITY_BUBBLE: {
                'beta': ParameterRange(0.25, 0.45, 0.33),
                'omega': ParameterRange(5.0, 7.0, 6.0),
                'tc_extension_factor': 1.15
            },
            BubbleType.UNKNOWN: {
                'beta': ParameterRange(0.1, 0.7, 0.33),
                'omega': ParameterRange(3.0, 12.0, 6.36),
                'tc_extension_factor': 1.2
            }
        }
    
    def _setup_strategies(self):
        """フィッティング戦略の設定"""
        self.strategies = {
            FittingStrategy.CONSERVATIVE: {
                'param_ranges': 'core',
                'initialization_method': 'grid_based',
                'trials': 100,
                'timeout_seconds': 30,
                'quality_threshold': 0.7,
                'description': '日常監視用：高速・安定重視'
            },
            FittingStrategy.EXTENSIVE: {
                'param_ranges': 'extended',
                'initialization_method': 'hybrid_grid_random',
                'trials': 500,
                'timeout_seconds': 120,
                'quality_threshold': 0.6,
                'description': '詳細分析用：精度・汎用性重視'
            },
            FittingStrategy.EMERGENCY: {
                'param_ranges': 'maximum',
                'initialization_method': 'random_wide',
                'trials': 1000,
                'timeout_seconds': 300,
                'quality_threshold': 0.3,
                'description': '危機検出用：網羅性・検出能力重視'
            }
        }
    
    def get_parameters_for_market(self, market_chars: MarketCharacteristics, 
                                 strategy: FittingStrategy = FittingStrategy.CONSERVATIVE) -> Dict[str, Any]:
        """市場特性に応じたパラメータセットを取得"""
        
        # 基本パラメータ範囲の選択
        range_type = self.strategies[strategy]['param_ranges']
        if range_type == 'core':
            base_ranges = self.core_ranges.copy()
        elif range_type == 'extended':
            base_ranges = self.extended_ranges.copy()
        else:  # maximum
            base_ranges = self.maximum_ranges.copy()
        
        # バブルタイプ別調整
        if market_chars.bubble_type in self.bubble_type_adjustments:
            adjustments = self.bubble_type_adjustments[market_chars.bubble_type]
            
            # beta, omega の調整
            if 'beta' in adjustments:
                base_ranges['beta'] = adjustments['beta']
            if 'omega' in adjustments:
                base_ranges['omega'] = adjustments['omega']
            
            # tc の拡張調整
            if 'tc_extension_factor' in adjustments:
                factor = adjustments['tc_extension_factor']
                tc_range = base_ranges['tc']
                base_ranges['tc'] = ParameterRange(
                    tc_range.min_val,
                    tc_range.max_val * factor,
                    tc_range.preferred_center
                )
        
        # データ期間による tc 調整
        period_adjustment = min(1.5, 1.0 + market_chars.data_period_days / 1000)
        tc_range = base_ranges['tc']
        base_ranges['tc'] = ParameterRange(
            tc_range.min_val,
            tc_range.max_val * period_adjustment,
            tc_range.preferred_center
        )
        
        # 完全パラメータセットの構築
        param_set = {
            'ranges': base_ranges,
            'fixed': self.fixed_params.copy(),
            'strategy': strategy,
            'initialization_method': self.strategies[strategy]['initialization_method'],
            'trials': self.strategies[strategy]['trials'],
            'quality_threshold': self.strategies[strategy]['quality_threshold'],
            'market_characteristics': market_chars,
            'timestamp': datetime.now()
        }
        
        # データ依存パラメータの計算式を追加
        param_set['calculated_formulas'] = {
            'A': 'np.log(np.mean(data))',
            'B': '(data[-1] - data[0]) / (len(data) - 1)'
        }
        
        return param_set
    
    def generate_initial_values(self, param_set: Dict[str, Any], data: np.ndarray) -> List[Dict[str, float]]:
        """初期値リストの生成"""
        
        ranges = param_set['ranges']
        method = param_set['initialization_method']
        trials = param_set['trials']
        
        # データ依存パラメータの計算
        log_data = np.log(data)
        A_calc = np.mean(log_data)
        B_calc = (log_data[-1] - log_data[0]) / (len(log_data) - 1)
        
        initial_values = []
        
        if method == 'grid_based':
            initial_values = self._generate_grid_initial_values(ranges, trials, A_calc, B_calc)
        elif method == 'hybrid_grid_random':
            # グリッド50% + ランダム50%
            grid_trials = trials // 2
            random_trials = trials - grid_trials
            initial_values.extend(self._generate_grid_initial_values(ranges, grid_trials, A_calc, B_calc))
            initial_values.extend(self._generate_random_initial_values(ranges, random_trials, A_calc, B_calc))
        else:  # random_wide
            initial_values = self._generate_random_initial_values(ranges, trials, A_calc, B_calc)
        
        return initial_values
    
    def _generate_grid_initial_values(self, ranges: Dict[str, ParameterRange], 
                                    trials: int, A_calc: float, B_calc: float) -> List[Dict[str, float]]:
        """グリッドベース初期値生成"""
        
        # 3次元グリッドの設定（tc, beta, omega）
        n_per_dim = int(np.ceil(trials ** (1/3)))
        
        tc_values = np.linspace(ranges['tc'].min_val, ranges['tc'].max_val, n_per_dim)
        beta_values = np.linspace(ranges['beta'].min_val, ranges['beta'].max_val, n_per_dim)
        omega_values = np.linspace(ranges['omega'].min_val, ranges['omega'].max_val, n_per_dim)
        
        initial_values = []
        for tc in tc_values:
            for beta in beta_values:
                for omega in omega_values:
                    if len(initial_values) >= trials:
                        break
                    initial_values.append({
                        'tc': float(tc),
                        'beta': float(beta),
                        'omega': float(omega),
                        'phi': self.fixed_params['phi'],
                        'A': float(A_calc),
                        'B': float(B_calc),
                        'C': self.fixed_params['C']
                    })
                if len(initial_values) >= trials:
                    break
            if len(initial_values) >= trials:
                break
        
        return initial_values[:trials]
    
    def _generate_random_initial_values(self, ranges: Dict[str, ParameterRange], 
                                      trials: int, A_calc: float, B_calc: float) -> List[Dict[str, float]]:
        """ランダム初期値生成"""
        
        initial_values = []
        for _ in range(trials):
            initial_values.append({
                'tc': np.random.uniform(ranges['tc'].min_val, ranges['tc'].max_val),
                'beta': np.random.uniform(ranges['beta'].min_val, ranges['beta'].max_val),
                'omega': np.random.uniform(ranges['omega'].min_val, ranges['omega'].max_val),
                'phi': self.fixed_params['phi'],
                'A': float(A_calc),
                'B': float(B_calc),
                'C': self.fixed_params['C']
            })
        
        return initial_values
    
    def get_fitting_bounds(self, param_set: Dict[str, Any]) -> Tuple[List[float], List[float]]:
        """フィッティング境界の取得"""
        
        ranges = param_set['ranges']
        
        # パラメータ順序: [tc, beta, omega, phi, A, B, C]
        lower_bounds = [
            ranges['tc'].min_val,
            ranges['beta'].min_val,
            ranges['omega'].min_val,
            -8 * np.pi,  # phi
            -np.inf,     # A (対数空間)
            -np.inf,     # B
            -2.0         # C
        ]
        
        upper_bounds = [
            ranges['tc'].max_val,
            ranges['beta'].max_val,
            ranges['omega'].max_val,
            8 * np.pi,   # phi
            np.inf,      # A (対数空間)
            np.inf,      # B
            2.0          # C
        ]
        
        return lower_bounds, upper_bounds
    
    def validate_parameters(self, params: Dict[str, float], 
                          market_chars: MarketCharacteristics) -> Dict[str, Any]:
        """パラメータの物理的・統計的妥当性検証"""
        
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'violations': [],
            'quality_score': 1.0
        }
        
        # 基本物理制約
        if params['tc'] <= 1.0:
            validation_result['violations'].append("tc must be > 1.0 (critical time after observation period)")
            validation_result['is_valid'] = False
        
        if not (0.05 <= params['beta'] <= 1.0):
            validation_result['violations'].append(f"beta={params['beta']:.3f} outside physical range [0.05, 1.0]")
            validation_result['is_valid'] = False
        
        if params['omega'] <= 0:
            validation_result['violations'].append("omega must be positive (angular frequency)")
            validation_result['is_valid'] = False
        
        # 理論値との比較
        if not (0.2 <= params['beta'] <= 0.8):
            validation_result['warnings'].append(f"beta={params['beta']:.3f} outside typical range [0.2, 0.8]")
            validation_result['quality_score'] *= 0.9
        
        if not (3.0 <= params['omega'] <= 15.0):
            validation_result['warnings'].append(f"omega={params['omega']:.2f} outside typical range [3.0, 15.0]")
            validation_result['quality_score'] *= 0.9
        
        # 論文典型値との近似度評価
        paper_beta = 0.33
        paper_omega = 6.36
        
        beta_deviation = abs(params['beta'] - paper_beta) / paper_beta
        omega_deviation = abs(params['omega'] - paper_omega) / paper_omega
        
        if beta_deviation < 0.1:
            validation_result['quality_score'] *= 1.1  # ボーナス
        elif beta_deviation > 0.5:
            validation_result['quality_score'] *= 0.8  # ペナルティ
        
        if omega_deviation < 0.2:
            validation_result['quality_score'] *= 1.1  # ボーナス
        elif omega_deviation > 0.8:
            validation_result['quality_score'] *= 0.8  # ペナルティ
        
        validation_result['quality_score'] = min(1.0, validation_result['quality_score'])
        
        return validation_result
    
    def suggest_fallback_strategy(self, current_strategy: FittingStrategy, 
                                 failure_reasons: List[str]) -> Optional[FittingStrategy]:
        """フィッティング失敗時のフォールバック戦略提案"""
        
        fallback_map = {
            FittingStrategy.CONSERVATIVE: FittingStrategy.EXTENSIVE,
            FittingStrategy.EXTENSIVE: FittingStrategy.EMERGENCY,
            FittingStrategy.EMERGENCY: None  # 最後の手段
        }
        
        # 失敗理由に基づく調整
        if "CONVERGENCE_FAILURE" in failure_reasons and current_strategy != FittingStrategy.EMERGENCY:
            return FittingStrategy.EMERGENCY
        
        if "POOR_FIT_QUALITY" in failure_reasons and current_strategy == FittingStrategy.CONSERVATIVE:
            return FittingStrategy.EXTENSIVE
        
        return fallback_map.get(current_strategy)
    
    def record_fitting_result(self, param_set: Dict[str, Any], 
                            result: Dict[str, Any], success: bool):
        """フィッティング結果の記録（学習用）"""
        
        record = {
            'timestamp': datetime.now(),
            'market_characteristics': param_set['market_characteristics'],
            'strategy': param_set['strategy'],
            'success': success,
            'result_quality': result.get('r_squared', 0.0) if success else 0.0,
            'parameters': result.get('parameters', {}) if success else {},
            'convergence_time': result.get('convergence_time', 0.0)
        }
        
        self.history.append(record)
        
        # 履歴サイズ制限
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
    
    def get_success_statistics(self, bubble_type: BubbleType = None, 
                             strategy: FittingStrategy = None) -> Dict[str, float]:
        """成功統計の取得"""
        
        filtered_history = self.history
        
        if bubble_type:
            filtered_history = [r for r in filtered_history 
                              if r['market_characteristics'].bubble_type == bubble_type]
        
        if strategy:
            filtered_history = [r for r in filtered_history if r['strategy'] == strategy]
        
        if not filtered_history:
            return {'success_rate': 0.0, 'avg_quality': 0.0, 'total_attempts': 0}
        
        successful = [r for r in filtered_history if r['success']]
        
        return {
            'success_rate': len(successful) / len(filtered_history),
            'avg_quality': np.mean([r['result_quality'] for r in successful]) if successful else 0.0,
            'total_attempts': len(filtered_history),
            'avg_convergence_time': np.mean([r['convergence_time'] for r in successful]) if successful else 0.0
        }
    
    def export_configuration(self, filepath: str):
        """設定のエクスポート"""
        config = {
            'fixed_params': self.fixed_params,
            'core_ranges': {k: {'min': v.min_val, 'max': v.max_val, 'center': v.preferred_center}
                           for k, v in self.core_ranges.items()},
            'extended_ranges': {k: {'min': v.min_val, 'max': v.max_val, 'center': v.preferred_center}
                              for k, v in self.extended_ranges.items()},
            'maximum_ranges': {k: {'min': v.min_val, 'max': v.max_val, 'center': v.preferred_center}
                             for k, v in self.maximum_ranges.items()},
            'strategies': self.strategies,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

# 使用例とテスト
def example_usage():
    """使用例の実演"""
    
    # パラメータマネージャーの初期化
    manager = AdaptiveParameterManager()
    
    # 市場特性の定義（2000年ドットコムバブル風）
    dotcom_market = MarketCharacteristics(
        data_period_days=1310,
        volatility=0.22,
        bubble_magnitude=5.787,  # +578.7%
        bubble_type=BubbleType.TECH_BUBBLE,
        data_quality_score=1.0
    )
    
    # 保守的戦略でパラメータセット取得
    conservative_params = manager.get_parameters_for_market(
        dotcom_market, FittingStrategy.CONSERVATIVE
    )
    
    print("🎯 2000年ドットコムバブル向けパラメータセット (保守的)")
    print(f"   tc範囲: [{conservative_params['ranges']['tc'].min_val:.3f}, {conservative_params['ranges']['tc'].max_val:.3f}]")
    print(f"   beta範囲: [{conservative_params['ranges']['beta'].min_val:.3f}, {conservative_params['ranges']['beta'].max_val:.3f}]")
    print(f"   omega範囲: [{conservative_params['ranges']['omega'].min_val:.3f}, {conservative_params['ranges']['omega'].max_val:.3f}]")
    print(f"   試行回数: {conservative_params['trials']}")
    
    # 模擬データでの初期値生成
    sample_data = np.exp(np.linspace(6.6, 8.5, 1310))  # 指数的成長データ
    initial_values = manager.generate_initial_values(conservative_params, sample_data)
    
    print(f"\n📊 初期値生成完了: {len(initial_values)}セット")
    print("   最初の3セット:")
    for i, iv in enumerate(initial_values[:3]):
        print(f"   {i+1}: tc={iv['tc']:.3f}, beta={iv['beta']:.3f}, omega={iv['omega']:.2f}")

if __name__ == "__main__":
    example_usage()