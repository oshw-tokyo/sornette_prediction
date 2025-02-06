# src/config/validation_settings.py

from typing import Dict

VALIDATION_SETTINGS = {
    'default': {
        'validation_cutoff_days': 30,  # デフォルトは90日前まで
        'minimum_data_points': 100,    # 最小必要データ点数
        'maximum_data_points': 1000    # 最大データ点数
    },
    'crash_1987': {
        'validation_cutoff_days': 180,
        'minimum_data_points': 200,
        'maximum_data_points': 1000
    }
    # 他のケース固有の設定を追加可能
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