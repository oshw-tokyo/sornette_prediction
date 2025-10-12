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
import pandas as pd
from typing import Tuple, Union, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def logarithm_periodic_func(
    t: np.ndarray,
    tc: float,
    beta: float,
    omega: float,
    phi: float,
    A: float,
    B: float,
    C: float
) -> np.ndarray:
    """
    Sornette論文式(54): LPPL数式 (過去実装完全準拠)

    log(p(t)) = A + B*(tc-t)^β + C*(tc-t)^β*cos(ω*log(tc-t) + φ)

    【時間単位の定義】
    - t: 正規化時間 [0, 1]
    - tc: 臨界時刻（tc > 1.0で未来予測）

    【重要】パラメータAについて
    対数価格データ（log-transformed price）に対してフィッティングする場合、
    Aは対数空間のオフセットとして直接使用されます。
    これは過去実装（archive/src_pre_migration_backup/fitting/utils.py）と完全に一致します。

    Args:
        t: 正規化時間 [0, 1]
        tc: 臨界時刻（tc > 1.0で未来予測）
        beta (β): べき乗指数 (典型値: 0.3-0.7)
        omega (ω): 角周波数 (典型値: 5.0-8.0)
        phi (φ): 位相 (-8π ~ 8π)
        A: オフセット（対数価格空間）
        B: 振幅パラメータ
        C: 振幅パラメータ

    Returns:
        log_prices: 対数価格（正規化済み）

    【科学的根拠】
    - 出典: "Why Stock Markets Crash" (Sornette, 2003), 式(54)
    - 実装元: archive/src_pre_migration_backup/fitting/utils.py Line 22-69
    - 実績: 1987年ブラックマンデー 100/100スコア達成

    ⚠️ この数式は科学的再現性の根幹です。むやみに変更しないこと。
    """
    t = np.asarray(t).ravel()
    dt = (tc - t).ravel()
    mask = dt > 0
    result = np.zeros_like(t, dtype=float)

    valid_dt = dt[mask]
    if len(valid_dt) > 0:
        # べき乗項
        power_term = np.power(valid_dt, beta).ravel()

        # 対数周期振動項
        log_term = np.log(valid_dt).ravel()
        cos_term = np.cos(omega * log_term + phi).ravel()
        oscillation = (C * power_term * cos_term).ravel()

        # LPPL式（過去実装と完全一致）
        base = (A + B * power_term).ravel()
        result[mask] = (base + oscillation).ravel()

    return result.ravel()


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


def convert_tc_to_date(
    tc: float,
    first_date: Union[datetime, pd.Timestamp, str],
    last_date: Union[datetime, pd.Timestamp, str],
    include_time: bool = True
) -> Optional[datetime]:
    """
    tc値から予測日時を計算（フィッティング期間考慮版）

    【アルゴリズム】
    - 時間正規化: t ∈ [0, 1]
      - t=0: first_date (フィッティング開始日)
      - t=1: last_date (フィッティング終了日)
    - tc > 1.0: 未来予測
    - tcの暦日換算: (tc - 1.0) × フィッティング期間の暦日数

    【修正内容 (Issue I128)】
    ❌ 修正前: days_beyond = (tc - 1.0) * 365  # 固定値
    ✅ 修正後: days_beyond = (tc - 1.0) * fitting_period_calendar_days

    【科学的根拠】
    - LPPL時間正規化に基づく変換
    - tcは正規化時間 [0, 1] を基準とする
    - フィッティング期間を正しく反映する必要がある
    - 窓サイズが異なる場合、同じtc値でも異なる予測日になる

    【検証結果（2025-10-12）】
    | 窓サイズ | フィッティング期間 | 実際の暦日数 | tc値 | 修正前（365日固定） | 修正後（期間考慮） | 誤差改善 |
    |---------|-----------------|------------|------|------------------|----------------|----------|
    | 750営業日 | 2021-10-19 ~ 2024-10-19 | 1096日 | 1.2 | 2024-12-31 | 2025-05-26 | 147日 |
    | 125営業日 | 2024-04-19 ~ 2024-10-19 | 183日 | 1.2 | 2024-12-31 | 2024-11-24 | 36日 |
    | 1987年 | 1983-11-03 ~ 1987-10-19 | 1446日 | 1.2128 | 1988-01-04 | 1988-08-21 | 231日 |

    Args:
        tc: 正規化tc値（tc > 1.0で未来予測）
        first_date: フィッティング期間の開始日
        last_date: フィッティング期間の終了日
        include_time: 時間精度まで含めるか（デフォルト: True）

    Returns:
        予測日時（tc <= 1.0の場合はNone）

    Examples:
        >>> # 750営業日窓（2021-10-19 ~ 2024-10-19, 1096暦日）
        >>> convert_tc_to_date(1.2, '2021-10-19', '2024-10-19')
        datetime.datetime(2025, 5, 26, ...)

        >>> # 125営業日窓（2024-04-19 ~ 2024-10-19, 183暦日）
        >>> convert_tc_to_date(1.2, '2024-04-19', '2024-10-19')
        datetime.datetime(2024, 11, 24, ...)

    Scientific Basis:
        LPPL時間正規化に基づく変換
        実装元: workspace_for_claude/verify_tc_conversion_problem.py:correct_tc_conversion()
        Issue: I128
        実装日: 2025-10-12
    """
    # 日付型への変換
    if isinstance(first_date, str):
        first_date = pd.to_datetime(first_date)
    if isinstance(last_date, str):
        last_date = pd.to_datetime(last_date)

    # pandas.Timestamp → datetime 変換
    if hasattr(first_date, 'to_pydatetime'):
        first_date = first_date.to_pydatetime()
    if hasattr(last_date, 'to_pydatetime'):
        last_date = last_date.to_pydatetime()

    # tc <= 1.0 は過去（通常は使用されない）
    if tc <= 1.0:
        logger.warning(f"tc={tc:.4f} <= 1.0 (not a future prediction)")
        return None

    # フィッティング期間の実際の暦日数
    fitting_period_calendar_days = (last_date - first_date).days

    # tcが正規化時間を超えた分を暦日に変換
    # tc=1.0 が last_date に対応
    # tc=2.0 が last_date + fitting_period_calendar_days に対応
    days_beyond = (tc - 1.0) * fitting_period_calendar_days

    if include_time:
        # 日数と時間に分離（時間精度対応）
        full_days = int(days_beyond)
        fractional_day = days_beyond - full_days
        hours = fractional_day * 24

        # 時間精度まで含めた予測日時を計算
        predicted_datetime = last_date + timedelta(days=full_days, hours=hours)
    else:
        # 日付のみ
        predicted_datetime = last_date + timedelta(days=days_beyond)

    return predicted_datetime
