#!/usr/bin/env python3
"""
品質評価付きフィッティングのテスト

境界張り付きやその他の問題を適切に検出し、
メタ情報を付与してフィッティング結果を評価
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# 環境設定
load_dotenv()
sys.path.append('.')

def main():
    print("🔍 品質評価付きフィッティングテスト")
    print("=" * 70)
    
    # 1. 品質評価システムの基本テスト
    print("\n📊 Step 1: 品質評価システムの基本テスト...")
    test_quality_evaluator()
    
    # 2. 品質評価統合多基準選択のテスト
    print("\n🎯 Step 2: 品質評価統合多基準選択のテスト...")
    test_quality_aware_selection()
    
    # 3. NASDAQデータでの実証テスト
    print("\n📈 Step 3: NASDAQデータでの実証テスト...")
    test_nasdaq_with_quality_assessment()
    
    print("\n✅ 品質評価付きフィッティングテスト完了")

def test_quality_evaluator():
    """品質評価システムの基本テスト"""
    from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator, FittingQuality
    
    evaluator = FittingQualityEvaluator()
    
    # テストケース1: 境界張り付き（NASDAQ問題）
    print("\n   🔍 テストケース1: 境界張り付き（NASDAQ問題）")
    params1 = {
        'tc': 1.001,  # 下限に張り付き
        'beta': 0.35,
        'omega': 6.5,
        'phi': 0.0,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats1 = {'r_squared': 0.95, 'rmse': 0.03}
    bounds1 = ([1.001, 0.1, 3.0, -3.14, -10, -10, -1.0], 
               [3.0, 0.8, 15.0, 3.14, 10, 10, 1.0])
    
    assessment1 = evaluator.evaluate_fitting(params1, stats1, bounds1)
    print(f"      品質: {assessment1.quality.value}")
    print(f"      信頼度: {assessment1.confidence:.2%}")
    print(f"      使用可能: {assessment1.is_usable}")
    print(f"      問題点: {assessment1.issues}")
    print(f"      境界張り付きパラメータ: {assessment1.metadata.get('boundary_stuck_params', 'なし')}")
    
    # テストケース2: 高品質フィット
    print("\n   🔍 テストケース2: 高品質フィット")
    params2 = {
        'tc': 1.25,
        'beta': 0.33,
        'omega': 6.36,
        'phi': 0.1,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats2 = {'r_squared': 0.92, 'rmse': 0.04}
    
    assessment2 = evaluator.evaluate_fitting(params2, stats2)
    print(f"      品質: {assessment2.quality.value}")
    print(f"      信頼度: {assessment2.confidence:.2%}")
    print(f"      使用可能: {assessment2.is_usable}")
    print(f"      問題点: {assessment2.issues}")
    
    # テストケース3: 過学習疑い
    print("\n   🔍 テストケース3: 過学習疑い")
    params3 = {
        'tc': 1.002,  # 境界近く
        'beta': 0.95,  # 極端な値
        'omega': 18.0,  # 極端な値
        'phi': 0.0,
        'A': 5.0,
        'B': 0.5,
        'C': 0.1
    }
    stats3 = {'r_squared': 0.98, 'rmse': 0.02}
    
    assessment3 = evaluator.evaluate_fitting(params3, stats3)
    print(f"      品質: {assessment3.quality.value}")
    print(f"      信頼度: {assessment3.confidence:.2%}")
    print(f"      使用可能: {assessment3.is_usable}")
    print(f"      問題点: {assessment3.issues}")

def test_quality_aware_selection():
    """品質評価統合多基準選択のテスト"""
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    # 合成データ生成（境界張り付きが発生しやすいパターン）
    print("\n   📊 合成データ生成...")
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    
    # 境界近くに収束しやすいパターン
    t = np.linspace(0.1, 0.99, 500)
    tc_true = 1.02  # 境界に近い
    log_prices = (5.0 + 0.3 * (tc_true - t)**0.2 * 
                 (1 + 0.05 * np.cos(5 * np.log(tc_true - t))) + 
                 0.03 * np.random.randn(500))
    prices = np.exp(log_prices)
    
    data = pd.DataFrame({'Close': prices}, index=dates)
    print(f"      データ生成完了: {len(data)}点")
    
    # 多基準選択実行
    print("\n   🎯 品質評価付き多基準選択実行...")
    selector = MultiCriteriaSelector()
    result = selector.perform_comprehensive_fitting(data)
    
    print(f"      総候補数: {len(result.all_candidates)}")
    print(f"      品質評価済み候補: {len([c for c in result.all_candidates if c.quality_assessment])}")
    print(f"      使用可能候補: {len([c for c in result.all_candidates if c.quality_assessment and c.quality_assessment.is_usable])}")
    
    # 品質別の分類
    quality_counts = {}
    for candidate in result.all_candidates:
        if candidate.quality_assessment:
            quality = candidate.quality_assessment.quality.value
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
    
    print(f"\n   📋 品質別分類:")
    for quality, count in quality_counts.items():
        print(f"      {quality}: {count}件")
    
    # 各選択基準の結果と品質
    print(f"\n   🎯 各選択基準での結果と品質:")
    for criteria, candidate in result.selections.items():
        if candidate and candidate.quality_assessment:
            qa = candidate.quality_assessment
            print(f"      {criteria.value}:")
            print(f"        tc={candidate.tc:.4f}, R²={candidate.r_squared:.3f}")
            print(f"        品質={qa.quality.value}, 信頼度={qa.confidence:.2%}")
            print(f"        使用可能={qa.is_usable}")
            if qa.issues:
                print(f"        問題: {qa.issues[:2]}")  # 最初の2つの問題

def test_nasdaq_with_quality_assessment():
    """NASDAQデータでの品質評価付き分析"""
    from src.data_sources.fred_data_client import FREDDataClient
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    # NASDAQデータ取得
    print("\n   📊 NASDAQデータ取得...")
    client = FREDDataClient()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2年分
    
    nasdaq_data = client.get_series_data(
        'NASDAQCOM',
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    if nasdaq_data is None:
        print("      ❌ データ取得失敗")
        return
    
    print(f"      ✅ {len(nasdaq_data)}日分のデータ取得")
    
    # 品質評価付き分析実行
    print("\n   🔍 品質評価付き分析実行...")
    selector = MultiCriteriaSelector()
    result = selector.perform_comprehensive_fitting(nasdaq_data)
    
    print(f"      総候補数: {len(result.all_candidates)}")
    
    # 品質分析
    boundary_stuck_count = 0
    usable_count = 0
    failed_count = 0
    
    for candidate in result.all_candidates:
        if candidate.quality_assessment:
            qa = candidate.quality_assessment
            
            if qa.quality.value == 'boundary_stuck':
                boundary_stuck_count += 1
            
            if qa.is_usable:
                usable_count += 1
            else:
                failed_count += 1
    
    print(f"\n   📊 品質分析結果:")
    print(f"      境界張り付き候補: {boundary_stuck_count}")
    print(f"      使用可能候補: {usable_count}")
    print(f"      使用不可候補: {failed_count}")
    
    # 品質の良い候補のみを表示
    print(f"\n   ✅ 品質良好な候補:")
    good_candidates = [c for c in result.all_candidates 
                      if c.quality_assessment and c.quality_assessment.is_usable]
    
    if good_candidates:
        # 品質の良い候補をtc値でソート
        good_candidates.sort(key=lambda x: x.tc)
        
        for i, candidate in enumerate(good_candidates[:5]):  # 上位5件
            qa = candidate.quality_assessment
            print(f"      候補{i+1}: tc={candidate.tc:.4f}, R²={candidate.r_squared:.3f}")
            print(f"              品質={qa.quality.value}, 信頼度={qa.confidence:.2%}")
    else:
        print("      ⚠️ 品質良好な候補が見つかりませんでした")
    
    # 従来選択（R²最大）vs 品質考慮選択の比較
    print(f"\n   🔄 従来選択 vs 品質考慮選択の比較:")
    
    # 従来のR²最大選択（品質無視）
    all_successful = [c for c in result.all_candidates if c.convergence_success]
    if all_successful:
        traditional_best = max(all_successful, key=lambda x: x.r_squared)
        print(f"      従来選択（R²最大）:")
        print(f"        tc={traditional_best.tc:.4f}, R²={traditional_best.r_squared:.3f}")
        if traditional_best.quality_assessment:
            print(f"        品質={traditional_best.quality_assessment.quality.value}")
            print(f"        使用可能={traditional_best.quality_assessment.is_usable}")
    
    # 品質考慮選択
    if good_candidates:
        quality_best = max(good_candidates, key=lambda x: x.quality_assessment.confidence)
        print(f"      品質考慮選択:")
        print(f"        tc={quality_best.tc:.4f}, R²={quality_best.r_squared:.3f}")
        print(f"        品質={quality_best.quality_assessment.quality.value}")
        print(f"        信頼度={quality_best.quality_assessment.confidence:.2%}")
    
    # 結果の可視化
    visualize_quality_results(result, nasdaq_data)

def visualize_quality_results(result, data):
    """品質評価結果の可視化"""
    print("\n   📊 結果可視化中...")
    
    # 候補の品質分布
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. tc値と品質の散布図
    quality_colors = {
        'high_quality': 'green',
        'acceptable': 'blue',
        'boundary_stuck': 'red',
        'poor_convergence': 'orange',
        'overfitting': 'purple',
        'unstable': 'brown',
        'failed': 'gray'
    }
    
    for candidate in result.all_candidates:
        if candidate.quality_assessment:
            quality = candidate.quality_assessment.quality.value
            color = quality_colors.get(quality, 'black')
            alpha = 0.8 if candidate.quality_assessment.is_usable else 0.3
            
            ax1.scatter(candidate.tc, candidate.r_squared, 
                       c=color, alpha=alpha, s=50)
    
    ax1.set_xlabel('tc value')
    ax1.set_ylabel('R² value')
    ax1.set_title('Candidate Quality Distribution (tc vs R²)')
    # 凡例を手動で作成
    legend_elements = [plt.scatter([], [], c=color, s=50, label=quality) 
                       for quality, color in quality_colors.items()]
    ax1.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 2. 品質カテゴリ別の候補数
    quality_counts = {}
    for candidate in result.all_candidates:
        if candidate.quality_assessment:
            quality = candidate.quality_assessment.quality.value
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
    
    if quality_counts:
        # 品質カテゴリを並び替え
        quality_order = ['high_quality', 'acceptable', 'boundary_stuck', 'poor_convergence', 
                        'overfitting', 'unstable', 'failed', 'critical_proximity']
        ordered_qualities = [q for q in quality_order if q in quality_counts]
        ordered_counts = [quality_counts[q] for q in ordered_qualities]
        ordered_colors = [quality_colors.get(q, 'gray') for q in ordered_qualities]
        
        bars = ax2.bar(range(len(ordered_qualities)), ordered_counts, 
                      color=ordered_colors, alpha=0.8, edgecolor='black', linewidth=1)
        ax2.set_xticks(range(len(ordered_qualities)))
        ax2.set_xticklabels(ordered_qualities, rotation=45, ha='right')
        
        # 値をバーの上に表示
        for bar, count in zip(bars, ordered_counts):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    str(count), ha='center', va='bottom')
    else:
        ax2.text(0.5, 0.5, 'No quality data available', ha='center', va='center',
                transform=ax2.transAxes, fontsize=12)
    
    ax2.set_ylabel('Number of Candidates')
    ax2.set_title('Candidates by Quality Category')
    ax2.grid(True, alpha=0.3)
    
    # 3. 使用可能 vs 使用不可の比較
    usable = [c for c in result.all_candidates 
              if c.quality_assessment and c.quality_assessment.is_usable]
    unusable = [c for c in result.all_candidates 
                if c.quality_assessment and not c.quality_assessment.is_usable]
    
    if usable:
        usable_tc = [c.tc for c in usable]
        ax3.hist(usable_tc, bins=20, alpha=0.7, color='green', label='Usable')
    
    if unusable:
        unusable_tc = [c.tc for c in unusable]
        ax3.hist(unusable_tc, bins=20, alpha=0.7, color='red', label='Not Usable')
    
    ax3.set_xlabel('tc value')
    ax3.set_ylabel('Number of Candidates')
    ax3.set_title('tc Distribution by Usability')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 価格データと予測
    ax4.plot(data.index, data['Close'], 'b-', linewidth=1, alpha=0.7, label='NASDAQ')
    
    # 使用可能な候補の予測を表示
    if usable:
        latest_date = data.index[-1]
        for candidate in usable[:3]:  # 上位3件
            days_to_crash = (candidate.tc - 1.0) * len(data)
            predicted_date = latest_date + timedelta(days=days_to_crash)
            ax4.axvline(predicted_date, color='green', alpha=0.5, linestyle='--')
    
    ax4.set_xlabel('Date')
    ax4.set_ylabel('Price')
    ax4.set_title('NASDAQ Price with High-Quality Predictions')
    ax4.legend()
    
    plt.tight_layout()
    
    # 保存
    os.makedirs('results/quality_assessment', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'results/quality_assessment/quality_aware_analysis_{timestamp}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"      📊 可視化保存: {filename}")
    plt.show()

if __name__ == "__main__":
    main()