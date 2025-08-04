#!/usr/bin/env python3
"""
2000年ドットコムバブル崩壊の検証

目的: 2000年3月のNASDAQ技術株バブル崩壊をLPPLモデルで検証
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from .base_crash_validator import BaseCrashValidator

class DotcomBubble2000Validator(BaseCrashValidator):
    """2000年ドットコムバブル専用バリデーター"""
    
    def __init__(self):
        super().__init__(
            crash_name="2000年ドットコムバブル崩壊",
            crash_date="2000-03-10",  # NASDAQピーク日
            data_series="NASDAQCOM"
        )
        
        # ドットコムバブル特有の設定
        self.bubble_start_year = 1995  # インターネット商業化開始
        self.expected_bubble_magnitude = 400  # 約4倍の上昇を期待
    
    def get_data_period(self):
        """データ取得期間（1995-2002年）"""
        return "1995-01-01", "2002-12-31"
    
    
    def get_expected_parameters(self):
        """期待されるLPPLパラメータ"""
        return {
            'beta': 0.33,  # 理論値
            'omega': 6.0,  # ドットコムバブル期の振動
            'description': 'インターネット技術株投機バブル'
        }
    
    def analyze_dotcom_specific_patterns(self):
        """ドットコム特有のパターン分析"""
        if self.pre_crash_data is None:
            return None
        
        print(f"\n=== ドットコムバブル特有パターン分析 ===\n")
        
        # 年次分析
        yearly_analysis = {}
        for year in range(1995, 2001):
            year_data = self.pre_crash_data[self.pre_crash_data.index.year == year]
            if len(year_data) > 0:
                start_price = year_data['Close'].iloc[0]
                end_price = year_data['Close'].iloc[-1]
                annual_return = ((end_price / start_price) - 1) * 100
                yearly_analysis[year] = {
                    'start': start_price,
                    'end': end_price,
                    'return': annual_return
                }
                print(f"📈 {year}年: {start_price:.1f} → {end_price:.1f} ({annual_return:+.1f}%)")
        
        # バブル加速期の特定（1999-2000年）
        bubble_peak_period = self.pre_crash_data[
            (self.pre_crash_data.index.year >= 1999) & 
            (self.pre_crash_data.index.year <= 2000)
        ]
        
        if len(bubble_peak_period) > 0:
            peak_start = bubble_peak_period['Close'].iloc[0]
            peak_end = bubble_peak_period['Close'].iloc[-1]
            peak_max = bubble_peak_period['Close'].max()
            
            acceleration_gain = ((peak_max / peak_start) - 1) * 100
            
            print(f"\n🚀 バブル加速期分析 (1999-2000年):")
            print(f"   加速期開始: {peak_start:.1f}")
            print(f"   加速期ピーク: {peak_max:.1f}")
            print(f"   加速期上昇率: {acceleration_gain:+.1f}%")
            
            # ドットコム特有の指標
            if acceleration_gain > 200:
                print("✅ 典型的なドットコムバブル加速パターンを確認")
            else:
                print("⚠️ ドットコムバブル加速パターンが弱い")
        
        # 技術株特有の急激な変動パターン
        volatility = self.pre_crash_data['Close'].pct_change().std() * (252**0.5) * 100
        print(f"\n📊 年次ボラティリティ: {volatility:.1f}%")
        
        if volatility > 40:
            print("✅ 技術株特有の高ボラティリティを確認")
        else:
            print("⚠️ 期待される高ボラティリティが見られない")
        
        return {
            'yearly_analysis': yearly_analysis,
            'bubble_acceleration': acceleration_gain if 'acceleration_gain' in locals() else 0,
            'annual_volatility': volatility
        }
    
    def run_dotcom_validation(self):
        """ドットコムバブル専用の完全検証"""
        print("🎯 2000年ドットコムバブル崩壊 完全検証開始\n")
        
        # 基本検証の実行
        base_results = self.run_validation(save_plots=True)
        
        if base_results is None:
            return None
        
        # ドットコム特有分析の追加
        dotcom_patterns = self.analyze_dotcom_specific_patterns()
        
        # 総合評価の調整
        adjusted_score = base_results['prediction_score']
        
        # ドットコム特有の評価基準
        if dotcom_patterns:
            bubble_acceleration = dotcom_patterns.get('bubble_acceleration', 0)
            annual_volatility = dotcom_patterns.get('annual_volatility', 0)
            
            # 加速度ボーナス
            if bubble_acceleration > 300:
                adjusted_score += 10
                print(f"🎯 ドットコム加速ボーナス: +10点 (加速度{bubble_acceleration:.1f}%)")
            
            # 高ボラティリティ確認
            if annual_volatility > 50:
                adjusted_score += 5
                print(f"📊 高ボラティリティ確認: +5点 (年次{annual_volatility:.1f}%)")
            
            adjusted_score = min(adjusted_score, 100)  # 上限100点
        
        # 結果の更新
        base_results['dotcom_specific_analysis'] = dotcom_patterns
        base_results['adjusted_prediction_score'] = adjusted_score
        base_results['validation_type'] = 'dotcom_bubble_2000'
        
        print(f"\n🏆 ドットコムバブル検証最終結果:")
        print(f"   基本予測スコア: {base_results['prediction_score']}/100")
        print(f"   調整後スコア: {adjusted_score}/100")
        
        if adjusted_score >= 80:
            print("✅ 優秀: ドットコムバブルでのLPPL予測が高精度で可能")
            print("✅ 科学的価値: 技術株バブルの理論的説明を確認")
        elif adjusted_score >= 60:
            print("⚠️ 良好: ドットコムバブルでのLPPL予測が概ね有効")
            print("🔬 研究価値: 技術株特有パターンの分析価値あり")
        else:
            print("🔶 要改善: 技術株バブルでの予測手法改良が必要")
        
        return base_results

def run_dotcom_bubble_test():
    """2000年ドットコムバブル検証のメイン実行関数"""
    validator = DotcomBubble2000Validator()
    return validator.run_dotcom_validation()

def main():
    """メイン実行関数（エントリーポイント互換）"""
    return run_dotcom_bubble_test()

if __name__ == "__main__":
    run_dotcom_bubble_test()