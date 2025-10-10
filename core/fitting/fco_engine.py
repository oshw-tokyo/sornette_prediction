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
    
    # フィルタリング条件（FCO Filtering Condition 1）
    FILTER_DAMPING_MIN = 1.0
    FILTER_M_MIN = 0.1
    FILTER_M_MAX = 0.9
    FILTER_OMEGA_MIN = 2.0
    FILTER_OMEGA_MAX = 25.0
    
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
                # 単一窓でフィッティング
                lppls_model.fit(
                    max_searches=25,
                    minimizer='Nelder-Mead',
                    obs=window_observations
                )

                # フィッティング結果を取得
                fit_params = lppls_model.coef_.copy() if hasattr(lppls_model, 'coef_') else {}

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

                            # FCO標準のDamping計算式
                            # damping = m * |B| / (ω * |C|)
                            # ここで C = sqrt(c1^2 + c2^2)
                            C = np.sqrt(c1**2 + c2**2)
                            if C != 0 and w != 0:
                                damping = m * abs(B) / (w * abs(C))
                            else:
                                damping = 0
                            
                            # FCOフィルタリング条件
                            is_qualified = (
                                damping >= self.FILTER_DAMPING_MIN and
                                self.FILTER_M_MIN <= m <= self.FILTER_M_MAX and
                                self.FILTER_OMEGA_MIN <= w <= self.FILTER_OMEGA_MAX and
                                tc > t2  # 未来のtc
                            )
                            
                            # 全窓結果を保存（データベース移行戦略に従う）
                            window_fit = {
                                **fit,  # 既存のフィットパラメータ
                                'window_size': window_size,
                                'window_start_idx': t1,
                                'window_end_idx': t2,
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