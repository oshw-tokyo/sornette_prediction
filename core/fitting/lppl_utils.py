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
    **生の価格データ**を正規化時間 [0, 1] で準備

    ⚠️ IMPORTANT: この関数は**生の価格データ（対数変換前）**を想定しています

    【時間正規化の科学的根拠】
    - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:28
    - 時間範囲: t ∈ [0, 1]（データ長に依存しない統一スケール）
    - tc未来保証: tc > 1.0 で未来予測
    - 実績: 1987年ブラックマンデー 100/100スコア達成

    Args:
        prices: **生の価格データ**（対数変換前、任意長）

    Returns:
        t: 正規化時間 [0, 1]
        log_prices_normalized: 正規化対数価格（初期値を0に調整）

    【使用例】
    ```python
    # APIから取得した生データを解析
    raw_prices = get_prices_from_api()
    t, log_prices_norm = prepare_normalized_data(raw_prices)
    ```

    ⚠️ 時間正規化 [0, 1] は過去実装の成功の鍵。むやみに変更しないこと。
    """
    # 時間正規化 [0, 1]
    t = np.linspace(0, 1, len(prices))

    # 対数変換（生データ → ログスケール）
    log_prices = np.log(prices)

    # 初期値を0に正規化（フィッティング安定性向上）
    log_prices_normalized = log_prices - log_prices[0]

    return t, log_prices_normalized


def prepare_normalized_data_from_log_prices(
    log_prices: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    **ログスケール済み価格データ**を正規化時間 [0, 1] で準備

    ✅ IMPORTANT: この関数は**対数変換済みデータ**を想定しています
    データベースの`log_close`カラムから読み込んだデータを直接使用します。

    【使用シーン】
    - データベースから`log_close`を読み込んだ場合
    - 事前にnp.log()変換済みのデータを使用する場合
    - 重複する対数変換を回避する最適化（高速化）

    【注意】
    生の価格データには使用しないでください。
    生データの場合は `prepare_normalized_data()` を使用してください。

    Args:
        log_prices: **対数変換済み**の価格データ（np.log(prices)済み、任意長）

    Returns:
        t: 正規化時間 [0, 1]
        log_prices_normalized: 正規化対数価格（初期値を0に調整）

    【データフロー例】
    ```python
    # データベースからログスケールデータを読み込み
    df = pd.read_sql("SELECT log_close FROM market_price_data WHERE ...", conn)
    log_prices = df['log_close'].values  # ← 既に np.log() 済み

    # ログデータ専用関数で準備（np.log()スキップ、高速化）
    t, log_prices_norm = prepare_normalized_data_from_log_prices(log_prices)
    ```

    【科学的精度保証】
    以下の2つは**完全に等価**です（数値的に1bit単位で一致）:
    ```python
    # 方法1: 生データから変換（既存実装）
    t, log_norm1 = prepare_normalized_data(raw_prices)

    # 方法2: ログデータ直接利用（新実装、最適化版）
    log_prices = np.log(raw_prices)
    t, log_norm2 = prepare_normalized_data_from_log_prices(log_prices)

    # 結果: log_norm1 == log_norm2 (完全一致)
    ```

    【時間正規化の科学的根拠】
    - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:28
    - 時間範囲: t ∈ [0, 1]（データ長に依存しない統一スケール）
    - tc未来保証: tc > 1.0 で未来予測
    - 実績: 1987年ブラックマンデー 100/100スコア達成

    ⚠️ 時間正規化 [0, 1] は過去実装の成功の鍵。むやみに変更しないこと。
    """
    # ⚠️ ASSERTION: ログスケールデータであることを実行時確認
    # 生データを誤って渡した場合のデバッグ用
    # （生データは通常 > 1.0、ログスケールは負の値も含む）
    if len(log_prices) > 0 and np.all(log_prices > 10.0):
        import warnings
        warnings.warn(
            "警告: 渡されたデータが生の価格データの可能性があります。\n"
            "ログスケールデータには prepare_normalized_data_from_log_prices() を、\n"
            "生データには prepare_normalized_data() を使用してください。",
            UserWarning
        )

    # 時間正規化 [0, 1]
    t = np.linspace(0, 1, len(log_prices))

    # ⚠️⚠️⚠️ CRITICAL: 対数変換はスキップ（既にlog変換済み） ⚠️⚠️⚠️
    # log_prices = np.log(prices)  ← これを実行しない（高速化のポイント）

    # 初期値を0に正規化（フィッティング安定性向上）
    log_prices_normalized = log_prices - log_prices[0]

    return t, log_prices_normalized
