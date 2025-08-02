#!/usr/bin/env python3
"""
個別株時系列予測一貫性分析

Alpha Vantage APIを使用して個別株の
LPPL予測一貫性を分析する
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
    print("📊 個別株時系列予測一貫性分析")
    print("=" * 60)
    
    # 統合データクライアント初期化
    from src.data_sources.unified_data_client import UnifiedDataClient
    from src.analysis.time_series_prediction_analyzer import TimeSeriesPredictionAnalyzer
    
    # データクライアント初期化
    data_client = UnifiedDataClient()
    
    if not data_client.available_sources:
        print("❌ 利用可能なデータソースがありません")
        return
    
    print(f"✅ 利用可能データソース: {data_client.available_sources}")
    
    # 分析対象銘柄（個別株中心）
    individual_stocks = {
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation', 
        'GOOGL': 'Alphabet Inc.',
        'TSLA': 'Tesla Inc.',
        'AMZN': 'Amazon.com Inc.'
    }
    
    market_indices = {
        'NASDAQ': 'NASDAQ Composite',
        'SP500': 'S&P 500'
    }
    
    # 全分析対象
    all_symbols = {**individual_stocks, **market_indices}
    
    print(f"📋 分析対象:")
    print(f"   個別株: {list(individual_stocks.keys())}")
    print(f"   指数: {list(market_indices.keys())}")
    
    # 分析期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)  # 2ヶ月間の分析（短縮版）
    
    print(f"📅 分析期間: {start_date.date()} - {end_date.date()}")
    print()
    
    # 結果保存用
    os.makedirs('results/individual_stock_analysis', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    analyzer = TimeSeriesPredictionAnalyzer()
    all_results = {}
    
    # 各銘柄の分析実行
    for i, (symbol, name) in enumerate(all_symbols.items(), 1):
        print(f"🔍 [{i}/{len(all_symbols)}] {symbol} ({name}) 分析開始...")
        
        try:
            # 一貫性分析実行
            metrics = analyzer.analyze_symbol_consistency(
                symbol,
                data_client,
                start_date,
                end_date,
                analysis_interval_days=14  # 2週間間隔（レート制限対策）
            )
            
            all_results[symbol] = {
                'metrics': metrics,
                'name': name,
                'category': 'stock' if symbol in individual_stocks else 'index'
            }
            
            # 簡易レポート表示
            print(f"   📊 {symbol} 結果サマリー:")
            print(f"      一貫性スコア: {metrics.consistency_score:.3f}")
            print(f"      予測数: {metrics.usable_predictions}/{metrics.total_predictions}")
            if metrics.convergence_date:
                days_to_convergence = (metrics.convergence_date - datetime.now()).days
                print(f"      収束予測: {metrics.convergence_date.date()} ({days_to_convergence}日後)")
            print()
            
            # 詳細データ保存
            detail_file = f'results/individual_stock_analysis/{symbol.lower()}_consistency_{timestamp}.csv'
            analyzer.save_results(symbol, detail_file)
            
            # 可視化
            viz_file = f'results/individual_stock_analysis/{symbol.lower()}_consistency_{timestamp}.png'
            analyzer.visualize_consistency(symbol, viz_file)
            
        except Exception as e:
            print(f"❌ {symbol} 分析エラー: {str(e)}")
            continue
    
    # 総合レポート生成
    generate_individual_stock_report(all_results, timestamp)
    
    print("✅ 個別株分析完了")
    print(f"📁 結果保存先: results/individual_stock_analysis/")

def generate_individual_stock_report(results: dict, timestamp: str):
    """個別株分析の総合レポート生成"""
    
    print("\n" + "=" * 60)
    print("📋 個別株 vs 指数 比較レポート")
    print("=" * 60)
    
    # カテゴリ別分類
    stocks = {k: v for k, v in results.items() if v['category'] == 'stock'}
    indices = {k: v for k, v in results.items() if v['category'] == 'index'}
    
    print(f"📊 分析結果サマリー:")
    print(f"   個別株: {len(stocks)}銘柄")
    print(f"   指数: {len(indices)}銘柄")
    
    # 詳細比較
    all_data = []
    
    for symbol, data in results.items():
        metrics = data['metrics']
        all_data.append({
            'Symbol': symbol,
            'Name': data['name'],
            'Category': data['category'],
            'Consistency Score': f"{metrics.consistency_score:.3f}",
            'Total Predictions': metrics.total_predictions,
            'Usable Predictions': metrics.usable_predictions,
            'Usable Rate': f"{metrics.usable_predictions/max(metrics.total_predictions,1):.1%}",
            'Prediction Std (days)': f"{metrics.prediction_std_days:.1f}",
            'Convergence Date': metrics.convergence_date.date() if metrics.convergence_date else 'N/A',
            'Mean Confidence': f"{metrics.confidence_mean:.2%}"
        })
    
    # 結果をDataFrameに変換してソート
    import pandas as pd
    df = pd.DataFrame(all_data)
    df_sorted = df.sort_values('Consistency Score', ascending=False)
    
    print(f"\n🏆 一貫性ランキング:")
    for i, row in df_sorted.head(10).iterrows():
        rank = df_sorted.index.get_loc(i) + 1
        category_icon = "📈" if row['Category'] == 'stock' else "📊"
        print(f"   {rank:2d}. {category_icon} {row['Symbol']} ({row['Name'][:20]}...)")
        print(f"        一貫性: {row['Consistency Score']}, 予測数: {row['Usable Predictions']}")
    
    # カテゴリ別分析
    if stocks and indices:
        stock_scores = [results[s]['metrics'].consistency_score for s in stocks]
        index_scores = [results[s]['metrics'].consistency_score for s in indices]
        
        print(f"\n📊 カテゴリ別比較:")
        print(f"   個別株平均一貫性: {np.mean(stock_scores):.3f}")
        print(f"   指数平均一貫性: {np.mean(index_scores):.3f}")
        
        if np.mean(stock_scores) > np.mean(index_scores):
            print(f"   💡 個別株の方が予測一貫性が高い傾向")
        else:
            print(f"   💡 指数の方が予測一貫性が高い傾向")
    
    # 警告銘柄
    low_consistency = [s for s, d in results.items() 
                      if d['metrics'].consistency_score < 0.5]
    
    if low_consistency:
        print(f"\n⚠️ 低一貫性銘柄 (< 0.5):")
        for symbol in low_consistency:
            data = results[symbol]
            print(f"   - {symbol} ({data['name'][:30]}): {data['metrics'].consistency_score:.3f}")
    
    # 高リスク収束予測
    near_term_predictions = []
    for symbol, data in results.items():
        if data['metrics'].convergence_date:
            days_to_convergence = (data['metrics'].convergence_date - datetime.now()).days
            if 0 < days_to_convergence < 180:  # 6ヶ月以内
                near_term_predictions.append((symbol, data, days_to_convergence))
    
    if near_term_predictions:
        near_term_predictions.sort(key=lambda x: x[2])  # 日数でソート
        
        print(f"\n🚨 短期収束予測 (6ヶ月以内):")
        for symbol, data, days in near_term_predictions:
            category_icon = "📈" if data['category'] == 'stock' else "📊"
            print(f"   {category_icon} {symbol}: {data['metrics'].convergence_date.date()} ({days}日後)")
            print(f"      一貫性: {data['metrics'].consistency_score:.3f}, 信頼度: {data['metrics'].convergence_confidence:.2%}")
    
    # CSVレポート保存
    report_file = f'results/individual_stock_analysis/individual_stock_report_{timestamp}.csv'
    df_sorted.to_csv(report_file, index=False)
    print(f"\n💾 詳細レポート保存: {report_file}")
    
    # 推奨アクション
    print(f"\n💡 推奨アクション:")
    if low_consistency:
        print("   1. 低一貫性銘柄の分析期間・手法見直し")
    if near_term_predictions:
        print("   2. 短期収束予測銘柄の監視強化")
    print("   3. 高一貫性銘柄のパラメータ分析")
    print("   4. より長期間でのデータ分析実行")

def quick_individual_test():
    """個別株の簡易テスト"""
    print("🔬 個別株分析簡易テスト")
    print("-" * 40)
    
    from src.data_sources.unified_data_client import UnifiedDataClient
    from src.analysis.time_series_prediction_analyzer import TimeSeriesPredictionAnalyzer
    
    # 1銘柄のみでテスト
    client = UnifiedDataClient()
    analyzer = TimeSeriesPredictionAnalyzer()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 1ヶ月
    
    # Appleでテスト
    print("🍎 Apple (AAPL) 簡易分析:")
    metrics = analyzer.analyze_symbol_consistency(
        'AAPL', client, start_date, end_date, analysis_interval_days=15
    )
    
    print(analyzer.generate_report('AAPL'))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='個別株時系列予測一貫性分析')
    parser.add_argument('--quick', action='store_true', help='簡易テスト実行')
    
    args = parser.parse_args()
    
    if args.quick:
        quick_individual_test()
    else:
        main()