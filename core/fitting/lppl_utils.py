"""
LPPL (Log-Periodic Power Law) 数式・ユーティリティ関数

【科学的根拠】
- 理論: Sornette (2003) "Why Stock Markets Crash", 式(54)
- 実装元: archive/src_pre_migration_backup/fitting/utils.py
- 実証実績: 1987年ブラックマンデー 100/100スコア達成

⚠️ この数式は科学的再現性の根幹です。むやみに変更しないこと。
変更時は必ず再現性テスト実施。
"""

import numpy as np
from typing import Tuple


def logarithm_periodic_func(
    t: np.ndarray,
    tc: float,
    beta: float,
    omega: float,
    phi: float,
    log_A: float,
    B: float,
    C: float
) -> np.ndarray:
    """
    Sornette論文式(54): LPPL数式

    log(p(t)) = A + B*(tc-t)^β + C*(tc-t)^β*cos(ω*log(tc-t) + φ)

    【時間単位の定義】
    - t: 正規化時間 [0, 1]
    - tc: 臨界時刻（tc > 1.0で未来予測）

    Args:
        t: 正規化時間 [0, 1]
        tc: 臨界時刻（tc > 1.0で未来予測）
        beta (β): べき乗指数 (典型値: 0.3-0.7)
        omega (ω): 角周波数 (典型値: 5.0-8.0)
        phi (φ): 位相 (-8π ~ 8π)
        log_A: オフセット（対数）
        B: 振幅パラメータ
        C: 振幅パラメータ

    Returns:
        log_prices: 対数価格（正規化済み）

    【科学的根拠】
    - 出典: "Why Stock Markets Crash" (Sornette, 2003), 式(54)
    - 実装元: archive/src_pre_migration_backup/fitting/utils.py
    - 実績: 1987年ブラックマンデー 100/100スコア達成

    ⚠️ この数式は科学的再現性の根幹です。むやみに変更しないこと。
    """
    dt = tc - t

    # tc <= t の場合は無限大を返す（フィッティング失敗として扱う）
    if np.any(dt <= 0):
        return np.full_like(t, np.inf, dtype=float)

    # べき乗項
    power_law_term = np.power(dt, beta)

    # 対数周期振動項
    log_dt = np.log(dt)
    oscillation_term = np.cos(omega * log_dt + phi)

    # LPPL式
    # log(price_normalized) = log(A) + B*(tc-t)^β + C*(tc-t)^β*cos(ω*log(tc-t) + φ)
    # 注意: log_A = log(A) として渡されている
    result = log_A + B * power_law_term + C * power_law_term * oscillation_term

    return result


def calculate_fit_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> Tuple[float, float]:
    """
    フィッティング品質指標の計算

    Args:
        y_true: 実測値（対数価格）
        y_pred: 予測値（対数価格）

    Returns:
        residuals: 残差二乗和
        r_squared: 決定係数 R²

    【R²の意味】
    - R² ∈ [0, 1]: フィット品質（1に近いほど良好）
    - R² < 0.5: 不適格
    - R² > 0.9: 優秀（1987年ブラックマンデー達成レベル）
    """
    # 残差二乗和
    residuals = np.sum((y_true - y_pred) ** 2)

    # 全変動
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

    # R²計算
    if ss_tot == 0:
        r_squared = 0.0
    else:
        r_squared = 1.0 - (residuals / ss_tot)

    return residuals, r_squared


def prepare_normalized_data(
    prices: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    価格データを正規化時間 [0, 1] で準備

    【時間正規化の科学的根拠】
    - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:28
    - 時間範囲: t ∈ [0, 1]（データ長に依存しない統一スケール）
    - tc未来保証: tc > 1.0 で未来予測
    - 実績: 1987年ブラックマンデー 100/100スコア達成

    Args:
        prices: 生の価格データ（任意長）

    Returns:
        t: 正規化時間 [0, 1]
        log_prices_normalized: 正規化対数価格（初期値を0に調整）

    ⚠️ 時間正規化 [0, 1] は過去実装の成功の鍵。むやみに変更しないこと。
    """
    # 時間正規化 [0, 1]
    t = np.linspace(0, 1, len(prices))

    # 対数変換
    log_prices = np.log(prices)

    # 初期値を0に正規化（フィッティング安定性向上）
    log_prices_normalized = log_prices - log_prices[0]

    return t, log_prices_normalized
