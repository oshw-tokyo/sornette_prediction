"""
カスタムFCOエンジン: 過去LPPL準拠の多重時間窓分析

⚠️⚠️⚠️ CRITICAL: この実装は科学的再現性の根幹です ⚠️⚠️⚠️

【科学的根拠】
- 実装元: archive/src_pre_migration_backup/fitting/fitter.py (100/100スコア達成)
- アルゴリズム: グリッドサーチ + 境界付き最適化
- FCO準拠: 126窓多重時間窓解析 (125-750日)

【Boulder LPPLSとの違い】
- Boulder LPPLS: 無制約最適化 + ランダム初期値 → 0% Confidence (1987年)
- カスタムFCO: 境界付き最適化 + グリッドサーチ → Phase 1で R²=0.9664 達成

【Phase 1検証結果 (2025-10-11)】⭐⭐⭐ 完全成功 ⭐⭐⭐
- ✅ R² = 0.9664 (目標 > 0.9)
- ✅ tc = 1.2128 (未来予測、境界張り付きなし)
- ✅ omega = 8.5234 (境界張り付き解消、範囲拡大により達成)
- ✅ 予測誤差 = 5日 (目標 ≤ 35日)
- 🎯 1987年ブラックマンデー予測: 実際10/19 vs 予測10/24 (5日差)

【重要な境界条件更新 (2025-10-11)】
⚠️ omega範囲拡大: [5.0, 8.0] → [5.0, 10.0]
- 根拠: Sornette論文で最大8.93の実例を確認
- 詳細: papers/extracted_texts/sornette_2004_0301543v1_*.txt
- 結果: omega境界張り付き問題を解消、予測精度向上（11日→5日）

【実装方針】
- ✅ Phase 1: 単一窓フィッティング（完了、R²=0.9664、予測誤差5日）
- 🔄 Phase 2: 126窓統合（本ファイル、実装予定）
- ⏭️ Phase 3: データベース・フロントエンド統合
- ⏭️ Phase 4: 最終検証

【依存関係】⚠️ CRITICAL ⚠️
- lppl_optimizer.py: グリッドサーチ + 境界付き最適化（LPPL_BOUNDSと完全一致必須）
- lppl_utils.py: 時間正規化、LPPL関数定義
- 過去実装: archive/src_pre_migration_backup/fitting/fitter.py（参照実装）

⚠️⚠️⚠️ 変更前の必須確認事項 ⚠️⚠️⚠️
1. lppl_optimizer.py の境界条件と完全一致しているか
2. 過去実装（archive/）との整合性は保たれているか
3. Phase 1検証テスト (workspace_for_claude/test_custom_fco_phase1_with_plot.py) で
   100/100スコア相当の結果が維持されるか

変更後の必須テスト:
  python workspace_for_claude/test_custom_fco_phase1_with_plot.py
  期待結果: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from multiprocessing import Pool, cpu_count
import time

from .lppl_optimizer import fit_lppl_grid_search, validate_lppl_parameters, check_boundary_adhesion
from .lppl_utils import prepare_normalized_data

logger = logging.getLogger(__name__)

# ⚠️⚠️⚠️ CRITICAL: 境界条件（過去実装ベース + omega拡大） ⚠️⚠️⚠️
#
# 【重要更新 (2025-10-11)】omega範囲拡大: [5.0, 8.0] → [5.0, 10.0]
# - 根拠: Sornette論文で最大 ω = 8.93 の実例を確認
# - 詳細: papers/extracted_texts/sornette_2004_0301543v1_*.txt
# - 結果: omega境界張り付き問題を解消、予測精度向上（11日→5日）
#
# 【依存関係】⚠️ CRITICAL ⚠️
# この境界条件は lppl_optimizer.py:120-123 の bounds と完全一致必須
# 不一致の場合、フィルタリング条件と最適化条件の矛盾が発生し、
# 適格フィット数が0になる可能性がある
#
# 【パラメータ説明】
# - tc: 1.01-1.5 (臨界時刻、正規化時間、tc > 1.0で未来予測)
# - beta: 0.3-0.7 (べき乗指数、典型値範囲)
# - omega: 5.0-10.0 (角周波数、拡大版、Sornette論文で最大8.93確認済み)
# - phi: -8π ~ 8π (位相)
# - A, B, C: -10 ~ 10, -10 ~ 10, -2.0 ~ 2.0 (線形パラメータ)
#
# 【科学的根拠】
# - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
# - 実績: 1987年ブラックマンデー 100/100スコア達成
# - Phase 1検証: R²=0.9664, 予測誤差5日達成
#
LPPL_BOUNDS = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
    [1.5,  0.7, 10.0,  8*np.pi,  10,  10,  2.0]  # upper (omega: 8.0→10.0)
)


@dataclass
class CustomFCOResult:
    """カスタムFCO分析結果"""
    ds_lppls_confidence: float  # DS-LPPLS Confidence (適格フィット率)
    qualified_fits: int  # 適格フィット数
    total_windows: int  # 総窓数
    window_results: List[Dict[str, Any]]  # 各窓の詳細結果
    predicted_tc: Optional[float]  # 予測tc（正規化時間の中央値）
    tc_std: Optional[float]  # tc標準偏差
    metadata: Dict[str, Any]  # その他メタデータ


class CustomFCOEngine:
    """
    カスタムFCO多重時間窓LPPLSエンジン

    【FCO標準パラメータ】
    - 126窓: 750日 → 125日、5日刻み
    - 固定endpoint: 全窓が最新日で終了

    【フィルタリング条件（過去実装準拠）】
    - beta: 0.3 - 0.7 (べき乗指数)
    - omega: 5.0 - 8.0 (角周波数)
    - R²: > 0.5 (最低フィット品質)
    - tc: > 1.0 (未来予測、正規化時間)

    【科学的根拠】
    実装元: archive/src_pre_migration_backup/fitting/fitter.py
    実績: 1987年ブラックマンデー 100/100スコア達成
    """

    # ⚠️ CRITICAL: FCO標準窓パラメータ（FCO公式仕様準拠）
    WINDOW_MIN = 125  # 最小窓サイズ（営業日）
    WINDOW_MAX = 750  # 最大窓サイズ（営業日）
    WINDOW_STEP = 5   # 窓の刻み幅
    # → 窓数: (750 - 125) / 5 + 1 = 126窓

    # ⚠️⚠️⚠️ CRITICAL: フィルタリング条件 ⚠️⚠️⚠️
    # 【重要更新 (2025-10-11)】omega範囲拡大: [5.0, 8.0] → [5.0, 10.0]
    # - 根拠: Sornette論文で最大 ω = 8.93 の実例を確認
    # - 詳細: papers/extracted_texts/sornette_2004_0301543v1_*.txt
    # - 結果: omega境界張り付き問題を解消、予測精度向上（11日→5日）
    #
    # 【依存関係】⚠️ CRITICAL ⚠️
    # これらの値は LPPL_BOUNDS (上記) および lppl_optimizer.py:120-123 と完全一致必須
    # 不一致の場合、適格フィット数が0になる可能性がある
    #
    # 【科学的根拠】
    # - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
    # - 実績: 1987年ブラックマンデー 100/100スコア達成
    # - Phase 1検証: R²=0.9664, 予測誤差5日達成
    #
    FILTER_BETA_MIN = 0.3
    FILTER_BETA_MAX = 0.7
    FILTER_OMEGA_MIN = 5.0
    FILTER_OMEGA_MAX = 10.0  # 拡大: 8.0 → 10.0
    FILTER_R2_MIN = 0.5
    FILTER_TC_MIN = 1.0  # 正規化時間で未来予測

    def __init__(self, n_tries: int = 10):
        """
        Args:
            n_tries: グリッドサーチの刻み数（デフォルト10 → 1000組み合わせ）
        """
        self.n_tries = n_tries
        logger.info(f"CustomFCOEngine initialized (n_tries={n_tries}, combinations={n_tries**3})")

    def compute_ds_lppls_confidence(
        self,
        prices: np.ndarray,
        timestamps: Optional[np.ndarray] = None
    ) -> CustomFCOResult:
        """
        DS-LPPLS Confidence指標を計算（多重時間窓分析）

        【アルゴリズム】
        1. 126窓（750→125日、5日刻み）を生成
        2. 各窓で時間正規化 [0, 1] + グリッドサーチフィッティング
        3. フィルタリング条件適用
        4. DS-LPPLS Confidence = 適格フィット数 / 総窓数

        Args:
            prices: 価格データ（生の価格）
            timestamps: タイムスタンプ（オプション、インデックスに使用）

        Returns:
            CustomFCOResult: FCO分析結果
        """
        n_total = len(prices)

        # 十分なデータがあるか確認
        if n_total < self.WINDOW_MAX:
            logger.warning(f"Insufficient data: {n_total} < {self.WINDOW_MAX}")
            # データ不足時は窓サイズを調整
            adjusted_max = n_total - 20
            window_sizes = list(range(self.WINDOW_MIN, adjusted_max, self.WINDOW_STEP))
        else:
            # FCO標準の126窓
            window_sizes = list(range(self.WINDOW_MIN, self.WINDOW_MAX + 1, self.WINDOW_STEP))

        logger.info(f"Analyzing {len(window_sizes)} windows (sizes: {window_sizes[0]}-{window_sizes[-1]})")

        # 多重窓分析を実行
        window_results = []
        qualified_fits = []
        tc_values = []

        total_windows_to_analyze = len(window_sizes)

        for idx, window_size in enumerate(window_sizes, 1):
            if window_size > n_total:
                logger.warning(f"Skipping window {window_size}: insufficient data ({n_total} points)")
                continue

            # プログレス表示（10窓ごと）
            if idx % 10 == 0 or idx == 1 or idx == total_windows_to_analyze:
                print(f"  Progress: {idx}/{total_windows_to_analyze} windows ({idx/total_windows_to_analyze*100:.1f}%) - window_size={window_size}")

            # 固定endpoint（最新日）から遡って window_size 分のデータを切り出し
            window_prices = prices[-window_size:]

            # 時間正規化 [0, 1] + フィッティング
            t, log_prices_normalized = prepare_normalized_data(window_prices)

            try:
                result = fit_lppl_grid_search(t, log_prices_normalized, n_tries=self.n_tries)

                if result is None:
                    logger.debug(f"Window {window_size}: Fitting failed (no convergence)")
                    window_results.append({
                        'window_size': window_size,
                        'window_start_idx': n_total - window_size,
                        'window_end_idx': n_total - 1,
                        'fit_success': False,
                        'is_qualified': False
                    })
                    continue

                # フィルタリング条件適用
                is_qualified = self._apply_filtering_conditions(result)

                # 窓結果を保存
                window_result = {
                    'window_size': window_size,
                    'window_start_idx': n_total - window_size,
                    'window_end_idx': n_total - 1,
                    'fit_success': True,
                    'is_qualified': is_qualified,
                    **result  # tc, beta, omega, phi, A, B, C, r2, residuals
                }
                window_results.append(window_result)

                if is_qualified:
                    qualified_fits.append(result)
                    tc_values.append(result['tc'])

                logger.debug(
                    f"Window {window_size}: R²={result['r2']:.4f}, "
                    f"tc={result['tc']:.4f}, qualified={is_qualified}"
                )

            except Exception as e:
                logger.warning(f"Window {window_size}: Unexpected error: {e}")
                window_results.append({
                    'window_size': window_size,
                    'window_start_idx': n_total - window_size,
                    'window_end_idx': n_total - 1,
                    'fit_success': False,
                    'is_qualified': False,
                    'error': str(e)
                })

        # DS-LPPLS Confidence計算
        total_windows = len(window_results)
        num_qualified = len(qualified_fits)
        ds_lppls_confidence = num_qualified / total_windows if total_windows > 0 else 0.0

        # 予測tc統計
        if tc_values:
            predicted_tc = float(np.median(tc_values))
            tc_std = float(np.std(tc_values))
        else:
            predicted_tc = None
            tc_std = None

        result = CustomFCOResult(
            ds_lppls_confidence=ds_lppls_confidence,
            qualified_fits=num_qualified,
            total_windows=total_windows,
            window_results=window_results,
            predicted_tc=predicted_tc,
            tc_std=tc_std,
            metadata={
                'n_tries': self.n_tries,
                'combinations': self.n_tries ** 3,
                'data_points': n_total,
                'analysis_date': pd.Timestamp.now().isoformat()
            }
        )

        logger.info(
            f"DS-LPPLS Confidence: {ds_lppls_confidence:.2%} "
            f"({num_qualified}/{total_windows} qualified)"
        )

        return result

    def _apply_filtering_conditions(self, result: Dict[str, float]) -> bool:
        """
        フィルタリング条件を適用（過去実装準拠 + 境界値張り付きチェック）

        【条件】
        1. beta ∈ [0.3, 0.7] - べき乗指数の典型範囲
        2. omega ∈ [5.0, 8.0] - 角周波数の典型範囲
        3. R² > 0.5 - 最低フィット品質
        4. tc > 1.0 - 未来予測（正規化時間）
        5. 境界値張り付きなし - 真の最適解であること（過去実装準拠）

        【境界値張り付きチェックの重要性】
        最適化アルゴリズムがパラメータの上限・下限に収束した場合、
        それは真の最適解ではなく、探索範囲の制約による人工的な結果である可能性が高い。

        例:
        - tc=1.0100 (下限1.01) に張り付き → 真の最適tcはもっと小さい可能性
        - beta=0.7000 (上限0.7) に張り付き → 真の最適betaはもっと大きい可能性

        このような結果は科学的に信頼性が低いため棄却する（過去実装での経験則）。

        【科学的根拠】
        実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
        実績: 1987年ブラックマンデー 100/100スコア達成
        境界値張り付き棄却: 過去実装での経験則

        Args:
            result: フィッティング結果

        Returns:
            適格判定（True/False）
        """
        # 基本的な範囲チェック
        is_qualified = (
            self.FILTER_BETA_MIN <= result['beta'] <= self.FILTER_BETA_MAX and
            self.FILTER_OMEGA_MIN <= result['omega'] <= self.FILTER_OMEGA_MAX and
            result['r2'] > self.FILTER_R2_MIN and
            result['tc'] > self.FILTER_TC_MIN
        )

        if not is_qualified:
            logger.debug(
                f"Filtering failed (basic checks): "
                f"beta={result['beta']:.4f} ({self.FILTER_BETA_MIN}-{self.FILTER_BETA_MAX}), "
                f"omega={result['omega']:.4f} ({self.FILTER_OMEGA_MIN}-{self.FILTER_OMEGA_MAX}), "
                f"R²={result['r2']:.4f} (>{self.FILTER_R2_MIN}), "
                f"tc={result['tc']:.4f} (>{self.FILTER_TC_MIN})"
            )
            return False

        # 境界値張り付きチェック（ユーザーフィードバックA0）
        # 過去実装で境界張り付きが発生しないことを確認済み
        # 60日前基準 + 1000日データで境界張り付きなしを達成
        has_adhesion = check_boundary_adhesion(result, LPPL_BOUNDS)
        if has_adhesion:
            logger.debug("Filtering failed: boundary adhesion detected")
            return False

        return True

    # ========================================================================
    # 🚀 マルチプロセッシング並列化実装 (Issue I127)
    # ========================================================================
    #
    # 【実装方針】
    # - 既存メソッド (compute_ds_lppls_confidence) は一切変更しない
    # - 新しい並列版メソッドを追加する形で実装
    # - 科学的精度100%保持（同一データで同一結果を保証）
    # - シンプルで管理しやすい実装（Python標準ライブラリのみ使用）
    #
    # 【アルゴリズム】
    # - 各窓の解析は完全に独立している
    # - multiprocessing.Pool で並列実行
    # - 結果集約は既存ロジックを再利用
    #
    # 【科学的根拠保証】
    # - フィッティングアルゴリズムは一切変更なし
    # - フィルタリング条件は完全一致
    # - 結果の順序のみ変わる可能性あり（ソート済みなので実質同一）
    #
    # 【期待効果】
    # - 8コアで約8倍高速化（51窓: 5-7分 → 約1分）
    #
    # 【実装日】2025-10-12
    # 【参照】workspace_for_claude/performance_optimization_investigation.md

    def compute_ds_lppls_confidence_parallel(
        self,
        prices: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        n_workers: Optional[int] = None
    ) -> CustomFCOResult:
        """
        DS-LPPLS Confidence指標を計算（多重時間窓分析、並列版）

        【並列化方針】
        - 各窓の解析は完全に独立 → multiprocessing.Pool で並列実行
        - 科学的精度100%保持（同一データで同一結果）
        - シンプルな実装（Python標準ライブラリのみ）

        【アルゴリズム】
        1. 126窓（750→125日、5日刻み）を生成
        2. 各窓を並列でフィッティング（multiprocessing.Pool）
        3. 結果集約（既存ロジック使用）
        4. DS-LPPLS Confidence = 適格フィット数 / 総窓数

        Args:
            prices: 価格データ（生の価格）
            timestamps: タイムスタンプ（オプション、インデックスに使用）
            n_workers: ワーカープロセス数（Noneの場合はCPU数-1を使用）

        Returns:
            CustomFCOResult: FCO分析結果（逐次版と科学的に同一）
        """
        # 計測開始
        start_time = time.perf_counter()

        n_total = len(prices)

        # ワーカー数の決定（1コアはOSに残す）
        if n_workers is None:
            n_workers = max(1, cpu_count() - 1)

        logger.info(f"Parallel analysis with {n_workers} workers (CPU count: {cpu_count()})")

        # 十分なデータがあるか確認
        if n_total < self.WINDOW_MAX:
            logger.warning(f"Insufficient data: {n_total} < {self.WINDOW_MAX}")
            adjusted_max = n_total - 20
            window_sizes = list(range(self.WINDOW_MIN, adjusted_max, self.WINDOW_STEP))
        else:
            window_sizes = list(range(self.WINDOW_MIN, self.WINDOW_MAX + 1, self.WINDOW_STEP))

        logger.info(f"Analyzing {len(window_sizes)} windows (sizes: {window_sizes[0]}-{window_sizes[-1]})")

        # 各窓のパラメータを準備
        # ⚠️ CRITICAL: multiprocessing.Pool では pickle 可能な引数のみ渡せる
        # → prices全体を渡し、各ワーカーが必要部分を切り出す
        window_params = [
            (prices, window_size, n_total, self.n_tries, idx, len(window_sizes))
            for idx, window_size in enumerate(window_sizes, 1)
        ]

        # 並列実行
        # ⚠️ CRITICAL: Pool.starmap は引数をタプルで渡す
        # → 静的ワーカー関数 (_fit_single_window_worker) を使用
        with Pool(n_workers) as pool:
            window_results = pool.starmap(_fit_single_window_worker_static, window_params)

        # 結果集約（既存ロジックと同一）
        qualified_fits = []
        tc_values = []

        for window_result in window_results:
            if window_result.get('is_qualified', False):
                qualified_fits.append(window_result)
                tc_values.append(window_result['tc'])

        # DS-LPPLS Confidence計算
        total_windows = len(window_results)
        num_qualified = len(qualified_fits)
        ds_lppls_confidence = num_qualified / total_windows if total_windows > 0 else 0.0

        # 予測tc統計
        if tc_values:
            predicted_tc = float(np.median(tc_values))
            tc_std = float(np.std(tc_values))
        else:
            predicted_tc = None
            tc_std = None

        # 計測終了
        elapsed_time = time.perf_counter() - start_time

        result = CustomFCOResult(
            ds_lppls_confidence=ds_lppls_confidence,
            qualified_fits=num_qualified,
            total_windows=total_windows,
            window_results=window_results,
            predicted_tc=predicted_tc,
            tc_std=tc_std,
            metadata={
                'n_tries': self.n_tries,
                'combinations': self.n_tries ** 3,
                'data_points': n_total,
                'analysis_date': pd.Timestamp.now().isoformat(),
                'parallel': True,
                'n_workers': n_workers,
                'elapsed_time_sec': elapsed_time
            }
        )

        logger.info(
            f"DS-LPPLS Confidence: {ds_lppls_confidence:.2%} "
            f"({num_qualified}/{total_windows} qualified) "
            f"- Elapsed time: {elapsed_time:.2f}s"
        )

        return result


# ============================================================================
# 静的ワーカー関数（multiprocessing.Pool用）
# ============================================================================
#
# ⚠️⚠️⚠️ CRITICAL: pickle可能な関数である必要がある ⚠️⚠️⚠️
#
# multiprocessing.Pool は引数をプロセス間でpickleして渡すため、
# 以下の条件を満たす必要がある:
# - モジュールレベル関数（グローバル関数）
# - クラスメソッドではない（staticmethodでも不可）
# - すべての引数がpickle可能
#
# そのため、CustomFCOEngineのメソッドではなく、
# モジュールレベルの静的関数として実装する。
#
# 【科学的精度保証】
# - フィッティングアルゴリズム: fit_lppl_grid_search() を直接呼び出し
# - フィルタリング条件: _apply_filtering_static() で完全一致を保証
# - 既存実装と完全に同一のロジック
#
# 【実装日】2025-10-12

def _fit_single_window_worker_static(
    prices_full: np.ndarray,
    window_size: int,
    n_total: int,
    n_tries: int,
    idx: int,
    total_windows: int
) -> Dict[str, Any]:
    """
    静的ワーカー関数: 単一窓のフィッティング（multiprocessing.Pool用）

    ⚠️ CRITICAL: この関数は科学的精度を100%保持する必要がある

    Args:
        prices_full: 価格データ全体（ワーカーが必要部分を切り出し）
        window_size: 窓サイズ
        n_total: データ総数
        n_tries: グリッドサーチ刻み数
        idx: 窓インデックス（プログレス表示用）
        total_windows: 総窓数（プログレス表示用）

    Returns:
        窓解析結果（dict）
    """
    # プログレス表示（10窓ごと）
    if idx % 10 == 0 or idx == 1 or idx == total_windows:
        print(f"  Progress: {idx}/{total_windows} windows ({idx/total_windows*100:.1f}%) - window_size={window_size}")

    if window_size > n_total:
        return {
            'window_size': window_size,
            'window_start_idx': n_total - window_size,
            'window_end_idx': n_total - 1,
            'fit_success': False,
            'is_qualified': False
        }

    # 固定endpoint（最新日）から遡って window_size 分のデータを切り出し
    window_prices = prices_full[-window_size:]

    # 時間正規化 [0, 1] + フィッティング
    t, log_prices_normalized = prepare_normalized_data(window_prices)

    try:
        result = fit_lppl_grid_search(t, log_prices_normalized, n_tries=n_tries)

        if result is None:
            return {
                'window_size': window_size,
                'window_start_idx': n_total - window_size,
                'window_end_idx': n_total - 1,
                'fit_success': False,
                'is_qualified': False
            }

        # フィルタリング条件適用（静的関数版）
        is_qualified = _apply_filtering_static(result)

        # 窓結果を返却
        return {
            'window_size': window_size,
            'window_start_idx': n_total - window_size,
            'window_end_idx': n_total - 1,
            'fit_success': True,
            'is_qualified': is_qualified,
            **result  # tc, beta, omega, phi, A, B, C, r2, residuals
        }

    except Exception as e:
        return {
            'window_size': window_size,
            'window_start_idx': n_total - window_size,
            'window_end_idx': n_total - 1,
            'fit_success': False,
            'is_qualified': False,
            'error': str(e)
        }


def _apply_filtering_static(result: Dict[str, float]) -> bool:
    """
    静的フィルタリング関数（multiprocessing.Pool用）

    ⚠️⚠️⚠️ CRITICAL: CustomFCOEngine._apply_filtering_conditions() と完全一致必須 ⚠️⚠️⚠️

    【科学的精度保証】
    - 条件は CustomFCOEngine のクラス定数と完全一致
    - LPPL_BOUNDS も同一のグローバル定数を使用
    - 既存実装と同一のロジック

    【条件】
    1. beta ∈ [0.3, 0.7]
    2. omega ∈ [5.0, 10.0]
    3. R² > 0.5
    4. tc > 1.0
    5. 境界値張り付きなし

    Args:
        result: フィッティング結果

    Returns:
        適格判定（True/False）
    """
    # CustomFCOEngine のクラス定数と完全一致
    FILTER_BETA_MIN = 0.3
    FILTER_BETA_MAX = 0.7
    FILTER_OMEGA_MIN = 5.0
    FILTER_OMEGA_MAX = 10.0
    FILTER_R2_MIN = 0.5
    FILTER_TC_MIN = 1.0

    # 基本的な範囲チェック
    is_qualified = (
        FILTER_BETA_MIN <= result['beta'] <= FILTER_BETA_MAX and
        FILTER_OMEGA_MIN <= result['omega'] <= FILTER_OMEGA_MAX and
        result['r2'] > FILTER_R2_MIN and
        result['tc'] > FILTER_TC_MIN
    )

    if not is_qualified:
        return False

    # 境界値張り付きチェック
    has_adhesion = check_boundary_adhesion(result, LPPL_BOUNDS)
    if has_adhesion:
        return False

    return True
