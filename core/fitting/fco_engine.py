"""
FCO (Financial Crisis Observatory) スタイルの多重時間窓LPPLS分析エンジン
Boulder Investment Technologies のlpplsライブラリを活用した実装
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from lppls.lppls import LPPLS

# 既存の実装との互換性のため
from .fitter import LogarithmPeriodicFitter

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
    
    def __init__(self, use_parallel: bool = True, max_workers: int = 8):
        """
        Args:
            use_parallel: 並列処理を使用するか
            max_workers: 並列処理のワーカー数
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        
        # 論文再現テスト用に既存実装も保持
        self.classic_fitter = LogarithmPeriodicFitter()
        
        logger.info(f"FCOEngine initialized (parallel={use_parallel}, workers={max_workers})")
    
    def prepare_observations(self, prices: np.ndarray, timestamps: Optional[np.ndarray] = None) -> np.ndarray:
        """
        価格データをLPPLS形式に変換
        
        Args:
            prices: 価格データ
            timestamps: タイムスタンプ（オプション）
        
        Returns:
            2xN形式の観測データ（時間、価格）
        """
        n = len(prices)
        
        if timestamps is None:
            # タイムスタンプがない場合は連番を使用
            timestamps = np.arange(n)
        
        # 2xN形式に変換（Boulder lppls形式）
        observations = np.array([timestamps, prices])
        
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
        
        # 多重時間窓分析を実行
        if self.use_parallel:
            # 並列処理版
            results = lppls_model.mp_compute_nested_fits(
                workers=self.max_workers,
                window_size=self.WINDOW_MAX if len(prices) >= self.WINDOW_MAX else adjusted_max,
                smallest_window_size=self.WINDOW_MIN,
                outer_increment=self.WINDOW_STEP,
                inner_increment=self.WINDOW_STEP,
                max_searches=25
            )
        else:
            # 逐次処理版
            results = lppls_model.compute_nested_fits(
                window_size=self.WINDOW_MAX if len(prices) >= self.WINDOW_MAX else adjusted_max,
                smallest_window_size=self.WINDOW_MIN,
                outer_increment=self.WINDOW_STEP,
                inner_increment=self.WINDOW_STEP,
                max_searches=25
            )
        
        # DS-LPPLS指標を計算
        indicators = lppls_model.compute_indicators(results)
        
        # 結果を解析
        return self._analyze_results(indicators, results)
    
    def _analyze_results(self, indicators: pd.DataFrame, raw_results: List) -> FCOAnalysisResult:
        """
        分析結果を解析してFCO形式に整形
        
        Args:
            indicators: Boulder lpplsの指標
            raw_results: 生の分析結果
        
        Returns:
            FCO分析結果
        """
        # 最新の指標値を取得
        if len(indicators) > 0:
            latest = indicators.iloc[-1]
            pos_conf = latest.get('pos_conf', 0.0)
            neg_conf = latest.get('neg_conf', 0.0)
        else:
            pos_conf = 0.0
            neg_conf = 0.0
        
        # バブルタイプを判定
        if pos_conf > 0.3:  # FCO閾値: 30%以上で中程度のバブル
            bubble_type = 'positive'
        elif neg_conf > 0.3:
            bubble_type = 'negative'
        else:
            bubble_type = 'none'
        
        # tc値のクラスタリング（簡易版）
        # TODO: k-meansクラスタリング実装
        tc_values = []
        for result_set in raw_results:
            if isinstance(result_set, list):
                for res in result_set:
                    if isinstance(res, dict) and res.get('is_qualified', False):
                        tc_values.append(res.get('tc', 0))
        
        if tc_values:
            predicted_tc = np.median(tc_values)
            tc_std = np.std(tc_values)
            scenario_probability = len(tc_values) / (len(window_sizes) if 'window_sizes' in locals() else 126)
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
            window_results=raw_results if isinstance(raw_results, list) else [],
            bubble_type=bubble_type,
            metadata={
                'num_windows': len(indicators),
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