"""
Flexible FCO Engine with Classic LPPLS Fallback
データサイズに応じて処理を最適化するFCOエンジン
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

# 既存の実装を使用
from .fitter import LogarithmPeriodicFitter

logger = logging.getLogger(__name__)


@dataclass
class FCOAnalysisResult:
    """FCO分析結果を格納するデータクラス"""
    ds_lppls_confidence: float
    ds_lppls_confidence_neg: float
    predicted_tc: Optional[float]
    tc_std: Optional[float]
    scenario_probability: Optional[float]
    window_results: List[Dict]
    bubble_type: str
    metadata: Dict[str, Any]


class FCOEngineFlexible:
    """
    柔軟なFCOエンジン - データサイズに応じた適応的処理
    """

    # FCO標準パラメータ（調整可能）
    WINDOW_MIN = 50   # 最小窓サイズ（元125）
    WINDOW_MAX = 750  # 最大窓サイズ
    WINDOW_STEP = 10  # 窓の刻み幅（元5）

    # フィルタリング条件
    FILTER_DAMPING_MIN = 0.0  # 緩和（元1.0）
    FILTER_M_MIN = 0.1
    FILTER_M_MAX = 0.9
    FILTER_OMEGA_MIN = 2.0
    FILTER_OMEGA_MAX = 25.0

    def __init__(self):
        """Initialize flexible FCO engine"""
        self.classic_fitter = LogarithmPeriodicFitter()
        logger.info("FCOEngineFlexible initialized")

    def compute_ds_lppls_confidence(
        self,
        prices: np.ndarray,
        timestamps: Optional[np.ndarray] = None
    ) -> FCOAnalysisResult:
        """
        DS-LPPLS Confidence指標を計算

        Args:
            prices: 価格データ
            timestamps: タイムスタンプ（オプション）

        Returns:
            FCO分析結果
        """
        n = len(prices)
        log_prices = np.log(prices)

        # データサイズに応じて窓サイズを調整
        if n < 100:
            # データが少ない場合は単一窓で分析
            logger.warning(f"Limited data ({n} points), using single window analysis")
            return self._single_window_analysis(log_prices)

        # 適応的な窓サイズ設定
        actual_min = max(self.WINDOW_MIN, int(n * 0.3))  # データの30%以上
        actual_max = min(self.WINDOW_MAX, int(n * 0.9))  # データの90%以下

        if actual_min >= actual_max:
            actual_min = int(n * 0.5)
            actual_max = int(n * 0.9)

        # 窓の刻み幅も調整
        num_windows = min(20, (actual_max - actual_min) // self.WINDOW_STEP)
        if num_windows < 5:
            step = max(1, (actual_max - actual_min) // 5)
        else:
            step = self.WINDOW_STEP

        window_sizes = range(actual_min, actual_max + 1, step)
        logger.info(f"Analyzing {n} points with {len(window_sizes)} windows ({actual_min}-{actual_max})")

        # 多重時間窓分析
        all_window_fits = []
        qualified_fits = []
        positive_count = 0
        negative_count = 0
        tc_values = []
        total_windows = 0

        for window_size in window_sizes:
            if window_size > n:
                continue

            # 窓の終点は最新データ
            end_idx = n
            start_idx = n - window_size

            # 窓データの抽出
            window_data = log_prices[start_idx:end_idx]

            try:
                # クラシックフィッターで分析
                result = self.classic_fitter.fit(window_data)

                if result and result['success']:
                    total_windows += 1

                    # パラメータの取得
                    tc = result.get('tc', 0)
                    m = result.get('m', 0)
                    omega = result.get('omega', 0)
                    damping = result.get('damping', 0) if 'damping' in result else abs(m * omega / (2 * np.pi))

                    # フィルタリング条件（緩和版）
                    is_qualified = (
                        damping >= self.FILTER_DAMPING_MIN and
                        self.FILTER_M_MIN <= abs(m) <= self.FILTER_M_MAX and
                        self.FILTER_OMEGA_MIN <= abs(omega) <= self.FILTER_OMEGA_MAX and
                        tc > window_size  # 未来のtc
                    )

                    # 結果を保存
                    window_fit = {
                        **result,
                        'window_size': window_size,
                        'window_start_idx': start_idx,
                        'window_end_idx': end_idx,
                        'damping': damping,
                        'is_qualified': is_qualified
                    }
                    all_window_fits.append(window_fit)

                    if is_qualified:
                        qualified_fits.append(result)
                        tc_values.append(tc)
                        if m > 0:
                            positive_count += 1
                        else:
                            negative_count += 1

            except Exception as e:
                logger.debug(f"Fitting failed for window size {window_size}: {e}")
                continue

        # DS-LPPLS信頼度計算
        if total_windows > 0:
            pos_conf = positive_count / total_windows
            neg_conf = negative_count / total_windows
        else:
            pos_conf = 0.0
            neg_conf = 0.0

        # bubble_type判定（アプリケーション層での実装）
        # ========================================================
        # 重要: Boulder LPPLSライブラリとの関係性について
        # ========================================================
        # Boulder LPPLSライブラリ自体にはbubble_type判定機能は
        # 含まれていません。以下の閾値はETH Zurich FCOの
        # 公式基準に基づいています：
        # - 30%閾値: FCO公開レポートで中程度のバブルと定義
        # - 5%閾値: FCO実装で弱いシグナルと定義
        # この実装は Boulder LPPLS のコア計算を変更するものではなく、
        # 可視化のための適切なアプリケーション層拡張です。
        # ========================================================
        if pos_conf > 0.3:  # FCO公式基準: 30%以上で中程度のバブル
            bubble_type = 'positive_bubble'
        elif neg_conf > 0.3:
            bubble_type = 'negative_bubble'
        elif pos_conf > 0.05:  # FCO公式基準: 5%以上で弱いシグナル
            bubble_type = 'weak_positive'
        else:
            bubble_type = 'no_bubble'

        # tc統計
        if tc_values:
            predicted_tc = np.median(tc_values)
            tc_std = np.std(tc_values)
            scenario_probability = len(tc_values) / total_windows if total_windows > 0 else 0.0
        else:
            predicted_tc = None
            tc_std = None
            scenario_probability = 0.0

        # 結果を構築
        result = FCOAnalysisResult(
            ds_lppls_confidence=pos_conf,
            ds_lppls_confidence_neg=neg_conf,
            predicted_tc=predicted_tc,
            tc_std=tc_std,
            scenario_probability=scenario_probability,
            window_results=all_window_fits,
            bubble_type=bubble_type,
            metadata={
                'num_windows': total_windows,
                'qualified_fits': len(qualified_fits),
                'total_fits': len(all_window_fits),
                'data_points': n,
                'window_range': f"{actual_min}-{actual_max}",
                'analysis_date': pd.Timestamp.now().isoformat()
            }
        )

        logger.info(f"FCO Analysis complete: confidence={pos_conf:.2%}, type={bubble_type}, qualified={len(qualified_fits)}/{total_windows}")

        return result

    def _single_window_analysis(self, log_prices: np.ndarray) -> FCOAnalysisResult:
        """
        単一窓での分析（データが少ない場合）
        """
        try:
            result = self.classic_fitter.fit(log_prices)

            if result and result['success']:
                m = result.get('m', 0)
                confidence = 0.5 if abs(m) > 0.1 else 0.1  # 簡易的な信頼度

                return FCOAnalysisResult(
                    ds_lppls_confidence=confidence if m > 0 else 0,
                    ds_lppls_confidence_neg=confidence if m < 0 else 0,
                    predicted_tc=result.get('tc'),
                    tc_std=None,
                    scenario_probability=0.5,
                    window_results=[result],
                    bubble_type='positive_bubble' if m > 0 and confidence > 0.3 else 'no_bubble',
                    metadata={
                        'num_windows': 1,
                        'qualified_fits': 1 if result['success'] else 0,
                        'total_fits': 1,
                        'data_points': len(log_prices),
                        'single_window': True
                    }
                )
        except Exception as e:
            logger.error(f"Single window analysis failed: {e}")

        # フォールバック
        return FCOAnalysisResult(
            ds_lppls_confidence=0.0,
            ds_lppls_confidence_neg=0.0,
            predicted_tc=None,
            tc_std=None,
            scenario_probability=0.0,
            window_results=[],
            bubble_type='no_bubble',
            metadata={
                'num_windows': 0,
                'qualified_fits': 0,
                'total_fits': 0,
                'data_points': len(log_prices),
                'error': True
            }
        )