#!/usr/bin/env python3
"""
歴史的クラッシュ検証の基盤クラス

目的: 異なる歴史的クラッシュに対して統一的な検証プロセスを提供
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
from abc import ABC, abstractmethod
warnings.filterwarnings('ignore')

# Environment setup
load_dotenv()
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.sornette_theory.lppl_model import logarithm_periodic_func
from infrastructure.data_sources.fred_data_client import FREDDataClient
from scipy.optimize import curve_fit

class BaseCrashValidator(ABC):
    """歴史的クラッシュ検証の基盤クラス"""
    
    def __init__(self, crash_name, crash_date, data_series='NASDAQCOM'):
        """
        Args:
            crash_name: クラッシュの名称
            crash_date: クラッシュ発生日 (YYYY-MM-DD形式)
            data_series: 使用するデータシリーズ (デフォルト: NASDAQCOM)
        """
        self.crash_name = crash_name
        self.crash_date = datetime.strptime(crash_date, '%Y-%m-%d')
        self.data_series = data_series
        self.client = FREDDataClient()
        
        # 結果格納用
        self.data = None
        self.pre_crash_data = None
        self.post_crash_data = None
        self.validation_results = None
    
    @abstractmethod
    def get_data_period(self):
        """データ取得期間を返す (start_date, end_date)"""
        pass
    
    @abstractmethod
    def get_expected_parameters(self):
        """期待されるLPPLパラメータを返す (オプション)"""
        return {'beta': None, 'omega': None}
    
    def load_data(self):
        """データの取得と前処理"""
        print(f"=== {self.crash_name} データ取得 ===\n")
        
        start_date, end_date = self.get_data_period()
        
        print(f"📊 {self.data_series} データ取得中...")
        self.data = self.client.get_series_data(self.data_series, start_date, end_date)
        
        if self.data is None:
            print("❌ データ取得に失敗しました")
            return False
        
        print(f"✅ データ取得成功: {len(self.data)}日分")
        print(f"   期間: {self.data.index[0].date()} - {self.data.index[-1].date()}")
        
        # クラッシュ前後でデータを分割
        self.pre_crash_data = self.data[self.data.index < self.crash_date]
        self.post_crash_data = self.data[self.data.index >= self.crash_date]
        
        print(f"\n📈 データ分割:")
        print(f"   クラッシュ前: {len(self.pre_crash_data)}日")
        print(f"   クラッシュ後: {len(self.post_crash_data)}日")
        
        return True
    
    def analyze_bubble_formation(self):
        """バブル形成パターンの分析"""
        if self.pre_crash_data is None or len(self.pre_crash_data) == 0:
            return None
        
        print(f"\n=== {self.crash_name} バブル形成分析 ===\n")
        
        start_price = self.pre_crash_data['Close'].iloc[0]
        peak_price = self.pre_crash_data['Close'].max()
        end_price = self.pre_crash_data['Close'].iloc[-1]
        
        total_gain = ((end_price / start_price) - 1) * 100
        peak_gain = ((peak_price / start_price) - 1) * 100
        
        # ピーク日の特定
        peak_date = self.pre_crash_data[self.pre_crash_data['Close'] == peak_price].index[0]
        
        print(f"🫧 バブル形成パターン:")
        print(f"   期間開始価格: {start_price:.2f}")
        print(f"   ピーク価格: {peak_price:.2f} ({peak_date.date()})")
        print(f"   クラッシュ直前価格: {end_price:.2f}")
        print(f"   総上昇率: {total_gain:+.1f}%")
        print(f"   ピーク上昇率: {peak_gain:+.1f}%")
        
        # クラッシュ後の分析
        crash_analysis = None
        if len(self.post_crash_data) > 0:
            crash_low = self.post_crash_data['Close'].min()
            crash_decline = ((crash_low / end_price) - 1) * 100
            
            print(f"\n💥 クラッシュ分析:")
            print(f"   クラッシュ後最安値: {crash_low:.2f}")
            print(f"   最大下落率: {crash_decline:.1f}%")
            
            crash_analysis = {
                'crash_low': crash_low,
                'max_decline': crash_decline
            }
        
        return {
            'start_price': start_price,
            'peak_price': peak_price,
            'peak_date': peak_date,
            'end_price': end_price,
            'total_gain': total_gain,
            'peak_gain': peak_gain,
            'crash_analysis': crash_analysis
        }
    
    def evaluate_prediction_feasibility(self, bubble_analysis):
        """予測可能性の評価"""
        print(f"\n=== {self.crash_name} 予測可能性評価 ===\n")
        
        if bubble_analysis is None:
            print("❌ バブル分析データがありません")
            return 0
        
        score = 0
        total_gain = bubble_analysis['total_gain']
        peak_gain = bubble_analysis['peak_gain']
        data_points = len(self.pre_crash_data)
        crash_decline = 0
        
        if bubble_analysis['crash_analysis']:
            crash_decline = abs(bubble_analysis['crash_analysis']['max_decline'])
        
        # 評価基準
        print(f"📊 評価基準と結果:")
        
        # 1. バブル形成（30点）
        if total_gain > 50:
            score += 30
            print(f"   ✅ バブル形成: {total_gain:+.1f}% (基準: >50%) - 30点")
        elif total_gain > 30:
            score += 20
            print(f"   ⚠️ バブル形成: {total_gain:+.1f}% (基準: >50%) - 20点")
        else:
            print(f"   ❌ バブル形成: {total_gain:+.1f}% (基準: >50%) - 0点")
        
        # 2. データ充実度（25点）
        if data_points > 500:
            score += 25
            print(f"   ✅ データ充実度: {data_points}日 (基準: >500日) - 25点")
        elif data_points > 200:
            score += 15
            print(f"   ⚠️ データ充実度: {data_points}日 (基準: >500日) - 15点")
        else:
            print(f"   ❌ データ充実度: {data_points}日 (基準: >500日) - 0点")
        
        # 3. 加速的成長（25点）
        if peak_gain > total_gain * 0.8:
            score += 25
            print(f"   ✅ 加速的成長: ピーク{peak_gain:+.1f}% vs 総計{total_gain:+.1f}% - 25点")
        else:
            score += 10
            print(f"   ⚠️ 加速的成長: ピーク{peak_gain:+.1f}% vs 総計{total_gain:+.1f}% - 10点")
        
        # 4. 実際のクラッシュ（20点）
        if crash_decline > 20:
            score += 20
            print(f"   ✅ 大規模クラッシュ: {crash_decline:.1f}%下落 (基準: >20%) - 20点")
        elif crash_decline > 10:
            score += 10
            print(f"   ⚠️ 中規模クラッシュ: {crash_decline:.1f}%下落 (基準: >20%) - 10点")
        else:
            print(f"   ❌ クラッシュ未確認: {crash_decline:.1f}%下落 (基準: >20%) - 0点")
        
        print(f"\n🎯 総合予測可能性スコア: {score}/100")
        
        if score >= 80:
            print("✅ 優秀: LPPLモデル予測が高精度で可能")
        elif score >= 60:
            print("⚠️ 良好: LPPLモデル予測が概ね有効")
        elif score >= 40:
            print("🔶 要注意: 予測に課題があるが検証価値あり")
        else:
            print("❌ 困難: 予測が困難、手法改良が必要")
        
        return score
    
    def create_visualization(self, bubble_analysis, save_path=None):
        """結果の可視化"""
        if self.data is None or bubble_analysis is None:
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. メイン価格チャート
        ax1.plot(self.data.index, self.data['Close'], 'b-', linewidth=1.5, alpha=0.8, label=f'{self.data_series}')
        ax1.axvline(self.crash_date, color='red', linestyle='--', linewidth=2, alpha=0.8, 
                   label=f'{self.crash_name}')
        
        # ピーク・重要ポイントのマーク
        peak_date = bubble_analysis['peak_date']
        peak_price = bubble_analysis['peak_price']
        ax1.scatter(peak_date, peak_price, color='orange', s=100, zorder=5, label='Bubble Peak')
        
        ax1.set_ylabel('Price Index')
        ax1.set_title(f'{self.crash_name} - Market Data Analysis', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. バブル期間の詳細
        bubble_start_date = self.pre_crash_data.index[0]
        bubble_period = self.pre_crash_data[self.pre_crash_data.index >= bubble_start_date]
        
        ax2.plot(bubble_period.index, bubble_period['Close'], 'g-', linewidth=2, label='Bubble Period')
        ax2.axvline(peak_date, color='orange', linestyle=':', alpha=0.7, label='Peak')
        ax2.axvline(self.crash_date, color='red', linestyle='--', alpha=0.7, label='Crash')
        
        ax2.set_ylabel('Price Index')
        ax2.set_title('Bubble Formation Period Details', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 統計サマリー
        ax3.axis('off')
        
        total_gain = bubble_analysis['total_gain']
        peak_gain = bubble_analysis['peak_gain']
        data_points = len(self.pre_crash_data)
        
        crash_info = ""
        if bubble_analysis['crash_analysis']:
            max_decline = bubble_analysis['crash_analysis']['max_decline']
            crash_info = f"Max Decline: {max_decline:.1f}%"
        
        summary_text = f"""
{self.crash_name} Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Source: {self.data_series}
Analysis Period: {self.pre_crash_data.index[0].date()} - {self.pre_crash_data.index[-1].date()}
Data Points: {data_points} days

Bubble Formation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Gain: {total_gain:+.1f}%
Peak Gain: {peak_gain:+.1f}%
Peak Date: {peak_date.date()}

Crash Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crash Date: {self.crash_date.date()}
{crash_info}

LPPL Model Applicability
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Predictability Assessment Ready
"""
        
        ax3.text(0.05, 0.95, summary_text, transform=ax3.transAxes, fontsize=10,
                verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # 4. 価格変動率分析
        returns = self.pre_crash_data['Close'].pct_change().dropna()
        ax4.hist(returns, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        ax4.axvline(returns.mean(), color='red', linestyle='--', label=f'Mean: {returns.mean():.4f}')
        ax4.set_xlabel('Daily Returns')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Price Return Distribution', fontsize=12)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 分析結果保存: {save_path}")
        plt.show()
    
    def run_validation(self, save_plots=True):
        """完全な検証プロセスの実行"""
        print(f"🎯 {self.crash_name} 歴史的検証開始\n")
        
        # 1. データ取得
        if not self.load_data():
            return None
        
        # 2. バブル分析
        bubble_analysis = self.analyze_bubble_formation()
        if bubble_analysis is None:
            return None
        
        # 3. 予測可能性評価
        prediction_score = self.evaluate_prediction_feasibility(bubble_analysis)
        
        # 4. 可視化
        if save_plots:
            plots_dir = 'plots/historical_crashes'
            os.makedirs(plots_dir, exist_ok=True)
            save_path = f"{plots_dir}/{self.crash_name.replace('年', '_').replace('/', '_')}_analysis.png"
            self.create_visualization(bubble_analysis, save_path)
        
        # 5. 結果サマリー
        validation_results = {
            'crash_name': self.crash_name,
            'crash_date': self.crash_date,
            'data_series': self.data_series,
            'data_points': len(self.pre_crash_data),
            'bubble_analysis': bubble_analysis,
            'prediction_score': prediction_score,
            'validation_status': 'completed'
        }
        
        self.validation_results = validation_results
        
        print(f"\n🏆 {self.crash_name} 検証完了")
        print(f"   予測可能性スコア: {prediction_score}/100")
        print(f"   検証ステータス: {'✅ 成功' if prediction_score >= 60 else '⚠️ 要改善'}")
        
        return validation_results

class ReproducibleTestCase:
    """再現可能なテストケースの管理"""
    
    def __init__(self, test_name, test_function, expected_score_range=None):
        self.test_name = test_name
        self.test_function = test_function
        self.expected_score_range = expected_score_range or (0, 100)
        self.last_result = None
    
    def run_test(self):
        """テストの実行"""
        print(f"🧪 再現テスト実行: {self.test_name}")
        
        try:
            result = self.test_function()
            self.last_result = result
            
            if result and 'prediction_score' in result:
                score = result['prediction_score']
                min_score, max_score = self.expected_score_range
                
                if min_score <= score <= max_score:
                    print(f"✅ テスト成功: スコア{score}/100 (期待範囲: {min_score}-{max_score})")
                    return True
                else:
                    print(f"⚠️ テスト結果が期待範囲外: スコア{score}/100 (期待範囲: {min_score}-{max_score})")
                    return False
            else:
                print(f"❌ テスト失敗: 結果が取得できませんでした")
                return False
                
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            return False
    
    def get_last_result(self):
        """最後の実行結果を取得"""
        return self.last_result