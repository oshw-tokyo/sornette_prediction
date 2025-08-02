#!/usr/bin/env python3
"""
NASDAQ過去時点分析

複数の過去時点でLPPLフィッティングを実行し、
予測の時系列推移と安定性を検証
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

from src.data_sources.fred_data_client import FREDDataClient
from src.fitting.multi_criteria_selection import MultiCriteriaSelector
import matplotlib.dates as mdates

def main():
    print("🕐 NASDAQ過去時点分析")
    print("=" * 70)
    
    # 1. NASDAQデータ取得（長期間）
    print("\n📊 Step 1: NASDAQ長期データ取得...")
    nasdaq_data = fetch_nasdaq_long_term()
    
    if nasdaq_data is None:
        print("❌ データ取得失敗")
        return
    
    # 2. 過去時点での分析実行
    print("\n📈 Step 2: 過去時点での系統的分析...")
    retrospective_results = perform_retrospective_analysis(nasdaq_data)
    
    # 3. 予測の時系列推移分析
    print("\n📊 Step 3: 予測推移の分析...")
    analyze_prediction_evolution(retrospective_results)
    
    # 4. 結果の可視化
    print("\n📈 Step 4: 結果の可視化...")
    visualize_retrospective_results(retrospective_results, nasdaq_data)
    
    # 5. 詳細レポート生成
    print("\n📄 Step 5: 詳細レポート生成...")
    generate_detailed_report(retrospective_results, nasdaq_data)
    
    print("\n✅ 過去時点分析完了")

def fetch_nasdaq_long_term():
    """NASDAQ長期データの取得"""
    client = FREDDataClient()
    
    # 過去3年分のデータを取得
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)
    
    print(f"   期間: {start_date.date()} - {end_date.date()}")
    
    data = client.get_series_data(
        'NASDAQCOM',
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    if data is not None:
        print(f"   ✅ {len(data)}日分のデータ取得成功")
        print(f"   価格範囲: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
    
    return data

def perform_retrospective_analysis(data):
    """過去時点での系統的分析"""
    results = []
    
    # 分析設定
    analysis_windows = [365, 730, 1095]  # 1年、2年、3年
    lookback_intervals = 7  # 7日ごとに過去に遡る
    lookback_periods = 26  # 26週間（約6ヶ月）分
    
    # 現在から過去に遡って分析
    current_date = data.index[-1]
    
    for i in range(lookback_periods):
        analysis_date = current_date - timedelta(days=i * lookback_intervals)
        
        # この日付までのデータを取得
        historical_data = data[data.index <= analysis_date]
        
        if len(historical_data) < 365:
            continue
        
        print(f"\n   📅 分析日: {analysis_date.date()}")
        
        for window_days in analysis_windows:
            if len(historical_data) >= window_days:
                # ウィンドウデータの抽出
                window_data = historical_data.tail(window_days).copy()
                
                # LPPL分析実行
                result = analyze_at_point(
                    window_data, 
                    analysis_date, 
                    window_days
                )
                
                if result:
                    results.append(result)
                    print(f"      {window_days}日窓: tc={result['tc']:.3f}, " +
                          f"予測日={result['predicted_date'].date()}, " +
                          f"R²={result['r_squared']:.3f}")
    
    return results

def analyze_at_point(window_data, analysis_date, window_days):
    """特定時点でのLPPL分析"""
    try:
        selector = MultiCriteriaSelector()
        selection_result = selector.perform_comprehensive_fitting(window_data)
        
        if selection_result.selections:
            # デフォルト（R²最大）結果を使用
            candidate = selection_result.get_selected_result()
            
            if candidate and candidate.r_squared > 0.7:
                # 予測日計算
                observation_days = window_days
                days_to_critical = (candidate.tc - 1.0) * observation_days
                predicted_date = analysis_date + timedelta(days=days_to_critical)
                
                return {
                    'analysis_date': analysis_date,
                    'window_days': window_days,
                    'tc': candidate.tc,
                    'beta': candidate.beta,
                    'omega': candidate.omega,
                    'r_squared': candidate.r_squared,
                    'rmse': candidate.rmse,
                    'predicted_date': predicted_date,
                    'days_to_crash': days_to_critical,
                    'window_start': window_data.index[0],
                    'window_end': window_data.index[-1],
                    'last_price': window_data['Close'].iloc[-1]
                }
        
    except Exception as e:
        print(f"         ⚠️ 分析エラー: {str(e)}")
    
    return None

def analyze_prediction_evolution(results):
    """予測の時系列推移分析"""
    if not results:
        print("   ⚠️ 分析結果がありません")
        return
    
    # データフレーム変換
    df = pd.DataFrame(results)
    
    # ウィンドウ別にグループ化
    for window in df['window_days'].unique():
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        
        print(f"\n   📊 {window}日ウィンドウの予測推移:")
        
        # tc値の統計
        tc_mean = window_df['tc'].mean()
        tc_std = window_df['tc'].std()
        tc_trend = np.polyfit(range(len(window_df)), window_df['tc'].values, 1)[0]
        
        print(f"      平均tc: {tc_mean:.3f} (±{tc_std:.3f})")
        print(f"      tc値トレンド: {tc_trend:+.4f}/週")
        
        # 予測日の変動
        pred_dates = window_df['predicted_date']
        date_changes = []
        for i in range(1, len(pred_dates)):
            change = (pred_dates.iloc[i] - pred_dates.iloc[i-1]).days
            date_changes.append(change)
        
        if date_changes:
            avg_change = np.mean(date_changes)
            print(f"      予測日の平均変化: {avg_change:+.1f}日/週")
        
        # 最近の予測の安定性
        recent_df = window_df.tail(8)  # 直近8週間
        if len(recent_df) > 1:
            recent_tc_std = recent_df['tc'].std()
            print(f"      直近8週間のtc安定性: ±{recent_tc_std:.3f}")
            
            # 収束の兆候を検出
            if recent_tc_std < 0.05 and tc_trend < 0:
                print(f"      ⚠️ 警告: tc値が収束傾向（臨界点接近の可能性）")

def visualize_retrospective_results(results, nasdaq_data):
    """過去時点分析結果の可視化"""
    if not results:
        return
    
    df = pd.DataFrame(results)
    
    # スタイル設定
    plt.style.use('seaborn-v0_8-darkgrid')
    fig = plt.figure(figsize=(20, 12))
    
    # 1. tc値の時系列推移（ウィンドウ別）
    ax1 = plt.subplot(3, 2, 1)
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        ax1.plot(window_df['analysis_date'], window_df['tc'], 
                marker='o', label=f'{window}日', linewidth=2)
    
    ax1.axhline(1.3, color='red', linestyle='--', alpha=0.5, label='高リスク閾値')
    ax1.axhline(1.5, color='orange', linestyle='--', alpha=0.5, label='中リスク閾値')
    ax1.set_xlabel('分析実行日')
    ax1.set_ylabel('tc値')
    ax1.set_title('tc値の時系列推移')
    ax1.legend()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 2. 予測日の推移
    ax2 = plt.subplot(3, 2, 2)
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        ax2.plot(window_df['analysis_date'], window_df['predicted_date'], 
                marker='s', label=f'{window}日', linewidth=2)
    
    # 実際の日付との比較線
    ax2.plot([df['analysis_date'].min(), df['analysis_date'].max()],
             [df['analysis_date'].min(), df['analysis_date'].max()],
             'k--', alpha=0.3, label='分析日=予測日')
    
    ax2.set_xlabel('分析実行日')
    ax2.set_ylabel('予測クラッシュ日')
    ax2.set_title('予測日の時系列推移')
    ax2.legend()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax2.yaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 3. R²値の推移
    ax3 = plt.subplot(3, 2, 3)
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        ax3.plot(window_df['analysis_date'], window_df['r_squared'], 
                marker='^', label=f'{window}日', linewidth=2)
    
    ax3.axhline(0.8, color='green', linestyle='--', alpha=0.5, label='高品質閾値')
    ax3.set_xlabel('分析実行日')
    ax3.set_ylabel('R²値')
    ax3.set_title('モデル適合度の推移')
    ax3.legend()
    ax3.set_ylim(0.5, 1.0)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 4. 予測までの日数
    ax4 = plt.subplot(3, 2, 4)
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        days_to_crash = (window_df['predicted_date'] - window_df['analysis_date']).dt.days
        ax4.plot(window_df['analysis_date'], days_to_crash, 
                marker='D', label=f'{window}日', linewidth=2)
    
    ax4.axhline(0, color='red', linestyle='-', linewidth=2, alpha=0.8)
    ax4.axhline(30, color='orange', linestyle='--', alpha=0.5, label='1ヶ月')
    ax4.axhline(90, color='yellow', linestyle='--', alpha=0.5, label='3ヶ月')
    ax4.set_xlabel('分析実行日')
    ax4.set_ylabel('予測までの日数')
    ax4.set_title('クラッシュまでの予測日数')
    ax4.legend()
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 5. 最新分析での各ウィンドウ比較
    ax5 = plt.subplot(3, 2, 5)
    latest_date = df['analysis_date'].max()
    latest_df = df[df['analysis_date'] == latest_date]
    
    if not latest_df.empty:
        windows = latest_df['window_days'].values
        tc_values = latest_df['tc'].values
        colors = ['red' if tc <= 1.3 else 'orange' if tc <= 1.5 else 'green' for tc in tc_values]
        
        bars = ax5.bar(windows, tc_values, color=colors, alpha=0.7, edgecolor='black')
        ax5.axhline(1.3, color='red', linestyle='--', alpha=0.5)
        ax5.axhline(1.5, color='orange', linestyle='--', alpha=0.5)
        ax5.set_xlabel('分析ウィンドウ（日）')
        ax5.set_ylabel('tc値')
        ax5.set_title(f'最新分析結果 ({latest_date.date()})')
        
        # 値をバーの上に表示
        for bar, tc in zip(bars, tc_values):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{tc:.3f}', ha='center', va='bottom')
    
    # 6. NASDAQ価格と予測の重ね合わせ
    ax6 = plt.subplot(3, 2, 6)
    
    # 価格データ
    recent_nasdaq = nasdaq_data.tail(180)  # 直近6ヶ月
    ax6.plot(recent_nasdaq.index, recent_nasdaq['Close'], 'b-', linewidth=2, label='NASDAQ')
    
    # 各時点での予測をマーク
    latest_predictions = df.groupby('analysis_date').first()
    for _, row in latest_predictions.tail(10).iterrows():
        ax6.axvline(row['predicted_date'], color='red', alpha=0.3, linestyle='--')
        ax6.text(row['predicted_date'], recent_nasdaq['Close'].max() * 0.95,
                f"tc={row['tc']:.2f}", rotation=90, fontsize=8, ha='right')
    
    ax6.set_xlabel('日付')
    ax6.set_ylabel('NASDAQ価格')
    ax6.set_title('NASDAQ価格と予測日の推移')
    ax6.legend()
    ax6.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    plt.tight_layout()
    
    # 保存
    os.makedirs('results/retrospective_analysis', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'results/retrospective_analysis/nasdaq_retrospective_{timestamp}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n   📊 可視化保存: {filename}")
    plt.show()

def generate_detailed_report(results, nasdaq_data):
    """詳細レポートの生成"""
    if not results:
        return
    
    df = pd.DataFrame(results)
    
    print("\n" + "=" * 70)
    print("📋 NASDAQ過去時点分析 詳細レポート")
    print("=" * 70)
    
    # 全体統計
    print(f"\n📊 全体統計:")
    print(f"   分析期間: {df['analysis_date'].min().date()} - {df['analysis_date'].max().date()}")
    print(f"   総分析数: {len(df)}")
    print(f"   平均tc値: {df['tc'].mean():.3f} (±{df['tc'].std():.3f})")
    print(f"   平均R²: {df['r_squared'].mean():.3f}")
    
    # ウィンドウ別分析
    print(f"\n📈 ウィンドウ別分析:")
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window]
        print(f"\n   {window}日ウィンドウ:")
        print(f"     サンプル数: {len(window_df)}")
        print(f"     tc値範囲: {window_df['tc'].min():.3f} - {window_df['tc'].max():.3f}")
        print(f"     平均tc: {window_df['tc'].mean():.3f}")
        
        # 最新の予測
        latest = window_df[window_df['analysis_date'] == window_df['analysis_date'].max()].iloc[0]
        print(f"     最新予測: tc={latest['tc']:.3f}, 予測日={latest['predicted_date'].date()}")
    
    # 予測の収束分析
    print(f"\n🎯 予測の収束分析:")
    recent_weeks = 8
    for window in sorted(df['window_days'].unique()):
        window_df = df[df['window_days'] == window].sort_values('analysis_date')
        recent_df = window_df.tail(recent_weeks)
        
        if len(recent_df) > 3:
            tc_trend = np.polyfit(range(len(recent_df)), recent_df['tc'].values, 1)[0]
            tc_std = recent_df['tc'].std()
            
            print(f"\n   {window}日ウィンドウ（直近{recent_weeks}週）:")
            print(f"     tc値トレンド: {tc_trend:+.4f}/週")
            print(f"     tc値標準偏差: {tc_std:.4f}")
            
            # 収束判定
            if abs(tc_trend) < 0.01 and tc_std < 0.05:
                print(f"     → 安定収束")
            elif tc_trend < -0.02:
                print(f"     → 臨界点接近中 ⚠️")
            else:
                print(f"     → 変動中")
    
    # 警告サマリー
    print(f"\n⚠️ 警告サマリー:")
    latest_df = df[df['analysis_date'] == df['analysis_date'].max()]
    high_risk = latest_df[latest_df['tc'] <= 1.3]
    
    if not high_risk.empty:
        print(f"   高リスク検出: {len(high_risk)}件")
        for _, row in high_risk.iterrows():
            print(f"     {row['window_days']}日窓: tc={row['tc']:.3f}, 予測={row['predicted_date'].date()}")
    else:
        print(f"   現時点で高リスク（tc≤1.3）なし")
    
    # CSVエクスポート
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'results/retrospective_analysis/nasdaq_retrospective_data_{timestamp}.csv'
    df.to_csv(filename, index=False)
    print(f"\n💾 詳細データ保存: {filename}")

if __name__ == "__main__":
    main()