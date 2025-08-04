# src/config/validation_settings.py

from typing import Dict

VALIDATION_SETTINGS = {
    '1987-10': {
        'validation_cutoff_days': 101,  # クラッシュに近すぎると(tc-t が 0 に近づくと)、フィッティングが発散する
        'minimum_data_points': 200,
        'maximum_data_points': 1000,
        'beta_expected': 0.33,  # 1987年クラッシュの期待されるパラメータ値
        'omega_expected': 7.4,
        'beta_tolerance': 0.03,  # 許容誤差
        'omega_tolerance': 0.2
    },
    'default': {
        'validation_cutoff_days': 30,
        'minimum_data_points': 100,
        'maximum_data_points': 1000,
        'beta_tolerance': 0.05,
        'omega_tolerance': 0.5
    }
}

def get_validation_settings(crash_id: str) -> Dict:
    """
    クラッシュケース固有の検証設定を取得

    Parameters:
    -----------
    crash_id : str
        クラッシュのID (例: 'crash_1987')

    Returns:
    --------
    Dict
        検証設定の辞書
    """
    return VALIDATION_SETTINGS.get(crash_id, VALIDATION_SETTINGS['default'])