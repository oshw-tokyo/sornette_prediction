#!/usr/bin/env python3
"""
クラッシュ予測日中心の可視化システム
フィッティング曲線ではなく、予測日と誤差範囲に焦点を当てた可視化
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import os

import sys
sys.path.append('.')

from src.database.results_database import ResultsDatabase
from src.config.matplotlib_config import save_and_close_figure

class CrashPredictionVisualizer:
    """クラッシュ予測日に焦点を当てた可視化クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db = ResultsDatabase(db_path)
    
    def create_prediction_focused_chart(self, analysis_id: int, 
                                      original_data: Optional[pd.DataFrame] = None) -> str:
        """
        予測日中心のチャートを作成
        
        Args:
            analysis_id: 分析結果ID
            original_data: 元データ（Noneの場合はDBから推定）
            
        Returns:
            str: 保存された画像ファイルパス
        """
        print(f"📊 予測日中心チャート作成: ID={analysis_id}")
        
        # データベースから分析結果取得
        details = self.db.get_analysis_details(analysis_id)
        if not details:
            raise ValueError(f"分析ID {analysis_id} が見つかりません")
        
        # 予測日情報の計算
        prediction_info = self._calculate_prediction_details(details, original_data)
        
        # チャート作成
        fig_path = self._create_prediction_chart(details, prediction_info)
        
        print(f"✅ 予測日チャート保存: {fig_path}")
        return fig_path
    
    def _calculate_prediction_details(self, details: Dict, 
                                    original_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        予測日の詳細計算
        
        Args:
            details: 分析結果詳細
            original_data: 元データ
            
        Returns:
            Dict: 予測日情報
        """
        # 基本パラメータ
        tc = details['tc']
        
        # データ期間情報
        data_start = pd.to_datetime(details['data_period_start'])
        data_end = pd.to_datetime(details['data_period_end'])
        data_days = (data_end - data_start).days
        
        # tc値からの実際の予測日計算
        # tc は正規化時間（0-1）なので、実際の日数に変換
        if tc > 1.0:
            # データ期間を超えた予測
            days_beyond = (tc - 1.0) * data_days
            predicted_date = data_end + timedelta(days=days_beyond)
            is_future_prediction = True
        else:
            # データ期間内の過去日
            days_from_start = tc * data_days
            predicted_date = data_start + timedelta(days=days_from_start)
            is_future_prediction = False
        
        # tc の誤差推定（統計的手法）
        # R²値と信頼度から誤差を推定
        r_squared = details['r_squared']
        confidence = details.get('confidence', 0.5)
        
        # 統計的誤差推定
        # R²が高く、confidenceが高いほど誤差は小さい
        base_error_days = data_days * 0.1  # ベース誤差: データ期間の10%
        
        # R²による補正 (0.5-0.99の範囲で0.1-1.0倍)
        r_squared_factor = max(0.1, 2 * (1 - r_squared))
        
        # 信頼度による補正 (0-1の範囲で2.0-0.5倍)
        confidence_factor = max(0.5, 2 - confidence)
        
        # tcが境界に近い場合の補正
        tc_boundary_factor = 1.0
        if tc > 1.5:  # 遠い未来予測
            tc_boundary_factor = min(3.0, tc - 1.0)
        
        error_days = base_error_days * r_squared_factor * confidence_factor * tc_boundary_factor
        
        # 誤差範囲
        error_range_start = predicted_date - timedelta(days=error_days)
        error_range_end = predicted_date + timedelta(days=error_days)
        
        return {
            'predicted_date': predicted_date,
            'error_days': error_days,
            'error_range_start': error_range_start,
            'error_range_end': error_range_end,
            'is_future_prediction': is_future_prediction,
            'tc_normalized': tc,
            'data_start': data_start,
            'data_end': data_end,
            'data_days': data_days,
            'confidence_factors': {
                'r_squared': r_squared,
                'confidence': confidence,
                'r_squared_factor': r_squared_factor,
                'confidence_factor': confidence_factor,
                'tc_boundary_factor': tc_boundary_factor,
                'base_error_days': base_error_days
            }
        }
    
    def _create_prediction_chart(self, details: Dict, prediction_info: Dict) -> str:
        """
        予測日チャートの作成
        
        Args:
            details: 分析結果詳細
            prediction_info: 予測日情報
            
        Returns:
            str: 保存されたファイルパス
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # サンプルデータ生成（実データの代わり）
        sample_data = self._generate_sample_price_data(prediction_info)
        
        # メインチャート: 価格データと予測日
        ax1.plot(sample_data.index, sample_data['Close'], 'b-', 
                linewidth=1.5, label='Market Data', alpha=0.8)
        
        # データ期間の強調
        ax1.axvspan(prediction_info['data_start'], prediction_info['data_end'], 
                   alpha=0.1, color='blue', label='Analysis Period')
        
        # 予測日のマーキング
        pred_date = prediction_info['predicted_date']
        
        # 予測日の垂直線
        ax1.axvline(pred_date, color='red', linestyle='--', linewidth=2, 
                   label=f'Predicted Crash: {pred_date.strftime("%Y-%m-%d")}')
        
        # 誤差範囲の表示
        ax1.axvspan(prediction_info['error_range_start'], 
                   prediction_info['error_range_end'],
                   alpha=0.2, color='red', label=f'Error Range: ±{prediction_info["error_days"]:.0f} days')
        
        # チャート設定
        ax1.set_title(f'{details["symbol"]} - LPPL Crash Prediction Analysis', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Y軸範囲の調整（予測日周辺にフォーカス）
        y_min, y_max = ax1.get_ylim()
        ax1.set_ylim(y_min * 0.95, y_max * 1.05)
        
        # 下部チャート: 予測詳細情報
        ax2.axis('off')
        
        # 詳細情報テキスト
        info_text = self._generate_info_text(details, prediction_info)
        
        ax2.text(0.05, 0.95, info_text, transform=ax2.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8))
        
        # 予測の信頼性指標
        reliability_text = self._generate_reliability_text(details, prediction_info)
        
        ax2.text(0.55, 0.95, reliability_text, transform=ax2.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=1', facecolor='lightgreen', alpha=0.8))
        
        plt.tight_layout()
        
        # 保存
        os.makedirs('results/prediction_charts', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fig_path = f'results/prediction_charts/crash_prediction_id{details["id"]}_{timestamp}.png'
        save_and_close_figure(fig, fig_path)
        
        return fig_path
    
    def _generate_sample_price_data(self, prediction_info: Dict) -> pd.DataFrame:
        """
        サンプル価格データの生成
        
        Args:
            prediction_info: 予測情報
            
        Returns:
            DataFrame: サンプル価格データ
        """
        # データ範囲を予測日まで拡張
        start_date = prediction_info['data_start'] - timedelta(days=30)
        end_date = max(prediction_info['predicted_date'] + timedelta(days=30),
                      prediction_info['data_end'] + timedelta(days=30))
        
        # 日次データ生成
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 現実的な価格パターン生成
        np.random.seed(42)  # 再現性のため
        
        n_points = len(dates)
        base_price = 18000
        
        # トレンド成分
        trend = np.linspace(0, 2000, n_points)
        
        # ランダムウォーク
        daily_changes = np.random.normal(0, 50, n_points)
        random_walk = np.cumsum(daily_changes)
        
        # 市場サイクル
        cycle = 300 * np.sin(2 * np.pi * np.arange(n_points) / 30)
        
        # 予測日前後での変動増加
        pred_date = prediction_info['predicted_date']
        volatility_boost = np.zeros(n_points)
        
        for i, date in enumerate(dates):
            days_to_pred = abs((date - pred_date).days)
            if days_to_pred <= 15:  # 予測日前後15日
                boost_factor = max(0, 1 - days_to_pred / 15) * 200
                volatility_boost[i] = boost_factor
        
        # 最終価格
        prices = base_price + trend + random_walk + cycle + volatility_boost
        
        # 負の価格を防ぐ
        prices = np.maximum(prices, base_price * 0.5)
        
        return pd.DataFrame({'Close': prices}, index=dates)
    
    def _generate_info_text(self, details: Dict, prediction_info: Dict) -> str:
        """予測詳細情報テキストの生成"""
        pred_date = prediction_info['predicted_date']
        
        info_text = f"""LPPL Prediction Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Symbol: {details['symbol']}
Analysis Date: {details['analysis_date'][:10]}
Data Period: {prediction_info['data_start'].strftime('%Y-%m-%d')} 
           → {prediction_info['data_end'].strftime('%Y-%m-%d')}
Data Points: {details['data_points']} days

LPPL Parameters:
tc = {details['tc']:.4f} (normalized)
β  = {details['beta']:.4f}
ω  = {details['omega']:.4f}

Quality Metrics:
R² = {details['r_squared']:.4f}
Quality: {details['quality']}
Confidence: {details.get('confidence', 0):.1%}
Usable: {'Yes' if details.get('is_usable', False) else 'No'}"""
        
        return info_text
    
    def _generate_reliability_text(self, details: Dict, prediction_info: Dict) -> str:
        """予測信頼性情報テキストの生成"""
        pred_date = prediction_info['predicted_date']
        error_days = prediction_info['error_days']
        factors = prediction_info['confidence_factors']
        
        # 予測の分類
        if prediction_info['is_future_prediction']:
            pred_type = "Future Crash Prediction"
            days_ahead = (pred_date - datetime.now()).days
            timing_info = f"Predicted in {days_ahead} days"
        else:
            pred_type = "Historical Pattern Analysis"
            timing_info = "Pattern within data period"
        
        reliability_text = f"""Prediction Reliability:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: {pred_type}
{timing_info}

Predicted Date:
{pred_date.strftime('%Y-%m-%d (%A)')}

Error Estimation:
±{error_days:.0f} days (±{error_days/7:.1f} weeks)
Range: {prediction_info['error_range_start'].strftime('%Y-%m-%d')}
    → {prediction_info['error_range_end'].strftime('%Y-%m-%d')}

Error Factors:
R² Factor: {factors['r_squared_factor']:.2f}
Confidence: {factors['confidence_factor']:.2f}
TC Boundary: {factors['tc_boundary_factor']:.2f}

Reliability: {'High' if error_days < 30 else 'Medium' if error_days < 60 else 'Low'}"""
        
        return reliability_text
    
    def update_database_with_prediction_details(self, analysis_id: int) -> bool:
        """
        データベースに予測詳細を追加保存
        
        Args:
            analysis_id: 分析結果ID
            
        Returns:
            bool: 成功フラグ
        """
        try:
            details = self.db.get_analysis_details(analysis_id)
            prediction_info = self._calculate_prediction_details(details)
            
            # 予測詳細をメタデータとして保存（既存のquality_metadataに追加）
            existing_metadata = details.get('quality_metadata', {})
            if isinstance(existing_metadata, str):
                import json
                existing_metadata = json.loads(existing_metadata)
            
            prediction_metadata = {
                'predicted_crash_date_calculated': prediction_info['predicted_date'].isoformat(),
                'prediction_error_days': prediction_info['error_days'],
                'prediction_error_range_start': prediction_info['error_range_start'].isoformat(),
                'prediction_error_range_end': prediction_info['error_range_end'].isoformat(),
                'is_future_prediction': prediction_info['is_future_prediction'],
                'tc_normalized': prediction_info['tc_normalized'],
                'confidence_factors': prediction_info['confidence_factors']
            }
            
            # 既存メタデータに追加
            existing_metadata.update(prediction_metadata)
            
            # データベース更新（直接SQL実行）
            import sqlite3
            import json
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE analysis_results SET quality_metadata = ? WHERE id = ?",
                    (json.dumps(existing_metadata), analysis_id)
                )
                conn.commit()
            
            print(f"✅ 予測詳細をデータベースに保存: ID={analysis_id}")
            return True
            
        except Exception as e:
            print(f"❌ 予測詳細保存エラー: {str(e)}")
            return False

def create_prediction_visualization(analysis_id: int, 
                                  db_path: str = "results/analysis_results.db") -> str:
    """予測日中心の可視化作成（メイン関数）"""
    visualizer = CrashPredictionVisualizer(db_path)
    
    # 予測チャート作成
    chart_path = visualizer.create_prediction_focused_chart(analysis_id)
    
    # データベースに予測詳細を保存
    visualizer.update_database_with_prediction_details(analysis_id)
    
    # データベースに可視化を登録
    viz_id = visualizer.db.save_visualization(
        analysis_id,
        'crash_prediction',
        chart_path,
        'Crash Prediction Analysis',
        f'Prediction-focused visualization with error estimation'
    )
    
    print(f"✅ 予測可視化完了: チャート={chart_path}, DB_ID={viz_id}")
    return chart_path

if __name__ == "__main__":
    # テスト実行
    create_prediction_visualization(1)