from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class BaseFittingParameters:
    """基本的なフィッティングパラメータ（最も緩い制約）"""
    Z_MIN: float = 0.0
    Z_MAX: float = 1.0
    OMEGA_MIN: float = 0.0
    OMEGA_MAX: float = 20.0
    
    MAX_RESIDUAL: float = 1.0
    MIN_R_SQUARED: float = 0.90

@dataclass
class ParameterSet:
    """特定の状況に応じたパラメータセット"""
    name: str
    z_range: tuple[float, float]
    omega_range: tuple[float, float]
    description: str
    source: str  # 論文の参照など



class FittingParameterManager:
    """フィッティングパラメータの管理クラス"""
    def __init__(self):
        self.base_params = BaseFittingParameters()
        self.parameter_sets = {
            'default': ParameterSet(
                name='default',
                z_range=(0.33, 0.68),
                omega_range=(5.0, 8.0),
                description='Default parameter set based on general observations',
                source='Multiple studies'
            ),
            'crash_1987': ParameterSet(
                name='crash_1987',
                z_range=(0.30, 0.36),
                omega_range=(7.2, 7.6),
                description='Parameters for 1987 crash analysis',
                source='Sornette et al. 1996'
            ),
            'crash_1929': ParameterSet(
                name='crash_1929',
                z_range=(0.42, 0.48),
                omega_range=(7.7, 8.1),
                description='Parameters for 1929 crash analysis',
                source='Sornette et al. 1996'
            )
        }
        self.current_set = 'default'

    def set_parameter_set(self, set_name: str):
        """パラメータセットを切り替え"""
        if set_name in self.parameter_sets:
            self.current_set = set_name
        else:
            raise ValueError(f"Unknown parameter set: {set_name}")

    def get_current_parameters(self) -> Dict[str, tuple[float, float]]:
        """現在のパラメータセットを取得"""
        param_set = self.parameter_sets[self.current_set]
        return {
            'z_range': param_set.z_range,
            'omega_range': param_set.omega_range
        }

    def add_parameter_set(self, name: str, params: ParameterSet):
        """新しいパラメータセットを追加"""
        self.parameter_sets[name] = params

    def validate_parameters(self, z: float, omega: float) -> tuple[bool, Optional[str]]:
        """パラメータの検証（現在のセットに基づく）"""
        current_params = self.parameter_sets[self.current_set]
        z_min, z_max = current_params.z_range
        omega_min, omega_max = current_params.omega_range

        if not z_min <= z <= z_max:
            return False, f"z parameter {z} outside range ({z_min}, {z_max})"
        if not omega_min <= omega <= omega_max:
            return False, f"omega parameter {omega} outside range ({omega_min}, {omega_max})"
        return True, None