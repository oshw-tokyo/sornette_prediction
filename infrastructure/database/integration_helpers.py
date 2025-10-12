#!/usr/bin/env python3
"""
データベース統合ヘルパー
既存の分析コードとデータベースを統合するためのユーティリティ
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import os

from .results_database import ResultsDatabase
from core.fitting.multi_criteria_selection import SelectionResult, FittingCandidate

class AnalysisResultSaver:
    """分析結果の自動保存クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db = ResultsDatabase(db_path)
        
    def save_lppl_analysis(self, symbol: str, data: pd.DataFrame, 
                          result: SelectionResult, data_source: str = "unknown") -> int:
        """
        LPPL分析結果の保存
        
        Args:
            symbol: 銘柄シンボル
            data: 価格データ
            result: 分析結果
            data_source: データソース名
            
        Returns:
            int: 保存されたレコードID
        """
        best = result.get_selected_result()
        if not best:
            raise ValueError("保存可能な分析結果がありません")

        # tc値から予測日を計算（Issue I128修正: first_date追加）
        predicted_date = self._calculate_predicted_date(best.tc, data.index[0], data.index[-1])
        days_to_crash = (predicted_date - datetime.now()).days if predicted_date else None
        
        # データベース保存用のディクショナリ作成
        result_data = {
            'symbol': symbol,
            'data_source': data_source,
            'data_period_start': data.index[0].strftime('%Y-%m-%d'),
            'data_period_end': data.index[-1].strftime('%Y-%m-%d'),
            'data_points': len(data),
            'tc': best.tc,
            'beta': best.beta,
            'omega': best.omega,
            'phi': best.phi,
            'A': best.A,
            'B': best.B,
            'C': best.C,
            'r_squared': best.r_squared,
            'rmse': best.rmse,
            'quality': best.quality_assessment.quality.value if best.quality_assessment else 'unknown',
            'confidence': best.quality_assessment.confidence if best.quality_assessment else 0.0,
            'is_usable': best.quality_assessment.is_usable if best.quality_assessment else False,
            'predicted_crash_date': predicted_date.strftime('%Y-%m-%d %H:%M:%S') if predicted_date else None,
            'days_to_crash': days_to_crash,
            'fitting_method': 'multi_criteria',
            'window_days': len(data),
            'total_candidates': len(result.all_candidates),
            'successful_candidates': len([c for c in result.all_candidates if c.convergence_success]),
            'quality_metadata': self._extract_quality_metadata(best),
            'selection_criteria': self._extract_selection_criteria(result)
        }
        
        analysis_id = self.db.save_analysis_result(result_data)
        
        print(f"📊 {symbol} 分析結果をデータベースに保存: ID={analysis_id}")
        return analysis_id
    
    def save_visualization_with_analysis(self, analysis_id: int, chart_type: str, 
                                       file_path: str, title: str = "", 
                                       description: str = "") -> int:
        """
        可視化データの保存（分析結果と関連付け）
        
        Args:
            analysis_id: 分析結果ID
            chart_type: チャートタイプ
            file_path: 画像ファイルパス
            title: タイトル
            description: 説明
            
        Returns:
            int: 可視化レコードID
        """
        if not os.path.exists(file_path):
            print(f"⚠️ 画像ファイルが見つかりません: {file_path}")
            return -1
        
        viz_id = self.db.save_visualization(
            analysis_id, chart_type, file_path, title, description
        )
        
        print(f"📊 可視化データ保存: ID={viz_id}, Type={chart_type}")
        return viz_id
    
    def _calculate_predicted_date(
        self,
        tc: float,
        first_date: pd.Timestamp,
        last_date: pd.Timestamp
    ) -> Optional[datetime]:
        """
        tc値から予測日時を計算（フィッティング期間考慮版）

        【修正内容 (Issue I128)】
        - first_date（フィッティング開始日）を追加
        - core.fitting.lppl_utils.convert_tc_to_date() を使用
        - フィッティング期間の実際の暦日数を反映
        - 窓ごとに異なる変換比率を適用

        Args:
            tc: tc値（正規化時間）
            first_date: フィッティング期間の開始日
            last_date: フィッティング期間の終了日

        Returns:
            datetime: 予測日時（時間精度まで含む）

        Scientific Basis:
            LPPL時間正規化に基づく変換
            Issue: I128
            実装日: 2025-10-12
        """
        from core.fitting.lppl_utils import convert_tc_to_date
        return convert_tc_to_date(tc, first_date, last_date, include_time=True)
    
    def _extract_quality_metadata(self, candidate: FittingCandidate) -> Dict[str, Any]:
        """品質評価メタデータの抽出"""
        if not candidate.quality_assessment:
            return {}
        
        qa = candidate.quality_assessment
        metadata = {
            'quality': qa.quality.value if hasattr(qa.quality, 'value') else str(qa.quality),
            'confidence': qa.confidence,
            'issues': qa.issues,
            'is_usable': qa.is_usable
        }
        
        # 追加のメタデータ
        if qa.metadata:
            metadata.update(qa.metadata)
        
        return metadata
    
    def _extract_selection_criteria(self, result: SelectionResult) -> Dict[str, Any]:
        """選択基準の情報抽出"""
        criteria = {
            'available_criteria': [],
            'selection_summary': {}
        }
        
        # 利用可能な選択基準
        for criteria_type, candidate in result.selections.items():
            if candidate:
                criteria['available_criteria'].append(criteria_type.value)
                if criteria_type.value not in criteria['selection_summary']:
                    criteria['selection_summary'][criteria_type.value] = candidate.r_squared
        
        return criteria
    
    def save_lppl_analysis_with_schedule(self, symbol: str, data: pd.DataFrame,
                                        result: SelectionResult, data_source: str,
                                        schedule_name: str, basis_date: str,
                                        backfill_batch_id: Optional[str] = None) -> int:
        """
        Save LPPL analysis with schedule metadata
        
        Args:
            symbol: Symbol
            data: Price data
            result: Analysis result
            data_source: Data source
            schedule_name: Schedule name
            basis_date: Analysis basis date
            backfill_batch_id: Batch ID for backfill
            
        Returns:
            int: Analysis ID
        """
        best = result.get_selected_result()
        if not best:
            raise ValueError("No valid analysis result to save")
        
        # Calculate predicted date from tc (Issue I128修正: first_date追加)
        predicted_date = self._calculate_predicted_date(best.tc, data.index[0], pd.to_datetime(basis_date))
        days_to_crash = (predicted_date - datetime.now()).days if predicted_date else None
        
        # Create database record with schedule metadata
        result_data = {
            'symbol': symbol,
            'data_source': data_source,
            'data_period_start': data.index[0].strftime('%Y-%m-%d'),
            'data_period_end': data.index[-1].strftime('%Y-%m-%d'),
            'data_points': len(data),
            'tc': best.tc,
            'beta': best.beta,
            'omega': best.omega,
            'phi': best.phi,
            'A': best.A,
            'B': best.B,
            'C': best.C,
            'r_squared': best.r_squared,
            'rmse': best.rmse,
            'quality': best.quality_assessment.quality.value if best.quality_assessment else 'unknown',
            'confidence': best.quality_assessment.confidence if best.quality_assessment else 0.0,
            'is_usable': best.quality_assessment.is_usable if best.quality_assessment else False,
            'predicted_crash_date': predicted_date.strftime('%Y-%m-%d %H:%M:%S') if predicted_date else None,
            'days_to_crash': days_to_crash,
            'fitting_method': 'multi_criteria',
            'window_days': len(data),
            'total_candidates': len(result.all_candidates),
            'successful_candidates': len([c for c in result.all_candidates if c.convergence_success]),
            'quality_metadata': self._extract_quality_metadata(best),
            'selection_criteria': self._extract_selection_criteria(result),
            # Schedule metadata
            'schedule_name': schedule_name,
            'analysis_basis_date': basis_date,
            'is_scheduled': True,
            'backfill_batch_id': backfill_batch_id
        }
        
        analysis_id = self.db.save_analysis_result(result_data)
        
        print(f"📊 {symbol} analysis saved: ID={analysis_id}, basis_date={basis_date}")
        return analysis_id


class DatabaseAnalysisViewer:
    """データベースからの分析結果閲覧クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db = ResultsDatabase(db_path)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        ダッシュボード表示用のデータ取得
        
        Returns:
            Dict: ダッシュボードデータ
        """
        # 基本統計
        stats = self.db.get_summary_statistics()
        
        # 最近の分析結果
        recent_analyses = self.db.get_recent_analyses(limit=20)
        
        # 銘柄別統計
        symbol_stats = self._get_symbol_statistics()
        
        # 品質トレンド
        quality_trend = self._get_quality_trend()
        
        return {
            'statistics': stats,
            'recent_analyses': recent_analyses.to_dict('records'),
            'symbol_statistics': symbol_stats,
            'quality_trend': quality_trend,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_symbol_statistics(self) -> Dict[str, Any]:
        """銘柄別統計の取得"""
        recent_analyses = self.db.get_recent_analyses(limit=100)
        
        if recent_analyses.empty:
            return {}
        
        symbol_stats = {}
        for symbol in recent_analyses['symbol'].unique():
            symbol_data = recent_analyses[recent_analyses['symbol'] == symbol]
            
            symbol_stats[symbol] = {
                'total_analyses': len(symbol_data),
                'usable_analyses': len(symbol_data[symbol_data['is_usable'] == True]),
                'average_r_squared': symbol_data['r_squared'].mean(),
                'latest_analysis': symbol_data['analysis_date'].max(),
                'latest_prediction': symbol_data.iloc[0]['predicted_crash_date'] if len(symbol_data) > 0 else None
            }
        
        return symbol_stats
    
    def _get_quality_trend(self) -> Dict[str, Any]:
        """品質トレンドの取得"""
        recent_analyses = self.db.get_recent_analyses(limit=50)
        
        if recent_analyses.empty:
            return {}
        
        # 日別品質統計
        recent_analyses['date'] = pd.to_datetime(recent_analyses['analysis_date']).dt.date
        daily_quality = recent_analyses.groupby('date').agg({
            'r_squared': 'mean',
            'confidence': 'mean',
            'is_usable': 'sum'
        }).to_dict('index')
        
        # 日付をキーとして文字列に変換
        daily_quality_str = {str(k): v for k, v in daily_quality.items()}
        
        return {
            'daily_quality': daily_quality_str,
            'overall_trend': {
                'improving': recent_analyses['r_squared'].iloc[:10].mean() > recent_analyses['r_squared'].iloc[-10:].mean(),
                'stable_quality': recent_analyses['confidence'].std() < 0.1
            }
        }


# 使用例
def example_integration():
    """統合例の実演"""
    print("🧪 データベース統合例")
    print("=" * 50)
    
    # 分析結果セーバー初期化
    saver = AnalysisResultSaver("results/example_integration.db")
    
    # ダミーデータでの保存例
    print("📊 サンプル分析結果の保存...")
    
    # 実際の使用では、MultiCriteriaSelector.perform_comprehensive_fitting() の結果を使用
    # ここではダミーデータを作成
    sample_data = pd.DataFrame({
        'Close': [100, 105, 103, 108, 110]
    }, index=pd.date_range('2024-01-01', periods=5))
    
    print("✅ 統合機能準備完了")
    
    # ビューアーのテスト
    viewer = DatabaseAnalysisViewer("results/example_integration.db")
    dashboard_data = viewer.get_dashboard_data()
    
    print(f"📊 ダッシュボードデータ: {len(dashboard_data)} セクション")
    
    return saver, viewer


if __name__ == "__main__":
    example_integration()