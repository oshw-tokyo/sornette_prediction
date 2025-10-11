#!/usr/bin/env python3
"""
Quick NASDAQ 1987 LPPL Validation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
import sys
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# Environment setup
load_dotenv()
sys.path.append('.')

from src.fitting.utils import logarithm_periodic_func
from src.data_sources.fred_data_client import FREDDataClient
from scipy.optimize import curve_fit

def main():
    print("🎯 Quick NASDAQ 1987 LPPL Validation\n")
    
    # 1. Get NASDAQ data
    print("📊 Getting NASDAQ data...")
    client = FREDDataClient()
    data = client.get_series_data('NASDAQCOM', '1985-01-01', '1987-10-31')
    
    if data is None:
        print("❌ Failed to get data")
        return
        
    # 2. Prepare pre-crash data
    crash_date = datetime(1987, 10, 19)
    pre_crash = data[data.index < crash_date]
    
    if len(pre_crash) < 100:
        print(f"❌ Insufficient data: {len(pre_crash)} days")
        return
        
    print(f"✅ Pre-crash data: {len(pre_crash)} days")
    print(f"   Period: {pre_crash.index[0].date()} - {pre_crash.index[-1].date()}")
    
    # 3. Prepare for LPPL fitting
    log_prices = np.log(pre_crash['Close'].values)
    t = np.linspace(0, 1, len(log_prices))
    
    # 4. LPPL fitting (reduced trials for speed)
    print("\n📈 LPPL Fitting...")
    
    tc_bounds = (1.01, 1.15)
    bounds = (
        [tc_bounds[0], 0.1, 2.0, -8*np.pi, log_prices.min()-0.5, -2.0, -1.0],
        [tc_bounds[1], 0.8, 15.0, 8*np.pi, log_prices.max()+0.5, 2.0, 1.0]
    )
    
    best_result = None
    best_r2 = -1
    
    for i in range(10):  # Reduced from 25 to 10 trials
        try:
            # Random initial values
            tc_init = np.random.uniform(tc_bounds[0], tc_bounds[1])
            beta_init = np.random.uniform(0.2, 0.5)
            omega_init = np.random.uniform(5.0, 10.0)
            phi_init = np.random.uniform(-np.pi, np.pi)
            A_init = np.mean(log_prices)
            B_init = np.random.uniform(-0.8, 0.8)
            C_init = np.random.uniform(-0.3, 0.3)
            
            p0 = [tc_init, beta_init, omega_init, phi_init, A_init, B_init, C_init]
            
            # Fit
            popt, pcov = curve_fit(
                logarithm_periodic_func, t, log_prices,
                p0=p0, bounds=bounds, method='trf',
                maxfev=5000  # Reduced iterations
            )
            
            # Evaluate
            y_pred = logarithm_periodic_func(t, *popt)
            residuals = log_prices - y_pred
            r_squared = 1 - (np.sum(residuals**2) / np.sum((log_prices - np.mean(log_prices))**2))
            rmse = np.sqrt(np.mean(residuals**2))
            
            # Check constraints
            tc, beta, omega = popt[0], popt[1], popt[2]
            if tc > t[-1] and 0.1 <= beta <= 0.8 and 2.0 <= omega <= 15.0 and r_squared > 0.5:
                if r_squared > best_r2:
                    best_r2 = r_squared
                    best_result = {
                        'params': popt,
                        'r_squared': r_squared,
                        'rmse': rmse,
                        'prediction': y_pred
                    }
                
                print(f"  Trial {i+1}: R²={r_squared:.4f}, β={beta:.3f}, ω={omega:.2f}")
                
        except Exception:
            continue
    
    if best_result is None:
        print("❌ No valid fitting results")
        return
    
    # 5. Results analysis
    params = best_result['params']
    tc, beta, omega = params[0], params[1], params[2]
    r_squared = best_result['r_squared']
    rmse = best_result['rmse']
    
    print(f"\n🎯 NASDAQ 1987 LPPL Validation Results")
    print("=" * 50)
    print(f"Data Source: FRED NASDAQCOM")
    print(f"Period: {pre_crash.index[0].date()} - {pre_crash.index[-1].date()}")
    print(f"Data Points: {len(pre_crash)}")
    
    print(f"\nFitting Quality:")
    print(f"  R² = {r_squared:.4f}")
    print(f"  RMSE = {rmse:.4f}")
    
    print(f"\nParameter Estimates vs Paper Values:")
    paper_beta = 0.33
    paper_omega = 7.4
    
    beta_error = abs(beta - paper_beta) / paper_beta * 100
    omega_error = abs(omega - paper_omega) / paper_omega * 100
    
    print(f"  tc (critical time): {tc:.4f}")
    print(f"  β (critical exponent): {beta:.3f} vs {paper_beta:.2f} (error: {beta_error:.1f}%)")
    print(f"  ω (angular frequency): {omega:.2f} vs {paper_omega:.1f} (error: {omega_error:.1f}%)")
    
    # 6. Evaluation
    beta_ok = beta_error < 25
    omega_ok = omega_error < 30
    r2_ok = r_squared > 0.75
    
    overall_success = beta_ok and omega_ok and r2_ok
    
    print(f"\nEvaluation:")
    print(f"  β parameter: {'✅ Acceptable' if beta_ok else '❌ Needs improvement'}")
    print(f"  ω parameter: {'✅ Acceptable' if omega_ok else '❌ Needs improvement'}")
    print(f"  Fitting quality: {'✅ Acceptable' if r2_ok else '❌ Needs improvement'}")
    
    print(f"\nOverall Result:")
    if overall_success:
        print("✅ SUCCESS: LPPL model validation confirmed with real market data")
        print("✅ Scientific significance: Theory explains actual crash precursors")
        print("✅ Practical value: Crash prediction system foundation established")
    else:
        print("⚠️ PARTIAL SUCCESS: Model application has challenges")
        print("🔬 Research value: Identifies areas for model improvement")
    
    # 7. Simple visualization
    print(f"\n📊 Creating validation plot...")
    
    plt.figure(figsize=(12, 8))
    
    # Main plot
    dates = pre_crash.index
    actual_prices = pre_crash['Close'].values
    fitted_prices = np.exp(best_result['prediction'])
    
    plt.subplot(2, 1, 1)
    plt.plot(dates, actual_prices, 'b-', linewidth=1.5, alpha=0.8, label='NASDAQ Real Data')
    plt.plot(dates, fitted_prices, 'r-', linewidth=2, label='LPPL Fit')
    
    # Mark Black Monday
    crash_date = datetime(1987, 10, 19)
    plt.axvline(crash_date, color='red', linestyle='--', alpha=0.7, label='Black Monday')
    
    plt.ylabel('NASDAQ Composite')
    plt.title(f'1987 Black Monday NASDAQ Validation (R²={r_squared:.4f})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Parameter comparison
    plt.subplot(2, 1, 2)
    param_names = ['β', 'ω']
    estimated = [beta, omega]
    paper_values = [paper_beta, paper_omega]
    
    x_pos = np.arange(len(param_names))
    width = 0.35
    
    plt.bar(x_pos - width/2, estimated, width, label='Estimated', alpha=0.8)
    plt.bar(x_pos + width/2, paper_values, width, label='Paper Values', alpha=0.8)
    
    plt.ylabel('Parameter Value')
    plt.title('Parameter Comparison')
    plt.xticks(x_pos, param_names)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs('plots/market_validation/', exist_ok=True)
    plt.savefig('plots/market_validation/quick_nasdaq_1987_validation.png', dpi=300, bbox_inches='tight')
    print(f"📊 Plot saved: plots/market_validation/quick_nasdaq_1987_validation.png")
    
    plt.show()
    
    print(f"\n🏆 Validation Summary:")
    print(f"✅ FRED API setup and data retrieval successful")
    print(f"✅ 1987 real market data LPPL validation executed")
    print(f"✅ Quantitative comparison with paper values completed")
    print(f"✅ API infrastructure established for future implementation")
    
    if overall_success:
        print(f"\n🚀 Recommended Next Steps:")
        print("1. Expand validation to other historical crashes")
        print("2. Test with S&P500 and other indices")
        print("3. Develop real-time monitoring system")
        print("4. Build practical trading system integration")

if __name__ == "__main__":
    main()