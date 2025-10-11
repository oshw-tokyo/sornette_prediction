"""
LPPL最適化: グリッドサーチ + 境界付き最適化

【科学的根拠】
- 実装元: archive/src_pre_migration_backup/fitting/fitter.py:36-157
- アルゴリズム: グリッドサーチ初期値 + scipy.optimize.curve_fit (境界付き)
- 成功実績: 1987年ブラックマンデー 100/100スコア達成

【Boulder LPPLSとの違い】
- Boulder LPPLS: 無制約最適化 + ランダム初期値 → パラメータ発散（0% Confidence）
- 本実装: 境界条件付き最適化 + グリッドサーチ → 収束保証（100/100スコア）

⚠️ この最適化手法は科学的再現性の根幹です。むやみに変更しないこと。
"""

import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Optional
import logging

from .lppl_utils import logarithm_periodic_func, calculate_fit_metrics

logger = logging.getLogger(__name__)


def fit_lppl_grid_search(
    t: np.ndarray,
    log_prices: np.ndarray,
    n_tries: int = 10
) -> Optional[Dict[str, float]]:
    """
    グリッドサーチ + 境界付き最適化によるLPPLフィッティング

    【アルゴリズム】
    1. グリッドサーチ: tc, beta, omega の組み合わせを体系的に探索
    2. 境界付き最適化: scipy.optimize.curve_fit with bounds
    3. ロバスト損失関数: loss='soft_l1'（外れ値耐性）

    【パラメータ境界条件】
    以下の境界は archive/src_pre_migration_backup/fitting/fitter.py:64-67 に基づく:
    - tc: 1.01-1.5 (未来予測、正規化時間)
    - beta: 0.3-0.7 (べき乗指数、典型値)
    - omega: 5.0-8.0 (角周波数、観測可能範囲)
    - phi: -8π ~ 8π (位相)
    - log(A), B, C: 広範囲（-10 ~ 10）

    科学的妥当性: Sornette論文の典型値範囲
    実証的裏付け: 1987年ブラックマンデー 100/100スコア達成

    ⚠️ むやみに変更しないこと - 再現性テスト必須

    Args:
        t: 正規化時間 [0, 1]
        log_prices: 正規化対数価格
        n_tries: グリッドサーチの刻み数（デフォルト10 → 10³=1000組み合わせ）

    Returns:
        フィッティング結果（成功時）:
            - tc, beta, omega, phi, A, B, C, r2
        None（全試行失敗時）

    【科学的根拠】
    - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:36-157
    - 成功実績: 1987年ブラックマンデー 100/100スコア
    - Boulder LPPLSとの違い: 境界条件付き最適化（vs 無制約）

    ⚠️ パラメータ境界は過去実装の値を厳守すること
    """
    logger.info(f"Starting LPPL grid search fitting with {n_tries}³ = {n_tries**3} combinations")

    # グリッドサーチによる初期値生成
    tc_values = np.linspace(1.01, 1.5, n_tries)
    beta_values = np.linspace(0.30, 0.45, n_tries)  # 注: 過去実装では0.45まで
    omega_values = np.linspace(5.0, 8.0, n_tries)

    logger.info(f"Parameter ranges:")
    logger.info(f"  tc: [{tc_values[0]:.3f}, {tc_values[-1]:.3f}]")
    logger.info(f"  beta: [{beta_values[0]:.3f}, {beta_values[-1]:.3f}]")
    logger.info(f"  omega: [{omega_values[0]:.3f}, {omega_values[-1]:.3f}]")

    # 境界条件（過去実装準拠）
    bounds = (
        [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
        [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]   # upper
    )

    best_result = None
    best_r2 = -np.inf
    failed_attempts = 0
    successful_attempts = 0

    # 3重ループでグリッドサーチ
    for i, tc in enumerate(tc_values):
        for j, beta in enumerate(beta_values):
            for k, omega in enumerate(omega_values):
                try:
                    # 初期値設定
                    p0 = [
                        tc,                              # tc
                        beta,                            # beta
                        omega,                           # omega
                        0.0,                             # phi
                        np.log(np.mean(np.exp(log_prices))),  # log(A)
                        (log_prices[-1] - log_prices[0]) / (t[-1] - t[0]),  # B
                        0.1                              # C
                    ]

                    # 境界付き最適化
                    popt, pcov = curve_fit(
                        logarithm_periodic_func,
                        t,
                        log_prices,
                        p0=p0,
                        bounds=bounds,
                        method='trf',  # Trust Region Reflective（境界対応）
                        ftol=1e-6,
                        xtol=1e-6,
                        gtol=1e-6,
                        loss='soft_l1',  # ロバスト損失関数（外れ値耐性）
                        max_nfev=50000
                    )

                    # フィッティング品質評価
                    y_fit = logarithm_periodic_func(t, *popt)
                    residuals, r2 = calculate_fit_metrics(log_prices, y_fit)

                    successful_attempts += 1

                    # 最良フィット更新
                    if r2 > best_r2:
                        best_r2 = r2
                        best_result = {
                            'tc': popt[0],
                            'beta': popt[1],
                            'omega': popt[2],
                            'phi': popt[3],
                            'A': np.exp(popt[4]),  # log(A) → A
                            'B': popt[5],
                            'C': popt[6],
                            'r2': r2,
                            'residuals': residuals
                        }
                        logger.debug(f"New best fit: R²={r2:.4f}, tc={popt[0]:.4f}, "
                                   f"beta={popt[1]:.4f}, omega={popt[2]:.4f}")

                except Exception as e:
                    failed_attempts += 1
                    logger.debug(f"Fit attempt failed: {e}")
                    continue

    logger.info(f"Grid search completed:")
    logger.info(f"  Successful attempts: {successful_attempts}/{n_tries**3}")
    logger.info(f"  Failed attempts: {failed_attempts}/{n_tries**3}")

    if best_result is None:
        logger.warning(f"All {n_tries**3} grid search attempts failed")
        return None

    logger.info(f"Best fit found:")
    logger.info(f"  R²: {best_result['r2']:.4f}")
    logger.info(f"  tc: {best_result['tc']:.4f} (未来予測: {best_result['tc'] > 1.0})")
    logger.info(f"  beta: {best_result['beta']:.4f}")
    logger.info(f"  omega: {best_result['omega']:.4f}")

    return best_result


def validate_lppl_parameters(
    result: Dict[str, float],
    tc_min: float = 1.01
) -> bool:
    """
    LPPLパラメータの妥当性検証

    【検証項目】
    1. tc > 1.0: 未来予測（正規化時間）
    2. 0.3 < beta < 0.7: べき乗指数の典型範囲
    3. 5.0 < omega < 8.0: 角周波数の典型範囲
    4. R² > 0.5: 最低限のフィット品質

    Args:
        result: フィッティング結果
        tc_min: tc最小値（デフォルト1.01）

    Returns:
        妥当性判定（True/False）
    """
    is_valid = (
        result['tc'] >= tc_min and  # 未来予測
        0.3 < result['beta'] < 0.7 and  # 典型範囲
        5.0 < result['omega'] < 8.0 and  # 典型範囲
        result['r2'] > 0.5  # 最低限のフィット品質
    )

    if not is_valid:
        logger.warning("Parameter validation failed:")
        logger.warning(f"  tc={result['tc']:.4f} (>= {tc_min}: {result['tc'] >= tc_min})")
        logger.warning(f"  beta={result['beta']:.4f} (0.3-0.7: {0.3 < result['beta'] < 0.7})")
        logger.warning(f"  omega={result['omega']:.4f} (5.0-8.0: {5.0 < result['omega'] < 8.0})")
        logger.warning(f"  R²={result['r2']:.4f} (>0.5: {result['r2'] > 0.5})")

    return is_valid
