import os
import yfinance as yf
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats  # 
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from sklearn.metrics import r2_score, mean_squared_error
import pandas as pd
import json

#
from analysis_logger import AnalysisLogger, get_latest_analyses

def ensure_output_dir(dir_name='analysis_results/temp'):
    """出力ディレクトリが存在しない場合は作成"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name

def download_stock_data(symbol, start_date, end_date):
    """
    Yahoo Financeから株価データをダウンロード
    """
    stock = yf.download(symbol, start=start_date, end=end_date)
    return stock

def prepare_data(stock_data):
    """
    分析用にデータを準備
    """
    # 終値を使用
    prices = stock_data['Close'].values
    # 時間を数値インデックスに変換
    times = np.arange(len(prices))
    return times, prices

def log_periodic_function(t, tc, m, omega, phi, A, B, C):
    """
    対数周期関数のモデル
    """
    # tをnumpy配列に変換
    t = np.asarray(t)
    # dtが負になる部分を除外
    dt = tc - t
    mask = dt > 0
    result = np.zeros_like(t, dtype=float)
    result[mask] = A + B * dt[mask]**m + C * dt[mask]**m * np.cos(omega * np.log(dt[mask]) + phi)
    return result

def fit_log_periodic(time, price, tc_guess):
    """
    対数周期関数のフィッティング
    """
    # データを1次元配列に変換
    time = np.asarray(time).ravel()
    price = np.asarray(price).ravel()
    
    # 初期値を調整
    mean_price = np.mean(price)
    std_price = np.std(price)
    
    # パラメータの初期値
    p0 = [
        tc_guess,      # tc
        0.33,          # m
        6.28,          # omega
        0,             # phi
        mean_price,    # A
        -std_price/2,  # B
        std_price/4    # C
    ]
    
    # フィッティングの境界条件
    bounds = (
        [tc_guess-50, 0.01, 1, -np.pi, mean_price*0.5, -np.inf, -np.inf],
        [tc_guess+50, 0.99, 20, np.pi, mean_price*1.5, np.inf, np.inf]
    )
    
    try:
        # フィッティングの実行
        popt, pcov = curve_fit(
            log_periodic_function, 
            time, 
            price, 
            p0=p0,
            bounds=bounds,
            maxfev=10000,
            method='trf'  # trust region reflective algorithm
        )
        return popt, pcov
    except (RuntimeError, ValueError) as e:
        print(f"フィッティングエラー: {e}")
        return None, None

def analyze_stock(symbol, start_date, end_date, tc_guess_days=30):
    """
    株価の対数周期性分析を実行
    """
    # データのダウンロード
    print(f"{symbol}のデータをダウンロード中...")
    stock_data = download_stock_data(symbol, start_date, end_date)
    
    # データの準備
    times, prices = prepare_data(stock_data)
    
    # tc_guessを設定（現在のデータ長から指定日数後）
    tc_guess = len(times) + tc_guess_days
    
    # フィッティング実行
    print("対数周期性分析を実行中...")
    popt, pcov = fit_log_periodic(times, prices, tc_guess)
    
    if popt is not None:
        tc, m, omega, phi, A, B, C = popt
        
        # 結果の表示
        print("\n分析結果:")
        print(f"予測される臨界時点: データ終了から約{tc - len(times):.1f}日後")
        print(f"べき指数 (m): {m:.3f}")
        print(f"角振動数 (omega): {omega:.3f}")
        print(f"位相 (phi): {phi:.3f}")
        print(f"振幅パラメータ A: {A:.2f}")
        print(f"振幅パラメータ B: {B:.2f}")
        print(f"振幅パラメータ C: {C:.2f}")
        
        # フィッティング曲線の生成
        t_fit = np.linspace(min(times), tc-1, 1000)
        price_fit = log_periodic_function(t_fit, *popt)
        
        # プロット
        plt.figure(figsize=(15, 10))
        
        # 実データのプロット
        plt.plot(times, prices, 'ko', label='実データ', markersize=2)
        
        # フィッティング曲線のプロット
        plt.plot(t_fit, price_fit, 'r-', label='予測モデル')
        
        # 臨界時点の表示
        plt.axvline(x=tc, color='g', linestyle='--', label='予測される臨界時点')
        
        # 日付ラベルの設定
        dates = stock_data.index
        plt.xticks(
            [0, len(times)-1, tc], 
            [dates[0].strftime('%Y-%m-01'), 
             dates[-1].strftime('%Y-%m-%d'),
             (dates[-1] + timedelta(days=int(tc - len(times)))).strftime('%Y-%m-%d')],
            rotation=45
        )
        
        plt.xlabel('日付')
        plt.ylabel('価格')
        plt.title(f'{symbol}の対数周期性分析')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        # グラフを保存
        output_dir = ensure_output_dir(dir_name="analysis_results/plots")
        plt.savefig(os.path.join(output_dir, f'{symbol}_analysis.png'))
        plt.close()  # プロットを閉じる
        
        return popt, stock_data
    else:
        print("分析に失敗しました。")
        return None, stock_data

def validate_fit_quality(times, prices, popt, plot=True, symbol=None):
    """
    フィッティングの品質を評価
    """
    # 入力データを1次元配列に確実に変換
    times = np.asarray(times).ravel()
    prices = np.asarray(prices).ravel()
    
    # モデルによる予測値の計算
    predicted_prices = log_periodic_function(times, *popt)
    
    # 評価指標の計算
    r2 = r2_score(prices, predicted_prices)
    rmse = np.sqrt(mean_squared_error(prices, predicted_prices))
    
    # 残差の計算と1次元配列への変換
    residuals = (prices - predicted_prices).ravel()
    
    # 残差の正規性検定
    _, normality_p_value = stats.normaltest(residuals)
    
    # 残差から無限大やNaNを除去
    residuals = residuals[np.isfinite(residuals)]
    
    # 自己相関の計算（残差が空でないことを確認）
    if len(residuals) > 0:
        # 残差の分散が0でないことを確認
        variance = np.var(residuals)
        if variance > 0:
            autocorr = np.correlate(residuals, residuals, mode='full') / (len(residuals) * variance)
            autocorr = autocorr[len(autocorr)//2:]
        else:
            print("警告: 残差の分散が0です")
            autocorr = np.zeros(len(residuals))
    else:
        print("警告: 有効な残差データがありません")
        autocorr = np.array([])
    
    if plot:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 実データvs予測値プロット
        axes[0,0].scatter(prices, predicted_prices, alpha=0.5)
        axes[0,0].plot([min(prices), max(prices)], [min(prices), max(prices)], 'r--')
        axes[0,0].set_xlabel('実際の価格')
        axes[0,0].set_ylabel('予測価格')
        axes[0,0].set_title('実際の価格 vs 予測価格')
        
        # 2. 残差プロット
        axes[0,1].scatter(times, residuals, alpha=0.5)
        axes[0,1].axhline(y=0, color='r', linestyle='--')
        axes[0,1].set_xlabel('時間')
        axes[0,1].set_ylabel('残差')
        axes[0,1].set_title('残差の時系列プロット')
        
        # 3. 残差のヒストグラム
        if len(residuals) > 0:
            axes[1,0].hist(residuals, bins=30, density=True, alpha=0.7)
            xmin, xmax = axes[1,0].get_xlim()
            x = np.linspace(xmin, xmax, 100)
            axes[1,0].plot(x, stats.norm.pdf(x, np.mean(residuals), np.std(residuals)), 'r-', lw=2)
            axes[1,0].set_xlabel('残差')
            axes[1,0].set_ylabel('頻度')
            axes[1,0].set_title('残差の分布')
        
        # 4. 自己相関プロット
        if len(autocorr) > 0:
            lags = np.arange(len(autocorr))
            axes[1,1].plot(lags, autocorr)
            axes[1,1].axhline(y=0, color='r', linestyle='--')
            axes[1,1].axhline(y=1.96/np.sqrt(len(times)), color='r', linestyle=':')
            axes[1,1].axhline(y=-1.96/np.sqrt(len(times)), color='r', linestyle=':')
            axes[1,1].set_xlabel('ラグ')
            axes[1,1].set_ylabel('自己相関')
            axes[1,1].set_title('残差の自己相関')
        
        plt.tight_layout()
        
        
        # ファイルを保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'fit_quality_{symbol}_{timestamp}.png' if symbol else f'fit_quality_{timestamp}.png'
        
        output_dir = ensure_output_dir(dir_name="analysis_results/plots")
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()

    
    # 最大自己相関の計算（自己相関が存在する場合のみ）
    max_autocorr = np.max(np.abs(autocorr[1:])) if len(autocorr) > 1 else 0
    
    return {
        'R2': r2,
        'RMSE': rmse,
        'Residuals_normality_p': normality_p_value,
        'Max_autocorr': max_autocorr
    }

def check_stability(times, prices, window_size=30, step=5, data=None, symbol=None):
    """
    パラメータの安定性をチェック
    
    Parameters:
    -----------
    times : array-like
        時間データ
    prices : array-like
        価格データ
    window_size : int
        分析ウィンドウのサイズ（日数）
    step : int
        ウィンドウのスライド幅（日数）
    data : pandas.DataFrame
        元の株価データ（日付情報を取得するため）
    """
    tc_estimates = []
    windows = []
    
    for i in range(0, len(times) - window_size, step):
        window_times = times[i:i+window_size]
        window_prices = prices[i:i+window_size]
        
        tc_guess = window_times[-1] + 30
        
        try:
            popt, _ = fit_log_periodic(window_times, window_prices, tc_guess)
            if popt is not None:
                tc_estimates.append(popt[0])
                windows.append(window_times[-1])
        except:
            continue
    
    if tc_estimates:
        plt.figure(figsize=(12, 6))
        plt.plot(windows, tc_estimates, 'bo-')
        plt.xlabel('ウィンドウ終了時点')
        plt.ylabel('予測された臨界時点')
        plt.title('臨界時点予測の安定性分析')
        plt.grid(True)
        
        # グラフを保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stability_{symbol}_{timestamp}.png' if symbol else f'stability_{timestamp}.png'
        
        output_dir = ensure_output_dir(dir_name="analysis_results/plots")
        plt.savefig(os.path.join(output_dir, filename))
        plt.close() # プロットを閉じる
        
        # 安定性の指標を計算
        tc_std = np.std(tc_estimates)
        tc_mean = np.mean(tc_estimates)
        tc_cv = tc_std / tc_mean  # 変動係数
        
        print(f"\n安定性分析結果:")
        print(f"臨界時点の平均: {tc_mean:.2f}")
        print(f"臨界時点の標準偏差: {tc_std:.2f}")
        print(f"変動係数: {tc_cv:.3f}")
        
        # 日付での表示を追加
        if data is not None:
            mean_days_from_end = tc_mean - len(times)
            predicted_mean_date = data.index[-1] + timedelta(days=int(mean_days_from_end))
            print(f"予測される平均的な臨界時点の日付: {predicted_mean_date.strftime('%Y年%m月%d日')}")
            
            # 標準偏差を考慮した予測範囲
            earliest_date = predicted_mean_date - timedelta(days=int(tc_std))
            latest_date = predicted_mean_date + timedelta(days=int(tc_std))
            print(f"予測範囲: {earliest_date.strftime('%Y年%m月%d日')} ～ {latest_date.strftime('%Y年%m月%d日')}")
        
        return tc_mean, tc_std, tc_cv
    else:
        print("安定性分析に失敗しました。")
        return None, None, None



def enhanced_analyze_stock(symbol, start_date, end_date, tc_guess_days=30):
    """拡張された株価分析関数"""
    logger = AnalysisLogger()
   
    # 基本分析の実行
    results, data = analyze_stock(symbol, start_date, end_date, tc_guess_days)
   
    if results is not None:
        times, prices = prepare_data(data)
        
        # 各分析の実行にsymbolを渡す
        quality_metrics = validate_fit_quality(times, prices, results, symbol=symbol)
        tc_mean, tc_std, tc_cv = check_stability(times, prices, data=data, symbol=symbol)
        warning_level = evaluate_prediction(symbol, results, data)
        
        # プロット情報の記録を更新
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plots_info = {
            'main_analysis': f'{symbol}_analysis.png',
            'fit_quality': f'fit_quality_{symbol}_{timestamp}.png',
            'stability': f'stability_{symbol}_{timestamp}.png'
        }
        
        # 結果の保存
        analysis_id = logger.save_analysis_results(
            symbol, results, data, quality_metrics,
            (tc_mean, tc_std, tc_cv), warning_level,
            start_date, end_date, plots_info
        )
        
        # レポートの生成と表示
        print(logger.generate_report(analysis_id))
        
        return results, data, quality_metrics, (tc_mean, tc_std, tc_cv), warning_level
    
    return None, None, None, None, None

def evaluate_prediction(symbol, results, data, tc_threshold_days=30):
    """
    予測の評価と警告の生成
    """
    if results is None:
        print("予測の評価ができません：フィッティング結果がありません。")
        return
    
    tc, m, omega, phi, A, B, C = results
    current_time = len(data)
    days_to_tc = tc - current_time
    
    # 日付の計算
    last_date = data.index[-1]  # データの最終日
    predicted_date = last_date + timedelta(days=int(days_to_tc))
    
    print("\n予測評価:")
    print(f"予測された臨界時点までの日数: {days_to_tc:.1f}日")
    print(f"予測された臨界時点の日付: {predicted_date.strftime('%Y年%m月%d日')}")
    
    # 警告レベルの設定
    warning_level = "低"
    if days_to_tc < tc_threshold_days:
        if m > 0.5:
            warning_level = "高"
        else:
            warning_level = "中"
    
    print(f"警告レベル: {warning_level}")
    
    # パラメータの妥当性チェック
    print("\nパラメータ妥当性チェック:")
    if 0 < m < 1:
        print(f"✓ べき指数(m)は正常範囲内です: {m:.3f}")
    else:
        print(f"⚠️ べき指数(m)が通常範囲外です: {m:.3f}")
        
    if 2 < omega < 20:
        print(f"✓ 角振動数(omega)は正常範囲内です: {omega:.3f}")
    else:
        print(f"⚠️ 角振動数(omega)が通常範囲外です: {omega:.3f}")
    
    return warning_level


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
   
   results_df = pd.DataFrame()
   processed_count = len(progress['completed']) + len(progress['failed'])
   
   def show_progress():
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
               temp_df = analyze_single_market(symbol, time_windows, pd.DataFrame())
               if not temp_df.empty:
                   results_df = pd.concat([results_df, temp_df], ignore_index=True)
                   progress['completed'].append(symbol)
               else:
                   progress['failed'].append(symbol)
               
               processed_count += 1
               show_progress()
               
               with open(progress_file, 'w') as f:
                   json.dump(progress, f)
               results_df.to_csv('all_market_analysis_results.csv', index=False)
               
           except Exception as e:
               print(f"エラー ({symbol}): {str(e)}")
               progress['failed'].append(symbol)
               processed_count += 1
               show_progress()
               
               with open(progress_file, 'w') as f:
                   json.dump(progress, f)
               continue
   
   return results_df

def analyze_single_market(symbol, time_windows, results_df):
    """単一銘柄の分析"""
    for window in time_windows:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window)
        
        try:
            results, data, quality_metrics, stability_metrics, warning_level = \
                enhanced_analyze_stock(symbol, start_date, end_date)
            
            if results is not None and quality_metrics is not None:
                tc, m, omega, phi, A, B, C = results
                
                temp_df = pd.DataFrame({
                    'symbol': [symbol],
                    'window_days': [window],
                    'analysis_date': [end_date.strftime('%Y-%m-%d')],
                    'warning_level': [warning_level],
                    'days_to_tc': [tc - len(data)],
                    'R2': [quality_metrics['R2']],
                    'tc_cv': [stability_metrics[2] if stability_metrics[2] is not None else None],
                    'm': [m],
                    'omega': [omega],
                    'predicted_date': [(end_date + timedelta(days=int(tc - len(data)))).strftime('%Y-%m-%d')]
                })
                
                results_df = pd.concat([results_df, temp_df], ignore_index=True)
                
        except Exception as e:
            print(f"エラー ({symbol}, {window}日): {str(e)}")
    
    return results_df

if __name__ == "__main__":
    results = analyze_markets_from_json()
    
    # 重要な銘柄のピックアップ
    critical_events = results[
        (results['warning_level'] == '高') & 
        (results['R2'] >= 0.8) &
        (results['tc_cv'] <= 0.1)
    ]
    
    if not critical_events.empty:
        print("\n=== 注目すべき市場変動の可能性 ===")
        print(critical_events[['symbol', 'window_days', 'predicted_date', 'R2']].to_string())