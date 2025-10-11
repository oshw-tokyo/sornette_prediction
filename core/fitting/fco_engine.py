"""
FCO (Financial Crisis Observatory) スタイルの多重時間窓LPPLS分析エンジン

═══════════════════════════════════════════════════════════════════════════════
📐 アーキテクチャ概要
═══════════════════════════════════════════════════════════════════════════════

このエンジンはETH ZurichのFCO標準手法に準拠した多重時間窓LPPLS分析を実装します。

【重要な依存関係】
- コアフィッティングエンジン: Boulder Investment Technologies lppls (MIT License)
  https://github.com/Boulder-Investment-Technologies/lppls
  ※ 数学的フィッティングロジックは一切変更せず、そのまま使用

【実装の責任分離】
┌─────────────────────────────────────────────────────────────────┐
│ Boulder lppls                 │ 本実装（FCOEngine）              │
├─────────────────────────────────────────────────────────────────┤
│ ✅ LPPLフィッティング         │ ✅ 多重時間窓の制御（126窓）     │
│ ✅ 非線形最適化               │ ✅ FCO標準フィルタリング         │
│ ✅ パラメータ推定             │ ✅ データ前処理（log変換）       │
│                               │ ✅ DS-LPPLS指標計算              │
│                               │ ✅ バブルタイプ判定              │
└─────────────────────────────────────────────────────────────────┘

【データフロー】
1. 前処理（prepare_observations）
   - 入力: 生の価格データまたはlog価格
   - 自動log変換判定（prices.max() > 10 で生データと判定）
   - 出力: 2xN形式（timestamps, log_prices）← Boulder lppls形式

2. 多重時間窓フィッティング（compute_ds_lppls_confidence）
   - FCO標準: 固定endpoint × 126窓（750→125日、5日刻み）
   - 各窓でBoulder lppls.fit()を呼び出し
   - ⚠️ compute_nested_fits()は使用しない（時系列分析用のため）

3. 後処理（_analyze_results）
   - FCO標準Damping計算: damping = m * |B| / (ω * |C|)
     ここで C = sqrt(c1² + c2²)
   - FCOフィルタリング条件適用:
     * Damping >= 1.0
     * 0.1 <= m <= 0.9
     * 2.0 <= ω <= 25.0
     * tc > t2（未来のtc）
   - DS-LPPLS Confidence計算: qualified_fits / total_windows

【重要な注意事項】
⚠️ Boulder lpplsの関数を直接変更しないこと
⚠️ フィルタリング条件はFCO標準に準拠（変更時は要検証）
⚠️ log変換は一度だけ適用（重複log変換を回避）

【参考文献】
- FCO公式手法: docs/fco_upgrade_v2/foundation/ds_lppls_indicators_detailed_specification.md
- Boulder lppls比較: docs/fco_upgrade_v2/foundation/comparison_fco_vs_current_implementation.md
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from lppls.lppls import LPPLS

# 既存の実装との互換性のため
from .fitter import LogarithmPeriodicFitter

# DS-LPPLS Confidence拡張実装
try:
    from core.fco_indicators.ds_lppls_confidence import DSLPPLSConfidenceCalculator
    HAS_ENHANCED_CONFIDENCE = True
except ImportError:
    HAS_ENHANCED_CONFIDENCE = False
    logger.warning("Enhanced DS-LPPLS Confidence calculator not available")

logger = logging.getLogger(__name__)


@dataclass
class FCOAnalysisResult:
    """FCO分析結果を格納するデータクラス"""
    ds_lppls_confidence: float  # 正のバブル信頼度
    ds_lppls_confidence_neg: float  # 負のバブル信頼度
    predicted_tc: Optional[float]  # 予測された臨界時間
    tc_std: Optional[float]  # 臨界時間の標準偏差
    scenario_probability: Optional[float]  # 最大クラスターのシナリオ確率
    window_results: List[Dict]  # 各窓の結果
    bubble_type: str  # 'positive', 'negative', or 'none'
    metadata: Dict[str, Any]  # その他のメタデータ


class FCOEngine:
    """
    FCO準拠の多重時間窓LPPLS分析エンジン
    126個の時間窓（125-750日）で同時分析を実行
    """
    
    # FCO標準パラメータ
    WINDOW_MIN = 125  # 最小窓サイズ（営業日）
    WINDOW_MAX = 750  # 最大窓サイズ（営業日）
    WINDOW_STEP = 5   # 窓の刻み幅
    
    # ========================================================================
    # FCO Filtering Condition 1 - フィルタリング条件（Boulder LPPLS完全準拠）
    # ========================================================================
    # 【重要】科学的信頼性に関わる設定 - むやみに変更しないこと
    #
    # 以下の閾値はBoulder LPPLS（FCO準拠実装）の標準値に**完全準拠**します。
    # 出典: /home/no-rules/.local/lib/python3.10/site-packages/lppls/lppls.py
    #        - Line 250-254: デフォルトフィルタリング条件
    #        - Line 293-318: フィルタリングロジック実装
    #        - Line 619-623: Oscillation & Damping計算式
    #
    # 【設定根拠】(Issue I124調査結果 2025-10-11)
    # 1. Damping (D) 閾値: 0.5 (Boulder標準)
    #    - 計算式: D = m * |B| / (ω * |C|), C = sqrt(c1² + c2²)
    #    - 科学的意味: クラッシュハザード率h(t)が非負であること
    #    - Boulder LPPLS: Line 254 "D_min = 0.5", Line 307 "D > D_min"
    #
    # 2. m範囲: 0.0 - 1.0 (Boulder標準)
    #    - べき乗指数の理論的範囲
    #    - Boulder LPPLS: Line 251 "m_min, m_max = (0.0, 1.0)"
    #    - 本実装: 0.0 < m < 1.0（境界値を除外、Line 298参照）
    #
    # 3. ω範囲: 2.0 - 15.0 (Boulder標準) ⚠️ 25.0から修正
    #    - 対数周期振動の角周波数範囲
    #    - Boulder LPPLS: Line 252 "w_min, w_max = (2.0, 15.0)"
    #    - 科学的意味: 観測可能な対数周期振動の範囲
    #
    # 4. Oscillation (O) 閾値: 2.5 (Boulder標準) 🆕 追加
    #    - 計算式: O = (ω / 2π) * log((tc - t1) / (tc - t2))
    #    - 科学的意味: 窓内の対数周期振動の回数
    #    - Boulder LPPLS: Line 253 "O_min = 2.5", Line 306 "O > O_min"
    #
    # 5. tc範囲条件 (Boulder標準) 🆕 根本的変更
    #    - Boulder LPPLS: Line 293-297
    #    - 条件: max(t2-60, t2-0.5*(t2-t1)) < tc < min(t2+252, t2+0.5*(t2-t1))
    #    - 科学的意味:
    #      a) 過去60日までのtcを許容（フィッティングの不確実性考慮）
    #      b) 未来252日（約1年）までの予測を許容
    #      c) 窓サイズの50%を前後の許容範囲とする
    #
    # 【Sornette論文の30日事前予測要件との関係】（重要な設計決定）
    # - 論文要件: tcと解析日が近すぎると精度低下（フィッティング関数の発散）
    # - 実装方針:
    #   a) Boulder条件: 統計的に安定したフィット（過去60日〜未来252日許容）
    #   b) Sornette要件: 予測精度保証のため tc >= t2 + 30日 を追加制約
    #   c) 最終判定: Boulder条件 AND Sornette要件 の両方を満たす必要あり
    # - 根拠: Boulderは事後分析も含むが、FCOは予測を目的とするため
    #
    # 【変更履歴】
    # - 2025-10-11 (1): Damping閾値を1.0→0.5に変更（Boulder標準準拠）
    # - 2025-10-11 (2): m上限を0.9→1.0に変更（Boulder標準準拠）
    # - 2025-10-11 (3): ω上限を25.0→15.0に変更（Boulder標準完全準拠）
    # - 2025-10-11 (4): Oscillation (O) 条件を追加（Boulder標準準拠）
    # - 2025-10-11 (5): tc条件をBoulder範囲条件に変更（重要な修正）
    # - 2025-10-11 (6): Sornette 30日事前予測要件を追加制約として実装（予測精度保証）
    # ========================================================================
    FILTER_DAMPING_MIN = 0.5    # Boulder LPPLS標準値
    FILTER_M_MIN = 0.0          # Boulder LPPLS標準値
    FILTER_M_MAX = 1.0          # Boulder LPPLS標準値
    FILTER_OMEGA_MIN = 2.0      # Boulder LPPLS標準値
    FILTER_OMEGA_MAX = 15.0     # Boulder LPPLS標準値（旧: 25.0）
    FILTER_OSCILLATION_MIN = 2.5  # Boulder LPPLS標準値（新規追加）

    # tc範囲パラメータ（Boulder LPPLS標準値）
    TC_RANGE_PAST_DAYS = 60     # tcの過去方向許容範囲（日数）
    TC_RANGE_FUTURE_DAYS = 252  # tcの未来方向許容範囲（日数、約1年）
    TC_RANGE_WINDOW_RATIO = 0.5 # 窓サイズに対する許容範囲比率

    # 🆕 Sornette論文の30日事前予測要件（Boulder条件への追加制約）
    # 出典: Sornette論文 - tcと解析日が近すぎると精度低下
    # 理由: クリティカルポイント付近でLPPLSフィッティング関数が発散するため
    # Boulder条件（過去60日許容）とは**別に**、予測目的では未来30日以上が必要
    MIN_TC_ADVANCE_DAYS = 30    # tc >= t2 + 30日（Sornette要件）
    
    def __init__(self, use_parallel: bool = True, max_workers: int = 8, use_enhanced_confidence: bool = True):
        """
        Args:
            use_parallel: 並列処理を使用するか
            max_workers: 並列処理のワーカー数
            use_enhanced_confidence: 拡張DS-LPPLS計算を使用するか
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        self.use_enhanced_confidence = use_enhanced_confidence and HAS_ENHANCED_CONFIDENCE
        
        # 論文再現テスト用に既存実装も保持
        self.classic_fitter = LogarithmPeriodicFitter()
        
        # 拡張DS-LPPLS計算機（利用可能な場合）
        if self.use_enhanced_confidence:
            self.enhanced_calculator = DSLPPLSConfidenceCalculator(
                max_window=self.WINDOW_MAX,
                min_window=self.WINDOW_MIN,
                step_size=self.WINDOW_STEP,
                n_workers=max_workers
            )
            logger.info(f"FCOEngine initialized with enhanced confidence calculator")
        
        logger.info(f"FCOEngine initialized (parallel={use_parallel}, workers={max_workers})")
    
    def prepare_observations(self, prices: np.ndarray, timestamps: Optional[np.ndarray] = None) -> np.ndarray:
        """
        価格データをLPPLS形式に変換

        Args:
            prices: 価格データ（生の価格またはlog価格）
            timestamps: タイムスタンプ（オプション）

        Returns:
            2xN形式の観測データ（時間、log価格）

        Note:
            LPPLモデルは対数価格に対してフィッティングを行います。
            このメソッドは自動的にlog変換を適用します。
        """
        n = len(prices)

        if timestamps is None:
            # タイムスタンプがない場合は連番を使用
            timestamps = np.arange(n)

        # Log変換を適用
        # 価格が既にlog変換されている場合（値が小さい場合）は、そのまま使用
        if prices.max() > 10:  # 生の価格データと判定（例: 100.0）
            log_prices = np.log(prices)
            logger.debug(f"Applied log transformation: price range {prices.min():.2f}-{prices.max():.2f} -> log range {log_prices.min():.4f}-{log_prices.max():.4f}")
        else:  # 既にlog変換済みと判定（例: 4.605）
            log_prices = prices
            logger.debug(f"Input appears to be already log-transformed: range {prices.min():.4f}-{prices.max():.4f}")

        # 2xN形式に変換（Boulder lppls形式）
        observations = np.array([timestamps, log_prices])

        return observations
    
    def compute_ds_lppls_confidence(self, prices: np.ndarray, 
                                   timestamps: Optional[np.ndarray] = None) -> FCOAnalysisResult:
        """
        FCO準拠のDS-LPPLS Confidence指標を計算
        
        Args:
            prices: 価格データ
            timestamps: タイムスタンプ（オプション）
        
        Returns:
            FCO分析結果
        """
        # データ準備
        observations = self.prepare_observations(prices, timestamps)
        
        # 十分なデータがあるか確認
        if len(prices) < self.WINDOW_MAX:
            logger.warning(f"Insufficient data: {len(prices)} < {self.WINDOW_MAX}")
            # データが不足している場合は窓サイズを調整
            adjusted_max = len(prices) - 20  # 余裕を持たせる
            window_sizes = range(self.WINDOW_MIN, adjusted_max, self.WINDOW_STEP)
        else:
            # FCO標準の126窓
            window_sizes = range(self.WINDOW_MIN, self.WINDOW_MAX + 1, self.WINDOW_STEP)
        
        logger.info(f"Analyzing with {len(window_sizes)} windows")
        
        # Boulder lpplsモデルを初期化
        lppls_model = LPPLS(observations)
        
        # 多重時間窓分析を実行（FCO標準: 固定endpointで126窓）
        # ⚠️ compute_nested_fits()は時系列分析用（nested構造）であり、
        # FCO標準の多重窓同時分析には適していない
        results = []
        max_window = self.WINDOW_MAX if len(prices) >= self.WINDOW_MAX else adjusted_max

        # FCO標準: 固定endpointで窓サイズのみ変化（126窓）
        # 750, 745, 740, ..., 130, 125 の126窓
        for window_size in range(max_window, self.WINDOW_MIN - 1, -self.WINDOW_STEP):
            if window_size > len(prices):
                logger.warning(f"Skipping window {window_size}: insufficient data ({len(prices)} points)")
                continue

            # 固定endpoint（最新日）から遡って window_size 分のデータを切り出し
            window_observations = observations[:, -window_size:]

            try:
                # 🆕 多重試行 + tc未来制約フィルタリング
                # Boulder LPPLSのtc初期化範囲が過去も許容するため（t2 ± 0.2Δt）、
                # 複数回試行してtc >= t2 + MIN_TC_ADVANCE_DAYSを満たす最良フィットを選択
                fit_params = self._fit_lppls_with_future_constraint(
                    window_observations,
                    max_searches=25
                )

                if fit_params is None:
                    # tc未来制約を満たすフィットなし
                    logger.debug(f"Window {window_size}: No future-constrained fit found")
                    continue

                # FCO形式に変換
                t1 = len(prices) - window_size
                t2 = len(prices) - 1

                # window_size情報を追加
                fit_params['window_size'] = window_size
                fit_params['window_start_idx'] = t1
                fit_params['window_end_idx'] = t2

                result = {
                    't1': t1,
                    't2': t2,
                    'res': [fit_params]  # Boulder形式に合わせてリスト化
                }

                results.append(result)

            except Exception as e:
                logger.warning(f"Window size {window_size} fitting failed: {e}")
                continue

        # DS-LPPLS指標を計算
        # ⚠️ Boulder LPPLSの compute_indicators()は nested_fits() 形式を期待するため使用不可
        # 独自実装の _analyze_results() を使用

        # 結果を解析（Boulder indicators不使用）
        return self._analyze_results(None, results)

    def _fit_lppls_with_future_constraint(
        self,
        observations: np.ndarray,
        max_searches: int = 25
    ) -> Optional[Dict[str, float]]:
        """
        未来予測を保証するLPPLSフィッティング

        Boulder LPPLSのtc初期化範囲が過去も許容するため（lppls.py:136で tc ∈ [t2-0.2Δt, t2+0.2Δt]）、
        複数回試行してtc >= t2 + MIN_TC_ADVANCE_DAYSを満たす最良フィットを選択する。

        根拠:
        - Boulder LPPLS実験結果: 1000日窓でtc=955（過去44日）が頻出
        - Sornette論文要件: tc >= t2 + 30日（フィッティング関数の発散防止）
        - 過去の成功実装: 明示的境界条件でtc未来保証

        実装戦略:
        1. max_searches回試行（各試行でランダム初期化）
        2. 各試行でtc >= t2 + MIN_TC_ADVANCE_DAYSをチェック
        3. 条件を満たす中でR²最大のフィットを選択

        Args:
            observations: 2xN numpy array [timestamps, log_prices]
            max_searches: 試行回数（デフォルト25）

        Returns:
            最良フィットパラメータ辞書、または None（適格フィットなし）
        """
        t2 = observations[0, -1]
        best_fit = None
        best_r2 = -np.inf

        for attempt in range(max_searches):
            try:
                # 個別LPPLS instance（試行ごとに初期化→ランダム初期値）
                lppls_model = LPPLS(observations)
                lppls_model.fit(max_searches=1, minimizer='Nelder-Mead')

                fit_params = lppls_model.coef_.copy() if hasattr(lppls_model, 'coef_') else {}
                tc = fit_params.get('tc', 0)

                # Sornette 30日要件チェック
                if tc < t2 + self.MIN_TC_ADVANCE_DAYS:
                    continue  # 棄却

                # R²計算（フィット品質評価）
                try:
                    fitted_values = np.array([
                        lppls_model.lppls(
                            t, tc,
                            fit_params.get('m', 0), fit_params.get('w', 0),
                            fit_params.get('a', 0), fit_params.get('b', 0),
                            fit_params.get('c1', 0), fit_params.get('c2', 0)
                        )
                        for t in observations[0, :]
                    ])

                    ss_res = np.sum((observations[1, :] - fitted_values) ** 2)
                    ss_tot = np.sum((observations[1, :] - np.mean(observations[1, :])) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else -np.inf
                except:
                    r2 = -np.inf

                # 最良フィット更新
                if r2 > best_r2:
                    best_r2 = r2
                    fit_params['r2'] = r2
                    best_fit = fit_params

            except Exception as e:
                # フィッティング失敗時はスキップ
                continue

        return best_fit

    def _analyze_results(self, indicators: pd.DataFrame, raw_results: List) -> FCOAnalysisResult:
        """
        分析結果を解析してFCO形式に整形
        
        Args:
            indicators: Boulder lpplsの指標
            raw_results: 生の分析結果
        
        Returns:
            FCO分析結果
        """
        # 手動でDS-LPPLS計算（indicatorsが正しく機能しない場合の対策）
        positive_count = 0
        negative_count = 0
        qualified_fits = []
        all_window_fits = []  # 全窓結果を保存（移行戦略に従う）
        tc_values = []
        total_windows = 0
        
        # resultsの構造を正しく解析
        for result_dict in raw_results:
            if isinstance(result_dict, dict) and 'res' in result_dict:
                total_windows += 1
                fits = result_dict.get('res', [])
                t1 = result_dict.get('t1', 0)
                t2 = result_dict.get('t2', 0)
                window_size = t2 - t1 if t2 > t1 else 0
                
                if isinstance(fits, list):
                    for fit in fits:
                        if isinstance(fit, dict):
                            m = fit.get('m', 0)
                            w = fit.get('w', 0)
                            tc = fit.get('tc', 0)
                            B = fit.get('b', 0)
                            c1 = fit.get('c1', 0)
                            c2 = fit.get('c2', 0)

                            # Boulder LPPLS標準のOscillation (O) 計算
                            # O = (ω / 2π) * log((tc - t1) / (tc - t2))
                            # 出典: lppls.py Line 619-620
                            if (tc - t2) != 0 and (tc - t1) / (tc - t2) > 0:
                                O = (w / (2.0 * np.pi)) * np.log((tc - t1) / (tc - t2))
                            else:
                                O = np.inf  # Boulder標準: 計算不可の場合は無限大

                            # Boulder LPPLS標準のDamping (D) 計算
                            # D = m * |B| / (ω * |C|)
                            # ここで C = sqrt(c1^2 + c2^2)
                            # 出典: lppls.py Line 622-623
                            C = np.sqrt(c1**2 + c2**2)
                            if C != 0 and w != 0:
                                damping = m * abs(B) / (w * abs(C))
                            else:
                                damping = 0

                            # Boulder LPPLS標準のtc範囲条件
                            # max(t2 - 60, t2 - 0.5*(t2 - t1)) < tc < min(t2 + 252, t2 + 0.5*(t2 - t1))
                            # 出典: lppls.py Line 293-297
                            tc_lower = max(t2 - self.TC_RANGE_PAST_DAYS,
                                         t2 - self.TC_RANGE_WINDOW_RATIO * (t2 - t1))
                            tc_upper = min(t2 + self.TC_RANGE_FUTURE_DAYS,
                                         t2 + self.TC_RANGE_WINDOW_RATIO * (t2 - t1))
                            tc_in_range = tc_lower < tc < tc_upper

                            # Sornette論文の30日事前予測要件
                            # tcと解析日が近すぎると精度低下（フィッティング関数の発散）
                            # Boulder条件に加えて、予測目的では tc >= t2 + 30日が必要
                            tc_advance_sufficient = (tc - t2) >= self.MIN_TC_ADVANCE_DAYS

                            # 統合フィルタリング条件（Boulder LPPLS標準 + Sornette要件）
                            # Boulder条件: 統計的に安定したフィット
                            # Sornette要件: 予測精度を保証する事前予測期間
                            is_qualified = (
                                tc_in_range and                              # Boulder: tc範囲条件
                                self.FILTER_M_MIN < m < self.FILTER_M_MAX and  # Boulder: m範囲
                                self.FILTER_OMEGA_MIN < w < self.FILTER_OMEGA_MAX and  # Boulder: ω範囲
                                O > self.FILTER_OSCILLATION_MIN and          # Boulder: Oscillation
                                damping > self.FILTER_DAMPING_MIN and        # Boulder: Damping
                                tc_advance_sufficient                         # Sornette: 30日事前予測要件
                            )
                            
                            # 全窓結果を保存（データベース移行戦略に従う）
                            window_fit = {
                                **fit,  # 既存のフィットパラメータ
                                'window_size': window_size,
                                'window_start_idx': t1,
                                'window_end_idx': t2,
                                'oscillation': O,  # Boulder LPPLS標準指標
                                'damping': damping,
                                'is_qualified': is_qualified
                            }
                            all_window_fits.append(window_fit)
                            
                            if is_qualified:
                                qualified_fits.append(fit)
                                tc_values.append(tc)
                                if m > 0:
                                    positive_count += 1
                                else:
                                    negative_count += 1
                                break  # 各窓から最初の適合フィットのみ使用
        
        # DS-LPPLS信頼度計算
        if total_windows > 0:
            pos_conf = positive_count / total_windows
            neg_conf = negative_count / total_windows
        else:
            # indicatorsから取得（フォールバック）
            if len(indicators) > 0:
                latest = indicators.iloc[-1]
                pos_conf = latest.get('pos_conf', 0.0)
                neg_conf = latest.get('neg_conf', 0.0)
            else:
                pos_conf = 0.0
                neg_conf = 0.0
        
        # bubble_type判定（アプリケーション層での実装）
        # ========================================================
        # 重要: Boulder LPPLSライブラリとの関係性について
        # ========================================================
        # Boulder LPPLSライブラリ（lppls）自体にはbubble_type判定機能は
        # 含まれていません。Boulder LPPLSはDS-LPPLS Confidence計算のみを
        # 提供し、閾値判定はユーザー側で実装する必要があります。
        #
        # 以下の閾値はETH Zurich FCO（Financial Crisis Observatory）の
        # 公式基準に基づいています：
        # - 30%閾値: FCO公開レポートで中程度のバブルと定義
        # - 5%閾値: FCO実装で弱いシグナルと定義
        #
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
            window_results=all_window_fits,  # 全窓結果を保存（移行戦略に従う）
            bubble_type=bubble_type,
            metadata={
                'num_windows': total_windows,
                'qualified_fits': len(qualified_fits),
                'total_fits': len(all_window_fits),
                'analysis_date': pd.Timestamp.now().isoformat()
            }
        )
        
        logger.info(f"FCO Analysis complete: confidence={pos_conf:.2%}, type={bubble_type}")
        
        return result
    
    def validate_paper_reproduction(self, prices: np.ndarray, 
                                   test_case: str = '1987') -> Dict[str, Any]:
        """
        論文再現テスト用の単一窓分析
        
        Args:
            prices: 価格データ
            test_case: テストケース名
        
        Returns:
            検証結果
        """
        logger.info(f"Running paper reproduction test: {test_case}")
        
        # 単一窓での分析（論文準拠）
        observations = self.prepare_observations(prices)
        lppls_model = LPPLS(observations)
        
        # 単一フィットを実行
        # 初期値は論文準拠
        lppls_model.fit(
            max_searches=25,
            minimizer='Nelder-Mead',
            obs=observations
        )
        
        # 結果を取得
        params = lppls_model.coef_
        
        # 論文値との比較
        if test_case == '1987':
            # 論文報告値
            expected_m = 0.33
            m_tolerance = 0.03
            expected_omega_range = (6.0, 8.0)
            
            # パラメータチェック
            m_check = abs(params.get('m', 0) - expected_m) <= m_tolerance
            omega_check = expected_omega_range[0] <= params.get('w', 0) <= expected_omega_range[1]
            
            # スコア計算（簡易版）
            score = 0
            if m_check:
                score += 50
            if omega_check:
                score += 50
            
            result = {
                'score': score,
                'parameters': params,
                'm_check': m_check,
                'omega_check': omega_check,
                'status': 'PASSED' if score == 100 else 'FAILED'
            }
        else:
            result = {
                'score': 0,
                'parameters': params,
                'status': 'NOT_IMPLEMENTED'
            }
        
        logger.info(f"Paper reproduction test result: {result['status']} (score={result['score']})")
        
        return result
    
    def fit_single_window(self, prices: np.ndarray, 
                         window_size: Optional[int] = None) -> Dict[str, Any]:
        """
        単一時間窓でのフィッティング（互換性用）
        
        Args:
            prices: 価格データ
            window_size: 窓サイズ（Noneの場合は全データ）
        
        Returns:
            フィッティング結果
        """
        if window_size and len(prices) > window_size:
            prices = prices[-window_size:]
        
        observations = self.prepare_observations(prices)
        lppls_model = LPPLS(observations)
        
        # フィッティング実行
        lppls_model.fit(max_searches=25)
        
        return lppls_model.coef_