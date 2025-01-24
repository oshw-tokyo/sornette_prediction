from ..fitting.fitter import LogarithmPeriodicFitter
from ..fitting.parameters import FittingParameterManager
from ..visualization.plots import plot_fitting_results
from ..visualization.plots import plot_stability_analysis

import yfinance as yf
import numpy as np
from scipy import stats  

from datetime import datetime, timedelta
import json


def analyze_markets_from_json(json_file='market_symbols.json', time_windows=[180, 365, 730]):
    """保存された銘柄リストを使用して市場分析を実行"""
    progress_file = 'analysis_progress.json'
    
    # 進捗状況の読み込み
    try:
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    except FileNotFoundError:
        progress = {'completed': [], 'failed': [], 'start_time': None}
    
    # 開始時刻の記録
    if not progress.get('start_time'):
        progress['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(json_file, 'r') as f:
        markets = json.load(f)
    
    # 全銘柄数の計算
    total_symbols = len(markets['japan']) + len(markets['us']) + \
                   sum(len(symbols) for symbols in markets['indices'].values())
    
    # processed_countを初期化
    processed_count = len(progress['completed']) + len(progress['failed'])
    
    def show_progress(processed_count):
        """進捗状況を表示"""
        current_time = datetime.now()
        start_time = datetime.strptime(progress['start_time'], '%Y-%m-%d %H:%M:%S')
        elapsed_time = current_time - start_time
        
        if processed_count > 0:
            avg_time_per_symbol = elapsed_time / processed_count
            remaining_symbols = total_symbols - processed_count
            estimated_remaining_time = avg_time_per_symbol * remaining_symbols
            
            print(f"\n進捗状況:")
            print(f"完了: {len(progress['completed'])} 失敗: {len(progress['failed'])}")
            print(f"進捗率: {processed_count/total_symbols*100:.1f}% ({processed_count}/{total_symbols})")
            print(f"経過時間: {str(elapsed_time).split('.')[0]}")
            print(f"予想残り時間: {str(estimated_remaining_time).split('.')[0]}")

    for category in ['japan', 'us', 'indices']:
        if category == 'indices':
            symbols = [s for region in markets[category].values() for s in region]
        else:
            symbols = markets[category]
        
        print(f"\n=== {category}市場の分析 ===")
        for symbol in symbols:
            if symbol in progress['completed']:
                processed_count += 1
                continue
            
            try:
                analyze_single_market(symbol, time_windows)
                progress['completed'].append(symbol)
            except Exception as e:
                print(f"エラー ({symbol}): {str(e)}")
                progress['failed'].append(symbol)
                
            processed_count += 1
            show_progress(processed_count)
            
            # 進捗の保存
            with open(progress_file, 'w') as f:
                json.dump(progress, f)

def analyze_single_market(symbol, time_windows):
    """単一銘柄の分析"""
    for window in time_windows:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window)
        
        try:
            print(f"\n分析開始: {symbol} (期間: {window}日)")
            results, data, quality_metrics, stability_metrics = \
                enhanced_analyze_stock(symbol, start_date, end_date)
            
            if results is not None and quality_metrics is not None and data is not None:
                print(f"分析完了: {symbol} (期間: {window}日)")
                
        except Exception as e:
            print(f"エラー ({symbol}, {window}日): {str(e)}")
            continue


def analyze_stock(symbol, start_date, end_date, tc_guess_days=30):
    """
    株価の対数周期性分析を実行（新しいフィッティングクラスを使用）
    """
    # データのダウンロード
    print(f"{symbol}のデータをダウンロード中...")
    stock_data = download_stock_data(symbol, start_date, end_date)
    
    if stock_data is None:
        print(f"{symbol}のデータ取得に失敗しました。")
        return None, None
    
    # データの準備
    times, prices = prepare_data(stock_data)
    
    # LogarithmPeriodicFitterのインスタンス化
    fitter = LogarithmPeriodicFitter()
    
    # 複数の初期値でフィッティングを実行
    print("対数周期性分析を実行中...")
    fitting_result = fitter.fit_with_multiple_initializations(times, prices, n_tries=5)
    
    if fitting_result.success:
        # 結果のプロット
        plot_fitting_results(times, prices, fitting_result, symbol, stock_data)
        
        # 結果の表示
        print("\n分析結果:")
        print(f"予測される臨界時点: データ終了から約{fitting_result.parameters['tc'] - len(times):.1f}日後")
        print(f"べき指数 (m): {fitting_result.parameters['m']:.3f}")
        print(f"角振動数 (omega): {fitting_result.parameters['omega']:.3f}")
        print(f"位相 (phi): {fitting_result.parameters['phi']:.3f}")
        print(f"R-squared: {fitting_result.r_squared:.3f}")
        print(f"残差: {fitting_result.residuals:.3f}")
        print(f"典型的な範囲内: {'はい' if fitting_result.is_typical_range else 'いいえ'}")
        
        return fitting_result, stock_data
    else:
        print(f"分析に失敗しました: {fitting_result.error_message}")
        return None, stock_data

def download_stock_data(symbol, start_date, end_date):
    """
    Yahoo Financeから株価データをダウンロード
    """
    try:
        stock = yf.download(symbol, start=start_date, end=end_date)
        if stock.empty:
            print(f"警告: {symbol}のデータが空です。")
            return None
        return stock
    except Exception as e:
        print(f"警告: {symbol}のダウンロードに失敗しました: {str(e)}")
        return None

def prepare_data(stock_data):
    """
    分析用にデータを準備
    """
    # 終値を使用
    prices = stock_data['Close'].values
    # 時間を数値インデックスに変換
    times = np.arange(len(prices))
    return times, prices




def enhanced_analyze_stock(symbol, start_date, end_date, tc_guess_days=30):
    """拡張された株価分析関数 - 新しいフィッティングクラスを使用"""
   
    # 基本分析の実行
    fitting_result, data = analyze_stock(symbol, start_date, end_date, tc_guess_days)
   
    if fitting_result is not None and fitting_result.success:
        times, prices = prepare_data(data)
        
        # フィッティング品質の評価
        quality_metrics = {
            'R2': fitting_result.r_squared,
            'RMSE': np.sqrt(fitting_result.residuals),
            'Residuals_normality_p': stats.normaltest(
                prices - LogarithmPeriodicFitter.logarithm_periodic_func(
                    times,
                    **fitting_result.parameters
                )
            )[1],
            'Max_autocorr': calculate_max_autocorr(
                prices - LogarithmPeriodicFitter.logarithm_periodic_func(
                    times,
                    **fitting_result.parameters
                )
            )
        }
        
        # 安定性分析の実行
        stability_metrics = analyze_stability(
            times, 
            prices, 
            data=data, 
            symbol=symbol,
            fitter=LogarithmPeriodicFitter()
        )
        
        # プロット情報の記録を更新
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plots_info = {
            'main_analysis': f'{symbol}_analysis.png',
            'fit_quality': f'fit_quality_{symbol}_{timestamp}.png',
            'stability': f'stability_{symbol}_{timestamp}.png'
        }
        
        # 結果の保存
        print(
            symbol,
            fitting_result.parameters,
            data,
            quality_metrics,
            stability_metrics,
            start_date,
            end_date,
            plots_info
        )
        
       
        return fitting_result.parameters, data, quality_metrics, stability_metrics
    
    return None, None, None, None

def analyze_stability(times, prices, data, symbol, fitter, 
                     window_size=30, step=5):
    """パラメータの安定性を分析する拡張関数"""
    tc_estimates = []
    windows = []
    
    for i in range(0, len(times) - window_size, step):
        window_times = times[i:i+window_size]
        window_prices = prices[i:i+window_size]
        
        try:
            fitting_result = fitter.fit_with_multiple_initializations(
                window_times,
                window_prices,
                n_tries=3
            )
            
            if fitting_result.success:
                tc_estimates.append(fitting_result.parameters['tc'])
                windows.append(window_times[-1])
                print(
                    symbol=symbol,
                    window_index=i,
                    success=True,
                    metrics={'tc': fitting_result.parameters['tc']}
                )
        except Exception as e:
            print(
                symbol=symbol,
                window_index=i,
                error=e
            )
            continue
    
    if tc_estimates:
        plot_stability_analysis(windows, tc_estimates, symbol)
        
        tc_std = np.std(tc_estimates)
        tc_mean = np.mean(tc_estimates)
        tc_cv = tc_std / tc_mean if tc_mean != 0 else float('inf')
        window_consistency = max(0, 1 - 2 * tc_cv)
        
        date_range = None
        if data is not None:
            mean_days_from_end = tc_mean - len(times)
            predicted_mean_date = data.index[-1] + timedelta(days=int(mean_days_from_end))
            earliest_date = predicted_mean_date - timedelta(days=int(tc_std))
            latest_date = predicted_mean_date + timedelta(days=int(tc_std))
            date_range = (predicted_mean_date, earliest_date, latest_date)
        
        print(
            symbol=symbol,
            tc_mean=tc_mean,
            tc_std=tc_std,
            tc_cv=tc_cv,
            window_consistency=window_consistency,
            date_range=date_range
        )
        
        return tc_mean, tc_std, tc_cv, window_consistency
    
    return None, None, None, None

def calculate_max_autocorr(residuals, max_lag=30):
    """残差の最大自己相関を計算"""
    residuals = residuals[np.isfinite(residuals)]
    if len(residuals) == 0:
        return 0.0
    
    variance = np.var(residuals)
    if variance <= 0:
        return 0.0
    
    autocorr = np.correlate(residuals, residuals, mode='full') / (len(residuals) * variance)
    autocorr = autocorr[len(autocorr)//2:]
    
    return np.max(np.abs(autocorr[1:min(max_lag+1, len(autocorr))]))


if __name__ == "__main__":
    analyze_markets_from_json(json_file='market_symbols_for_test.json')
