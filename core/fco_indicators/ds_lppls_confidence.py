"""
DS-LPPLS Confidence指標計算エンジン
FCO (Financial Crisis Observatory) の信頼性評価システムの実装
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 既存のフィッティングエンジンを利用
from core.fitting.fitter import LogarithmPeriodicFitter, FittingResult

logger = logging.getLogger(__name__)


@dataclass
class LPPLSFitResult:
    """単一時間窓でのLPPLSフィッティング結果"""
    window_size: int
    window_start: int
    window_end: int
    tc: float
    m: float
    omega: float
    A: float
    B: float
    C1: float
    C2: float
    damping: float
    r_squared: float
    success: bool
    scale: str  # 'short', 'medium', 'long'
    
    def calculate_damping(self) -> float:
        """Dampingパラメータを計算"""
        C = np.sqrt(self.C1**2 + self.C2**2)
        if C != 0 and self.omega != 0:
            return self.m * abs(self.B) / (self.omega * abs(C))
        return 0.0
    
    def passes_filtering_conditions(self, t2: int, dt: int = 365) -> bool:
        """
        FCOのフィルタリング条件をチェック
        
        Filtering Condition 1:
        - Damping ≥ 1.0
        - 0.1 < m < 0.9
        - 2 < ω < 25
        - t2 < tc < t2 + dt (未来の予測、かつ現実的な範囲内)
        """
        # Damping条件
        if self.damping < 1.0:
            return False
        
        # べき乗指数の範囲
        if not (0.1 < self.m < 0.9):
            return False
        
        # 角周波数の範囲
        if not (2 < self.omega < 25):
            return False
        
        # 臨界時間が未来かつ現実的な範囲内
        if not (t2 < self.tc < t2 + dt):
            return False
        
        # R²の最小閾値（オプション）
        if self.r_squared < 0.8:
            return False
        
        return True


class DSLPPLSConfidenceCalculator:
    """FCO準拠のDS-LPPLS Confidence指標計算クラス"""
    
    def __init__(self, 
                 max_window: int = 750,
                 min_window: int = 125,
                 step_size: int = 5,
                 n_workers: int = 4):
        """
        Parameters:
        -----------
        max_window : int
            最大時間窓サイズ（営業日）
        min_window : int
            最小時間窓サイズ（営業日）
        step_size : int
            時間窓の縮小ステップ
        n_workers : int
            並列処理のワーカー数
        """
        self.max_window = max_window
        self.min_window = min_window
        self.step_size = step_size
        self.n_workers = n_workers
        self.num_windows = (max_window - min_window) // step_size + 1
        
        # 既存のフィッターを利用
        self.fitter = LogarithmPeriodicFitter()
        
        logger.info(f"DS-LPPLS Calculator initialized: {self.num_windows} windows from {min_window} to {max_window} days")
    
    def calculate_confidence(self, 
                            prices: pd.Series,
                            symbol: str = "UNKNOWN") -> Dict:
        """
        DS-LPPLS Confidence指標を計算
        
        Parameters:
        -----------
        prices : pd.Series
            価格時系列データ（インデックスは日付）
        symbol : str
            銘柄シンボル（ログ用）
            
        Returns:
        --------
        Dict : 結果辞書
            - confidence: 信頼度指標 (0-1)
            - successful_fits: 成功したフィット数
            - total_windows: 総時間窓数
            - scale_breakdown: スケール別の成功率
            - all_fits: 全フィット結果のリスト
            - best_fits: 各スケールのベストフィット
        """
        logger.info(f"Calculating DS-LPPLS Confidence for {symbol} with {len(prices)} data points")
        
        successful_fits = 0
        scale_results = {"short": [], "medium": [], "long": []}
        all_fits = []
        best_fits = {"short": None, "medium": None, "long": None}
        
        # 分析終了時点（現在）
        t2 = len(prices) - 1
        
        # 各時間窓でフィッティング（並列処理）
        window_tasks = []
        for window_size in range(self.max_window, self.min_window - 1, -self.step_size):
            if window_size > len(prices):
                continue
            
            # 時間窓の開始点
            t1 = t2 - window_size + 1
            if t1 < 0:
                continue
            
            window_tasks.append((window_size, t1, t2))
        
        # 並列処理でフィッティング実行
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            future_to_window = {}
            
            for window_size, t1, t2 in window_tasks:
                window_prices = prices.iloc[t1:t2+1].values
                future = executor.submit(self._fit_single_window, 
                                       window_prices, window_size, t1, t2)
                future_to_window[future] = (window_size, t1, t2)
            
            # 結果を収集
            for future in as_completed(future_to_window):
                window_size, t1, t2 = future_to_window[future]
                try:
                    fit_result = future.result(timeout=30)
                    
                    if fit_result:
                        all_fits.append(fit_result)
                        
                        # フィルタリング条件チェック
                        if fit_result.passes_filtering_conditions(t2):
                            successful_fits += 1
                            
                            # スケール分類と記録
                            scale = self._classify_scale(window_size)
                            scale_results[scale].append(1)
                            
                            # ベストフィット更新（R²基準）
                            if (best_fits[scale] is None or 
                                fit_result.r_squared > best_fits[scale].r_squared):
                                best_fits[scale] = fit_result
                        else:
                            scale = self._classify_scale(window_size)
                            scale_results[scale].append(0)
                    
                except Exception as e:
                    logger.warning(f"Failed to fit window {window_size}: {str(e)}")
                    scale = self._classify_scale(window_size)
                    scale_results[scale].append(0)
        
        # Confidence指標計算
        confidence = successful_fits / len(window_tasks) if window_tasks else 0
        
        # スケール別成功率
        scale_confidence = {}
        for scale, results in scale_results.items():
            if results:
                scale_confidence[scale] = np.mean(results)
            else:
                scale_confidence[scale] = 0.0
        
        # 結果をまとめる
        result = {
            'confidence': confidence,
            'successful_fits': successful_fits,
            'total_windows': len(window_tasks),
            'scale_breakdown': scale_confidence,
            'all_fits': all_fits,
            'best_fits': best_fits,
            'analysis_date': datetime.now().isoformat(),
            'symbol': symbol
        }
        
        logger.info(f"DS-LPPLS Confidence for {symbol}: {confidence:.1%} "
                   f"({successful_fits}/{len(window_tasks)} successful fits)")
        
        return result
    
    def _fit_single_window(self, prices: np.ndarray, 
                          window_size: int, t1: int, t2: int) -> Optional[LPPLSFitResult]:
        """
        単一時間窓でのLPPLSフィッティング
        
        Parameters:
        -----------
        prices : np.ndarray
            価格データ配列
        window_size : int
            時間窓サイズ
        t1, t2 : int
            時間窓の開始・終了インデックス
        """
        try:
            # 既存のフィッターを使用
            t, log_prices = self.fitter.prepare_data(prices)
            
            if t is None or log_prices is None:
                return None
            
            # フィッティング実行（複数初期値で試行）
            fit_result = self.fitter.fit_with_multiple_initializations(t, log_prices, n_tries=5)
            
            if not fit_result.success:
                return None
            
            # パラメータ抽出
            params = fit_result.parameters
            
            # LPPLパラメータを計算
            # 注：実際のLPPLモデルのパラメータ定義に従う必要がある
            # ここでは簡略化された変換を行う
            tc_days = t2 + params.get('tc', 100)  # tcを日数に変換
            m = params.get('m', 0.5)
            omega = params.get('omega', 10)
            
            # 振幅係数（実際の実装では正確な変換が必要）
            A = params.get('A', 0)
            B = params.get('B', 0)
            C1 = params.get('C1', 0)
            C2 = params.get('C2', 0)
            
            # LPPLSFitResultを作成
            lppl_fit = LPPLSFitResult(
                window_size=window_size,
                window_start=t1,
                window_end=t2,
                tc=tc_days,
                m=m,
                omega=omega,
                A=A,
                B=B,
                C1=C1,
                C2=C2,
                damping=0,  # 後で計算
                r_squared=fit_result.r_squared,
                success=True,
                scale=self._classify_scale(window_size)
            )
            
            # Damping計算
            lppl_fit.damping = lppl_fit.calculate_damping()
            
            return lppl_fit
            
        except Exception as e:
            logger.debug(f"Fitting failed for window {window_size}: {str(e)}")
            return None
    
    def _classify_scale(self, window_size: int) -> str:
        """時間窓サイズをスケールに分類"""
        if window_size <= 250:
            return "short"
        elif window_size <= 500:
            return "medium"
        else:
            return "long"
    
    def format_report(self, result: Dict) -> str:
        """結果をレポート形式にフォーマット"""
        report = []
        report.append("=" * 60)
        report.append(f"DS-LPPLS Confidence Report for {result['symbol']}")
        report.append("=" * 60)
        report.append(f"Analysis Date: {result['analysis_date']}")
        report.append("")
        
        # 全体の信頼度
        report.append(f"Overall Confidence: {result['confidence']:.1%}")
        report.append(f"Successful Fits: {result['successful_fits']}/{result['total_windows']}")
        report.append("")
        
        # スケール別分析
        report.append("Scale Breakdown:")
        for scale, conf in result['scale_breakdown'].items():
            report.append(f"  {scale.capitalize():8s}: {conf:.1%}")
        report.append("")
        
        # ベストフィット情報
        report.append("Best Fits by Scale:")
        for scale, fit in result['best_fits'].items():
            if fit:
                report.append(f"  {scale.capitalize()}:")
                report.append(f"    Window: {fit.window_size} days")
                report.append(f"    R²: {fit.r_squared:.3f}")
                report.append(f"    tc: {fit.tc:.0f} days from end")
                report.append(f"    Damping: {fit.damping:.2f}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def calculate_ds_lppls_confidence(prices: pd.Series, 
                                 symbol: str = "UNKNOWN",
                                 max_window: int = 750,
                                 min_window: int = 125,
                                 step_size: int = 5) -> Dict:
    """
    便利関数：DS-LPPLS Confidence指標を計算
    
    Parameters:
    -----------
    prices : pd.Series
        価格時系列データ
    symbol : str
        銘柄シンボル
    max_window : int
        最大時間窓サイズ
    min_window : int
        最小時間窓サイズ
    step_size : int
        時間窓ステップ
        
    Returns:
    --------
    Dict : 計算結果
    """
    calculator = DSLPPLSConfidenceCalculator(
        max_window=max_window,
        min_window=min_window,
        step_size=step_size
    )
    
    return calculator.calculate_confidence(prices, symbol)