#!/usr/bin/env python3
"""
クイックスタート例

初回実行者向けの最小限の例を提供
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
import sys
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# 環境変数読み込み
load_dotenv()

# パス設定
sys.path.append('.')

def main():
    print("🚀 LPPL予測システム クイックスタート")
    print("=" * 50)
    
    try:
        # 1. 環境チェック
        print("\n📋 Step 1: 環境チェック...")
        check_basic_environment()
        
        # 2. 合成データでの基本テスト
        print("\n🧪 Step 2: 合成データでの基本テスト...")
        test_with_synthetic_data()
        
        # 3. 品質評価システムテスト
        print("\n🔍 Step 3: 品質評価システムテスト...")
        test_quality_evaluation()
        
        # 4. 実データ分析（可能な場合）
        print("\n📊 Step 4: 実データ分析テスト...")
        test_real_data_analysis()
        
        print("\n✅ クイックスタート完了！")
        print("\n📖 次のステップ:")
        print("   1. USER_EXECUTION_GUIDE.md を読んで詳細な使用方法を確認")
        print("   2. comprehensive_market_analysis.py で包括的分析を実行")
        print("   3. streamlit run src/ui/criteria_comparison_dashboard.py でUIを起動")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        print("\n🔧 トラブルシューティング:")
        print("   1. python check_environment.py を実行して環境を確認")
        print("   2. pip install -r requirements.txt で依存関係を再インストール")
        print("   3. USER_EXECUTION_GUIDE.md のトラブルシューティングを参照")

def check_basic_environment():
    """基本環境チェック"""
    
    # 必須モジュールのインポートテスト
    required_modules = [
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'), 
        ('matplotlib', 'Matplotlib'),
        ('scipy', 'SciPy')
    ]
    
    for module_name, display_name in required_modules:
        try:
            __import__(module_name)
            print(f"   ✅ {display_name}")
        except ImportError:
            raise ImportError(f"{display_name}が見つかりません。pip install {module_name}を実行してください。")
    
    # プロジェクトファイルの確認
    required_files = [
        'src/fitting/multi_criteria_selection.py',
        'src/fitting/fitting_quality_evaluator.py'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"必須ファイル {file_path} が見つかりません。")
    
    print("   ✅ 基本環境OK")

def test_with_synthetic_data():
    """合成データでの基本テスト"""
    
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    # 簡単な合成LPPLデータ生成
    n_points = 500
    t = np.linspace(0.1, 0.9, n_points)
    tc_true = 1.2
    
    # LPPL式で合成データ生成
    log_prices = (5.0 + 0.3 * (tc_true - t)**0.3 * 
                 (1 + 0.1 * np.cos(6 * np.log(tc_true - t))) + 
                 0.02 * np.random.randn(n_points))
    
    prices = np.exp(log_prices)
    dates = pd.date_range('2020-01-01', periods=n_points, freq='D')
    data = pd.DataFrame({'Close': prices}, index=dates)
    
    print(f"   📊 合成データ生成: {len(data)}点")
    
    # 多基準選択分析実行
    selector = MultiCriteriaSelector()
    result = selector.perform_comprehensive_fitting(data)
    
    print(f"   🎯 フィッティング結果:")
    print(f"      総候補数: {len(result.all_candidates)}")
    print(f"      成功候補: {len([c for c in result.all_candidates if c.convergence_success])}")
    
    # デフォルト結果表示
    default_result = result.get_selected_result()
    if default_result:
        print(f"      最良結果: tc={default_result.tc:.3f}, R²={default_result.r_squared:.3f}")
        print(f"      理論値からの誤差: Δtc={abs(default_result.tc - tc_true):.3f}")
    
    print("   ✅ 合成データテスト完了")

def test_quality_evaluation():
    """品質評価システムテスト"""
    
    from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator, FittingQuality
    
    evaluator = FittingQualityEvaluator()
    
    # テストケース1: 良好なフィット
    print("   🔍 テストケース1: 良好なパラメータ")
    good_params = {'tc': 1.25, 'beta': 0.33, 'omega': 6.36}
    good_stats = {'r_squared': 0.92, 'rmse': 0.04}
    
    assessment1 = evaluator.evaluate_fitting(good_params, good_stats)
    print(f"      品質: {assessment1.quality.value}")
    print(f"      信頼度: {assessment1.confidence:.2%}")
    print(f"      使用可能: {assessment1.is_usable}")
    
    # テストケース2: 境界張り付き
    print("   🔍 テストケース2: 境界張り付き")
    bad_params = {'tc': 1.001, 'beta': 0.35, 'omega': 6.5}
    bad_stats = {'r_squared': 0.95, 'rmse': 0.03}
    
    assessment2 = evaluator.evaluate_fitting(bad_params, bad_stats)
    print(f"      品質: {assessment2.quality.value}")
    print(f"      信頼度: {assessment2.confidence:.2%}")
    print(f"      使用可能: {assessment2.is_usable}")
    
    # 臨界点極近の特別メッセージ確認
    if assessment2.quality == FittingQuality.CRITICAL_PROXIMITY:
        print(f"      ⚠️ フィッティングエラー: {assessment2.metadata.get('interpretation', '')}")
        print(f"      原因: {assessment2.metadata.get('primary_cause', '')}")
        print(f"      推奨: {assessment2.metadata.get('recommended_action', '')}")
    
    print("   ✅ 品質評価テスト完了")

def test_real_data_analysis():
    """実データ分析テスト"""
    
    try:
        from src.data_sources.fred_data_client import FREDDataClient
        
        print("   📡 FRED API接続テスト...")
        client = FREDDataClient()
        
        # 短期間のデータ取得テスト
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1年分
        
        data = client.get_series_data(
            'NASDAQCOM',
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if data is not None and len(data) > 100:
            print(f"   ✅ データ取得成功: {len(data)}日分")
            
            # 簡易分析実行
            from src.fitting.multi_criteria_selection import MultiCriteriaSelector
            selector = MultiCriteriaSelector()
            
            # データ量を制限して高速化
            sample_data = data.tail(300) if len(data) > 300 else data
            result = selector.perform_comprehensive_fitting(sample_data)
            
            if result.selections:
                default_result = result.get_selected_result()
                print(f"   📊 NASDAQ分析結果:")
                print(f"      tc値: {default_result.tc:.3f}")
                print(f"      R²: {default_result.r_squared:.3f}")
                
                # 品質評価結果
                if default_result.quality_assessment:
                    qa = default_result.quality_assessment
                    print(f"      品質: {qa.quality.value}")
                    print(f"      使用可能: {qa.is_usable}")
            
            print("   ✅ 実データ分析テスト完了")
        else:
            print("   ⚠️ データ取得に失敗（API制限またはネットワーク問題）")
            print("   💡 オフラインでも合成データテストは正常に動作しています")
            
    except Exception as e:
        print(f"   ⚠️ 実データテストスキップ: {str(e)}")
        print("   💡 基本機能は正常に動作しています")

if __name__ == "__main__":
    main()