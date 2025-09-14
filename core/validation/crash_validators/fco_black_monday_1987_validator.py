#!/usr/bin/env python3
"""
FCOベース 1987年ブラックマンデーの再現検証

目的: FCO (Financial Crisis Observatory) 方式で1987年検証を実施
     DS-LPPLS指標を用いた多重時間窓分析による検証
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# プロジェクトパスの設定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from core.validation.crash_validators.base_crash_validator import BaseCrashValidator
from core.fitting.fco_engine import FCOEngine
from infrastructure.data_sources.fred_data_client import FREDDataClient

class FCOBlackMonday1987Validator(BaseCrashValidator):
    """FCOベース 1987年ブラックマンデー検証器"""
    
    def __init__(self):
        super().__init__(
            crash_name="1987 Black Monday (FCO)",
            crash_date="1987-10-19",
            data_series="NASDAQCOM"
        )
        
        # FCOエンジンの初期化
        self.fco_engine = FCOEngine(use_parallel=True, max_workers=4)
        
        # 既存の検証済み結果（比較用）
        self.proven_results = {
            'total_gain': 65.2,
            'peak_gain': 85.1,
            'max_decline': 28.2,
            'prediction_score': 100,
            'data_points': 706
        }
    
    def get_data_period(self):
        """データ取得期間（実証済み期間）"""
        return "1985-01-01", "1987-11-30"
    
    def get_expected_parameters(self):
        """期待されるパラメータ（FCO分析用）"""
        return {
            'ds_lppls_threshold': 30.0,  # DS-LPPLS > 30%でバブル判定
            'critical_threshold': 50.0,  # DS-LPPLS > 50%で危機的
            'window_range': (125, 750),  # FCO標準の時間窓範囲
            'description': 'FCO多重時間窓分析による1987年検証'
        }
    
    def run_fco_analysis(self):
        """FCOベースの分析実行"""
        if self.pre_crash_data is None:
            print("❌ データが読み込まれていません")
            return None
        
        print("\n=== FCO多重時間窓分析 ===\n")
        
        # クラッシュ前データでFCO分析
        prices = self.pre_crash_data['Close'].values
        
        # タイムスタンプの準備（日数ベース）
        timestamps = np.arange(len(prices))
        
        print(f"📊 分析対象データ: {len(prices)}日分")
        print(f"   期間: {self.pre_crash_data.index[0].date()} - {self.pre_crash_data.index[-1].date()}")
        print(f"   価格範囲: {prices.min():.2f} - {prices.max():.2f}")
        
        # FCO分析実行
        print("\n🔄 126時間窓での並列分析を実行中...")
        fco_result = self.fco_engine.compute_ds_lppls_confidence(
            prices=prices,
            timestamps=timestamps
        )
        
        return fco_result
    
    def evaluate_fco_results(self, fco_result):
        """FCO結果の評価"""
        print("\n=== FCO結果評価 ===\n")
        
        # DS-LPPLS指標の取得（パーセンテージに変換）
        ds_lppls_pos = fco_result.ds_lppls_confidence * 100
        ds_lppls_neg = fco_result.ds_lppls_confidence_neg * 100
        num_windows = fco_result.metadata.get('num_windows', 126)
        successful_fits = fco_result.metadata.get('qualified_fits', len(fco_result.window_results) if fco_result.window_results else 0)
        
        print(f"📈 DS-LPPLS分析結果:")
        print(f"   分析窓数: {num_windows}")
        print(f"   成功フィット数: {successful_fits}")
        print(f"   DS-LPPLS Confidence (Positive): {ds_lppls_pos:.1f}%")
        print(f"   DS-LPPLS Confidence (Negative): {ds_lppls_neg:.1f}%")
        
        # バブルタイプの判定
        bubble_type = fco_result.bubble_type
        print(f"\n🫧 バブル判定: {bubble_type}")
        
        if bubble_type == "positive_bubble":
            print("   ✅ 正のバブル検出（価格上昇バブル）")
        elif bubble_type == "negative_bubble":
            print("   ⚠️ 負のバブル検出（価格下落バブル）")
        elif bubble_type == "weak_positive":
            print("   🔶 弱い正のバブルシグナル")
        elif bubble_type == "no_bubble":
            print("   ❌ バブル未検出")
        else:
            print("   🔶 不確定状態")
        
        # 予測クラッシュ日の分析
        if fco_result.predicted_tc is not None:
            tc_mean = fco_result.predicted_tc
            tc_std = fco_result.tc_std if fco_result.tc_std is not None else 0
            
            # 実際のクラッシュ日との比較
            actual_crash_idx = len(self.pre_crash_data)
            
            print(f"\n📅 予測クラッシュ時期分析:")
            print(f"   予測tc平均: {tc_mean:.1f}日")
            print(f"   予測tc標準偏差: {tc_std:.1f}日")
            print(f"   実際のクラッシュ: {actual_crash_idx}日後")
            
            # 予測精度の評価
            prediction_error = abs(tc_mean - actual_crash_idx)
            accuracy_percentage = max(0, 100 - (prediction_error / actual_crash_idx * 100))
            
            print(f"   予測誤差: {prediction_error:.1f}日")
            print(f"   予測精度: {accuracy_percentage:.1f}%")
            
            return {
                'ds_lppls_pos': ds_lppls_pos,
                'ds_lppls_neg': ds_lppls_neg,
                'bubble_type': bubble_type,
                'tc_mean': tc_mean,
                'tc_std': tc_std,
                'prediction_accuracy': accuracy_percentage,
                'num_windows': num_windows,
                'successful_fits': successful_fits
            }
        
        return {
            'ds_lppls_pos': ds_lppls_pos,
            'ds_lppls_neg': ds_lppls_neg,
            'bubble_type': bubble_type,
            'num_windows': num_windows,
            'successful_fits': successful_fits
        }
    
    def calculate_fco_score(self, bubble_analysis, fco_evaluation):
        """FCOベースのスコア計算（100点満点）"""
        print("\n=== FCOスコア計算 ===\n")
        
        score = 0
        
        # 1. バブル形成評価（30点） - 既存の基準を使用
        total_gain = bubble_analysis['total_gain']
        if total_gain > 50:
            score += 30
            print(f"   ✅ バブル形成: {total_gain:+.1f}% - 30点")
        elif total_gain > 30:
            score += 20
            print(f"   ⚠️ バブル形成: {total_gain:+.1f}% - 20点")
        else:
            print(f"   ❌ バブル形成: {total_gain:+.1f}% - 0点")
        
        # 2. DS-LPPLS信頼度（25点） - FCO独自基準
        ds_lppls = fco_evaluation['ds_lppls_pos']
        if ds_lppls > 50:
            score += 25
            print(f"   ✅ DS-LPPLS信頼度: {ds_lppls:.1f}% - 25点")
        elif ds_lppls > 30:
            score += 15
            print(f"   ⚠️ DS-LPPLS信頼度: {ds_lppls:.1f}% - 15点")
        else:
            print(f"   ❌ DS-LPPLS信頼度: {ds_lppls:.1f}% - 0点")
        
        # 3. 多重窓分析成功率（25点）
        success_rate = (fco_evaluation['successful_fits'] / fco_evaluation['num_windows']) * 100
        if success_rate > 60:
            score += 25
            print(f"   ✅ 分析成功率: {success_rate:.1f}% - 25点")
        elif success_rate > 40:
            score += 15
            print(f"   ⚠️ 分析成功率: {success_rate:.1f}% - 15点")
        else:
            print(f"   ❌ 分析成功率: {success_rate:.1f}% - 0点")
        
        # 4. クラッシュ規模（20点） - 既存の基準を使用
        if bubble_analysis['crash_analysis']:
            crash_decline = abs(bubble_analysis['crash_analysis']['max_decline'])
            if crash_decline > 20:
                score += 20
                print(f"   ✅ クラッシュ規模: {crash_decline:.1f}% - 20点")
            elif crash_decline > 10:
                score += 10
                print(f"   ⚠️ クラッシュ規模: {crash_decline:.1f}% - 10点")
            else:
                print(f"   ❌ クラッシュ規模: {crash_decline:.1f}% - 0点")
        
        print(f"\n🎯 FCO総合スコア: {score}/100")
        
        return score
    
    def compare_with_lppl(self):
        """既存LPPL結果との比較"""
        print("\n=== FCO vs 既存LPPL比較 ===\n")
        
        print("📊 比較結果:")
        print("   手法              | スコア | 判定")
        print("   ----------------- | ------ | ----")
        print(f"   既存LPPL          | 100/100 | ✅")
        
        # FCOスコアは実行後に表示
        return True
    
    def run_fco_validation(self):
        """FCO検証の完全実行"""
        print("\n" + "="*60)
        print("🔬 FCO方式による1987年ブラックマンデー再現検証")
        print("="*60)
        
        # 1. データ読み込み
        if not self.load_data():
            return False
        
        # 2. バブル形成分析（既存方式）
        bubble_analysis = self.analyze_bubble_formation()
        
        # 3. FCO分析実行
        fco_result = self.run_fco_analysis()
        
        if fco_result is None:
            print("❌ FCO分析に失敗しました")
            return False
        
        # 4. FCO結果評価
        fco_evaluation = self.evaluate_fco_results(fco_result)
        
        # 5. スコア計算
        fco_score = self.calculate_fco_score(bubble_analysis, fco_evaluation)
        
        # 6. 既存結果との比較
        self.compare_with_lppl()
        print(f"   FCO方式          | {fco_score}/100 | {'✅' if fco_score >= 80 else '⚠️'}")
        
        # 7. 最終判定
        print("\n" + "="*60)
        print("📋 最終判定")
        print("="*60)
        
        if fco_score >= 80:
            print("✅ FCO方式でも1987年クラッシュの予測可能性を確認")
            print("✅ 科学的根拠の維持: FCO多重時間窓分析が有効")
        else:
            print("⚠️ FCO方式では予測精度が低下")
            print("🔧 要調整: パラメータまたは実装の見直しが必要")
        
        return fco_score >= 80

def main():
    """メイン実行関数"""
    validator = FCOBlackMonday1987Validator()
    success = validator.run_fco_validation()
    
    if success:
        print("\n✅ FCO検証成功: 1987年ブラックマンデーの再現性確認")
    else:
        print("\n❌ FCO検証失敗: 追加調整が必要")
    
    return success

if __name__ == "__main__":
    main()