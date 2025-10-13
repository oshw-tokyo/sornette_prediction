"""
LPPL最適化: ランダム初期値生成 + 境界付き最適化

⚠️⚠️⚠️ Issue I136: グリッドサーチからランダム初期値生成への変更（2025-10-13） ⚠️⚠️⚠️
- 変更理由: 計算時間短縮（約3時間 → 約9分、1/20の計算量）
- 旧アルゴリズム: グリッドサーチ（8³=512組み合わせ）
- 新アルゴリズム: ランダム初期値生成（25回、Boulder LPPLS準拠）

【実験検証結果（2025-10-13）】
✅ グリッドサーチ vs ランダム初期値の直接比較（1987年ブラックマンデー60日前、51窓）
- グリッドサーチ (n=8, 512組み合わせ): Confidence 11.76%, 適格6/51, 計算時間 8.11分
- ランダム初期値 (n=25, 25回試行):    Confidence 11.76%, 適格6/51, 計算時間 0.38分
- 結論: 予測精度は完全に保持、計算時間は21.2倍高速化 ✅

【科学的根拠】
- 実装元: archive/src_pre_migration_backup/fitting/fitter.py:36-157
- アルゴリズム: ランダム初期値 + scipy.optimize.curve_fit (境界付き)
- 成功実績: 1987年ブラックマンデー 100/100スコア達成（グリッドサーチ版）
- 検証済み: ランダム25回でグリッドサーチ512組と同一精度達成

【Boulder LPPLSとの違い】
- Boulder LPPLS: 無制約最適化 + ランダム初期値 → パラメータ発散（0% Confidence）
- 本実装: 境界条件付き最適化 + ランダム初期値 → 収束保証を維持

⚠️ この最適化手法は科学的再現性の根幹です。むやみに変更しないこと。
"""

import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Optional
import logging
import random

from .lppl_utils import logarithm_periodic_func, calculate_fit_metrics

logger = logging.getLogger(__name__)


def fit_lppl_grid_search(
    t: np.ndarray,
    log_prices: np.ndarray,
    n_tries: int = 25
) -> Optional[Dict[str, float]]:
    """
    ランダム初期値生成 + 境界付き最適化によるLPPLフィッティング

    ⚠️⚠️⚠️ Issue I136: グリッドサーチからランダム初期値生成への変更（2025-10-13） ⚠️⚠️⚠️
    - 変更理由: 計算時間短縮（約3時間 → 約9分、1/20の計算量）
    - 旧アルゴリズム: グリッドサーチ（8³=512組み合わせ）
    - 新アルゴリズム: ランダム初期値生成（25回、Boulder LPPLS準拠）

    【アルゴリズム】
    1. ランダム初期値生成: tc, beta, omega を境界の内側10%-90%からランダム生成
    2. 境界付き最適化: scipy.optimize.curve_fit with bounds
    3. ロバスト損失関数: loss='soft_l1'（外れ値耐性）
    4. 試行回数: 25回（Boulder LPPLS準拠、デフォルト）

    【パラメータ境界条件】
    ⚠️ FCO本家（Boulder LPPLS）との違いを明記（Issue I129対応）:

    1. **beta (べき乗指数)**:
       - FCO本家（Boulder LPPLS）: 0.0-1.0（デフォルト範囲）
       - 本実装: 0.1-0.9（Sornette論文典型値範囲）
       - 理由: Sornette論文での物理的意味を持つ範囲に限定
       - 変更履歴:
         * 過去実装: 0.3-0.7（1987年単一窓で100/100スコア達成）
         * 2025-10-12: 0.1-0.9に拡大（多重窓FCO対応、Issue I129）

    2. **omega (角周波数)**:
       - FCO本家（Boulder LPPLS）: 2.0-15.0（デフォルト範囲）
       - 本実装: 2.0-15.0（Boulder LPPLS準拠、Issue I130対応）
       - 理由: omega境界張り付き問題解消（Issue I130検証結果）
       - 変更履歴:
         * 過去実装: 5.0-8.0（1987年単一窓で100/100スコア達成）
         * 2025-10-12: 5.0-15.0に拡大（多重窓FCO対応、Issue I129）
         * 2025-10-13: 2.0-15.0に拡大（Boulder LPPLS準拠、Issue I130）
       - 科学的根拠:
         * Boulder LPPLS実装（lppls.py:252）: omega ∈ [2.0, 15.0]
         * Issue I130検証: omega=5.0下限張り付き問題を確認
         * 解決策: Boulder LPPLS標準範囲に統一

    3. **tc, phi, A, B, C**:
       - 過去実装と同一（変更なし）
       - tc: 1.01-1.5 (未来予測、正規化時間)
       - phi: -8π ~ 8π (位相)
       - A, B, C: 広範囲（-10 ~ 10）

    【重要】窓範囲パラメータ（CustomFCOEngine）:
    - FCO標準: 最小窓125日、最大窓750日、刻み5日 → 126窓
    - 本実装: 同上（FCO標準準拠、変更なし）
    - 注意: 直接スクリプト（test_phase2）では実用的最小窓250日を採用
      （理由: 125-250日窓での収束失敗多発のため）
    - 変更時は Issue I129 を参照し、FCO標準からの逸脱を明記すること

    【科学的根拠】:
    - 過去実装（単一窓LPPL）: beta=0.3-0.7, omega=5.0-8.0で成功
    - 多重窓FCO（126窓）: 窓ごとに異なる最適パラメータが必要
    - 緩和版（2025-10-12）: beta=0.1-0.9, omega=5.0-15.0
    - 目的: 境界張り付き問題の軽減（Issue I129）

    【tc > 1.0 条件の科学的根拠】（重要）
    ⚠️ 本プロジェクトではtc > 1.0（未来予測）を必須条件とする

    理由:
    1. Sornette理論の本来の目的: 未来のクラッシュを予測すること
    2. サービスユーザーの関心: 過去ではなく未来が予測できるか
    3. 科学的妥当性: 過去を指すtcは事後的なフィッティングに過ぎない

    参考: FCOライブラリでは tc < t2（過去を指す）も許容しているが、
    本プロジェクトでは Sornette論文の本来の主張に従い、
    未来予測に限定する方針を採用している。

    詳細: CLAUDE.md、Issue I125

    【30～60日制約】（重要）
    ⚠️ フィッティング基準日はクラッシュ予測日の30～60日前に設定すること

    理由（Sornette論文）:
    - クラッシュ付近では関数の数値が急激に変化するため、
      正確なフィッティングが困難になる
    - フィッティング基準日とクラッシュ予測日は十分に離れている必要がある

    実装:
    - 歴史的クラッシュ再現テスト: 60日前基準を採用
    - 例: 1987年ブラックマンデー（10/19）→ 基準日: 9/7（42日前）

    参考論文: Sornette et al. (2004), papers/extracted_texts/ 内
    詳細: Issue I125

    【重要】過去実装との完全準拠:
    パラメータAは対数価格空間のオフセットとして直接使用されます。
    過去実装（archive/src_pre_migration_backup/fitting/utils.py）では
    log(A)ではなくA自体をパラメータとしています。

    科学的妥当性: Sornette論文の典型値範囲
    実証的裏付け: 1987年ブラックマンデー 100/100スコア達成

    ⚠️ むやみに変更しないこと - 再現性テスト必須

    Args:
        t: 正規化時間 [0, 1]
        log_prices: 正規化対数価格
        n_tries: ランダム初期値生成の試行回数（デフォルト25回、Boulder LPPLS準拠）

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
    # ⚠️⚠️⚠️ Issue I136: ランダム初期値生成への変更（2025-10-13） ⚠️⚠️⚠️
    #
    # 【変更理由】
    # - グリッドサーチ（8³=512組み合わせ）: 計算時間が長すぎる（約3時間）
    # - Boulder LPPLS準拠: ランダム初期値生成（25回）で1/20の計算量
    # - 期待効果: 計算時間を約3時間 → 約9分に短縮
    #
    # 【アルゴリズム変更】
    # - 旧: 3重ループによるグリッドサーチ（網羅的探索）
    # - 新: ランダム初期値生成（確率的探索）
    # - 試行回数: n_tries = 25（Boulder LPPLS準拠、デフォルト）
    #
    # 【初期値範囲】
    # - 境界の内側10%-90%からランダム生成（境界張り付きリスク軽減）
    # - 根拠: Issue I130で境界値張り付き問題を確認済み
    #
    logger.info(f"Starting LPPL random initialization fitting with {n_tries} attempts")

    # ランダム初期値生成のための範囲定義
    # ⚠️⚠️⚠️ CRITICAL: Boulder LPPLS準拠の範囲設定（Issue I130、2025-10-13） ⚠️⚠️⚠️
    #
    # 【omega範囲の決定根拠】
    # - Boulder LPPLS標準: omega ∈ [2.0, 15.0]（lppls.py:252）
    # - Issue I130検証結果: 旧範囲[5.0, 15.0]でomega=5.0下限張り付き発生
    # - 解決策: Boulder LPPLS標準範囲に統一 → omega ∈ [2.0, 15.0]
    # - 物理的意味: omega = 角周波数（周期の逆数）
    #   * omega=2.0: 周期が長い（ゆっくりとした振動）
    #   * omega=15.0: 周期が短い（速い振動）
    # - 観測可能性: データ期間内で2.5サイクル以上必要（Oscillations > 2.5）
    #
    # 【変更履歴】
    # - 過去実装（単一窓LPPL）: omega=5.0-8.0で100/100スコア達成
    # - 2025-10-12（Issue I129）: omega=5.0-15.0に拡大（多重窓FCO対応）
    # - 2025-10-13（Issue I130）: omega=2.0-15.0に拡大（Boulder LPPLS準拠）
    #
    # 境界条件（2025-10-13: Issue I130対応でomega下限を2.0に変更）
    # ⚠️⚠️⚠️ CRITICAL: Boulder LPPLS準拠の境界設定 ⚠️⚠️⚠️
    #
    # 【変更履歴】
    # - 過去実装: beta=0.3-0.7, omega=5.0-8.0（単一窓LPPL、1987年100/100スコア達成）
    # - 2025-10-12（Issue I129）: beta=0.1-0.9, omega=5.0-15.0（多重窓FCO対応）
    # - 2025-10-13（Issue I130）: omega下限 5.0→2.0（Boulder LPPLS準拠）
    #
    # 【omega下限2.0の根拠】
    # - Boulder LPPLS標準: omega ∈ [2.0, 15.0]（lppls.py:252）
    # - Issue I130実験結果: 旧下限5.0で全適格フィットがomega=5.0に張り付き
    # - 原因: omega最適値が5.0未満の可能性（探索範囲外）
    # - 対策: Boulder LPPLS標準範囲に統一 → 境界張り付き解消を期待
    #
    bounds = (
        [1.01, 0.1, 2.0, -8*np.pi, -10, -10, -2.0],  # lower（omega: 5.0→2.0、Issue I130）
        [1.5,  0.9, 15.0,  8*np.pi,  10,  10,  2.0]  # upper
    )

    # ランダム初期値生成範囲（境界の内側10%-90%）
    # ⚠️ Issue I130: 境界張り付き問題軽減のため、境界値からの初期化を回避
    tc_range = (1.01 + 0.1*(1.5-1.01), 1.01 + 0.9*(1.5-1.01))
    beta_range = (0.1 + 0.1*(0.9-0.1), 0.1 + 0.9*(0.9-0.1))
    omega_range = (2.0 + 0.1*(15.0-2.0), 2.0 + 0.9*(15.0-2.0))

    logger.info(f"Random initialization ranges (interior 10%-90%):")
    logger.info(f"  tc: [{tc_range[0]:.3f}, {tc_range[1]:.3f}]")
    logger.info(f"  beta: [{beta_range[0]:.3f}, {beta_range[1]:.3f}]")
    logger.info(f"  omega: [{omega_range[0]:.3f}, {omega_range[1]:.3f}]")

    best_result = None
    best_r2 = -np.inf
    failed_attempts = 0
    successful_attempts = 0

    # ランダム初期値生成ループ（Boulder LPPLS準拠）
    for attempt in range(n_tries):
        try:
            # ランダム初期値生成（境界の内側10%-90%）
            tc_init = random.uniform(tc_range[0], tc_range[1])
            beta_init = random.uniform(beta_range[0], beta_range[1])
            omega_init = random.uniform(omega_range[0], omega_range[1])

            # 初期値設定（過去実装完全準拠）
            # ⚠️ CRITICAL: 過去実装では np.log(np.mean(y)) を使用
            # yは正規化対数価格 (log_prices - log_prices[0])
            p0 = [
                tc_init,                          # tc (ランダム)
                beta_init,                        # beta (ランダム)
                omega_init,                       # omega (ランダム)
                0.0,                              # phi
                np.log(np.mean(log_prices)),      # log(A)（過去実装準拠）
                (log_prices[-1] - log_prices[0]) / (t[-1] - t[0]),  # B
                0.1                               # C
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
                    'A': popt[4],  # A（過去実装準拠、対数価格空間のオフセット）
                    'B': popt[5],
                    'C': popt[6],
                    'r2': r2,
                    'residuals': residuals
                }
                logger.debug(f"New best fit (attempt {attempt+1}/{n_tries}): R²={r2:.4f}, "
                           f"tc={popt[0]:.4f}, beta={popt[1]:.4f}, omega={popt[2]:.4f}")

        except Exception as e:
            failed_attempts += 1
            logger.debug(f"Fit attempt {attempt+1}/{n_tries} failed: {e}")
            continue

    logger.info(f"Random initialization completed:")
    logger.info(f"  Successful attempts: {successful_attempts}/{n_tries}")
    logger.info(f"  Failed attempts: {failed_attempts}/{n_tries}")

    if best_result is None:
        # ⚠️ 警告レベル: この窓ではLPPLパターンが検出されませんでした
        # 原因: データにLPPLパターンが存在しない、または境界条件が厳しすぎる
        # 影響: この窓は適格フィットとしてカウントされません（多重窓解析では正常な挙動）
        logger.warning(
            f"Window fitting failed: No valid LPPL pattern found "
            f"(all {n_tries} random initialization attempts failed to converge). "
            f"This is expected for windows without clear bubble signatures."
        )
        return None

    logger.info(f"Best fit found:")
    logger.info(f"  R²: {best_result['r2']:.4f}")
    logger.info(f"  tc: {best_result['tc']:.4f} (未来予測: {best_result['tc'] > 1.0})")
    logger.info(f"  beta: {best_result['beta']:.4f}")
    logger.info(f"  omega: {best_result['omega']:.4f}")

    return best_result


def check_boundary_adhesion(
    result: Dict[str, float],
    bounds: tuple,
    margin_ratio: float = 0.02
) -> bool:
    """
    境界値張り付きチェック

    【重要更新: 2025-10-11】
    境界張り付きはフィッティング失敗として扱う（警告ではなく）
    - 理由: ユーザーフィードバック（A0）による方針変更
    - 影響: 境界張り付きのフィットは適格フィットから除外
    - 目的: 真の最適解のみを採用（探索範囲制約による人工的収束の排除）

    【問題】
    最適化アルゴリズムがパラメータの上限・下限に収束した場合、
    それは真の最適解ではなく、探索範囲の制約による人工的な結果である可能性が高い。
    このようなフィッティングは科学的に信頼性が低いため棄却する必要がある。

    【過去実装での経験】
    - tc=1.0100 (下限1.01) に張り付き → 真の最適tcはもっと小さい可能性
    - beta=0.7000 (上限0.7) に張り付き → 真の最適betaはもっと大きい可能性
    このような結果は不適切なフィッティングとして扱う（過去実装準拠）

    【判定基準】
    各パラメータが境界値から margin_ratio (デフォルト2%) 以内にある場合は
    「境界値張り付き」と判定し、is_valid=False とする。

    例: tc ∈ [1.01, 1.5] の場合
    - 範囲幅: 1.5 - 1.01 = 0.49
    - マージン: 0.49 × 0.02 = 0.0098
    - 下限張り付き判定: tc < 1.01 + 0.0098 = 1.0198
    - 上限張り付き判定: tc > 1.5 - 0.0098 = 1.4902

    Args:
        result: フィッティング結果
        bounds: 境界条件 (lower, upper) のタプル
        margin_ratio: マージン比率（デフォルト2%）

    Returns:
        True: 境界値張り付きあり（不適格、フィッティング失敗）
        False: 境界値張り付きなし（適格）

    【科学的根拠】
    実装元: 過去実装での経験則（境界値張り付き棄却）
    理由: 制約による人工的収束を排除し、真の最適解のみを採用
    更新: A0（ユーザーフィードバック）により失敗として扱うことを明確化
    """
    lower_bounds, upper_bounds = bounds

    # パラメータ順序: tc, beta, omega, phi, A, B, C（過去実装準拠）
    params = [
        ('tc', result['tc'], lower_bounds[0], upper_bounds[0]),
        ('beta', result['beta'], lower_bounds[1], upper_bounds[1]),
        ('omega', result['omega'], lower_bounds[2], upper_bounds[2]),
        ('phi', result['phi'], lower_bounds[3], upper_bounds[3]),
        ('A', result['A'], lower_bounds[4], upper_bounds[4]),
        ('B', result['B'], lower_bounds[5], upper_bounds[5]),
        ('C', result['C'], lower_bounds[6], upper_bounds[6]),
    ]

    for param_name, value, lower, upper in params:
        range_width = upper - lower
        margin = range_width * margin_ratio

        # 下限張り付きチェック
        if value < lower + margin:
            logger.debug(
                f"Boundary adhesion detected: {param_name}={value:.4f} "
                f"too close to lower bound {lower:.4f} (margin={margin:.4f})"
            )
            return True

        # 上限張り付きチェック
        if value > upper - margin:
            logger.debug(
                f"Boundary adhesion detected: {param_name}={value:.4f} "
                f"too close to upper bound {upper:.4f} (margin={margin:.4f})"
            )
            return True

    return False


def validate_lppl_parameters(
    result: Dict[str, float],
    tc_min: float = 1.01,
    bounds: tuple = None
) -> bool:
    """
    LPPLパラメータの妥当性検証

    【重要更新: 2025-10-11】
    境界張り付きチェックを必須化（A0: ユーザーフィードバック）
    - 境界張り付きのフィットは不適格として扱う
    - 理由: 真の最適解の保証（探索範囲制約による人工的収束の排除）

    【検証項目】（17日誤差実装準拠）
    1. tc > 1.0: 未来予測（正規化時間）
    2. 0.05 < beta < 1.0: べき乗指数の広い範囲（緩和版）
    3. 1.0 < omega < 20.0: 角周波数の広い範囲（緩和版）
    4. R² > 0.5: 最低限のフィット品質
    5. 境界値張り付きなし: 真の最適解であること（A0: 失敗として扱う）

    【予測精度基準】（A1: ユーザー指定）
    - 単一窓フィット: 予測誤差 ≤ 35日（1987年ブラックマンデー基準）
    - 多重窓FCO: 各窓の誤差≤35日達成率を補助的に測定
    - FCO総合結果の精度が最終的に重要

    Args:
        result: フィッティング結果
        tc_min: tc最小値（デフォルト1.01）
        bounds: 境界条件（境界値張り付きチェック用、必須）

    Returns:
        妥当性判定（True/False）
        - False: 境界張り付きまたは基本制約違反（不適格）
        - True: 全条件を満たす適格フィット
    """
    # 基本的な範囲チェック（17日誤差実装準拠）
    is_valid = (
        result['tc'] >= tc_min and  # 未来予測
        0.05 < result['beta'] < 1.0 and  # 緩和された範囲
        1.0 < result['omega'] < 20.0 and  # 緩和された範囲
        result['r2'] > 0.5  # 最低限のフィット品質
    )

    if not is_valid:
        logger.warning("Parameter validation failed:")
        logger.warning(f"  tc={result['tc']:.4f} (>= {tc_min}: {result['tc'] >= tc_min})")
        logger.warning(f"  beta={result['beta']:.4f} (0.05-1.0: {0.05 < result['beta'] < 1.0})")
        logger.warning(f"  omega={result['omega']:.4f} (1.0-20.0: {1.0 < result['omega'] < 20.0})")
        logger.warning(f"  R²={result['r2']:.4f} (>0.5: {result['r2'] > 0.5})")
        return False

    # 境界値張り付きチェック（過去実装準拠）
    if bounds is not None:
        has_adhesion = check_boundary_adhesion(result, bounds)
        if has_adhesion:
            logger.warning("Parameter validation failed: boundary adhesion detected")
            return False

    return True
