#!/usr/bin/env python3
"""
FRED API動作確認スクリプト
Alpha Vantageを除外し、FREDのみで市場分析を実行
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.append('.')

# matplotlib設定（GUIを無効化）
from src.config.matplotlib_config import configure_matplotlib_for_automation, save_and_close_figure
configure_matplotlib_for_automation()
import matplotlib.pyplot as plt

from src.data_sources.unified_data_client import UnifiedDataClient
from src.fitting.multi_criteria_selection import MultiCriteriaSelector
from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator

def test_fred_data_access():
    """FREDデータアクセスのテスト"""
    print("🧪 FREDデータアクセステスト")
    print("=" * 60)
    
    # 統合クライアント初期化（Alpha Vantageは無効化済み）
    client = UnifiedDataClient()
    
    # テスト対象の指数
    test_symbols = ['NASDAQ', 'SP500', 'DJIA', 'VIX']
    
    # データ取得期間
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    results = {}
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol} データ取得中...")
        
        data, source = client.get_data_with_fallback(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if data is not None:
            print(f"   ✅ 成功: {len(data)}日分 (ソース: {source})")
            print(f"   期間: {data.index[0].date()} - {data.index[-1].date()}")
            print(f"   最新価格: {data['Close'].iloc[-1]:.2f}")
            results[symbol] = data
        else:
            print(f"   ❌ 失敗")
    
    return results

def test_lppl_fitting(data, symbol):
    """LPPLフィッティングのテスト"""
    print(f"\n🎯 {symbol} LPPLフィッティング")
    print("-" * 40)
    
    # MultiCriteriaSelector を使用
    selector = MultiCriteriaSelector()
    
    # フィッティング実行
    result = selector.perform_comprehensive_fitting(data)
    
    # 結果の要約
    print(f"総候補数: {len(result.all_candidates)}")
    print(f"成功候補: {len([c for c in result.all_candidates if c.success])}")
    
    if result.best_by_r_squared:
        best = result.best_by_r_squared
        print(f"\n最良結果 (R²基準):")
        print(f"  tc: {best.tc:.3f}")
        print(f"  β: {best.beta:.3f}")
        print(f"  ω: {best.omega:.3f}")
        print(f"  R²: {best.r_squared:.3f}")
        
        # 品質評価
        if best.quality_assessment:
            qa = best.quality_assessment
            print(f"  品質: {qa.quality.value}")
            print(f"  信頼度: {qa.confidence:.1%}")
            print(f"  使用可能: {qa.is_usable}")
    
    return result

def visualize_results(data, result, symbol):
    """結果の可視化"""
    if not result.best_by_r_squared:
        return
    
    best = result.best_by_r_squared
    
    # シンプルな可視化
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # データとフィッティング結果
    t = np.arange(len(data))
    prices = data['Close'].values
    
    # LPPLモデル計算
    from src.core.models import lppl_model
    fitted_values = lppl_model(t, best.tc, best.beta, best.omega, 
                              best.phi, best.A, best.B, best.C)
    
    # プロット1: 価格とフィッティング
    ax1.plot(data.index, prices, 'b-', label='Actual Price', alpha=0.7)
    ax1.plot(data.index, fitted_values, 'r-', label='LPPL Fit', linewidth=2)
    ax1.set_title(f'{symbol} - LPPL Fitting Result')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # プロット2: 残差
    residuals = prices - fitted_values
    ax2.plot(data.index, residuals, 'g-', alpha=0.7)
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.5)
    ax2.set_title('Residuals')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Residual')
    ax2.grid(True, alpha=0.3)
    
    # 情報追加
    info_text = f'tc: {best.tc:.3f}, β: {best.beta:.3f}, ω: {best.omega:.3f}, R²: {best.r_squared:.3f}'
    fig.suptitle(f'{symbol} LPPL Analysis\n{info_text}', fontsize=14)
    
    plt.tight_layout()
    
    # 保存
    os.makedirs('results/fred_test', exist_ok=True)
    filename = f'results/fred_test/{symbol.lower()}_analysis.png'
    save_and_close_figure(fig, filename)

def main():
    """メイン実行関数"""
    print("🚀 FRED限定動作確認")
    print("=" * 60)
    print("Alpha Vantageを除外し、FREDのみで分析を実行します")
    
    # 1. データアクセステスト
    market_data = test_fred_data_access()
    
    if not market_data:
        print("\n❌ データ取得に失敗しました")
        return
    
    # 2. 各指数でLPPL分析
    print("\n" + "=" * 60)
    print("📈 LPPL分析開始")
    
    for symbol, data in market_data.items():
        if symbol == 'VIX':  # VIXは変動率指数なのでスキップ
            continue
            
        result = test_lppl_fitting(data, symbol)
        
        if len([c for c in result.all_candidates if c.success]) > 0:
            visualize_results(data, result, symbol)
    
    print("\n✅ 動作確認完了！")
    print("\n📁 結果:")
    print("   - データ取得: FRED APIのみ使用")
    print("   - 分析対象: NASDAQ, S&P500, DJIA")
    print("   - 結果保存: results/fred_test/")

if __name__ == "__main__":
    main()