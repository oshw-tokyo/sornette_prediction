#!/usr/bin/env python3
"""
包括的市場クラッシュ予測分析

利用可能な全市場データに対してLPPL解析を実行し、
クラッシュリスクを網羅的に評価
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
from src.monitoring.multi_market_monitor import MultiMarketMonitor, MarketIndex, TimeWindow
from src.data_management.prediction_database import PredictionDatabase
import yfinance as yf

def main():
    print("🌍 包括的市場クラッシュ予測分析")
    print("=" * 70)
    
    # 1. 利用可能な市場データソース確認
    print("\n📊 Step 1: 利用可能な市場データソースの確認...")
    markets_to_analyze = get_comprehensive_market_list()
    print_market_summary(markets_to_analyze)
    
    # 2. FRED経由での市場データ取得
    print("\n📈 Step 2: FRED経由での市場データ取得...")
    fred_data = fetch_fred_markets()
    
    # 3. Yahoo Finance経由での追加市場データ取得
    print("\n🌏 Step 3: Yahoo Finance経由での国際市場データ取得...")
    yahoo_data = fetch_yahoo_markets()
    
    # 4. 暗号通貨データ取得
    print("\n💰 Step 4: 暗号通貨市場データ取得...")
    crypto_data = fetch_crypto_markets()
    
    # 5. 商品市場データ取得
    print("\n🏛️ Step 5: 商品市場データ取得...")
    commodity_data = fetch_commodity_markets()
    
    # 6. 全市場の統合LPPL解析
    print("\n🔬 Step 6: 全市場の統合LPPL解析実行...")
    analysis_results = perform_comprehensive_analysis(
        fred_data, yahoo_data, crypto_data, commodity_data
    )
    
    # 7. リスクレポート生成
    print("\n📊 Step 7: 統合リスクレポート生成...")
    generate_risk_report(analysis_results)
    
    # 8. 可視化
    print("\n📈 Step 8: 結果の可視化...")
    visualize_comprehensive_results(analysis_results)
    
    print("\n✅ 包括的市場分析完了")

def get_comprehensive_market_list():
    """包括的な市場リスト"""
    return {
        'FRED_MARKETS': {
            'SP500': 'S&P 500 Index',
            'DJIA': 'Dow Jones Industrial Average',
            'NASDAQCOM': 'NASDAQ Composite',
            'RUT': 'Russell 2000',
            'VIXCLS': 'VIX Volatility Index',
            'DFF': 'Federal Funds Rate',
            'DCOILWTICO': 'WTI Crude Oil',
            'GOLDAMGBD228NLBM': 'Gold Price',
            'DEXUSEU': 'USD/EUR Exchange Rate',
            'DEXCHUS': 'USD/CNY Exchange Rate',
            'DEXJPUS': 'USD/JPY Exchange Rate'
        },
        'YAHOO_MARKETS': {
            '^GSPC': 'S&P 500 (Yahoo)',
            '^DJI': 'Dow Jones (Yahoo)', 
            '^IXIC': 'NASDAQ (Yahoo)',
            '^RUT': 'Russell 2000 (Yahoo)',
            '^FTSE': 'FTSE 100 (UK)',
            '^GDAXI': 'DAX (Germany)',
            '^FCHI': 'CAC 40 (France)',
            '^N225': 'Nikkei 225 (Japan)',
            '^HSI': 'Hang Seng (Hong Kong)',
            '000001.SS': 'Shanghai Composite',
            '^KS11': 'KOSPI (South Korea)',
            '^AXJO': 'ASX 200 (Australia)',
            '^BSESN': 'BSE SENSEX (India)',
            '^GSPTSE': 'S&P/TSX (Canada)',
            '^BVSP': 'Bovespa (Brazil)',
            '^MXX': 'IPC Mexico',
            'IMOEX.ME': 'MOEX Russia Index'
        },
        'CRYPTO_MARKETS': {
            'BTC-USD': 'Bitcoin',
            'ETH-USD': 'Ethereum',
            'BNB-USD': 'Binance Coin',
            'XRP-USD': 'Ripple',
            'ADA-USD': 'Cardano',
            'SOL-USD': 'Solana',
            'DOGE-USD': 'Dogecoin'
        },
        'COMMODITY_MARKETS': {
            'GC=F': 'Gold Futures',
            'SI=F': 'Silver Futures',
            'CL=F': 'Crude Oil Futures',
            'NG=F': 'Natural Gas Futures',
            'ZW=F': 'Wheat Futures',
            'ZC=F': 'Corn Futures',
            'HG=F': 'Copper Futures',
            'PL=F': 'Platinum Futures'
        },
        'SECTOR_ETFS': {
            'XLF': 'Financial Sector',
            'XLK': 'Technology Sector',
            'XLE': 'Energy Sector',
            'XLV': 'Healthcare Sector',
            'XLI': 'Industrial Sector',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLB': 'Materials Sector',
            'XLRE': 'Real Estate Sector',
            'XLU': 'Utilities Sector'
        }
    }

def print_market_summary(markets):
    """市場サマリーの表示"""
    total_markets = sum(len(m) for m in markets.values())
    print(f"\n📊 分析対象市場サマリー:")
    print(f"   総市場数: {total_markets}")
    for category, market_dict in markets.items():
        print(f"   {category}: {len(market_dict)}市場")

def fetch_fred_markets():
    """FRED市場データの取得"""
    client = FREDDataClient()
    fred_markets = get_comprehensive_market_list()['FRED_MARKETS']
    
    # 主要指数のみ取得（API制限を考慮）
    priority_indices = ['SP500', 'NASDAQCOM', 'DJIA', 'GOLDAMGBD228NLBM', 'DCOILWTICO']
    
    data = {}
    for symbol in priority_indices:
        if symbol in fred_markets:
            print(f"   📥 {fred_markets[symbol]}...")
            try:
                # 過去5年分のデータを取得
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5*365)
                
                df = client.get_series_data(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if df is not None and len(df) > 100:
                    data[symbol] = df
                    print(f"      ✅ {len(df)}日分のデータ取得")
                else:
                    print(f"      ⚠️ データ不足またはエラー")
                    
            except Exception as e:
                print(f"      ❌ エラー: {str(e)}")
    
    return data

def fetch_yahoo_markets():
    """Yahoo Finance市場データの取得"""
    yahoo_markets = get_comprehensive_market_list()['YAHOO_MARKETS']
    
    # 主要国際市場を優先
    priority_markets = ['^GSPC', '^FTSE', '^GDAXI', '^N225', '^HSI', '000001.SS']
    
    data = {}
    for symbol in priority_markets:
        if symbol in yahoo_markets:
            print(f"   📥 {yahoo_markets[symbol]}...")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='5y')
                
                if not df.empty and len(df) > 100:
                    data[symbol] = df
                    print(f"      ✅ {len(df)}日分のデータ取得")
                else:
                    print(f"      ⚠️ データ不足")
                    
            except Exception as e:
                print(f"      ❌ エラー: {str(e)}")
    
    return data

def fetch_crypto_markets():
    """暗号通貨市場データの取得"""
    crypto_markets = get_comprehensive_market_list()['CRYPTO_MARKETS']
    
    # 主要暗号通貨のみ
    priority_crypto = ['BTC-USD', 'ETH-USD']
    
    data = {}
    for symbol in priority_crypto:
        if symbol in crypto_markets:
            print(f"   📥 {crypto_markets[symbol]}...")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='5y')
                
                if not df.empty and len(df) > 100:
                    data[symbol] = df
                    print(f"      ✅ {len(df)}日分のデータ取得")
                else:
                    print(f"      ⚠️ データ不足")
                    
            except Exception as e:
                print(f"      ❌ エラー: {str(e)}")
    
    return data

def fetch_commodity_markets():
    """商品市場データの取得"""
    commodity_markets = get_comprehensive_market_list()['COMMODITY_MARKETS']
    
    # 主要商品のみ
    priority_commodities = ['GC=F', 'CL=F']
    
    data = {}
    for symbol in priority_commodities:
        if symbol in commodity_markets:
            print(f"   📥 {commodity_markets[symbol]}...")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='5y')
                
                if not df.empty and len(df) > 100:
                    data[symbol] = df
                    print(f"      ✅ {len(df)}日分のデータ取得")
                else:
                    print(f"      ⚠️ データ不足")
                    
            except Exception as e:
                print(f"      ❌ エラー: {str(e)}")
    
    return data

def perform_comprehensive_analysis(fred_data, yahoo_data, crypto_data, commodity_data):
    """全市場の統合LPPL解析"""
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    all_markets = get_comprehensive_market_list()
    results = []
    
    # FRED データ解析
    print("\n   🔬 FREDデータ解析中...")
    for symbol, df in fred_data.items():
        market_name = all_markets['FRED_MARKETS'].get(symbol, symbol)
        print(f"      分析中: {market_name}")
        
        result = analyze_single_market(symbol, df, market_name, 'FRED')
        if result:
            results.append(result)
    
    # Yahoo データ解析
    print("\n   🔬 Yahoo Financeデータ解析中...")
    for symbol, df in yahoo_data.items():
        market_name = all_markets['YAHOO_MARKETS'].get(symbol, symbol)
        print(f"      分析中: {market_name}")
        
        result = analyze_single_market(symbol, df, market_name, 'Yahoo')
        if result:
            results.append(result)
    
    # 暗号通貨解析
    print("\n   🔬 暗号通貨データ解析中...")
    for symbol, df in crypto_data.items():
        market_name = all_markets['CRYPTO_MARKETS'].get(symbol, symbol)
        print(f"      分析中: {market_name}")
        
        result = analyze_single_market(symbol, df, market_name, 'Crypto')
        if result:
            results.append(result)
    
    # 商品市場解析
    print("\n   🔬 商品市場データ解析中...")
    for symbol, df in commodity_data.items():
        market_name = all_markets['COMMODITY_MARKETS'].get(symbol, symbol)
        print(f"      分析中: {market_name}")
        
        result = analyze_single_market(symbol, df, market_name, 'Commodity')
        if result:
            results.append(result)
    
    return results

def analyze_single_market(symbol, df, market_name, data_source):
    """単一市場のLPPL解析"""
    from src.fitting.multi_criteria_selection import MultiCriteriaSelector
    
    try:
        # 複数の期間で解析
        windows = [365, 730, 1095]  # 1年、2年、3年
        
        best_result = None
        best_confidence = 0
        
        for window_days in windows:
            # 直近のウィンドウデータを抽出
            if len(df) >= window_days:
                window_data = df.tail(window_days).copy()
                
                # LPPL解析実行
                selector = MultiCriteriaSelector()
                selection_result = selector.perform_comprehensive_fitting(window_data)
                
                if selection_result.selections:
                    # デフォルト（R²最大）結果を使用
                    candidate = selection_result.get_selected_result()
                    
                    if candidate and candidate.r_squared > 0.7:
                        # 予測日計算
                        observation_days = window_days
                        days_to_critical = (candidate.tc - 1.0) * observation_days
                        predicted_date = df.index[-1] + timedelta(days=days_to_critical)
                        
                        # 信頼度計算
                        confidence = calculate_confidence(candidate)
                        
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_result = {
                                'symbol': symbol,
                                'market_name': market_name,
                                'data_source': data_source,
                                'window_days': window_days,
                                'tc': candidate.tc,
                                'beta': candidate.beta,
                                'omega': candidate.omega,
                                'r_squared': candidate.r_squared,
                                'rmse': candidate.rmse,
                                'predicted_date': predicted_date,
                                'confidence': confidence,
                                'risk_level': categorize_risk(candidate.tc),
                                'last_price': df['Close'].iloc[-1] if 'Close' in df.columns else df.iloc[-1],
                                'analysis_date': df.index[-1]
                            }
        
        return best_result
        
    except Exception as e:
        print(f"         ⚠️ 解析エラー ({market_name}): {str(e)}")
        return None

def calculate_confidence(candidate):
    """信頼度スコアの計算"""
    base_score = candidate.r_squared
    
    # tc値による調整
    if candidate.tc <= 1.2:
        tc_multiplier = 1.0
    elif candidate.tc <= 1.5:
        tc_multiplier = 0.8
    elif candidate.tc <= 2.0:
        tc_multiplier = 0.6
    else:
        tc_multiplier = 0.3
    
    # 理論値との適合性
    beta_score = 1.0 - min(1.0, abs(candidate.beta - 0.33) / 0.33)
    omega_score = 1.0 - min(1.0, abs(candidate.omega - 6.36) / 6.36)
    theory_score = (beta_score + omega_score) / 2
    
    # 総合スコア
    confidence = base_score * tc_multiplier * (0.7 + 0.3 * theory_score)
    
    return min(1.0, confidence)

def categorize_risk(tc):
    """リスクレベルの分類"""
    if tc <= 1.1:
        return "🚨 差し迫った"
    elif tc <= 1.3:
        return "⚠️ 高リスク"
    elif tc <= 1.5:
        return "⚡ 中リスク"
    elif tc <= 2.0:
        return "👁️ 監視推奨"
    else:
        return "📊 長期トレンド"

def generate_risk_report(results):
    """統合リスクレポートの生成"""
    if not results:
        print("   ⚠️ 分析結果がありません")
        return
    
    # リスクレベル別に分類
    high_risk = [r for r in results if r['tc'] <= 1.3]
    medium_risk = [r for r in results if 1.3 < r['tc'] <= 1.5]
    monitoring = [r for r in results if 1.5 < r['tc'] <= 2.0]
    
    print("\n" + "=" * 70)
    print("🎯 包括的市場リスクレポート")
    print("=" * 70)
    
    print(f"\n📊 分析サマリー:")
    print(f"   総分析市場数: {len(results)}")
    print(f"   高リスク市場: {len(high_risk)}")
    print(f"   中リスク市場: {len(medium_risk)}")
    print(f"   監視推奨市場: {len(monitoring)}")
    
    if high_risk:
        print(f"\n🚨 高リスク市場 (tc ≤ 1.3):")
        for r in sorted(high_risk, key=lambda x: x['tc']):
            print(f"   {r['market_name']} ({r['symbol']}):")
            print(f"     - tc値: {r['tc']:.3f}")
            print(f"     - 予測クラッシュ日: {r['predicted_date'].strftime('%Y-%m-%d')}")
            print(f"     - 信頼度: {r['confidence']:.2%}")
            print(f"     - R²: {r['r_squared']:.3f}")
    
    if medium_risk:
        print(f"\n⚡ 中リスク市場 (1.3 < tc ≤ 1.5):")
        for r in sorted(medium_risk, key=lambda x: x['tc']):
            print(f"   {r['market_name']} ({r['symbol']}):")
            print(f"     - tc値: {r['tc']:.3f}")
            print(f"     - 予測日: {r['predicted_date'].strftime('%Y-%m-%d')}")
            print(f"     - 信頼度: {r['confidence']:.2%}")
    
    # 市場カテゴリー別サマリー
    print(f"\n📈 カテゴリー別分析:")
    categories = {}
    for r in results:
        cat = r['data_source']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    
    for cat, cat_results in categories.items():
        avg_tc = np.mean([r['tc'] for r in cat_results])
        high_risk_count = len([r for r in cat_results if r['tc'] <= 1.3])
        print(f"   {cat}: {len(cat_results)}市場分析, 平均tc={avg_tc:.2f}, 高リスク={high_risk_count}")
    
    # CSVエクスポート
    df_results = pd.DataFrame(results)
    os.makedirs('results/comprehensive_analysis', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'results/comprehensive_analysis/market_risk_report_{timestamp}.csv'
    df_results.to_csv(filename, index=False)
    print(f"\n💾 詳細レポート保存: {filename}")

def visualize_comprehensive_results(results):
    """結果の包括的可視化"""
    if not results:
        return
    
    plt.style.use('seaborn-v0_8-darkgrid')
    fig = plt.figure(figsize=(20, 12))
    
    # 1. tc値分布
    ax1 = plt.subplot(2, 3, 1)
    tc_values = [r['tc'] for r in results]
    ax1.hist(tc_values, bins=20, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.axvline(1.3, color='red', linestyle='--', label='High Risk Threshold')
    ax1.axvline(1.5, color='orange', linestyle='--', label='Medium Risk Threshold')
    ax1.set_xlabel('tc value')
    ax1.set_ylabel('Number of Markets')
    ax1.set_title('tc Value Distribution')
    ax1.legend()
    
    # 2. 市場別リスクマップ
    ax2 = plt.subplot(2, 3, 2)
    sorted_results = sorted(results, key=lambda x: x['tc'])[:15]  # 上位15市場
    markets = [r['market_name'][:20] for r in sorted_results]
    tc_vals = [r['tc'] for r in sorted_results]
    colors = ['red' if tc <= 1.3 else 'orange' if tc <= 1.5 else 'green' for tc in tc_vals]
    
    bars = ax2.barh(markets, tc_vals, color=colors)
    ax2.axvline(1.3, color='red', linestyle='--', alpha=0.5)
    ax2.axvline(1.5, color='orange', linestyle='--', alpha=0.5)
    ax2.set_xlabel('tc value')
    ax2.set_title('High Risk Market Ranking')
    
    # 3. 予測タイムライン
    ax3 = plt.subplot(2, 3, 3)
    high_risk_results = [r for r in results if r['tc'] <= 1.5]
    if high_risk_results:
        dates = [r['predicted_date'] for r in high_risk_results]
        positions = range(len(high_risk_results))
        colors_timeline = ['red' if r['tc'] <= 1.3 else 'orange' for r in high_risk_results]
        
        for i, (date, r) in enumerate(zip(dates, high_risk_results)):
            ax3.plot([date, date], [i-0.4, i+0.4], color=colors_timeline[i], linewidth=3)
            ax3.text(date, i, r['market_name'][:15], fontsize=8, ha='right', va='center')
        
        ax3.set_ylim(-1, len(high_risk_results))
        ax3.set_xlabel('Predicted Crash Date')
        ax3.set_title('Crash Prediction Timeline')
        ax3.grid(axis='x')
    
    # 4. 信頼度 vs tc値
    ax4 = plt.subplot(2, 3, 4)
    tc_vals_all = [r['tc'] for r in results]
    conf_vals = [r['confidence'] for r in results]
    
    scatter = ax4.scatter(tc_vals_all, conf_vals, c=tc_vals_all, cmap='RdYlGn_r', 
                         s=100, alpha=0.6, edgecolors='black')
    ax4.axvline(1.3, color='red', linestyle='--', alpha=0.5)
    ax4.axvline(1.5, color='orange', linestyle='--', alpha=0.5)
    ax4.set_xlabel('tc value')
    ax4.set_ylabel('Confidence')
    ax4.set_title('tc value vs Confidence')
    plt.colorbar(scatter, ax=ax4, label='tc value')
    
    # 5. カテゴリー別リスク分布
    ax5 = plt.subplot(2, 3, 5)
    categories = {}
    for r in results:
        cat = r['data_source']
        if cat not in categories:
            categories[cat] = {'high': 0, 'medium': 0, 'low': 0}
        
        if r['tc'] <= 1.3:
            categories[cat]['high'] += 1
        elif r['tc'] <= 1.5:
            categories[cat]['medium'] += 1
        else:
            categories[cat]['low'] += 1
    
    cat_names = list(categories.keys())
    high_counts = [categories[c]['high'] for c in cat_names]
    medium_counts = [categories[c]['medium'] for c in cat_names]
    low_counts = [categories[c]['low'] for c in cat_names]
    
    x = np.arange(len(cat_names))
    width = 0.6
    
    ax5.bar(x, high_counts, width, label='High Risk', color='red', alpha=0.8)
    ax5.bar(x, medium_counts, width, bottom=high_counts, label='Medium Risk', color='orange', alpha=0.8)
    ax5.bar(x, low_counts, width, bottom=np.array(high_counts)+np.array(medium_counts), 
            label='Low Risk', color='green', alpha=0.8)
    
    ax5.set_xticks(x)
    ax5.set_xticklabels(cat_names)
    ax5.set_ylabel('Number of Markets')
    ax5.set_title('Risk Distribution by Category')
    ax5.legend()
    
    # 6. R²分布
    ax6 = plt.subplot(2, 3, 6)
    r2_values = [r['r_squared'] for r in results]
    ax6.hist(r2_values, bins=20, alpha=0.7, color='darkgreen', edgecolor='black')
    ax6.axvline(np.mean(r2_values), color='red', linestyle='--', 
                label=f'Average R²={np.mean(r2_values):.3f}')
    ax6.set_xlabel('R² value')
    ax6.set_ylabel('Number of Markets')
    ax6.set_title('Model Fit Quality Distribution')
    ax6.legend()
    
    plt.tight_layout()
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'results/comprehensive_analysis/risk_visualization_{timestamp}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n📊 可視化保存: {filename}")
    plt.show()

if __name__ == "__main__":
    main()