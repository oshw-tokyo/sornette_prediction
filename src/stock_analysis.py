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

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import warnings
import logging

from src.analysis_logger import AnalysisLogger


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FittingParameters:
    """Sornette model fitting parameters with theoretical constraints"""
    
    # Theoretical constraints
    Z_MIN: float = 0.0
    Z_MAX: float = 1.0
    Z_TYPICAL_MIN: float = 0.33
    Z_TYPICAL_MAX: float = 0.68
    
    OMEGA_MIN: float = 5.0
    OMEGA_MAX: float = 8.0
    
    # Fitting quality thresholds
    MAX_RESIDUAL: float = 1.0  # Maximum acceptable residual for good fit
    MIN_R_SQUARED: float = 0.95  # Minimum R-squared for acceptable fit # Initially 0.95
    
    @classmethod
    def validate_parameters(cls, z: float, omega: float) -> Tuple[bool, Optional[str]]:
        """
        Validate if parameters are within theoretical constraints
        
        Args:
            z: Power law exponent
            omega: Log-periodic angular frequency
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not cls.Z_MIN < z < cls.Z_MAX:
            return False, f"z parameter {z} outside theoretical range ({cls.Z_MIN}, {cls.Z_MAX})"
            
        if not cls.OMEGA_MIN <= omega <= cls.OMEGA_MAX:
            return False, f"omega parameter {omega} outside typical range ({cls.OMEGA_MIN}, {cls.OMEGA_MAX})"
            
        return True, None
    
    @classmethod
    def is_typical_range(cls, z: float, omega: float) -> Tuple[bool, Optional[str]]:
        """
        Check if parameters are within typical ranges observed in empirical studies
        
        Args:
            z: Power law exponent
            omega: Log-periodic angular frequency
            
        Returns:
            Tuple of (is_typical: bool, message: Optional[str])
        """
        if not cls.Z_TYPICAL_MIN <= z <= cls.Z_TYPICAL_MAX:
            return False, f"z parameter {z} outside typical range ({cls.Z_TYPICAL_MIN}, {cls.Z_TYPICAL_MAX})"
            
        if not cls.OMEGA_MIN <= omega <= cls.OMEGA_MAX:
            return False, f"omega parameter {omega} outside typical range ({cls.OMEGA_MIN}, {cls.OMEGA_MAX})"
            
        return True, None

    @classmethod
    def get_parameter_ranges(cls) -> dict:
        """
        Get the recommended parameter ranges for fitting
        
        Returns:
            Dictionary containing parameter ranges
        """
        return {
            'z': {
                'min': cls.Z_MIN,
                'max': cls.Z_MAX,
                'typical_min': cls.Z_TYPICAL_MIN,
                'typical_max': cls.Z_TYPICAL_MAX
            },
            'omega': {
                'min': cls.OMEGA_MIN,
                'max': cls.OMEGA_MAX
            }
        }
#


@dataclass
class FittingResult:
    """フィッティング結果を格納するデータクラス"""
    success: bool
    parameters: Dict[str, float]
    residuals: float
    r_squared: float
    error_message: Optional[str] = None
    is_typical_range: bool = False

class LogPeriodicFitter:
    """対数周期性のフィッティングを行うクラス"""
    
    def __init__(self):
        self.params = FittingParameters()
        
    @staticmethod
    def log_periodic_func(t: np.ndarray, tc: float, m: float, omega: float, 
                         phi: float, A: float, B: float, C: float) -> np.ndarray:
        """対数周期関数のモデル"""
        dt = tc - t
        return A + B * np.power(dt, m) * (1 + C * np.cos(omega * np.log(dt) + phi))

    def fit_log_periodic(self, t: np.ndarray, y: np.ndarray, 
                        initial_params: Optional[Dict[str, float]] = None) -> FittingResult:
        """対数周期関数のフィッティングを実行"""
        # デバッグ出力を追加
        logger.info(f"Starting fit with data shape: t={t.shape}, y={y.shape}")
        
        # データの検証
        if len(t) == 0 or len(y) == 0:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message="Empty input data"
            )
        
        if len(t) != len(y):
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message="Input arrays must have the same length"
            )
        
        # デフォルトの初期パラメータ
        default_params = {
            'tc': t[-1] + (t[-1] - t[0]) * 0.1,
            'm': 0.45,
            'omega': 6.5,
            'phi': 0,
            'A': np.mean(y),
            'B': (y[-1] - y[0]) / (t[-1] - t[0]),
            'C': 0.1
        }
        
        # 初期パラメータの設定
        params = {**default_params, **(initial_params or {})}
        logger.info(f"Initial parameters: {params}")
        
        try:
            # 境界条件の調整
            bounds = (
                [t[-1], self.params.Z_MIN, self.params.OMEGA_MIN, -2*np.pi, -np.inf, -np.inf, -0.5],  # Cの下限を調整
                [t[-1] + (t[-1] - t[0])*0.5, self.params.Z_MAX, self.params.OMEGA_MAX, 2*np.pi, np.inf, np.inf, 0.5]   # Cの上限を調整
            )
            logger.info(f"Bounds: {bounds}")

            # フィッティングの実行
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                popt, pcov = curve_fit(
                    self.log_periodic_func, t, y,
                    p0=[params['tc'], params['m'], params['omega'], 
                        params['phi'], params['A'], params['B'], params['C']],
                    bounds=bounds,
                    maxfev=50000,
                    ftol=1e-8,
                    xtol=1e-8,
                    method='trf'
                )
            
            # フィッティング結果のパラメータを取得
            fitted_params = {
                'tc': popt[0], 'm': popt[1], 'omega': popt[2],
                'phi': popt[3], 'A': popt[4], 'B': popt[5], 'C': popt[6]
            }
            logger.info(f"Fitted parameters: {fitted_params}")
            
            # パラメータの検証
            is_valid, error_msg = self.params.validate_parameters(
                z=fitted_params['m'], 
                omega=fitted_params['omega']
            )
            
            if not is_valid:
                logger.warning(f"Parameter validation failed: {error_msg}")
                return FittingResult(
                    success=False,
                    parameters=fitted_params,
                    residuals=np.inf,
                    r_squared=0,
                    error_message=error_msg
                )
            
            # フィッティング品質の評価
            y_fit = self.log_periodic_func(t, *popt)
            residuals = np.mean((y - y_fit) ** 2)
            r_squared = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - np.mean(y)) ** 2)
            logger.info(f"Fit quality: residuals={residuals}, R²={r_squared}")
            
            # 品質チェックの閾値を調整
            if residuals > self.params.MAX_RESIDUAL or r_squared < self.params.MIN_R_SQUARED:
                logger.warning(f"Poor fit quality: residuals={residuals}, R²={r_squared}")
                return FittingResult(
                    success=False,
                    parameters=fitted_params,
                    residuals=residuals,
                    r_squared=r_squared,
                    error_message="Poor fit quality"
                )
            
            # 典型的な範囲内かどうかのチェック
            is_typical, _ = self.params.is_typical_range(
                z=fitted_params['m'], 
                omega=fitted_params['omega']
            )
            
            return FittingResult(
                success=True,
                parameters=fitted_params,
                residuals=residuals,
                r_squared=r_squared,
                is_typical_range=is_typical
            )
                
        except Exception as e:
            logger.error(f"Fitting failed: {str(e)}")
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                error_message=str(e)
            )

    def fit_with_multiple_initializations(self, t: np.ndarray, y: np.ndarray, 
                                        n_tries: int = 5) -> FittingResult:
        """
        複数の初期値でフィッティングを試行し、最良の結果を返す
        
        Args:
            t: 時間データ
            y: 価格データ
            n_tries: 試行回数
            
        Returns:
            FittingResult: 最良のフィッティング結果
        """
        best_result = FittingResult(success=False, parameters={}, residuals=np.inf, r_squared=0)
        
        for i in range(n_tries):
            # ランダムな初期パラメータの生成
            initial_params = {
                'tc': t[-1] + (t[-1] - t[0]) * np.random.uniform(0.05, 0.15),
                'm': np.random.uniform(self.params.Z_TYPICAL_MIN, self.params.Z_TYPICAL_MAX),
                'omega': np.random.uniform(self.params.OMEGA_MIN, self.params.OMEGA_MAX),
                'phi': np.random.uniform(-np.pi, np.pi),
                'A': np.mean(y) + np.random.normal(0, np.std(y) * 0.1),
                'B': (y[-1] - y[0]) / (t[-1] - t[0]) * (1 + np.random.normal(0, 0.1)),
                'C': np.random.uniform(0.05, 0.15)
            }
            
            result = self.fit_log_periodic(t, y, initial_params)
            
            if result.success and result.residuals < best_result.residuals:
                best_result = result
                
        return best_result

def ensure_output_dir(dir_name='analysis_results/temp'):
    """出力ディレクトリが存在しない場合は作成"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name

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
    
    # LogPeriodicFitterのインスタンス化
    fitter = LogPeriodicFitter()
    
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

def plot_fitting_results(times, prices, fitting_result, symbol, stock_data):
    """フィッティング結果をプロット"""
    tc = fitting_result.parameters['tc']
    
    # フィッティング曲線の生成
    t_fit = np.linspace(min(times), tc-1, 1000)
    price_fit = LogPeriodicFitter.log_periodic_func(
        t_fit, 
        tc=fitting_result.parameters['tc'],
        m=fitting_result.parameters['m'],
        omega=fitting_result.parameters['omega'],
        phi=fitting_result.parameters['phi'],
        A=fitting_result.parameters['A'],
        B=fitting_result.parameters['B'],
        C=fitting_result.parameters['C']
    )
    
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
    plt.close()

def plot_stability_analysis(windows, tc_estimates, symbol):
    """
    安定性分析の結果をプロット

    Parameters:
    -----------
    windows : array-like
        分析ウィンドウの終了時点
    tc_estimates : array-like
        各ウィンドウでの臨界時点の予測値
    symbol : str
        分析対象の銘柄コード
    """
    plt.figure(figsize=(12, 6))
    
    # メインのプロット
    plt.plot(windows, tc_estimates, 'bo-', label='臨界時点予測', markersize=4)
    
    # 平均値と標準偏差の範囲を表示
    tc_mean = np.mean(tc_estimates)
    tc_std = np.std(tc_estimates)
    plt.axhline(y=tc_mean, color='r', linestyle='--', label='平均値')
    plt.fill_between(windows, 
                    tc_mean - tc_std, tc_mean + tc_std, 
                    color='r', alpha=0.2, label='±1標準偏差')
    
    # プロットの装飾
    plt.xlabel('ウィンドウ終了時点（データポイント）')
    plt.ylabel('予測された臨界時点（データポイント）')
    plt.title(f'{symbol} - 臨界時点予測の安定性分析')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # y軸の範囲を適切に設定
    y_margin = tc_std * 2
    plt.ylim(min(tc_estimates) - y_margin, max(tc_estimates) + y_margin)
    
    # 変動係数（CV）を計算して表示
    cv = tc_std / tc_mean if tc_mean != 0 else float('inf')
    plt.text(0.02, 0.98, 
             f'変動係数 (CV): {cv:.3f}\n標準偏差: {tc_std:.1f}',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # グラフを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = ensure_output_dir(dir_name="analysis_results/plots")
    plt.savefig(os.path.join(output_dir, f'stability_{symbol}_{timestamp}.png'))
    plt.close()

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
    

    Returns:
    --------
    tuple:
        (tc_mean, tc_std, tc_cv, window_consistency)

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

        # 時間窓での一貫性を計算
        window_consistency = max(0, 1 - 2 * tc_cv) if tc_cv is not None else 0
        
        print(f"\n安定性分析結果:")
        print(f"臨界時点の平均: {tc_mean:.2f}")
        print(f"臨界時点の標準偏差: {tc_std:.2f}")
        print(f"変動係数: {tc_cv:.3f}")
        print(f"予測一貫性: {window_consistency:.3f}") 
        
        # 日付での表示を追加
        if data is not None:
            mean_days_from_end = tc_mean - len(times)
            predicted_mean_date = data.index[-1] + timedelta(days=int(mean_days_from_end))
            print(f"予測される平均的な臨界時点の日付: {predicted_mean_date.strftime('%Y年%m月%d日')}")
            
            # 標準偏差を考慮した予測範囲
            earliest_date = predicted_mean_date - timedelta(days=int(tc_std))
            latest_date = predicted_mean_date + timedelta(days=int(tc_std))
            print(f"予測範囲: {earliest_date.strftime('%Y年%m月%d日')} ～ {latest_date.strftime('%Y年%m月%d日')}")
        
        return tc_mean, tc_std, tc_cv, window_consistency
    else:
        print("安定性分析に失敗しました。")
        return None, None, None, None


def enhanced_analyze_stock(symbol, start_date, end_date, tc_guess_days=30):
    """拡張された株価分析関数 - 新しいフィッティングクラスを使用"""
    logger = AnalysisLogger()
   
    # 基本分析の実行
    fitting_result, data = analyze_stock(symbol, start_date, end_date, tc_guess_days)
   
    if fitting_result is not None and fitting_result.success:
        times, prices = prepare_data(data)
        
        # フィッティング品質の評価
        quality_metrics = {
            'R2': fitting_result.r_squared,
            'RMSE': np.sqrt(fitting_result.residuals),
            'Residuals_normality_p': stats.normaltest(
                prices - LogPeriodicFitter.log_periodic_func(
                    times,
                    **fitting_result.parameters
                )
            )[1],
            'Max_autocorr': calculate_max_autocorr(
                prices - LogPeriodicFitter.log_periodic_func(
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
            fitter=LogPeriodicFitter()
        )
        
        # プロット情報の記録を更新
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plots_info = {
            'main_analysis': f'{symbol}_analysis.png',
            'fit_quality': f'fit_quality_{symbol}_{timestamp}.png',
            'stability': f'stability_{symbol}_{timestamp}.png'
        }
        
        # 結果の保存
        analysis_id = logger.save_analysis_results(
            symbol,
            fitting_result.parameters,
            data,
            quality_metrics,
            stability_metrics,
            start_date,
            end_date,
            plots_info
        )
        
        # レポートの生成と表示
        print(logger.generate_report(analysis_id))
        
        return fitting_result.parameters, data, quality_metrics, stability_metrics
    
    return None, None, None, None

def analyze_stability(times, prices, data, symbol, fitter, 
                     window_size=30, step=5):
    """
    パラメータの安定性を分析する拡張関数
    """
    tc_estimates = []
    windows = []
    
    for i in range(0, len(times) - window_size, step):
        window_times = times[i:i+window_size]
        window_prices = prices[i:i+window_size]
        
        try:
            # 各ウィンドウで複数回フィッティングを試行
            fitting_result = fitter.fit_with_multiple_initializations(
                window_times,
                window_prices,
                n_tries=3  # ウィンドウ解析では試行回数を減らして処理時間を短縮
            )
            
            if fitting_result.success:
                tc_estimates.append(fitting_result.parameters['tc'])
                windows.append(window_times[-1])
        except Exception as e:
            logger.error(f"Window analysis failed: {str(e)}")
            continue
    
    if tc_estimates:
        # 安定性の視覚化
        plot_stability_analysis(windows, tc_estimates, symbol)
        
        # 安定性指標の計算
        tc_std = np.std(tc_estimates)
        tc_mean = np.mean(tc_estimates)
        tc_cv = tc_std / tc_mean if tc_mean != 0 else float('inf')
        window_consistency = max(0, 1 - 2 * tc_cv)
        
        print(f"\n安定性分析結果:")
        print(f"臨界時点の平均: {tc_mean:.2f}")
        print(f"臨界時点の標準偏差: {tc_std:.2f}")
        print(f"変動係数: {tc_cv:.3f}")
        print(f"予測一貫性: {window_consistency:.3f}")
        
        # 日付での予測範囲の表示
        if data is not None:
            mean_days_from_end = tc_mean - len(times)
            predicted_mean_date = data.index[-1] + timedelta(days=int(mean_days_from_end))
            earliest_date = predicted_mean_date - timedelta(days=int(tc_std))
            latest_date = predicted_mean_date + timedelta(days=int(tc_std))
            
            print(f"予測される平均的な臨界時点: {predicted_mean_date.strftime('%Y年%m月%d日')}")
            print(f"予測範囲: {earliest_date.strftime('%Y年%m月%d日')} ～ "
                  f"{latest_date.strftime('%Y年%m月%d日')}")
        
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

if __name__ == "__main__":
    analyze_markets_from_json(json_file='market_symbols_for_test.json')
    
    
