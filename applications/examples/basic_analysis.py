#!/usr/bin/env python3
"""
統一LPPL分析システム - 基本分析例

本番コードを使用した統合システムのデモンストレーション
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
import sys
import os
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.append('.')

# matplotlib設定（GUIを無効化）
from infrastructure.config.matplotlib_config import configure_matplotlib_for_automation
configure_matplotlib_for_automation()

from infrastructure.data_sources.unified_data_client import UnifiedDataClient
from core.fitting.multi_criteria_selection import MultiCriteriaSelector
from infrastructure.database.integration_helpers import AnalysisResultSaver
from infrastructure.visualization.lppl_visualizer import LPPLVisualizer

def perform_basic_lppl_analysis(symbol: str = 'NASDAQ', days: int = 180) -> Dict:
    """
    基本的なLPPL分析を実行
    
    Args:
        symbol: 分析対象銘柄
        days: 分析期間（日数）
        
    Returns:
        Dict: 分析結果
    """
    print("🎯 統合LPPL分析システム - 基本分析")
    print("=" * 70)
    print("本番コードベースを使用した分析システム")
    
    # 1. データ取得
    print(f"\n📊 Step 1: {symbol} データ取得")
    client = UnifiedDataClient()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    data, source = client.get_data_with_fallback(
        symbol,
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    if data is None:
        print("❌ データ取得に失敗")
        return {"success": False, "error": "データ取得失敗"}
    
    print(f"✅ データ取得成功: {len(data)}日分 (ソース: {source})")
    print(f"   期間: {data.index[0].strftime('%Y-%m-%d')} - {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"   価格範囲: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
    
    # 2. LPPL分析実行
    print(f"\n🎯 Step 2: LPPL分析実行")
    selector = MultiCriteriaSelector()
    
    print("📊 多基準フィッティング実行中...")
    result = selector.perform_comprehensive_fitting(data)
    
    successful = [c for c in result.all_candidates if c.convergence_success]
    print(f"✅ 分析完了: {len(successful)}/{len(result.all_candidates)} 候補成功")
    
    best = result.get_selected_result()
    if not best:
        print("❌ 使用可能な結果がありません")
        return {"success": False, "error": "フィッティング失敗"}
    
    print(f"📊 最良結果:")
    print(f"   tc={best.tc:.4f}, β={best.beta:.4f}, ω={best.omega:.4f}")
    print(f"   R²={best.r_squared:.4f}, 品質={best.quality_assessment.quality.value}")
    
    # 3. データベース保存
    print(f"\n💾 Step 3: 結果保存（統一データベース）")
    
    # 統一データベース使用
    saver = AnalysisResultSaver("results/analysis_results.db")
    
    try:
        analysis_id = saver.save_lppl_analysis(symbol, data, result, source)
        print(f"✅ 分析結果保存: ID={analysis_id}")
        
        # 4. 統一可視化システム
        print(f"\n📊 Step 4: 統一可視化生成")
        visualizer = LPPLVisualizer("results/analysis_results.db")
        
        # 包括的可視化作成（実データ使用）
        viz_path = visualizer.create_comprehensive_visualization(analysis_id, data)
        viz_id = visualizer.update_database_visualization(analysis_id, viz_path)
        
        print(f"✅ 包括的可視化作成: 可視化ID={viz_id}")
        
        # 5. 結果サマリー
        print(f"\n📋 Step 5: 分析結果サマリー")
        
        summary = {
            "success": True,
            "analysis_id": analysis_id,
            "symbol": symbol,
            "data_source": source,
            "data_period": f"{data.index[0].strftime('%Y-%m-%d')} - {data.index[-1].strftime('%Y-%m-%d')}",
            "data_points": len(data),
            "parameters": {
                "tc": best.tc,
                "beta": best.beta,
                "omega": best.omega,
                "phi": best.phi,
                "A": best.A,
                "B": best.B,
                "C": best.C
            },
            "quality": {
                "r_squared": best.r_squared,
                "quality": best.quality_assessment.quality.value,
                "confidence": best.quality_assessment.confidence,
                "is_usable": best.quality_assessment.is_usable
            },
            "visualization": {
                "path": viz_path,
                "database_id": viz_id
            }
        }
        
        # 結果表示
        print(f"   📊 分析ID: {analysis_id}")
        print(f"   📊 データソース: {source}")
        print(f"   📊 品質評価: {best.quality_assessment.quality.value} (信頼度: {best.quality_assessment.confidence:.1%})")
        print(f"   📊 予測可能: {'✅' if best.quality_assessment.is_usable else '❌'}")
        print(f"   📊 可視化: {viz_path}")
        
        return summary
        
    except Exception as e:
        print(f"❌ 保存エラー: {str(e)}")
        return {"success": False, "error": str(e)}

def launch_dashboard():
    """ダッシュボード起動案内"""
    print(f"\n🌐 ブラウザダッシュボード")
    print("=" * 50)
    print("以下のコマンドで結果をブラウザで確認できます:")
    print()
    print("python entry_points/main.py dashboard")
    print()
    print("または:")
    print("./start_dashboard.sh")
    print()
    print("📊 統一データベース: results/analysis_results.db")
    print("🔗 URL: http://localhost:8501")

def main():
    """メイン実行関数"""
    print("🎯 統合LPPL分析システム")
    print("=" * 70)
    print("修正されたフィッティングアルゴリズムと統一アーキテクチャ")
    print()
    
    try:
        # 基本分析実行
        result = perform_basic_lppl_analysis('NASDAQ', 180)
        
        if result["success"]:
            print(f"\n🎉 分析完了!")
            print(f"✅ スケール問題修正済み")
            print(f"✅ 統一データベース使用")
            print(f"✅ 包括的可視化生成")
            
            # ダッシュボード案内
            launch_dashboard()
            
        else:
            print(f"\n❌ 分析失敗: {result['error']}")
            
    except Exception as e:
        print(f"❌ システムエラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()