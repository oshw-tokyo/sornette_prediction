#!/usr/bin/env python3
"""
時系列予測一貫性分析システム

各銘柄ごとに、様々なタイミングで実施したクラッシュの予測を一つにまとめ、
それらの予測がおよそ特定の時点を指し続けているのかどうかを分析する
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class PredictionPoint:
    """単一の予測ポイント"""
    analysis_date: datetime
    predicted_crash_date: datetime
    tc: float
    beta: float
    omega: float
    r_squared: float
    rmse: float
    confidence: float
    window_days: int
    quality_assessment: Optional[Any] = None
    
    @property
    def days_to_prediction(self) -> int:
        """分析日から予測日までの日数"""
        return (self.predicted_crash_date - self.analysis_date).days

@dataclass 
class ConsistencyMetrics:
    """予測一貫性指標"""
    symbol: str
    total_predictions: int
    usable_predictions: int
    prediction_std_days: float  # 予測日の標準偏差（日数）
    tc_std: float  # tc値の標準偏差
    confidence_mean: float  # 平均信頼度
    convergence_date: Optional[datetime]  # 収束予測日
    convergence_confidence: float  # 収束信頼度
    outlier_count: int  # 外れ値数
    consistency_score: float  # 0-1の一貫性スコア

class TimeSeriesPredictionAnalyzer:
    """銘柄別時系列予測分析クラス"""
    
    def __init__(self):
        """初期化"""
        self.predictions = {}  # symbol -> List[PredictionPoint]
        self.consistency_metrics = {}  # symbol -> ConsistencyMetrics
        
        # 分析パラメータ
        self.analysis_windows = [30, 60, 90, 180, 365, 730]  # 分析期間（日）
        self.outlier_threshold = 2.0  # 外れ値判定の標準偏差倍数
        
    def add_prediction(self, symbol: str, prediction: PredictionPoint):
        """予測ポイントを追加"""
        if symbol not in self.predictions:
            self.predictions[symbol] = []
        self.predictions[symbol].append(prediction)
        
    def analyze_symbol_consistency(self, symbol: str, 
                                 data_client,
                                 analysis_start: datetime,
                                 analysis_end: datetime,
                                 analysis_interval_days: int = 7) -> ConsistencyMetrics:
        """
        特定銘柄の予測一貫性を分析
        
        Args:
            symbol: 分析対象銘柄
            data_client: データ取得クライアント（FRED等）
            analysis_start: 分析開始日
            analysis_end: 分析終了日  
            analysis_interval_days: 分析実行間隔（日）
            
        Returns:
            ConsistencyMetrics: 一貫性指標
        """
        from ..fitting.multi_criteria_selection import MultiCriteriaSelector
        
        print(f"📊 {symbol} 時系列予測一貫性分析開始")
        print(f"   期間: {analysis_start.date()} - {analysis_end.date()}")
        
        selector = MultiCriteriaSelector()
        predictions = []
        
        # 分析日程を生成
        current_date = analysis_start
        analysis_dates = []
        
        while current_date <= analysis_end:
            analysis_dates.append(current_date)
            current_date += timedelta(days=analysis_interval_days)
            
        print(f"   分析回数: {len(analysis_dates)}回")
        
        # 各分析日で複数ウィンドウの予測を実行
        for i, analysis_date in enumerate(analysis_dates):
            print(f"   進捗: {i+1}/{len(analysis_dates)} ({analysis_date.date()})")
            
            for window_days in self.analysis_windows:
                try:
                    # データ期間計算
                    data_end = analysis_date
                    data_start = data_end - timedelta(days=window_days)
                    
                    # データ取得
                    data = self._get_market_data(
                        data_client, symbol, 
                        data_start.strftime('%Y-%m-%d'),
                        data_end.strftime('%Y-%m-%d')
                    )
                    
                    if data is None or len(data) < 50:
                        continue
                        
                    # LPPL フィッティング実行
                    result = selector.perform_comprehensive_fitting(data)
                    best_result = result.get_selected_result()
                    
                    if best_result and best_result.quality_assessment:
                        qa = best_result.quality_assessment
                        
                        # 予測日計算（tcから実際の日付に変換）
                        predicted_crash_date = self._tc_to_date(
                            best_result.tc, analysis_date, window_days
                        )
                        
                        # 予測ポイント作成
                        prediction = PredictionPoint(
                            analysis_date=analysis_date,
                            predicted_crash_date=predicted_crash_date,
                            tc=best_result.tc,
                            beta=best_result.beta,
                            omega=best_result.omega,
                            r_squared=best_result.r_squared,
                            rmse=best_result.rmse,
                            confidence=qa.confidence,
                            window_days=window_days,
                            quality_assessment=qa
                        )
                        
                        predictions.append(prediction)
                        
                except Exception as e:
                    print(f"      ⚠️ {analysis_date.date()} (window={window_days}) エラー: {str(e)}")
                    continue
        
        # 予測データを保存
        self.predictions[symbol] = predictions
        
        # 一貫性指標計算
        metrics = self._calculate_consistency_metrics(symbol, predictions)
        self.consistency_metrics[symbol] = metrics
        
        print(f"✅ {symbol} 分析完了: {len(predictions)}個の予測")
        
        return metrics
    
    def _get_market_data(self, client, symbol: str, start_date: str, end_date: str):
        """データ取得の統一インターフェース"""
        try:
            # 統合クライアントの場合
            if hasattr(client, 'get_data_with_fallback'):
                data, source = client.get_data_with_fallback(symbol, start_date, end_date)
                if data is not None:
                    print(f"      データ取得成功 ({source}): {len(data)}日分")
                return data
            
            # 従来のクライアント（FRED等）
            elif hasattr(client, 'get_series_data'):
                # FRED用の銘柄マッピング
                fred_symbols = {
                    'NASDAQ': 'NASDAQCOM',
                    'SP500': 'SP500', 
                    'DJIA': 'DJIA',
                    'VIX': 'VIXCLS'
                }
                mapped_symbol = fred_symbols.get(symbol, symbol)
                return client.get_series_data(mapped_symbol, start_date, end_date)
            else:
                # その他のクライアント
                return client.get_data(symbol, start_date, end_date)
                
        except Exception as e:
            print(f"      データ取得エラー ({symbol}): {str(e)}")
            return None
    
    def _tc_to_date(self, tc: float, analysis_date: datetime, window_days: int) -> datetime:
        """tc値を実際の予測日に変換"""
        # tcは正規化時間での臨界点
        # tc > 1.0 の場合、データ期間終了後の日数を計算
        if tc > 1.0:
            days_beyond = (tc - 1.0) * window_days
            return analysis_date + timedelta(days=days_beyond)
        else:
            # tc <= 1.0 の場合、データ期間内
            days_from_start = tc * window_days
            return analysis_date - timedelta(days=window_days) + timedelta(days=days_from_start)
    
    def _calculate_consistency_metrics(self, symbol: str, 
                                     predictions: List[PredictionPoint]) -> ConsistencyMetrics:
        """一貫性指標の計算"""
        
        if not predictions:
            return ConsistencyMetrics(
                symbol=symbol, total_predictions=0, usable_predictions=0,
                prediction_std_days=float('inf'), tc_std=float('inf'),
                confidence_mean=0.0, convergence_date=None,
                convergence_confidence=0.0, outlier_count=0,
                consistency_score=0.0
            )
        
        # 使用可能な予測のみフィルタリング
        usable_predictions = [
            p for p in predictions 
            if p.quality_assessment and p.quality_assessment.is_usable
        ]
        
        if len(usable_predictions) < 2:
            return ConsistencyMetrics(
                symbol=symbol, total_predictions=len(predictions),
                usable_predictions=len(usable_predictions),
                prediction_std_days=float('inf'), tc_std=float('inf'),
                confidence_mean=np.mean([p.confidence for p in predictions]),
                convergence_date=None, convergence_confidence=0.0,
                outlier_count=0, consistency_score=0.0
            )
        
        # 予測日の一貫性計算
        predicted_dates = [p.predicted_crash_date for p in usable_predictions]
        date_timestamps = [d.timestamp() for d in predicted_dates]
        
        prediction_std_seconds = np.std(date_timestamps)
        prediction_std_days = prediction_std_seconds / (24 * 3600)
        
        # tc値の一貫性
        tc_values = [p.tc for p in usable_predictions]
        tc_std = np.std(tc_values)
        
        # 信頼度平均
        confidence_mean = np.mean([p.confidence for p in usable_predictions])
        
        # 外れ値検出
        outliers = self._detect_outliers(usable_predictions)
        outlier_count = len(outliers)
        
        # 収束予測日計算（外れ値除外後の中央値）
        filtered_predictions = [p for p in usable_predictions if p not in outliers]
        if filtered_predictions:
            filtered_dates = [p.predicted_crash_date for p in filtered_predictions]
            convergence_timestamp = np.median([d.timestamp() for d in filtered_dates])
            convergence_date = datetime.fromtimestamp(convergence_timestamp)
            convergence_confidence = np.mean([p.confidence for p in filtered_predictions])
        else:
            convergence_date = None
            convergence_confidence = 0.0
        
        # 一貫性スコア計算（0-1、1が最高）
        consistency_score = self._calculate_consistency_score(
            prediction_std_days, tc_std, confidence_mean, outlier_count, len(usable_predictions)
        )
        
        return ConsistencyMetrics(
            symbol=symbol,
            total_predictions=len(predictions),
            usable_predictions=len(usable_predictions),
            prediction_std_days=prediction_std_days,
            tc_std=tc_std,
            confidence_mean=confidence_mean,
            convergence_date=convergence_date,
            convergence_confidence=convergence_confidence,
            outlier_count=outlier_count,
            consistency_score=consistency_score
        )
    
    def _detect_outliers(self, predictions: List[PredictionPoint]) -> List[PredictionPoint]:
        """外れ値検出（予測日ベース）"""
        if len(predictions) < 3:
            return []
            
        dates = [p.predicted_crash_date.timestamp() for p in predictions]
        mean_date = np.mean(dates)
        std_date = np.std(dates)
        
        outliers = []
        for p in predictions:
            z_score = abs(p.predicted_crash_date.timestamp() - mean_date) / std_date
            if z_score > self.outlier_threshold:
                outliers.append(p)
                
        return outliers
    
    def _calculate_consistency_score(self, pred_std_days: float, tc_std: float,
                                   confidence_mean: float, outlier_count: int,
                                   total_predictions: int) -> float:
        """一貫性スコア計算"""
        
        # 各要素のスコア（0-1）
        
        # 1. 予測日の一貫性（標準偏差が小さいほど高スコア）
        pred_consistency = 1.0 / (1.0 + pred_std_days / 30.0)  # 30日基準
        
        # 2. tc値の一貫性
        tc_consistency = 1.0 / (1.0 + tc_std / 0.1)  # 0.1基準
        
        # 3. 平均信頼度
        confidence_score = confidence_mean
        
        # 4. 外れ値率の逆数
        outlier_rate = outlier_count / max(total_predictions, 1)
        outlier_score = 1.0 - outlier_rate
        
        # 重み付き平均
        weights = [0.4, 0.3, 0.2, 0.1]  # 予測日一貫性を最重視
        scores = [pred_consistency, tc_consistency, confidence_score, outlier_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def visualize_consistency(self, symbol: str, save_path: Optional[str] = None):
        """一貫性分析結果の可視化"""
        
        if symbol not in self.predictions:
            print(f"❌ {symbol} の予測データがありません")
            return
            
        predictions = self.predictions[symbol]
        metrics = self.consistency_metrics.get(symbol)
        
        if not predictions:
            return
            
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{symbol} Prediction Consistency Analysis', fontsize=16)
        
        # 1. 予測日の時系列
        ax1 = axes[0, 0]
        analysis_dates = [p.analysis_date for p in predictions]
        predicted_dates = [p.predicted_crash_date for p in predictions]
        colors = ['green' if p.quality_assessment.is_usable else 'red' for p in predictions]
        
        ax1.scatter(analysis_dates, predicted_dates, c=colors, alpha=0.6)
        if metrics and metrics.convergence_date:
            ax1.axhline(metrics.convergence_date, color='blue', linestyle='--', 
                       label=f'Convergence Date: {metrics.convergence_date.date()}')
        ax1.set_xlabel('Analysis Date')
        ax1.set_ylabel('Predicted Crash Date')
        ax1.set_title('Prediction Timeline')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. tc値の推移
        ax2 = axes[0, 1]
        tc_values = [p.tc for p in predictions]
        ax2.scatter(analysis_dates, tc_values, c=colors, alpha=0.6)
        ax2.axhline(np.mean(tc_values), color='blue', linestyle='--', 
                   label=f'Mean tc: {np.mean(tc_values):.3f}')
        ax2.set_xlabel('Analysis Date')
        ax2.set_ylabel('tc value')
        ax2.set_title('tc Value Evolution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 信頼度分布
        ax3 = axes[0, 2]
        confidences = [p.confidence for p in predictions]
        ax3.hist(confidences, bins=20, alpha=0.7, color='steelblue', edgecolor='black')
        ax3.axvline(np.mean(confidences), color='red', linestyle='--',
                   label=f'Mean: {np.mean(confidences):.3f}')
        ax3.set_xlabel('Confidence')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Confidence Distribution')
        ax3.legend()
        
        # 4. ウィンドウ別予測分布
        ax4 = axes[1, 0]
        window_groups = {}
        for p in predictions:
            if p.window_days not in window_groups:
                window_groups[p.window_days] = []
            window_groups[p.window_days].append(p.predicted_crash_date)
            
        for window, dates in window_groups.items():
            timestamps = [d.timestamp() for d in dates]
            ax4.scatter([window] * len(timestamps), timestamps, 
                       alpha=0.6, label=f'{window}d window')
        ax4.set_xlabel('Analysis Window (days)')
        ax4.set_ylabel('Predicted Date (timestamp)')
        ax4.set_title('Predictions by Window Size')
        
        # 5. 一貫性指標
        ax5 = axes[1, 1]
        if metrics:
            metric_names = ['Pred Consistency', 'tc Consistency', 'Confidence', 'Outlier Rate']
            metric_values = [
                1.0 / (1.0 + metrics.prediction_std_days / 30.0),
                1.0 / (1.0 + metrics.tc_std / 0.1),
                metrics.confidence_mean,
                1.0 - (metrics.outlier_count / max(metrics.total_predictions, 1))
            ]
            
            bars = ax5.bar(metric_names, metric_values, alpha=0.7, color='lightcoral')
            ax5.set_ylim(0, 1)
            ax5.set_ylabel('Score (0-1)')
            ax5.set_title('Consistency Metrics')
            
            # 値をバーの上に表示
            for bar, value in zip(bars, metric_values):
                ax5.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                        f'{value:.3f}', ha='center', va='bottom')
        
        # 6. 予測までの日数分布
        ax6 = axes[1, 2]
        days_to_prediction = [p.days_to_prediction for p in predictions]
        ax6.hist(days_to_prediction, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
        ax6.axvline(np.mean(days_to_prediction), color='red', linestyle='--',
                   label=f'Mean: {np.mean(days_to_prediction):.0f} days')
        ax6.set_xlabel('Days to Prediction')
        ax6.set_ylabel('Frequency')
        ax6.set_title('Prediction Horizon Distribution')
        ax6.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 可視化保存: {save_path}")
        plt.show()
    
    def generate_report(self, symbol: str) -> str:
        """一貫性分析レポート生成"""
        
        if symbol not in self.consistency_metrics:
            return f"❌ {symbol} の分析結果がありません"
            
        metrics = self.consistency_metrics[symbol]
        predictions = self.predictions[symbol]
        
        report = f"""
📊 {symbol} 時系列予測一貫性分析レポート
{'=' * 60}

🔢 基本統計:
   総予測数: {metrics.total_predictions}
   使用可能予測数: {metrics.usable_predictions}
   使用可能率: {metrics.usable_predictions/max(metrics.total_predictions,1):.1%}

📅 予測一貫性:
   予測日標準偏差: {metrics.prediction_std_days:.1f} 日
   tc値標準偏差: {metrics.tc_std:.4f}
   外れ値数: {metrics.outlier_count}

🎯 収束分析:
   収束予測日: {metrics.convergence_date.date() if metrics.convergence_date else 'N/A'}
   収束信頼度: {metrics.convergence_confidence:.2%}

📈 品質指標:
   平均信頼度: {metrics.confidence_mean:.2%}
   一貫性スコア: {metrics.consistency_score:.3f} (0-1)

💡 解釈:
"""
        
        # 解釈の追加
        if metrics.consistency_score > 0.8:
            report += "   ✅ 高い予測一貫性 - 信頼できる収束予測"
        elif metrics.consistency_score > 0.6:
            report += "   🟡 中程度の予測一貫性 - 注意深い監視が必要"
        else:
            report += "   🔴 低い予測一貫性 - 予測の信頼性に問題"
            
        if metrics.prediction_std_days < 30:
            report += "\\n   ✅ 予測日のばらつきが小さい"
        elif metrics.prediction_std_days < 90:
            report += "\\n   🟡 予測日のばらつきが中程度"
        else:
            report += "\\n   🔴 予測日のばらつきが大きい"
            
        return report
    
    def save_results(self, symbol: str, filepath: str):
        """分析結果をCSVで保存"""
        
        if symbol not in self.predictions:
            print(f"❌ {symbol} の予測データがありません")
            return
            
        predictions = self.predictions[symbol]
        
        # DataFrame作成
        data = []
        for p in predictions:
            data.append({
                'analysis_date': p.analysis_date.strftime('%Y-%m-%d'),
                'predicted_crash_date': p.predicted_crash_date.strftime('%Y-%m-%d'),
                'days_to_prediction': p.days_to_prediction,
                'tc': p.tc,
                'beta': p.beta,
                'omega': p.omega,
                'r_squared': p.r_squared,
                'rmse': p.rmse,
                'confidence': p.confidence,
                'window_days': p.window_days,
                'quality': p.quality_assessment.quality.value if p.quality_assessment else 'unknown',
                'is_usable': p.quality_assessment.is_usable if p.quality_assessment else False
            })
            
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"💾 分析結果保存: {filepath}")


# 使用例とテスト
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_sources.fred_data_client import FREDDataClient
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # テスト実行
    analyzer = TimeSeriesPredictionAnalyzer()
    fred_client = FREDDataClient()
    
    # NASDAQ の6ヶ月間分析（テスト用短期間）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)  # 2ヶ月間
    
    metrics = analyzer.analyze_symbol_consistency(
        'NASDAQ', fred_client, start_date, end_date, analysis_interval_days=7
    )
    
    print(analyzer.generate_report('NASDAQ'))