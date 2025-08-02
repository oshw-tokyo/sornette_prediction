#!/usr/bin/env python3
"""
2016-2019年期間の詳細分析

目的: 高品質フィット（R²=0.968）の詳細分析により、
     「隠れたバブル特性」か「単なる数学的フィット」かを判定
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

# Environment setup
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.fitting.utils import logarithm_periodic_func
from src.data_sources.fred_data_client import FREDDataClient
from src.parameter_management import AdaptiveParameterManager, MarketCharacteristics, BubbleType, FittingStrategy
from scipy.optimize import curve_fit

def analyze_2016_2019_detailed():
    """2016-2019年期間の詳細分析"""
    
    print("🔍 2016-2019年期間の詳細分析開始")
    print("=" * 60)
    
    # データ取得
    client = FREDDataClient()
    data = client.get_series_data('NASDAQCOM', '2016-01-01', '2019-12-31')
    
    if data is None:
        print("❌ データ取得失敗")
        return None
    
    print(f"✅ データ取得成功: {len(data)}日分")
    print(f"   期間: {data.index[0].date()} - {data.index[-1].date()}")
    
    # パラメータマネージャー初期化
    param_manager = AdaptiveParameterManager()
    
    # 市場特性設定
    market_chars = MarketCharacteristics(
        data_period_days=len(data),
        volatility=data['Close'].pct_change().std() * np.sqrt(252),
        bubble_magnitude=((data['Close'].max() / data['Close'].iloc[0]) - 1) * 100,
        bubble_type=BubbleType.UNKNOWN,
        data_quality_score=1.0
    )
    
    # フィッティング実行（詳細ログ付き）
    detailed_results = execute_detailed_fitting(data, param_manager, market_chars)
    
    # tc値の詳細分析
    tc_analysis = analyze_tc_values(detailed_results, data.index[0], data.index[-1])
    
    # 予測時期と実際のイベントの比較
    event_comparison = compare_with_actual_events(tc_analysis, data.index[-1])
    
    # 結果の可視化
    create_detailed_visualization(data, detailed_results, tc_analysis, event_comparison)
    
    # 最終解釈
    final_interpretation = interpret_results(detailed_results, tc_analysis, event_comparison)
    
    return {
        'data': data,
        'fitting_results': detailed_results,
        'tc_analysis': tc_analysis,
        'event_comparison': event_comparison,
        'interpretation': final_interpretation
    }

def execute_detailed_fitting(data, param_manager, market_chars):
    """詳細なフィッティング実行"""
    
    print("\n🔬 詳細フィッティング実行...")
    
    # CONSERVATIVEストラテジーでパラメータ取得
    param_set = param_manager.get_parameters_for_market(market_chars, FittingStrategy.CONSERVATIVE)
    
    # 初期値生成
    initial_values = param_manager.generate_initial_values(param_set, data['Close'].values)
    
    # 境界取得
    lower_bounds, upper_bounds = param_manager.get_fitting_bounds(param_set)
    
    # データ準備
    log_prices = np.log(data['Close'].values)
    t = np.linspace(0, 1, len(data))
    
    print(f"   初期値セット数: {len(initial_values)}")
    print(f"   データ点数: {len(data)}")
    
    successful_fits = []
    failed_attempts = 0
    
    for i, init_vals in enumerate(initial_values):
        try:
            # 初期値をリストに変換
            p0 = [
                init_vals['tc'], init_vals['beta'], init_vals['omega'], 
                init_vals['phi'], init_vals['A'], init_vals['B'], init_vals['C']
            ]
            
            # フィッティング実行
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, log_prices,
                p0=p0, 
                bounds=(lower_bounds, upper_bounds),
                method='trf',
                maxfev=10000,
                ftol=1e-8,
                xtol=1e-8
            )
            
            # 評価
            y_pred = logarithm_periodic_func(t, *popt)
            r_squared = 1 - (np.sum((log_prices - y_pred)**2) / 
                           np.sum((log_prices - np.mean(log_prices))**2))
            rmse = np.sqrt(np.mean((log_prices - y_pred)**2))
            
            # パラメータ抽出
            params = {
                'tc': popt[0], 'beta': popt[1], 'omega': popt[2],
                'phi': popt[3], 'A': popt[4], 'B': popt[5], 'C': popt[6]
            }
            
            # 基本制約チェック
            if (popt[0] > 1.0 and 0.05 <= popt[1] <= 1.0 and 
                popt[2] > 0 and r_squared > 0.1):
                
                successful_fits.append({
                    'trial': i,
                    'parameters': params,
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'fitted_values': y_pred,
                    'initial_values': init_vals
                })
                
                # 高品質フィットの詳細ログ
                if r_squared > 0.9:
                    print(f"   🎯 高品質フィット #{i}: R²={r_squared:.4f}, tc={popt[0]:.4f}")
                    
        except Exception as e:
            failed_attempts += 1
            continue
    
    print(f"\n📊 フィッティング結果:")
    print(f"   成功: {len(successful_fits)}")
    print(f"   失敗: {failed_attempts}")
    print(f"   成功率: {len(successful_fits)/(len(initial_values)):.1%}")
    
    if successful_fits:
        r2_scores = [fit['r_squared'] for fit in successful_fits]
        print(f"   最良R²: {max(r2_scores):.4f}")
        print(f"   平均R²: {np.mean(r2_scores):.4f}")
    
    return successful_fits

def analyze_tc_values(fitting_results, start_date, end_date):
    """tc値の詳細分析"""
    
    if not fitting_results:
        return None
    
    print(f"\n📅 tc値詳細分析...")
    
    tc_values = [fit['parameters']['tc'] for fit in fitting_results]
    
    tc_analysis = {
        'values': tc_values,
        'mean': np.mean(tc_values),
        'std': np.std(tc_values),
        'min': np.min(tc_values),
        'max': np.max(tc_values),
        'median': np.median(tc_values)
    }
    
    print(f"   tc統計:")
    print(f"   平均: {tc_analysis['mean']:.4f}")
    print(f"   標準偏差: {tc_analysis['std']:.4f}")
    print(f"   範囲: [{tc_analysis['min']:.4f}, {tc_analysis['max']:.4f}]")
    print(f"   中央値: {tc_analysis['median']:.4f}")
    
    # 観測期間情報
    observation_days = (end_date - start_date).days
    observation_years = observation_days / 365.25
    
    print(f"\n⏰ 時間軸分析:")
    print(f"   観測期間: {observation_years:.1f}年 ({observation_days}日)")
    
    # 予測される臨界時刻の計算
    predicted_dates = []
    for tc in tc_values:
        # tcは正規化時間（0-1）での値なので、実際の日数に変換
        days_to_critical = (tc - 1.0) * observation_days
        predicted_date = end_date + timedelta(days=days_to_critical)
        predicted_dates.append(predicted_date)
    
    tc_analysis['predicted_dates'] = predicted_dates
    tc_analysis['mean_predicted_date'] = end_date + timedelta(days=(tc_analysis['mean'] - 1.0) * observation_days)
    
    print(f"   平均予測日: {tc_analysis['mean_predicted_date'].date()}")
    print(f"   予測日範囲: {min(predicted_dates).date()} - {max(predicted_dates).date()}")
    
    return tc_analysis

def compare_with_actual_events(tc_analysis, observation_end_date):
    """実際のイベントとの比較"""
    
    if tc_analysis is None:
        return None
    
    print(f"\n🎯 実際のイベントとの比較...")
    
    # 主要な市場イベント
    major_events = {
        'コロナショック': datetime(2020, 3, 23),    # 最安値日
        'コロナ急騰開始': datetime(2020, 4, 1),     # 反発開始
        '2021年急騰ピーク': datetime(2021, 2, 16), # NASDAQ史上最高値
        '2022年調整開始': datetime(2022, 1, 1),    # 金利上昇による調整
    }
    
    print(f"   観測終了: {observation_end_date.date()}")
    
    # 予測精度の評価
    mean_predicted_date = tc_analysis['mean_predicted_date']
    prediction_accuracy = {}
    
    for event_name, event_date in major_events.items():
        days_diff = abs((event_date - mean_predicted_date).days)
        prediction_accuracy[event_name] = {
            'event_date': event_date,
            'days_difference': days_diff,
            'accuracy_score': max(0, 1 - days_diff / 365)  # 1年以内で線形減衰
        }
        
        print(f"   {event_name}: {event_date.date()} (差: {days_diff}日)")
    
    # 最も近いイベントを特定
    closest_event = min(prediction_accuracy.items(), 
                       key=lambda x: x[1]['days_difference'])
    
    print(f"   最近接イベント: {closest_event[0]} (差: {closest_event[1]['days_difference']}日)")
    
    return {
        'major_events': major_events,
        'prediction_accuracy': prediction_accuracy,
        'closest_event': closest_event,
        'mean_predicted_date': mean_predicted_date
    }

def interpret_results(fitting_results, tc_analysis, event_comparison):
    """結果の総合解釈"""
    
    print(f"\n🧠 結果の総合解釈...")
    
    if not fitting_results or tc_analysis is None:
        return {'interpretation': 'ANALYSIS_FAILED', 'confidence': 0.0}
    
    # 統計的品質
    r2_scores = [fit['r_squared'] for fit in fitting_results]
    best_r2 = max(r2_scores)
    mean_r2 = np.mean(r2_scores)
    
    # tc値の妥当性
    mean_tc = tc_analysis['mean']
    tc_std = tc_analysis['std']
    tc_stability = 1.0 / (1.0 + tc_std)  # 安定性指標
    
    # 予測精度
    prediction_quality = 0.0
    if event_comparison:
        closest_event_accuracy = event_comparison['closest_event'][1]['accuracy_score']
        prediction_quality = closest_event_accuracy
    
    # 解釈分類
    interpretation = 'UNKNOWN'
    confidence = 0.0
    
    if best_r2 > 0.9 and 1.05 <= mean_tc <= 1.5 and prediction_quality > 0.5:
        interpretation = 'EARLY_BUBBLE_DETECTION'
        confidence = min(best_r2, prediction_quality, tc_stability)
        print("   🎯 解釈: 早期バブル特性検出")
        print("   根拠: 高品質フィット + 現実的tc値 + 実イベント対応")
        
    elif best_r2 > 0.9 and mean_tc > 2.0:
        interpretation = 'MATHEMATICAL_FIT_ONLY'
        confidence = best_r2 * 0.5  # 予測価値が低いので割引
        print("   📊 解釈: 数学的フィットのみ")
        print("   根拠: 高品質フィットだが非現実的tc値")
        
    elif best_r2 > 0.8 and tc_stability > 0.7:
        interpretation = 'LONG_TERM_TREND_CAPTURE'
        confidence = best_r2 * tc_stability * 0.7
        print("   📈 解釈: 長期トレンド捕捉")
        print("   根拠: 安定したパラメータ推定")
        
    else:
        interpretation = 'INCONCLUSIVE'
        confidence = 0.3
        print("   ❓ 解釈: 判定困難")
        print("   根拠: 混合的な指標")
    
    print(f"   信頼度: {confidence:.2f}")
    
    return {
        'interpretation': interpretation,
        'confidence': confidence,
        'statistical_quality': {'best_r2': best_r2, 'mean_r2': mean_r2},
        'tc_validity': {'mean_tc': mean_tc, 'stability': tc_stability},
        'prediction_quality': prediction_quality
    }

def create_detailed_visualization(data, fitting_results, tc_analysis, event_comparison):
    """詳細可視化の作成"""
    
    if not fitting_results:
        print("❌ 可視化データなし")
        return
    
    print(f"\n📊 詳細可視化作成中...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. メイン価格チャート + ベストフィット
    best_fit = max(fitting_results, key=lambda x: x['r_squared'])
    
    ax1.plot(data.index, data['Close'], 'b-', linewidth=1.5, label='実際のNASDAQ', alpha=0.8)
    
    # ベストフィットの可視化
    fitted_prices = np.exp(best_fit['fitted_values'])
    ax1.plot(data.index, fitted_prices, 'r-', linewidth=2, label=f'LPPLフィット (R²={best_fit["r_squared"]:.3f})')
    
    # 予測期間の表示
    if tc_analysis and event_comparison:
        predicted_date = tc_analysis['mean_predicted_date']
        ax1.axvline(predicted_date, color='orange', linestyle=':', linewidth=2, 
                   label=f'予測臨界日: {predicted_date.date()}')
        
        # 主要イベントの表示
        for event_name, event_date in event_comparison['major_events'].items():
            if event_date <= datetime(2022, 12, 31):  # 表示範囲内のみ
                ax1.axvline(event_date, color='red', linestyle='--', alpha=0.6)
                ax1.text(event_date, ax1.get_ylim()[1]*0.9, event_name, 
                        rotation=90, fontsize=8, ha='right')
    
    ax1.set_ylabel('NASDAQ Composite')
    ax1.set_title('2016-2019年期間のLPPLフィッティング詳細分析', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. tc値の分布
    if tc_analysis:
        tc_values = tc_analysis['values']
        ax2.hist(tc_values, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.axvline(tc_analysis['mean'], color='red', linestyle='--', 
                   label=f'平均: {tc_analysis["mean"]:.3f}')
        ax2.axvline(tc_analysis['median'], color='orange', linestyle='--', 
                   label=f'中央値: {tc_analysis["median"]:.3f}')
        ax2.set_xlabel('tc値')
        ax2.set_ylabel('頻度')
        ax2.set_title('tc値の分布')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # 3. R²スコアの分布
    r2_scores = [fit['r_squared'] for fit in fitting_results]
    ax3.hist(r2_scores, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
    ax3.axvline(np.mean(r2_scores), color='red', linestyle='--', 
               label=f'平均: {np.mean(r2_scores):.3f}')
    ax3.axvline(max(r2_scores), color='orange', linestyle='--', 
               label=f'最大: {max(r2_scores):.3f}')
    ax3.set_xlabel('R²スコア')
    ax3.set_ylabel('頻度')
    ax3.set_title('フィッティング品質分布')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 結果サマリー
    ax4.axis('off')
    
    summary_text = f"""
2016-2019年詳細分析結果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
データ期間: {data.index[0].date()} - {data.index[-1].date()}
データ点数: {len(data)}日

フィッティング結果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
成功数: {len(fitting_results)}
最良R²: {max(r2_scores):.4f}
平均R²: {np.mean(r2_scores):.4f}

tc値分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
平均tc: {tc_analysis['mean']:.4f}
標準偏差: {tc_analysis['std']:.4f}
予測日: {tc_analysis['mean_predicted_date'].date()}

最近接イベント
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{event_comparison['closest_event'][0]}
日付: {event_comparison['closest_event'][1]['event_date'].date()}
差: {event_comparison['closest_event'][1]['days_difference']}日
"""
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
            verticalalignment='top', 
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存
    os.makedirs('plots/detailed_analysis', exist_ok=True)
    save_path = 'plots/detailed_analysis/2016_2019_detailed_analysis.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"📊 詳細分析結果保存: {save_path}")
    plt.show()

def main():
    """メイン実行関数"""
    result = analyze_2016_2019_detailed()
    
    if result:
        print(f"\n🎯 2016-2019年詳細分析完了")
        print(f"   解釈: {result['interpretation']['interpretation']}")
        print(f"   信頼度: {result['interpretation']['confidence']:.2f}")
        
        if result['tc_analysis']:
            print(f"   平均tc: {result['tc_analysis']['mean']:.4f}")
            print(f"   予測日: {result['tc_analysis']['mean_predicted_date'].date()}")
        
        return result
    else:
        print("❌ 分析失敗")
        return None

if __name__ == "__main__":
    main()