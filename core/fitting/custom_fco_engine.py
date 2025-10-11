"""
カスタムFCOエンジン: 過去LPPL準拠の多重時間窓分析

【科学的根拠】
- 実装元: archive/src_pre_migration_backup/fitting/fitter.py (100/100スコア達成)
- アルゴリズム: グリッドサーチ + 境界付き最適化
- FCO準拠: 126窓多重時間窓解析 (125-750日)

【Boulder LPPLSとの違い】
- Boulder LPPLS: 無制約最適化 + ランダム初期値 → 0% Confidence (1987年)
- カスタムFCO: 境界付き最適化 + グリッドサーチ → Phase 1で R²=0.9382 達成

【実装方針】
- Phase 1: 単一窓フィッティング（完了、R²=0.9382）
- Phase 2: 126窓統合（本ファイル）
- Phase 3: データベース・フロントエンド統合
- Phase 4: 最終検証

⚠️ この実装は科学的再現性の根幹です。むやみに変更しないこと。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .lppl_optimizer import fit_lppl_grid_search, validate_lppl_parameters
from .lppl_utils import prepare_normalized_data

logger = logging.getLogger(__name__)


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

    # FCO標準窓パラメータ
    WINDOW_MIN = 125  # 最小窓サイズ（営業日）
    WINDOW_MAX = 750  # 最大窓サイズ（営業日）
    WINDOW_STEP = 5   # 窓の刻み幅

    # フィルタリング条件（過去実装準拠）
    FILTER_BETA_MIN = 0.3
    FILTER_BETA_MAX = 0.7
    FILTER_OMEGA_MIN = 5.0
    FILTER_OMEGA_MAX = 8.0
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
        フィルタリング条件を適用（過去実装準拠）

        【条件】
        1. beta ∈ [0.3, 0.7] - べき乗指数の典型範囲
        2. omega ∈ [5.0, 8.0] - 角周波数の典型範囲
        3. R² > 0.5 - 最低フィット品質
        4. tc > 1.0 - 未来予測（正規化時間）

        【科学的根拠】
        実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
        実績: 1987年ブラックマンデー 100/100スコア達成

        Args:
            result: フィッティング結果

        Returns:
            適格判定（True/False）
        """
        is_qualified = (
            self.FILTER_BETA_MIN <= result['beta'] <= self.FILTER_BETA_MAX and
            self.FILTER_OMEGA_MIN <= result['omega'] <= self.FILTER_OMEGA_MAX and
            result['r2'] > self.FILTER_R2_MIN and
            result['tc'] > self.FILTER_TC_MIN
        )

        if not is_qualified:
            logger.debug(
                f"Filtering failed: "
                f"beta={result['beta']:.4f} ({self.FILTER_BETA_MIN}-{self.FILTER_BETA_MAX}), "
                f"omega={result['omega']:.4f} ({self.FILTER_OMEGA_MIN}-{self.FILTER_OMEGA_MAX}), "
                f"R²={result['r2']:.4f} (>{self.FILTER_R2_MIN}), "
                f"tc={result['tc']:.4f} (>{self.FILTER_TC_MIN})"
            )

        return is_qualified
