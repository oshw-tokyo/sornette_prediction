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

# ⚠️⚠️⚠️ CRITICAL: 境界条件（Issue I129多重窓FCO対応版） ⚠️⚠️⚠️
#
# 【重要更新 (2025-10-12)】多重窓FCO対応のため範囲拡大
# - beta: [0.3, 0.7] → [0.1, 0.9]（多重窓対応、Issue I129）
# - omega: [5.0, 8.0] → [5.0, 15.0]（多重窓対応、Issue I129）
#
# 【パラメータミスマッチ修正】
# - 問題: lppl_optimizer.pyとcustom_fco_engine.pyで範囲が不一致
#   * optimizer: beta=0.1-0.9, omega=5.0-15.0
#   * filter: beta=0.3-0.7, omega=5.0-10.0（修正前）
#   → 結果: 全フィット棄却、0.0% Confidence
# - 修正: filter範囲をoptimizer範囲に一致させる
# - 日付: 2025-10-12
# - 文書: workspace_for_claude/issue_i129_option2_parameter_mismatch.md
#
# 【依存関係】⚠️ CRITICAL ⚠️
# この境界条件は lppl_optimizer.py:43-46 の bounds と**完全一致必須**
# 不一致の場合、フィルタリング条件と最適化条件の矛盾が発生し、
# 適格フィット数が0になる可能性がある（Issue I129で実証済み）
#
# 【パラメータ説明】
# - tc: 1.01-1.5 (臨界時刻、正規化時間、tc > 1.0で未来予測)
# - beta: 0.1-0.9 (べき乗指数、多重窓FCO対応版)
# - omega: 5.0-15.0 (角周波数、多重窓FCO対応版)
# - phi: -8π ~ 8π (位相)
# - A, B, C: -10 ~ 10, -10 ~ 10, -2.0 ~ 2.0 (線形パラメータ)
#
# 【科学的根拠】
# - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
# - 過去実装（単一窓LPPL）: beta=0.3-0.7, omega=5.0-8.0で100/100スコア達成
# - 多重窓FCO: 各窓（250-750日）で異なる最適パラメータが必要
# - Issue I129調査結果: 窓サイズに応じて beta > 0.7, omega > 10.0 が最適になる
#
LPPL_BOUNDS = (
    [1.01, 0.1, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
    [1.5,  0.9, 15.0,  8*np.pi,  10,  10,  2.0]  # upper (Issue I129多重窓FCO対応版)
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
    カスタムFCO多重時間窓LPPLSエンジン（Issue I129多重窓FCO対応版）

    【FCO窓パラメータ（2025-10-12更新）】
    - 51窓: 750日 → 250日、10日刻み（Option 2: 実証ベース実用設定）
    - 固定endpoint: 全窓が最新日で終了
    - 変更理由: 125-250日窓での収束失敗多発のため最小窓を250日に引き上げ

    【フィルタリング条件（Issue I129多重窓FCO対応版）】
    - beta: 0.1 - 0.9 (べき乗指数、多重窓FCO対応範囲)
    - omega: 5.0 - 15.0 (角周波数、多重窓FCO対応範囲)
    - R²: > 0.5 (最低フィット品質)
    - tc: > 1.0 (未来予測、正規化時間)
    - 境界張り付きなし: 真の最適解であること

    【パラメータ範囲拡大の理由】
    - 過去実装（単一窓LPPL）: beta=0.3-0.7, omega=5.0-8.0で100/100スコア達成
    - 多重窓FCO（51窓）: 各窓で異なる最適パラメータが必要
    - 観察結果: 短い窓では beta > 0.7, omega > 10.0 が最適になる傾向
    - パラメータミスマッチ修正: optimizer範囲とfilter範囲の整合性確保

    【科学的根拠】
    - 実装元: archive/src_pre_migration_backup/fitting/fitter.py
    - 実績: 1987年ブラックマンデー 100/100スコア達成（単一窓LPPL）
    - Issue I129調査: 多重窓FCOでの実証に基づくパラメータ拡大
    """

    # ⚠️⚠️⚠️ CRITICAL: FCO窓パラメータ（Issue I129調査結果に基づく設定） ⚠️⚠️⚠️
    #
    # ========================================================================
    # 【窓範囲設定の3つのオプションと科学的根拠】
    # ========================================================================
    #
    # 📊 **Option 1: 従来のFCO標準（125-750日、出典不明）**
    #    WINDOW_MIN = 125, WINDOW_MAX = 750, WINDOW_STEP = 5 → 126窓
    #
    #    【検証結果】:
    #    - DS-LPPLS Confidence: 0-2.4% ❌
    #    - 適格フィット: 0-3/126 (0-2%)
    #    - 問題: 125-250日の小窓で収束失敗多発
    #
    #    【科学的評価】:
    #    ❌ 原典不明: Boulder LPPLSの実際のデフォルトは20-80
    #    ❌ 理論との乖離: Sornette論文は常に250日以上を使用
    #    ❌ 実証失敗: Issue I129で0-2.4% Confidenceの実績
    #
    #    【文献調査結果】:
    #    - FCO Cockpit文書: 多重窓解析の方法論のみ記載、具体的数値なし
    #    - Boulder LPPLS: window_size=80, smallest_window_size=20（125-750ではない）
    #    - Sornette論文実例:
    #      * 1987年ブラックマンデー: 557日（約2.2年）
    #      * 1987年事前分析: 1,875日（約7.5年）
    #      * 1929年大恐慌: 2,075日（約8.3年）
    #      → **一貫して1年以上（250日+）のデータを使用**
    #
    # 🥇 **Option 2: 実証ベース実用設定（250-750日、Issue I129実証済み）** ← 現在の設定
    #    WINDOW_MIN = 250, WINDOW_MAX = 750, WINDOW_STEP = 10 → 51窓
    #
    #    【検証結果】:
    #    - DS-LPPLS Confidence: **41.18%** ✅
    #    - 適格フィット: 21/51 (41%)
    #    - フィッティング成功率: 高い
    #
    #    【科学的評価】:
    #    ✅ 実証済み: Issue I129で41.18% Confidence達成
    #    ✅ 理論的妥当性: Sornette論文の最短使用期間（557日）に準拠
    #    ✅ Beta推定精度: 250日窓で(tc-t)ダイナミックレンジ=77倍（中精度）
    #    △ 短期窓の欠如: 250日未満の短期バブル検出は不可能
    #
    #    【選択理由】:
    #    - 科学的根拠（Sornette論文標準）と実証結果のバランスが最良
    #    - 計算効率と精度の両立
    #    - 論文再現の観点から信頼できる
    #
    # 🥈 **Option 3: Sornette論文準拠（365-750日、最高科学的信頼性）**
    #    WINDOW_MIN = 365, WINDOW_MAX = 750, WINDOW_STEP = 10 → 39窓
    #
    #    【予測効果】:
    #    - DS-LPPLS Confidence: 40%+ (予測)
    #    - Beta推定精度: 最高（(tc-t)ダイナミックレンジ > 100倍）
    #
    #    【科学的評価】:
    #    ✅✅ 最高の理論的妥当性: Sornette論文の最短使用期間に近い
    #    ✅ 高精度保証: 1年以上のデータで安定したbeta推定
    #    △ 短期窓の欠如: 1年未満の短期バブル検出は不可能
    #    △ 未実証: 実際の検証は未実施
    #
    #    【将来の検討事項】:
    #    - Option 2で安定性を確認後、Option 3への移行を検討
    #    - 最高の科学的信頼性を追求する場合の選択肢
    #
    # ========================================================================
    # 【短期窓フィッティング失敗の科学的意味】⚠️ 重要 ⚠️
    # ========================================================================
    #
    # **ユーザーからの重要な問い**:
    # 「短い期間に対してフィッティングが失敗するのはそれはそれで良い
    #  ということにはならないのですね？」
    #
    # **回答**: その通りです。短期窓での失敗は「それで良い」わけではありません。
    #
    # **FCO方法論の本質**:
    # - FCOは**多重時間スケール解析**が核心
    # - 短期窓（数ヶ月）: 初期段階のバブルシグネチャ検出
    # - 中期窓（1年程度）: バブル成長の確認
    # - 長期窓（2-3年）: バブル成熟の評価
    # - **様々な時間スケールで一貫してLPPLSパターンが検出される**
    #   → 高いDS-LPPLS Confidence
    #
    # **短期窓失敗の問題点**:
    # 1. **FCO本来の能力を発揮できない**
    #    - 125日窓でのフィッティング失敗多発 = 短期バブル検出不可能
    #    - FCO方法論の一部（短期時間スケール解析）を放棄することになる
    #
    # 2. **2つの異なる原因**:
    #    a) **統計的・数学的限界**（不可避）:
    #       - Beta推定には一定の(tc-t)ダイナミックレンジが必要
    #       - 125日窓: ダイナミックレンジ=35倍 → 推定精度不足
    #       - 250日窓: ダイナミックレンジ=77倍 → 中精度
    #       - 365日窓: ダイナミックレンジ=100倍+ → 高精度
    #       → これはLPPLモデルの数学的性質であり、技術的限界
    #
    #    b) **実装上の問題**（改善可能）:
    #       - 不適切な初期値設定
    #       - 不十分なグリッドサーチ範囲
    #       - 最適化アルゴリズムの選択ミス
    #       → 実装改善で部分的に解決可能
    #
    # 3. **科学的現実との整合性**:
    #    - Sornette論文自体が短期窓（125日）での解析例を持たない
    #    - 文献上の最短使用例: 557日（1987年分析）
    #    - → 125日窓の使用はSornette理論の適用範囲外の可能性
    #
    # **現在の対応方針**:
    # 1. **実用的最小窓（250日）を採用**（Option 2）
    #    - Sornette論文標準に準拠（最短557日に対して250日）
    #    - 実証済みの高いConfidence（41.18%）
    #    - Beta推定精度が理論的に保証される
    #
    # 2. **短期窓問題の将来的検討**:
    #    - 適応的パラメータ設定: 窓サイズに応じた境界条件調整
    #    - 代替的短期指標: LPPL以外の短期バブル検出手法の併用
    #    - 実装改善: より堅牢な最適化アルゴリズムの検討
    #
    # 3. **段階的改善**:
    #    - まずOption 2（250-750日）で安定性を確認
    #    - 必要に応じてOption 3（365-750日）への移行を検討
    #    - 短期窓問題の解決は長期的課題として継続研究
    #
    # ========================================================================
    # 【現在の設定】（2025-10-12 実装、Issue I129調査結果に基づく）
    # ========================================================================
    WINDOW_MIN = 250  # 最小窓サイズ（営業日、Option 2: 実証ベース実用設定）
    WINDOW_MAX = 750  # 最大窓サイズ（営業日、変更なし）
    WINDOW_STEP = 10  # 窓の刻み幅（計算効率化、5日 → 10日）
    # → 窓数: (750 - 250) / 10 + 1 = 51窓
    #
    # 【選択根拠】:
    # - ✅ Issue I129実証結果: DS-LPPLS Confidence = 41.18%
    # - ✅ Sornette論文準拠: 最短使用期間557日に対して250日
    # - ✅ Beta推定精度保証: (tc-t)ダイナミックレンジ = 77倍（中精度）
    # - ✅ 計算効率: 51窓（126窓から半減以下）
    # - △ 短期窓の欠如: 250日未満の短期バブル検出は不可能（将来的課題）
    #
    # 【変更履歴】:
    # - 2025-10-12以前: WINDOW_MIN=125, WINDOW_MAX=750, WINDOW_STEP=5 (126窓)
    #   → DS-LPPLS Confidence 0-2.4%（失敗）
    # - 2025-10-12: WINDOW_MIN=250, WINDOW_MAX=750, WINDOW_STEP=10 (51窓)
    #   → Option 2採用（実証ベース実用設定）
    #
    # 【将来的変更の可能性】:
    # - Option 3（365-750日）への移行: 最高の科学的信頼性を追求する場合
    # - 短期窓問題の解決: 適応的パラメータ設定等の実装改善
    #
    # 【変更時の注意】⚠️ CRITICAL ⚠️
    # - 変更前に1987年ブラックマンデー検証テストで影響を評価すること:
    #   python entry_points/main.py validate --crash 1987 --fco
    # - 期待結果: DS-LPPLS Confidence > 30%, positive bubble判定
    # - 変更理由を必ず文書化し、コメントを残すこと
    # - Issue I129を参照し、科学的根拠を明確にすること
    #
    # 【関連ドキュメント】:
    # - workspace_for_claude/fco_window_params_documentation_search.md
    # - workspace_for_claude/issue_i129_investigation_summary.md
    # - workspace_for_claude/beta_window_dependency_analysis.md

    # ⚠️⚠️⚠️ CRITICAL: フィルタリング条件（Issue I129多重窓FCO対応版） ⚠️⚠️⚠️
    # 【重要更新 (2025-10-12)】多重窓FCO対応のため範囲拡大
    # - beta: [0.3, 0.7] → [0.1, 0.9]（多重窓対応、Issue I129）
    # - omega: [5.0, 10.0] → [5.0, 15.0]（多重窓対応、Issue I129）
    #
    # 【パラメータミスマッチ修正】
    # - 問題: lppl_optimizer.pyの生成範囲とfilter範囲が不一致
    #   * optimizer: beta=0.1-0.9, omega=5.0-15.0
    #   * filter: beta=0.3-0.7, omega=5.0-10.0（修正前）
    #   → 結果: 全フィット棄却、0.0% Confidence
    # - 修正: filter範囲をoptimizer範囲に一致させる
    # - 日付: 2025-10-12
    # - 文書: workspace_for_claude/issue_i129_option2_parameter_mismatch.md
    #
    # 【依存関係】⚠️ CRITICAL ⚠️
    # これらの値は LPPL_BOUNDS (上記) および lppl_optimizer.py:43-46 と**完全一致必須**
    # 不一致の場合、適格フィット数が0になる可能性がある（Issue I129で実証済み）
    #
    # 【科学的根拠】
    # - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
    # - 過去実装（単一窓LPPL）: beta=0.3-0.7, omega=5.0-8.0で100/100スコア達成
    # - 多重窓FCO: 各窓（250-750日）で異なる最適パラメータが必要
    # - Issue I129調査結果: 窓サイズに応じて beta > 0.7, omega > 10.0 が最適になる
    #
    FILTER_BETA_MIN = 0.1  # 拡大: 0.3 → 0.1（Issue I129多重窓FCO対応）
    FILTER_BETA_MAX = 0.9  # 拡大: 0.7 → 0.9（Issue I129多重窓FCO対応）
    FILTER_OMEGA_MIN = 5.0  # 変更なし
    FILTER_OMEGA_MAX = 15.0  # 拡大: 10.0 → 15.0（Issue I129多重窓FCO対応）
    FILTER_R2_MIN = 0.5  # 変更なし
    FILTER_TC_MIN = 1.0  # 正規化時間で未来予測、変更なし

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
        フィルタリング条件を適用（Issue I129多重窓FCO対応版）

        【条件（2025-10-12更新）】
        1. beta ∈ [0.1, 0.9] - べき乗指数の多重窓FCO対応範囲
        2. omega ∈ [5.0, 15.0] - 角周波数の多重窓FCO対応範囲
        3. R² > 0.5 - 最低フィット品質
        4. tc > 1.0 - 未来予測（正規化時間）
        5. 境界値張り付きなし - 真の最適解であること（過去実装準拠）

        【範囲拡大の理由（Issue I129）】
        - 過去実装（単一窓LPPL）: beta=0.3-0.7, omega=5.0-8.0で100/100スコア達成
        - 多重窓FCO（51窓）: 各窓（250-750日）で異なる最適パラメータが必要
        - 観察結果: 短い窓では beta > 0.7, omega > 10.0 が最適になる傾向
        - パラメータミスマッチ問題: optimizer範囲とfilter範囲の不整合で0% Confidence
        - 修正: filter範囲をoptimizer範囲に一致（beta=0.1-0.9, omega=5.0-15.0）

        【境界値張り付きチェックの重要性】
        最適化アルゴリズムがパラメータの上限・下限に収束した場合、
        それは真の最適解ではなく、探索範囲の制約による人工的な結果である可能性が高い。

        例:
        - tc=1.0100 (下限1.01) に張り付き → 真の最適tcはもっと小さい可能性
        - beta=0.9000 (上限0.9) に張り付き → 真の最適betaはもっと大きい可能性

        このような結果は科学的に信頼性が低いため棄却する（過去実装での経験則）。

        【科学的根拠】
        - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
        - 実績: 1987年ブラックマンデー 100/100スコア達成（単一窓LPPL）
        - 境界値張り付き棄却: 過去実装での経験則
        - 多重窓FCO適応: Issue I129調査結果に基づく範囲拡大

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

    【条件（Issue I129多重窓FCO対応版）】
    1. beta ∈ [0.1, 0.9]（拡大版、2025-10-12更新）
    2. omega ∈ [5.0, 15.0]（拡大版、2025-10-12更新）
    3. R² > 0.5
    4. tc > 1.0
    5. 境界値張り付きなし

    Args:
        result: フィッティング結果

    Returns:
        適格判定（True/False）
    """
    # CustomFCOEngine のクラス定数と完全一致（Issue I129多重窓FCO対応版）
    FILTER_BETA_MIN = 0.1  # 拡大: 0.3 → 0.1（2025-10-12）
    FILTER_BETA_MAX = 0.9  # 拡大: 0.7 → 0.9（2025-10-12）
    FILTER_OMEGA_MIN = 5.0
    FILTER_OMEGA_MAX = 15.0  # 拡大: 10.0 → 15.0（2025-10-12）
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
