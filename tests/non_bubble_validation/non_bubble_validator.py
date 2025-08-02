#!/usr/bin/env python3
"""
非バブル期間でのフィッティング失敗例検証

目的: LPPLモデルが正常な市場期間で適切に失敗することを確認し、
     バブル検出の選択性（specificity）を実証する
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import json
warnings.filterwarnings('ignore')

# Environment setup
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.fitting.utils import logarithm_periodic_func
from src.data_sources.fred_data_client import FREDDataClient
from src.parameter_management import AdaptiveParameterManager, MarketCharacteristics, BubbleType, FittingStrategy
from scipy.optimize import curve_fit

class NonBubblePeriodValidator:
    """非バブル期間の検証クラス"""
    
    def __init__(self):
        self.client = FREDDataClient()
        self.param_manager = AdaptiveParameterManager()
        self.validation_results = []
        
        # 非バブル期間の定義
        self.non_bubble_periods = {
            'post_dotcom_recovery': {
                'name': '2003-2006年ドットコム回復期',
                'start_date': '2003-01-01',
                'end_date': '2006-12-31',
                'description': 'ドットコムバブル崩壊後の安定回復期',
                'expected_pattern': 'stable_growth',
                'data_series': 'NASDAQCOM'
            },
            'pre_financial_crisis': {
                'name': '2005-2007年金融危機前期',
                'start_date': '2005-01-01', 
                'end_date': '2007-12-31',
                'description': '金融危機前の住宅バブル形成期（ただし株式市場では比較的安定）',
                'expected_pattern': 'moderate_growth',
                'data_series': 'NASDAQCOM'
            },
            'post_financial_recovery': {
                'name': '2010-2012年金融危機回復期',
                'start_date': '2010-01-01',
                'end_date': '2012-12-31', 
                'description': '金融危機後の段階的回復期',
                'expected_pattern': 'gradual_recovery',
                'data_series': 'NASDAQCOM'
            },
            'steady_bull_market': {
                'name': '2016-2019年安定上昇期',
                'start_date': '2016-01-01',
                'end_date': '2019-12-31',
                'description': 'コロナ前の安定した強気相場',
                'expected_pattern': 'steady_bull',
                'data_series': 'NASDAQCOM'
            },
            'covid_recovery': {
                'name': '2021-2022年コロナ回復期',
                'start_date': '2021-03-01',
                'end_date': '2022-12-31',
                'description': 'コロナ後の回復期（一部バブル的要素含む可能性）',
                'expected_pattern': 'volatile_recovery',
                'data_series': 'NASDAQCOM'
            }
        }
    
    def load_non_bubble_data(self, period_key: str) -> Optional[pd.DataFrame]:
        """非バブル期間データの取得"""
        
        if period_key not in self.non_bubble_periods:
            print(f"❌ 未知の期間キー: {period_key}")
            return None
        
        period_info = self.non_bubble_periods[period_key]
        
        print(f"📊 {period_info['name']} データ取得中...")
        print(f"   期間: {period_info['start_date']} - {period_info['end_date']}")
        print(f"   特徴: {period_info['description']}")
        
        data = self.client.get_series_data(
            period_info['data_series'],
            period_info['start_date'],
            period_info['end_date']
        )
        
        if data is None:
            print("❌ データ取得失敗")
            return None
        
        print(f"✅ データ取得成功: {len(data)}日分")
        return data
    
    def analyze_period_characteristics(self, data: pd.DataFrame, period_key: str) -> Dict:
        """期間特性の分析"""
        
        period_info = self.non_bubble_periods[period_key]
        
        # 基本統計
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        max_price = data['Close'].max()
        min_price = data['Close'].min()
        
        total_return = ((end_price / start_price) - 1) * 100
        max_gain = ((max_price / start_price) - 1) * 100
        max_drawdown = ((min_price / max_price) - 1) * 100
        
        # ボラティリティ分析
        returns = data['Close'].pct_change().dropna()
        daily_volatility = returns.std()
        annual_volatility = daily_volatility * np.sqrt(252) * 100
        
        # トレンド分析
        days = len(data)
        time_series = np.arange(days)
        log_prices = np.log(data['Close'].values)
        
        # 線形トレンド
        trend_coef = np.polyfit(time_series, log_prices, 1)[0]
        annual_trend = trend_coef * 252 * 100  # 年率化
        
        # R²（線形トレンドへの適合度）
        linear_fit = np.poly1d(np.polyfit(time_series, log_prices, 1))(time_series)
        linear_r2 = 1 - np.sum((log_prices - linear_fit)**2) / np.sum((log_prices - np.mean(log_prices))**2)
        
        characteristics = {
            'period_name': period_info['name'],
            'data_points': days,
            'total_return': total_return,
            'max_gain': max_gain,
            'max_drawdown': max_drawdown,
            'annual_volatility': annual_volatility,
            'annual_trend': annual_trend,
            'linear_r2': linear_r2,
            'price_range': {
                'start': start_price,
                'end': end_price,
                'max': max_price,
                'min': min_price
            }
        }
        
        print(f"\n📈 {period_info['name']} 特性分析:")
        print(f"   総リターン: {total_return:+.1f}%")
        print(f"   最大上昇: {max_gain:+.1f}%")
        print(f"   最大下落: {max_drawdown:.1f}%")
        print(f"   年率ボラティリティ: {annual_volatility:.1f}%")
        print(f"   線形トレンド適合度: R²={linear_r2:.3f}")
        
        return characteristics
    
    def attempt_lppl_fitting(self, data: pd.DataFrame, period_key: str) -> Dict:
        """LPPLフィッティングの試行（失敗を期待）"""
        
        print(f"\n🧪 LPPLフィッティング試行: {self.non_bubble_periods[period_key]['name']}")
        
        # 市場特性の設定（非バブル期間として）
        market_chars = MarketCharacteristics(
            data_period_days=len(data),
            volatility=data['Close'].pct_change().std() * np.sqrt(252),
            bubble_magnitude=((data['Close'].max() / data['Close'].iloc[0]) - 1) * 100,
            bubble_type=BubbleType.UNKNOWN,  # 非バブル期間
            data_quality_score=1.0
        )
        
        # フィッティング結果格納
        fitting_results = {
            'period_key': period_key,
            'strategies_attempted': [],
            'best_result': None,
            'all_attempts': [],
            'failure_analysis': {}
        }
        
        # 段階的フィッティング試行
        strategies = [FittingStrategy.CONSERVATIVE, FittingStrategy.EXTENSIVE, FittingStrategy.EMERGENCY]
        
        for strategy in strategies:
            print(f"\n📊 {strategy.value} 戦略でフィッティング試行...")
            
            try:
                # パラメータセット取得
                param_set = self.param_manager.get_parameters_for_market(market_chars, strategy)
                
                # 初期値生成
                initial_values = self.param_manager.generate_initial_values(param_set, data['Close'].values)
                
                # 境界取得
                lower_bounds, upper_bounds = self.param_manager.get_fitting_bounds(param_set)
                
                # フィッティング実行
                strategy_result = self._execute_fitting_attempts(
                    data['Close'].values, initial_values, lower_bounds, upper_bounds, strategy
                )
                
                fitting_results['strategies_attempted'].append(strategy)
                fitting_results['all_attempts'].append(strategy_result)
                
                # 最良結果の更新
                if (fitting_results['best_result'] is None or 
                    (strategy_result['best_r2'] > fitting_results['best_result']['best_r2'])):
                    fitting_results['best_result'] = strategy_result
                
                print(f"   戦略結果: 成功率={strategy_result['success_rate']:.1%}, 最良R²={strategy_result['best_r2']:.3f}")
                
                # 十分良い結果が得られた場合は早期終了
                if strategy_result['best_r2'] > 0.8:
                    print("⚠️ 予期しない高品質フィット検出 - バブル的特性の可能性")
                    break
                    
            except Exception as e:
                print(f"   ❌ 戦略 {strategy.value} でエラー: {str(e)}")
                continue
        
        # 失敗分析
        fitting_results['failure_analysis'] = self._analyze_fitting_failures(fitting_results)
        
        return fitting_results
    
    def _execute_fitting_attempts(self, prices: np.ndarray, initial_values: List[Dict], 
                                lower_bounds: List[float], upper_bounds: List[float], 
                                strategy: FittingStrategy) -> Dict:
        """フィッティング試行の実行"""
        
        log_prices = np.log(prices)
        t = np.linspace(0, 1, len(prices))
        
        successful_fits = []
        failed_attempts = 0
        
        print(f"   {len(initial_values)}回の試行を実行中...")
        
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
                    maxfev=5000,  # 非バブル期間では収束が困難なため試行回数制限
                    ftol=1e-6,
                    xtol=1e-6
                )
                
                # 評価
                y_pred = logarithm_periodic_func(t, *popt)
                r_squared = 1 - (np.sum((log_prices - y_pred)**2) / 
                               np.sum((log_prices - np.mean(log_prices))**2))
                rmse = np.sqrt(np.mean((log_prices - y_pred)**2))
                
                # パラメータ妥当性チェック
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
                        'converged': True
                    })
                else:
                    failed_attempts += 1
                    
            except Exception as e:
                failed_attempts += 1
                continue
        
        # 結果サマリー
        success_rate = len(successful_fits) / len(initial_values)
        best_r2 = max([fit['r_squared'] for fit in successful_fits]) if successful_fits else 0.0
        avg_r2 = np.mean([fit['r_squared'] for fit in successful_fits]) if successful_fits else 0.0
        
        return {
            'strategy': strategy,
            'total_attempts': len(initial_values),
            'successful_fits': len(successful_fits),
            'failed_attempts': failed_attempts,
            'success_rate': success_rate,
            'best_r2': best_r2,
            'average_r2': avg_r2,
            'fit_details': successful_fits[:5]  # 上位5件のみ保存
        }
    
    def _analyze_fitting_failures(self, fitting_results: Dict) -> Dict:
        """フィッティング失敗の分析"""
        
        best_result = fitting_results['best_result']
        
        failure_analysis = {
            'overall_assessment': 'unknown',
            'failure_indicators': [],
            'bubble_likelihood': 0.0,
            'specificity_confirmed': False
        }
        
        if best_result is None:
            failure_analysis['overall_assessment'] = 'complete_failure'
            failure_analysis['failure_indicators'].append('NO_CONVERGENCE')
            failure_analysis['specificity_confirmed'] = True
            return failure_analysis
        
        # R²基準での評価
        best_r2 = best_result['best_r2']
        if best_r2 < 0.3:
            failure_analysis['failure_indicators'].append('POOR_FIT_QUALITY')
        if best_r2 < 0.5:
            failure_analysis['failure_indicators'].append('INSUFFICIENT_EXPLANATION')
        
        # 成功率での評価
        success_rate = best_result['success_rate']
        if success_rate < 0.1:
            failure_analysis['failure_indicators'].append('LOW_CONVERGENCE_RATE')
        if success_rate < 0.3:
            failure_analysis['failure_indicators'].append('UNSTABLE_FITTING')
        
        # 総合評価
        if best_r2 < 0.4 and success_rate < 0.2:
            failure_analysis['overall_assessment'] = 'appropriate_failure'
            failure_analysis['specificity_confirmed'] = True
        elif best_r2 < 0.6 and success_rate < 0.5:
            failure_analysis['overall_assessment'] = 'marginal_failure'
            failure_analysis['specificity_confirmed'] = True
        elif best_r2 > 0.8 and success_rate > 0.7:
            failure_analysis['overall_assessment'] = 'unexpected_success'
            failure_analysis['bubble_likelihood'] = min(1.0, best_r2 * success_rate)
            failure_analysis['specificity_confirmed'] = False
        else:
            failure_analysis['overall_assessment'] = 'mixed_results'
            failure_analysis['bubble_likelihood'] = (best_r2 * success_rate) * 0.7
        
        return failure_analysis
    
    def create_comparison_visualization(self, period_results: List[Dict], save_path: str = None):
        """複数期間の比較可視化"""
        
        if not period_results:
            print("❌ 可視化データがありません")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # データの準備
        period_names = [r['characteristics']['period_name'] for r in period_results]
        r2_scores = [r['fitting_results']['best_result']['best_r2'] if r['fitting_results']['best_result'] else 0 
                    for r in period_results]
        success_rates = [r['fitting_results']['best_result']['success_rate'] if r['fitting_results']['best_result'] else 0 
                        for r in period_results]
        bubble_magnitudes = [r['characteristics']['max_gain'] for r in period_results]
        volatilities = [r['characteristics']['annual_volatility'] for r in period_results]
        
        # 1. R²スコア比較
        colors = ['red' if r2 > 0.8 else 'orange' if r2 > 0.5 else 'green' for r2 in r2_scores]
        bars1 = ax1.bar(range(len(period_names)), r2_scores, color=colors, alpha=0.7)
        ax1.axhline(y=0.8, color='red', linestyle='--', alpha=0.5, label='バブル閾値 (0.8)')
        ax1.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5, label='警戒閾値 (0.5)')
        ax1.set_ylabel('最良R²スコア')
        ax1.set_title('LPPLフィッティング品質 (低い方が望ましい)')
        ax1.set_xticks(range(len(period_names)))
        ax1.set_xticklabels([name.replace('年', '\n') for name in period_names], rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # バーに値を表示
        for bar, score in zip(bars1, r2_scores):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{score:.3f}', ha='center', va='bottom', fontsize=9)
        
        # 2. 成功率比較
        colors2 = ['red' if sr > 0.7 else 'orange' if sr > 0.3 else 'green' for sr in success_rates]
        bars2 = ax2.bar(range(len(period_names)), success_rates, color=colors2, alpha=0.7)
        ax2.axhline(y=0.7, color='red', linestyle='--', alpha=0.5, label='バブル閾値 (70%)')
        ax2.axhline(y=0.3, color='orange', linestyle='--', alpha=0.5, label='警戒閾値 (30%)')
        ax2.set_ylabel('フィッティング成功率')
        ax2.set_title('収束成功率 (低い方が望ましい)')
        ax2.set_xticks(range(len(period_names)))
        ax2.set_xticklabels([name.replace('年', '\n') for name in period_names], rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # バーに値を表示
        for bar, rate in zip(bars2, success_rates):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{rate:.1%}', ha='center', va='bottom', fontsize=9)
        
        # 3. バブル規模 vs R²の散布図
        scatter_colors = ['red' if r2 > 0.8 else 'orange' if r2 > 0.5 else 'green' for r2 in r2_scores]
        ax3.scatter(bubble_magnitudes, r2_scores, c=scatter_colors, s=100, alpha=0.7)
        for i, name in enumerate(period_names):
            ax3.annotate(name.split('年')[0], (bubble_magnitudes[i], r2_scores[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        ax3.axhline(y=0.8, color='red', linestyle='--', alpha=0.5)
        ax3.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5)
        ax3.set_xlabel('最大上昇率 (%)')
        ax3.set_ylabel('最良R²スコア')
        ax3.set_title('バブル規模 vs フィッティング品質')
        ax3.grid(True, alpha=0.3)
        
        # 4. 総合判定サマリー
        ax4.axis('off')
        
        # 判定結果の集計
        appropriate_failures = sum(1 for r in period_results 
                                 if r['fitting_results']['failure_analysis']['overall_assessment'] == 'appropriate_failure')
        unexpected_successes = sum(1 for r in period_results 
                                 if r['fitting_results']['failure_analysis']['overall_assessment'] == 'unexpected_success')
        mixed_results = len(period_results) - appropriate_failures - unexpected_successes
        
        summary_text = f"""
非バブル期間検証結果サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
検証期間数: {len(period_results)}

判定結果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 適切な失敗: {appropriate_failures}期間
⚠️ 予期しない成功: {unexpected_successes}期間  
🔶 混合結果: {mixed_results}期間

LPPLモデル選択性
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
選択性スコア: {appropriate_failures/len(period_results)*100:.1f}%
(非バブル期間での適切な失敗率)

品質基準
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
R² < 0.5: 適切な失敗
0.5 ≤ R² < 0.8: 注意が必要
R² ≥ 0.8: バブル的特性の可能性

結論
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'✅ LPPLモデルは非バブル期間を適切に識別' if appropriate_failures >= len(period_results)*0.7
 else '⚠️ 一部期間でバブル的特性を検出 - 要詳細分析'}
"""
        
        ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11,
                verticalalignment='top', 
                bbox=dict(boxstyle='round', 
                         facecolor='lightgreen' if appropriate_failures >= len(period_results)*0.7 else 'lightyellow', 
                         alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 比較結果保存: {save_path}")
        plt.show()
    
    def run_comprehensive_validation(self, periods: List[str] = None) -> List[Dict]:
        """包括的な非バブル期間検証の実行"""
        
        if periods is None:
            periods = list(self.non_bubble_periods.keys())
        
        print("🎯 非バブル期間での包括的検証開始\n")
        print(f"検証対象: {len(periods)}期間")
        
        all_results = []
        
        for period_key in periods:
            print(f"\n{'='*60}")
            print(f"🔍 検証期間: {period_key}")
            print('='*60)
            
            # データ取得
            data = self.load_non_bubble_data(period_key)
            if data is None:
                continue
            
            # 期間特性分析
            characteristics = self.analyze_period_characteristics(data, period_key)
            
            # LPPLフィッティング試行
            fitting_results = self.attempt_lppl_fitting(data, period_key)
            
            # 結果の評価
            period_result = {
                'period_key': period_key,
                'data': data,
                'characteristics': characteristics,
                'fitting_results': fitting_results
            }
            
            all_results.append(period_result)
            
            # 期間別サマリー
            failure_analysis = fitting_results['failure_analysis']
            print(f"\n🏆 {period_key} 検証結果:")
            print(f"   総合評価: {failure_analysis['overall_assessment']}")
            print(f"   選択性確認: {'✅ 成功' if failure_analysis['specificity_confirmed'] else '⚠️ 要注意'}")
            if failure_analysis['bubble_likelihood'] > 0:
                print(f"   バブル可能性: {failure_analysis['bubble_likelihood']:.1%}")
        
        # 包括的な可視化
        if all_results:
            print(f"\n📊 {len(all_results)}期間の比較可視化作成中...")
            os.makedirs('plots/non_bubble_validation', exist_ok=True)
            save_path = 'plots/non_bubble_validation/comprehensive_non_bubble_validation.png'
            self.create_comparison_visualization(all_results, save_path)
        
        # 結果のエクスポート
        self.export_validation_results(all_results)
        
        return all_results
    
    def export_validation_results(self, results: List[Dict], filepath: str = None):
        """検証結果のエクスポート"""
        
        if filepath is None:
            os.makedirs('results/non_bubble_validation', exist_ok=True)
            filepath = f'results/non_bubble_validation/validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # JSON用にデータを変換
        export_data = {
            'validation_timestamp': datetime.now().isoformat(),
            'total_periods': len(results),
            'results': []
        }
        
        for result in results:
            export_result = {
                'period_key': result['period_key'],
                'characteristics': result['characteristics'],
                'fitting_summary': {
                    'strategies_attempted': [s.value for s in result['fitting_results']['strategies_attempted']],
                    'best_r2': result['fitting_results']['best_result']['best_r2'] if result['fitting_results']['best_result'] else 0,
                    'best_success_rate': result['fitting_results']['best_result']['success_rate'] if result['fitting_results']['best_result'] else 0,
                    'failure_analysis': result['fitting_results']['failure_analysis']
                }
            }
            export_data['results'].append(export_result)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 検証結果エクスポート: {filepath}")

def run_non_bubble_validation():
    """非バブル期間検証のメイン実行関数"""
    validator = NonBubblePeriodValidator()
    
    # 全期間での検証実行
    results = validator.run_comprehensive_validation()
    
    print(f"\n🎯 非バブル期間検証完了")
    print(f"   検証期間数: {len(results)}")
    
    # 成功統計の表示
    appropriate_failures = sum(1 for r in results 
                             if r['fitting_results']['failure_analysis']['overall_assessment'] == 'appropriate_failure')
    
    print(f"   適切な失敗: {appropriate_failures}/{len(results)} ({appropriate_failures/len(results)*100:.1f}%)")
    print(f"   LPPLモデル選択性: {'✅ 良好' if appropriate_failures >= len(results)*0.7 else '⚠️ 要改善'}")
    
    return results

if __name__ == "__main__":
    run_non_bubble_validation()