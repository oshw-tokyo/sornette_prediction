#!/usr/bin/env python3
"""
シンプル銘柄分析システム

指定された銘柄に対してLPPL分析を実行
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
sys.path.append('.')

from core.sornette_theory.lppl_model import logarithm_periodic_func
from infrastructure.data_sources.fred_data_client import FREDDataClient
from infrastructure.data_sources.alpha_vantage_client import AlphaVantageClient
from scipy.optimize import curve_fit

def analyze_symbol(symbol: str, period: str = '1y') -> dict:
    """
    指定銘柄のLPPL分析実行
    
    Args:
        symbol: 分析対象銘柄 (NASDAQCOM, AAPL, TSLA, etc.)
        period: 分析期間 (1y, 2y, 3y)
    
    Returns:
        dict: 分析結果
    """
    print(f"🎯 {symbol} LPPL分析開始")
    print("=" * 50)
    
    # 期間設定
    days_map = {'1y': 365, '2y': 730, '3y': 1095, '5y': 1825}
    days = days_map.get(period, 365)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # データ取得
    print(f"📊 {symbol} データ取得中... (期間: {period})")
    
    data = None
    source = None
    
    # FRED銘柄の場合
    fred_symbols = ['NASDAQCOM', 'SP500', 'DJIA', 'NASDAQ', 'DGS10']
    if symbol.upper() in fred_symbols:
        fred_client = FREDDataClient()
        data = fred_client.get_series_data(
            symbol.upper(), 
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        source = "FRED"
    else:
        # Alpha Vantage銘柄の場合
        av_client = AlphaVantageClient()
        data = av_client.get_stock_data(symbol.upper())
        if data is not None:
            # 期間でフィルタ
            data = data[data.index >= start_date]
        source = "Alpha Vantage"
    
    if data is None or len(data) == 0:
        return {
            "success": False,
            "error": f"データ取得失敗: {symbol}",
            "symbol": symbol,
            "source": source
        }
    
    print(f"✅ データ取得成功: {len(data)}日分")
    print(f"   ソース: {source}")
    print(f"   期間: {data.index[0].date()} - {data.index[-1].date()}")
    print(f"   価格範囲: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
    
    # LPPL分析実行
    print(f"\n🎯 LPPL分析実行中...")
    
    try:
        log_prices = np.log(data['Close'].values)
        t = np.linspace(0, 1, len(data))
        
        # 複数の初期値でフィッティング試行
        best_result = None
        best_r2 = -1
        
        # 初期値のバリエーション
        tc_values = [1.05, 1.1, 1.2, 1.3, 1.5]
        beta_values = [0.3, 0.5, 0.7]
        omega_values = [5.0, 6.5, 8.0]
        
        trials = 0
        for tc in tc_values:
            for beta in beta_values:
                for omega in omega_values:
                    trials += 1
                    if trials > 15:  # 最大15回試行
                        break
                        
                    try:
                        # 初期パラメータ
                        A_init = np.mean(log_prices)
                        B_init = (log_prices[-1] - log_prices[0]) / len(log_prices)
                        p0 = [tc, beta, omega, 0.0, A_init, B_init, 0.1]
                        
                        # 境界設定
                        bounds = (
                            [1.001, 0.1, 1.0, -2*np.pi, log_prices.min()-1, -2, -2],
                            [2.0, 1.0, 15.0, 2*np.pi, log_prices.max()+1, 2, 2]
                        )
                        
                        # フィッティング実行
                        popt, _ = curve_fit(
                            logarithm_periodic_func, t, log_prices,
                            p0=p0, bounds=bounds, method='trf',
                            maxfev=2000
                        )
                        
                        # R²計算
                        y_pred = logarithm_periodic_func(t, *popt)
                        r2 = 1 - np.sum((log_prices - y_pred)**2) / np.sum((log_prices - np.mean(log_prices))**2)
                        
                        if r2 > best_r2 and r2 > 0.1:
                            best_r2 = r2
                            best_result = {
                                'tc': popt[0],
                                'beta': popt[1], 
                                'omega': popt[2],
                                'phi': popt[3],
                                'A': popt[4],
                                'B': popt[5],
                                'C': popt[6],
                                'r_squared': r2,
                                'rmse': np.sqrt(np.mean((log_prices - y_pred)**2)),
                                'y_pred': y_pred
                            }
                            
                    except Exception:
                        continue
        
        if best_result is None:
            return {
                "success": False,
                "error": "LPPL フィッティングが収束しませんでした",
                "symbol": symbol,
                "source": source,
                "data_points": len(data)
            }
        
        # 結果表示
        print(f"✅ LPPL分析完了:")
        print(f"   tc (臨界時間): {best_result['tc']:.4f}")
        print(f"   β (臨界指数): {best_result['beta']:.4f}")
        print(f"   ω (角周波数): {best_result['omega']:.4f}")
        print(f"   R²: {best_result['r_squared']:.4f}")
        print(f"   RMSE: {best_result['rmse']:.4f}")
        
        # バブル危険度評価
        risk_level = "低"
        risk_color = "🟢"
        
        if best_result['tc'] < 1.2 and best_result['r_squared'] > 0.8:
            risk_level = "高"
            risk_color = "🔴"
        elif best_result['tc'] < 1.5 and best_result['r_squared'] > 0.6:
            risk_level = "中"  
            risk_color = "🟡"
            
        print(f"\n{risk_color} バブル危険度: {risk_level}")
        
        # 可視化作成
        create_analysis_plot(data, best_result, symbol, source)
        
        return {
            "success": True,
            "symbol": symbol,
            "source": source,
            "period": period,
            "data_points": len(data),
            "analysis_date": datetime.now().isoformat(),
            "parameters": {
                "tc": best_result['tc'],
                "beta": best_result['beta'],
                "omega": best_result['omega'],
                "phi": best_result['phi'],
                "A": best_result['A'],
                "B": best_result['B'],
                "C": best_result['C']
            },
            "quality": {
                "r_squared": best_result['r_squared'],
                "rmse": best_result['rmse']
            },
            "risk_assessment": {
                "level": risk_level,
                "color": risk_color,
                "reasoning": f"tc={best_result['tc']:.3f}, R²={best_result['r_squared']:.3f}"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"分析エラー: {str(e)}",
            "symbol": symbol,
            "source": source,
            "data_points": len(data)
        }

def create_analysis_plot(data, result, symbol, source):
    """分析結果の可視化"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Price Chart + LPPL Prediction
    ax1.plot(data.index, data['Close'], 'b-', linewidth=1.5, alpha=0.8, label='Actual Price')
    
    # LPPL prediction line
    t = np.linspace(0, 1, len(data))
    predicted_log = result['y_pred']
    predicted_price = np.exp(predicted_log)
    ax1.plot(data.index, predicted_price, 'r--', linewidth=2, label='LPPL Prediction')
    
    # Add crash prediction vertical line
    tc = result['tc']
    if tc > 1.0:  # Only show if crash is predicted in the future
        # Calculate crash date based on tc value
        data_period_days = len(data)
        crash_days_from_end = (tc - 1.0) * data_period_days
        if crash_days_from_end < 365:  # Only show if within reasonable time frame
            crash_date = data.index[-1] + pd.Timedelta(days=int(crash_days_from_end))
            ax1.axvline(crash_date, color='red', linestyle=':', linewidth=2, alpha=0.8, 
                       label=f'Predicted Crash (tc={tc:.3f})')
    
    ax1.set_ylabel('Price')
    ax1.set_title(f'{symbol} LPPL Analysis (Source: {source})', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Log Price + Fitting
    log_prices = np.log(data['Close'].values)
    ax2.plot(range(len(data)), log_prices, 'b-', linewidth=1.5, alpha=0.8, label='Actual (Log)')
    ax2.plot(range(len(data)), predicted_log, 'r--', linewidth=2, label='LPPL Fit')
    
    # Add crash prediction vertical line in normalized space
    if tc > 1.0 and (tc - 1.0) * data_period_days < 365:
        crash_position = tc * len(data)
        if crash_position <= len(data) * 1.5:  # Show if within reasonable range
            ax2.axvline(crash_position, color='red', linestyle=':', linewidth=2, alpha=0.8)
    
    ax2.set_ylabel('Log Price')
    ax2.set_xlabel('Days')
    ax2.set_title('Log Price Fitting', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. パラメータ表示
    ax3.axis('off')
    
    param_text = f"""
{symbol} LPPL Analysis Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Source: {source}
Analysis Period: {data.index[0].date()} - {data.index[-1].date()}
Data Points: {len(data)} days

LPPL Parameters
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tc (Critical Time): {result['tc']:.4f}
β (Critical Exponent): {result['beta']:.4f}
ω (Angular Frequency): {result['omega']:.4f}
φ (Phase): {result['phi']:.4f}

Quality Metrics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
R² (R-squared): {result['r_squared']:.4f}
RMSE: {result['rmse']:.4f}

Risk Assessment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'🔴 High Risk' if result['tc'] < 1.2 else '🟡 Medium Risk' if result['tc'] < 1.5 else '🟢 Low Risk'}
"""
    
    ax3.text(0.05, 0.95, param_text, transform=ax3.transAxes, fontsize=11,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    # 4. Residuals Analysis
    residuals = log_prices - predicted_log
    ax4.plot(range(len(data)), residuals, 'g-', linewidth=1, alpha=0.7)
    ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax4.fill_between(range(len(data)), residuals, alpha=0.3, color='green')
    
    ax4.set_ylabel('Residuals')
    ax4.set_xlabel('Days')
    ax4.set_title('Fitting Residuals', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存
    plots_dir = 'results/symbol_analysis'
    os.makedirs(plots_dir, exist_ok=True)
    
    filename = f"{plots_dir}/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_lppl_analysis.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"📊 分析結果保存: {filename}")
    
    plt.show()

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='銘柄LPPL分析システム')
    parser.add_argument('symbol', help='分析対象銘柄 (例: NASDAQCOM, AAPL, TSLA)')
    parser.add_argument('--period', default='1y', choices=['1y', '2y', '3y', '5y'],
                       help='分析期間 (デフォルト: 1y)')
    
    args = parser.parse_args()
    
    result = analyze_symbol(args.symbol, args.period)
    
    if result['success']:
        print(f"\n🎉 {args.symbol} 分析完了!")
        print(f"リスクレベル: {result['risk_assessment']['color']} {result['risk_assessment']['level']}")
    else:
        print(f"\n❌ 分析失敗: {result['error']}")

if __name__ == "__main__":
    main()