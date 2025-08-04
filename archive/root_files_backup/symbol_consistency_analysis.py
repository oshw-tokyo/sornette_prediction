#!/usr/bin/env python3
"""
銘柄別時系列予測一貫性分析

各銘柄ごとに、様々なタイミングで実施したクラッシュ予測の一貫性を分析し、
特定の時点への収束性を確認する
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# 環境設定
load_dotenv()
sys.path.append('.')

def main():
    print("🎯 銘柄別時系列予測一貫性分析")
    print("=" * 60)
    
    from src.analysis.time_series_prediction_analyzer import TimeSeriesPredictionAnalyzer
    from src.data_sources.fred_data_client import FREDDataClient
    
    # 分析対象銘柄
    symbols = {
        'NASDAQ': 'NASDAQCOM',
        'SP500': 'SP500',
        'DJIA': 'DJIA'
    }
    
    # 分析期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3ヶ月間の分析
    
    print(f"📅 分析期間: {start_date.date()} - {end_date.date()}")
    print(f"📊 分析銘柄: {list(symbols.keys())}")
    print()
    
    # データクライアント初期化
    fred_client = FREDDataClient()
    analyzer = TimeSeriesPredictionAnalyzer()
    
    # 結果保存用
    os.makedirs('results/consistency_analysis', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    all_results = {}
    
    # 各銘柄の分析実行
    for symbol_display, symbol_fred in symbols.items():
        print(f"🔍 {symbol_display} 分析開始...")
        
        try:
            # 一貫性分析実行
            metrics = analyzer.analyze_symbol_consistency(
                symbol_display,  # 表示名
                fred_client,
                start_date,
                end_date,
                analysis_interval_days=7  # 週次分析
            )
            
            all_results[symbol_display] = metrics
            
            # レポート生成・表示
            report = analyzer.generate_report(symbol_display)
            print(report)
            print()
            
            # 詳細データ保存
            detail_file = f'results/consistency_analysis/{symbol_display.lower()}_consistency_{timestamp}.csv'
            analyzer.save_results(symbol_display, detail_file)
            
            # 可視化
            viz_file = f'results/consistency_analysis/{symbol_display.lower()}_consistency_{timestamp}.png'
            analyzer.visualize_consistency(symbol_display, viz_file)
            
        except Exception as e:
            print(f"❌ {symbol_display} 分析エラー: {str(e)}")
            continue
    
    # サマリーレポート生成
    generate_summary_report(all_results, timestamp)
    
    print("✅ 全銘柄の一貫性分析完了")
    print(f"📁 結果保存先: results/consistency_analysis/")

def generate_summary_report(results: dict, timestamp: str):
    """全銘柄のサマリーレポート生成"""
    
    print("\n" + "=" * 60)
    print("📋 全銘柄サマリーレポート")
    print("=" * 60)
    
    summary_data = []
    
    for symbol, metrics in results.items():
        summary_data.append({
            'Symbol': symbol,
            'Total Predictions': metrics.total_predictions,
            'Usable Predictions': metrics.usable_predictions,
            'Usable Rate': f"{metrics.usable_predictions/max(metrics.total_predictions,1):.1%}",
            'Prediction Std (days)': f"{metrics.prediction_std_days:.1f}",
            'Consistency Score': f"{metrics.consistency_score:.3f}",
            'Convergence Date': metrics.convergence_date.date() if metrics.convergence_date else 'N/A',
            'Convergence Confidence': f"{metrics.convergence_confidence:.2%}",
            'Mean Confidence': f"{metrics.confidence_mean:.2%}"
        })
        
        # 個別銘柄サマリー
        print(f"\n🎯 {symbol}:")
        print(f"   一貫性スコア: {metrics.consistency_score:.3f}")
        print(f"   収束予測日: {metrics.convergence_date.date() if metrics.convergence_date else 'N/A'}")
        print(f"   予測ばらつき: {metrics.prediction_std_days:.1f} 日")
        
        # 評価
        if metrics.consistency_score > 0.8:
            print(f"   📊 評価: 高一貫性 - 信頼できる予測")
        elif metrics.consistency_score > 0.6:
            print(f"   📊 評価: 中一貫性 - 要注意監視")
        else:
            print(f"   📊 評価: 低一貫性 - 予測信頼性に問題")
    
    # サマリーCSV保存
    summary_df = pd.DataFrame(summary_data)
    summary_file = f'results/consistency_analysis/summary_report_{timestamp}.csv'
    summary_df.to_csv(summary_file, index=False)
    
    print(f"\n💾 サマリーレポート保存: {summary_file}")
    
    # 最も一貫性の高い銘柄
    if results:
        best_symbol = max(results.keys(), key=lambda s: results[s].consistency_score)
        best_score = results[best_symbol].consistency_score
        
        print(f"\n🏆 最高一貫性銘柄: {best_symbol} (スコア: {best_score:.3f})")
        
        if results[best_symbol].convergence_date:
            days_to_convergence = (results[best_symbol].convergence_date - datetime.now()).days
            print(f"🎯 収束予測: {results[best_symbol].convergence_date.date()} ({days_to_convergence}日後)")
    
    # 警告銘柄
    warning_symbols = [s for s, m in results.items() if m.consistency_score < 0.6]
    if warning_symbols:
        print(f"\n⚠️ 要注意銘柄: {', '.join(warning_symbols)}")
        print("   → 予測一貫性が低く、注意深い監視が必要")

def quick_analysis():
    """簡易分析（テスト用）"""
    print("🔬 簡易一貫性分析テスト")
    print("-" * 40)
    
    from src.analysis.time_series_prediction_analyzer import TimeSeriesPredictionAnalyzer
    from src.data_sources.fred_data_client import FREDDataClient
    
    # 短期テスト（2週間、3回分析）
    analyzer = TimeSeriesPredictionAnalyzer()
    fred_client = FREDDataClient()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    metrics = analyzer.analyze_symbol_consistency(
        'NASDAQ', fred_client, start_date, end_date, analysis_interval_days=7
    )
    
    print(analyzer.generate_report('NASDAQ'))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='銘柄別時系列予測一貫性分析')
    parser.add_argument('--quick', action='store_true', help='簡易テスト実行')
    
    args = parser.parse_args()
    
    if args.quick:
        quick_analysis()
    else:
        main()