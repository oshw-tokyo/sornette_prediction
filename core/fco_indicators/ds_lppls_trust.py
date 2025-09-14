"""
DS-LPPLS Trust指標計算エンジン
ブートストラップ法による統計的信頼性評価
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# DS-LPPLS Confidence計算機を利用
from .ds_lppls_confidence import DSLPPLSConfidenceCalculator, LPPLSFitResult

logger = logging.getLogger(__name__)


@dataclass
class TrustResult:
    """Trust指標計算結果"""
    trust_score: float  # 0-1のTrust指標
    confidence_mean: float  # ブートストラップでの平均Confidence
    confidence_std: float  # Confidenceの標準偏差
    n_bootstrap: int  # ブートストラップ回数
    successful_bootstraps: int  # 成功したブートストラップ数
    metadata: Dict  # その他のメタデータ


class DSLPPLSTrustCalculator:
    """
    FCO準拠のDS-LPPLS Trust指標計算クラス
    ブートストラップ法による統計的信頼性評価
    """
    
    def __init__(self, 
                 n_bootstrap: int = 100,
                 block_size: int = 20,
                 confidence_calculator: Optional[DSLPPLSConfidenceCalculator] = None,
                 n_workers: int = 4):
        """
        Parameters:
        -----------
        n_bootstrap : int
            ブートストラップサンプル数
        block_size : int
            ブロックブートストラップのブロックサイズ
        confidence_calculator : DSLPPLSConfidenceCalculator
            Confidence計算機（Noneの場合は内部で生成）
        n_workers : int
            並列処理のワーカー数
        """
        self.n_bootstrap = n_bootstrap
        self.block_size = block_size
        self.n_workers = n_workers
        
        # Confidence計算機
        if confidence_calculator is None:
            self.confidence_calculator = DSLPPLSConfidenceCalculator(
                max_window=750,
                min_window=125,
                step_size=5,
                n_workers=1  # 各ブートストラップ内では並列化しない
            )
        else:
            self.confidence_calculator = confidence_calculator
        
        logger.info(f"DS-LPPLS Trust Calculator initialized: {n_bootstrap} bootstraps")
    
    def calculate_trust(self, 
                       prices: pd.Series,
                       symbol: str = "UNKNOWN",
                       method: str = "block") -> TrustResult:
        """
        DS-LPPLS Trust指標を計算
        
        Parameters:
        -----------
        prices : pd.Series
            価格時系列データ（インデックスは日付）
        symbol : str
            銘柄シンボル（ログ用）
        method : str
            ブートストラップ方法 ('block' or 'residual')
            
        Returns:
        --------
        TrustResult : Trust指標計算結果
        """
        logger.info(f"Calculating DS-LPPLS Trust for {symbol} using {method} bootstrap")
        
        # 元のデータでConfidence計算
        original_confidence = self.confidence_calculator.calculate_confidence(prices, symbol)
        original_conf_value = original_confidence['confidence']
        
        # ブートストラップサンプルでのConfidence値を収集
        bootstrap_confidences = []
        successful_bootstraps = 0
        
        # 並列処理でブートストラップ実行
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = []
            
            for i in range(self.n_bootstrap):
                if method == "block":
                    synthetic_prices = self._block_bootstrap(prices)
                else:  # residual
                    synthetic_prices = self._residual_bootstrap(prices)
                
                future = executor.submit(
                    self._calculate_single_bootstrap,
                    synthetic_prices, f"{symbol}_boot_{i}"
                )
                futures.append(future)
            
            # 結果を収集
            for future in as_completed(futures):
                try:
                    conf_value = future.result(timeout=60)
                    if conf_value is not None:
                        bootstrap_confidences.append(conf_value)
                        successful_bootstraps += 1
                except Exception as e:
                    logger.warning(f"Bootstrap calculation failed: {str(e)}")
        
        # Trust指標を計算
        if bootstrap_confidences:
            confidence_array = np.array(bootstrap_confidences)
            
            # Trust = ブートストラップ分布での元の値の位置
            # 元の値より低い値の割合（元の結果の信頼性）
            trust_score = np.mean(confidence_array <= original_conf_value)
            
            # 統計量計算
            confidence_mean = np.mean(confidence_array)
            confidence_std = np.std(confidence_array)
        else:
            # ブートストラップが全て失敗した場合
            trust_score = 0.0
            confidence_mean = 0.0
            confidence_std = 0.0
        
        # 結果をまとめる
        result = TrustResult(
            trust_score=trust_score,
            confidence_mean=confidence_mean,
            confidence_std=confidence_std,
            n_bootstrap=self.n_bootstrap,
            successful_bootstraps=successful_bootstraps,
            metadata={
                'original_confidence': original_conf_value,
                'bootstrap_method': method,
                'block_size': self.block_size if method == "block" else None,
                'symbol': symbol,
                'confidence_distribution': bootstrap_confidences
            }
        )
        
        logger.info(f"DS-LPPLS Trust for {symbol}: {trust_score:.1%} "
                   f"(original conf: {original_conf_value:.1%}, "
                   f"mean boot conf: {confidence_mean:.1%})")
        
        return result
    
    def _block_bootstrap(self, prices: pd.Series) -> pd.Series:
        """
        ブロックブートストラップで合成時系列を生成
        時系列の相関構造を保持
        
        Parameters:
        -----------
        prices : pd.Series
            元の価格時系列
            
        Returns:
        --------
        pd.Series : 合成価格時系列
        """
        n = len(prices)
        returns = prices.pct_change().dropna()
        
        # ブロック数を計算
        n_blocks = n // self.block_size + 1
        
        # ランダムにブロックを選択
        synthetic_returns = []
        for _ in range(n_blocks):
            # ランダムな開始位置
            start_idx = np.random.randint(0, len(returns) - self.block_size + 1)
            block = returns.iloc[start_idx:start_idx + self.block_size].values
            synthetic_returns.extend(block)
        
        # 元のデータと同じ長さに調整
        synthetic_returns = synthetic_returns[:len(returns)]
        
        # 価格に変換
        synthetic_prices = [prices.iloc[0]]
        for ret in synthetic_returns:
            synthetic_prices.append(synthetic_prices[-1] * (1 + ret))
        
        # 元のインデックスを使用してSeriesを作成
        return pd.Series(synthetic_prices[:n], index=prices.index)
    
    def _residual_bootstrap(self, prices: pd.Series) -> pd.Series:
        """
        残差リサンプリングで合成時系列を生成
        トレンドを保持しながらランダム性を追加
        
        Parameters:
        -----------
        prices : pd.Series
            元の価格時系列
            
        Returns:
        --------
        pd.Series : 合成価格時系列
        """
        # 対数価格に変換
        log_prices = np.log(prices)
        
        # 線形トレンドをフィット
        x = np.arange(len(log_prices))
        coeffs = np.polyfit(x, log_prices, 1)
        trend = np.polyval(coeffs, x)
        
        # 残差を計算
        residuals = log_prices - trend
        
        # 残差をリサンプリング
        resampled_residuals = np.random.choice(residuals, size=len(residuals), replace=True)
        
        # 合成対数価格を作成
        synthetic_log_prices = trend + resampled_residuals
        
        # 価格に変換
        synthetic_prices = np.exp(synthetic_log_prices)
        
        return pd.Series(synthetic_prices, index=prices.index)
    
    def _calculate_single_bootstrap(self, prices: pd.Series, label: str) -> Optional[float]:
        """
        単一のブートストラップサンプルでConfidence計算
        
        Parameters:
        -----------
        prices : pd.Series
            合成価格時系列
        label : str
            ラベル（ログ用）
            
        Returns:
        --------
        float : Confidence値（失敗時はNone）
        """
        try:
            result = self.confidence_calculator.calculate_confidence(prices, label)
            return result['confidence']
        except Exception as e:
            logger.debug(f"Bootstrap {label} failed: {str(e)}")
            return None
    
    def format_report(self, result: TrustResult) -> str:
        """結果をレポート形式にフォーマット"""
        report = []
        report.append("=" * 60)
        report.append(f"DS-LPPLS Trust Report for {result.metadata.get('symbol', 'UNKNOWN')}")
        report.append("=" * 60)
        report.append("")
        
        # Trust指標
        report.append(f"Trust Score: {result.trust_score:.1%}")
        report.append(f"  Interpretation: ", end="")
        if result.trust_score > 0.7:
            report.append("High confidence in the analysis")
        elif result.trust_score > 0.4:
            report.append("Moderate confidence in the analysis")
        else:
            report.append("Low confidence - results may be unreliable")
        report.append("")
        
        # ブートストラップ統計
        report.append("Bootstrap Statistics:")
        report.append(f"  Original Confidence: {result.metadata['original_confidence']:.1%}")
        report.append(f"  Mean Bootstrap Confidence: {result.confidence_mean:.1%}")
        report.append(f"  Std Dev: {result.confidence_std:.3f}")
        report.append(f"  Successful Bootstraps: {result.successful_bootstraps}/{result.n_bootstrap}")
        report.append("")
        
        # 信頼区間
        if result.metadata.get('confidence_distribution'):
            conf_dist = np.array(result.metadata['confidence_distribution'])
            ci_lower = np.percentile(conf_dist, 2.5)
            ci_upper = np.percentile(conf_dist, 97.5)
            report.append(f"95% Confidence Interval: [{ci_lower:.1%}, {ci_upper:.1%}]")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def calculate_ds_lppls_trust(prices: pd.Series, 
                            symbol: str = "UNKNOWN",
                            n_bootstrap: int = 100,
                            method: str = "block") -> TrustResult:
    """
    便利関数：DS-LPPLS Trust指標を計算
    
    Parameters:
    -----------
    prices : pd.Series
        価格時系列データ
    symbol : str
        銘柄シンボル
    n_bootstrap : int
        ブートストラップ回数
    method : str
        ブートストラップ方法
        
    Returns:
    --------
    TrustResult : Trust指標計算結果
    """
    calculator = DSLPPLSTrustCalculator(
        n_bootstrap=n_bootstrap,
        n_workers=4
    )
    
    return calculator.calculate_trust(prices, symbol, method)