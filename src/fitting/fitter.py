import numpy as np
from scipy.optimize import curve_fit
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from .utils import (power_law_func, logarithm_periodic_func, 
                   assess_statistical_significance, calculate_fit_metrics)

@dataclass
class FittingResult:
    """フィッティング結果を格納するデータクラス"""
    success: bool
    parameters: Dict[str, float]
    residuals: float
    r_squared: float
    statistical_significance: Dict
    error_message: Optional[str] = None
    is_typical_range: bool = False

class LogarithmPeriodicFitter:
    """Critical Market Crashes の式(54)に基づく対数周期性フィッティング"""
    
    def prepare_data(self, prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """データの前処理"""
        try:
            log_prices = np.log(prices)
            normalized_log_prices = log_prices - log_prices[0]
            t = np.linspace(0, 1, len(prices))
            
            return t, normalized_log_prices
            
        except Exception as e:
            print(f"ERROR: Data preparation failed: {str(e)}")
            return None, None
        
    def fit_with_multiple_initializations(self, t: np.ndarray, y: np.ndarray, n_tries: int = 10) -> FittingResult:
        """複数の初期値で最適なフィッティングを試みる"""
        best_result = None
        best_r2 = -np.inf
        failed_attempts = 0     

        # グリッドベースの初期値の生成
        tc_values = np.linspace(1.01, 1.2, n_tries)
        beta_values = np.linspace(0.30, 0.36, n_tries)
        
        print(f"\nStarting multiple initialization fitting with {n_tries} tries...")
        
        for i, (tc, beta) in enumerate(zip(tc_values, beta_values)):
            try:
                # べき乗則フィット
                power_result = self.fit_power_law(t, y, initial_params={
                    'tc': tc, 
                    'beta': beta,
                    'A': np.log(np.mean(y)),
                    'B': (y[-1]-y[0])/(t[-1]-t[0])
                })
                
                if power_result.success:
                    # 対数周期フィット
                    result = self.fit_logarithm_periodic(t, y, power_result.parameters)
                    
                    if result.success and result.r_squared > best_r2:
                        best_r2 = result.r_squared
                        best_result = result
                        print(f"Trial {i+1}/{n_tries}:")
                        print(f"  tc={result.parameters['tc']:.4f}")
                        print(f"  beta={result.parameters['beta']:.4f}")
                        print(f"  R2={result.r_squared:.4f}")
            
            except Exception as e:
                failed_attempts += 1
                print(f"Trial {i+1} failed: {str(e)}")
                continue
        
        if best_result is None:
            raise ValueError(f"All fitting attempts failed ({failed_attempts}/{n_tries} failures)")
            
        return best_result

    def fit_power_law(self, t: np.ndarray, y: np.ndarray, initial_params: dict = None) -> FittingResult:
        """べき乗則フィッティング（初期値を指定可能に修正）"""
        try:

            # データのシェイプを統一
            t = np.asarray(t).ravel()
            y = np.asarray(y).ravel()

            # 入力データの情報を出力
            print("\nPower Law Fitting Analysis:")
            print("---------------------------")
            print(f"Input check:")
            print(f"t shape: {t.shape}, y shape: {y.shape}")
            print(f"t range: [{t.min():.3f}, {t.max():.3f}]")
            print(f"y range: [{y.min():.3f}, {y.max():.3f}]")

            # データの有効性チェック
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                raise ValueError("Invalid values in data")

            # 初期値の設定 - Aについては対数空間で設定（補足：価格に対数を取るケース想定）
            if initial_params is None:
                p0 = [
                    1.2,    # tc (critical time): クリティカル時刻。観測期間(t∈[0,1])の直後を初期値に
                    0.45,   # β (beta): べき指数。論文で報告される典型値0.3-0.7の中央値を初期値に
                    np.log(np.mean(y)),  # log(A): オフセットパラメータ。データの平均値の対数を初期値に 
                    (y[-1]-y[0])/(t[-1]-t[0])  # B: スケールパラメータ。データの全体的な傾きを初期値に
                ]
            else:
                p0 = [
                    initial_params['tc'],
                    initial_params['beta'],
                    initial_params['A'],
                    initial_params['B']
                ]            
            
            print("\nInitial parameter values:")
            print(f"tc (critical time): {p0[0]:.3f}")
            print(f"beta (power law exponent): {p0[1]:.3f}")
            print(f"log(A) (log offset): {p0[2]:.3f}")
            print(f"B (scale parameter): {p0[3]:.3f}")            

            ## 境界の設定
            ## 補足：価格に対数を取るケース想定（対数を取らない場合も適用可）
            #
            # tc: 変更なし（時間に関するパラメータのため）
            #
            # β:
            #     通常価格: 通常0.3-0.7程度
            #     対数価格: より広い範囲（0.1-1.0）を許容可能
            #
            # A,B:
            #     通常価格: 価格スケールに依存
            #     対数価格: スケールフリー

            bounds = (
            [
                1.01,   # tc_min: クリティカル時刻は観測期間(t∈[0,1])より後
                0.1,    # β_min: べき指数は正（対数価格の場合は0.1程度まで許容）
                -np.inf, # A_min: オフセットパラメータに制限なし
                -np.inf  # B_min: スケールパラメータに制限なし
            ],
            [
                2.5,    # tc_max: 観測期間の2倍程度まで
                0.99,    # β_max: べき指数は1以下（対数価格では発散を防ぐ）
                np.inf,  # A_max: オフセットパラメータに制限なし
                np.inf   # B_max: スケールパラメータに制限なし
            ]
            )

            print("\nParameter bounds:")
            print(f"tc: [{bounds[0][0]:.3f}, {bounds[1][0]:.3f}]")
            print(f"beta: [{bounds[0][1]:.3f}, {bounds[1][1]:.3f}]")
            print("log(A): [-inf, inf]")
            print("B: [-inf, inf]")            

            # フィッティングの実行
            popt, pcov = curve_fit(
                            f=power_law_func,
                            xdata=t,
                            ydata=y,
                            p0=p0,
                            bounds=bounds,
                            method='trf',           # 境界のある最適化に適している
                            ftol=1e-4,             # 関数値の収束判定基準
                            xtol=1e-4,             # パラメータの収束判定基準
                            gtol=1e-4,             # 勾配の収束判定基準
                            loss='soft_l1',        # 外れ値に対してロバスト
                            max_nfev=50000,        # 最大反復回数
                        )
                        # = curve_fit(power_law_func, t, y, p0=p0, bounds=bounds, maxfev=10000, method='trf')

            # パラメータの不確かさを計算
            perr = np.sqrt(np.diag(pcov))

            # フィッティング結果の詳細な出力
            print("\nFitted parameters:")
            print(f"tc (critical time) = {popt[0]:.6f} ± {perr[0]:.6f}")
            print(f"beta (power law exponent) = {popt[1]:.6f} ± {perr[1]:.6f}")
            print(f"log(A)  = {popt[2]:.6f} ± {perr[2]:.6f}")
            print(f"A (offset) = {np.exp(popt[2]):.6f} ± {np.exp(popt[2])*perr[2]:.6f}")            
            print(f"B (scale) = {popt[3]:.6f} ± {perr[3]:.6f}")
            
            # フィッティング品質の評価
            y_fit = power_law_func(t, *popt)
            residuals, r_squared = calculate_fit_metrics(y, y_fit)

            print("\nFitting quality metrics:")
            print(f"R-squared: {r_squared:.6f}")
            print(f"Residuals (MSE): {residuals:.6e}")
            print("---------------------------\n")

            if r_squared < 0.6:  # この閾値は調整可能
                raise ValueError(f"Poor fit quality (R2={r_squared:.3f})")            

            return FittingResult(
                success=True,
                parameters={'tc': popt[0], 'beta': popt[1], 
                            'A': np.exp(popt[2]), 'B': popt[3]},
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=assess_statistical_significance(y, y_fit)
            )
            
        except Exception as e:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    def fit_logarithm_periodic(self, t: np.ndarray, y: np.ndarray, 
                             power_law_params: Dict[str, float]) -> FittingResult:
        """第2段階: 対数周期項を含む完全なフィッティング"""
        try:
            t = np.asarray(t).ravel()
            y = np.asarray(y).ravel()
            
            # べき乗則フィットの残差を計算
            y_power = power_law_func(t, **power_law_params)
            residuals = y - y_power
            
            # デバッグ情報
            print(f"Power law residuals range: [{residuals.min():.3e}, {residuals.max():.3e}]")

            # 補足：価格に対数を取るケースを想定
            tc_init = min(max(power_law_params['tc'], 1.05), 1.5)  # 下限を1.05(tc-t -> 0 でフィッティングが不安定化)
            p0 = [
                tc_init,  # tc: べき乗則フィットで得られたクリティカル時刻を初期値に
                power_law_params['beta'], # β: べき乗則フィットで得られたべき指数を初期値に
                6.36,   # ω (omega): 対数周期の角振動数。論文で報告される典型値5-8の中央値を初期値に
                0.0,    # φ (phi): 位相。特に事前情報がないため0を初期値に
                np.log(power_law_params['A']),  # log(A): べき乗則フィットで得られたオフセットの対数値
                power_law_params['B'],  # B: べき乗則フィットで得られたスケールパラメータ
                0.1     # C: 対数周期項の振幅。べき乗項に対して10%程度の変調を仮定
            ]
            
            # 補足：価格に対数を取るケース想定            
            bounds = ([
                1.01, 0.1,  
                2.0, -8*np.pi, -np.inf, -np.inf, -2.0
            ], [
                p0[0]*1.4, 0.9,
                15.0, 8*np.pi, np.inf, np.inf, 2.0
            ])

            # 初期パラメータの出力
            print("\nLogarithm Periodic Fitting Analysis:")
            print("---------------------------")
            print("Initial parameter values:")
            print(f"tc (critical time): {p0[0]:.3f}")
            print(f"beta (power law exponent): {p0[1]:.3f}")
            print(f"omega (angular frequency): {p0[2]:.3f}")
            print(f"phi (phase): {p0[3]:.3f}")
            print(f"log(A) (log offset): {p0[4]:.3f}")
            print(f"B (scale parameter): {p0[5]:.3f}")
            print(f"C (oscillation amplitude): {p0[6]:.3f}")

            print("\nParameter bounds:")
            print(f"tc: [{bounds[0][0]:.3f}, {bounds[1][0]:.3f}]")
            print(f"beta: [{bounds[0][1]:.3f}, {bounds[1][1]:.3f}]")
            print(f"omega: [{bounds[0][2]:.3f}, {bounds[1][2]:.3f}]")
            print(f"phi: [{bounds[0][3]:.3f}, {bounds[1][3]:.3f}]")
            print("log(A): [-inf, inf]")
            print("B: [-inf, inf]")
            print(f"C: [{bounds[0][6]:.3f}, {bounds[1][6]:.3f}]")     


            # フィッティングの実行
            try:
                popt, pcov = curve_fit(
                    logarithm_periodic_func, t, y, 
                    p0=p0, bounds=bounds, 
                    maxfev=10000,
                    method='trf',
                    ftol=1e-8,     # 収束条件
                    xtol=1e-8,     # 収束条件
                    loss='soft_l1'  # 頑健な損失関数
                )
                perr = np.sqrt(np.diag(pcov))   

                print("\nFitted parameters:")
                print(f"tc (critical time) = {popt[0]:.6f} ± {perr[0]:.6f}")
                print(f"beta (power law exponent) = {popt[1]:.6f} ± {perr[1]:.6f}")
                print(f"omega (angular frequency) = {popt[2]:.6f} ± {perr[2]:.6f}")
                print(f"phi (phase) = {popt[3]:.6f} ± {perr[3]:.6f}")
                print(f"log(A) = {popt[4]:.6f} ± {perr[4]:.6f}")
                print(f"A (offset) = {np.exp(popt[4]):.6f} ± {np.exp(popt[4])*perr[4]:.6f}")
                print(f"B (scale) = {popt[5]:.6f} ± {perr[5]:.6f}")
                print(f"C (oscillation amplitude) = {popt[6]:.6f} ± {perr[6]:.6f}")
                
                y_fit = logarithm_periodic_func(t, *popt)
                residuals, r_squared = calculate_fit_metrics(y, y_fit)

                # フィッティング品質の出力
                print("\nFitting quality metrics:")
                print(f"R-squared: {r_squared:.6f}")
                print(f"Residuals (MSE): {residuals:.6e}")
                print("---------------------------\n")            


            except (RuntimeError, ValueError) as e:
                print("\nCurve fitting error:")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print("\nFitting state at failure:")
                print("Initial parameters:")
                for i, param in enumerate(['tc', 'beta', 'omega', 'phi', 'log(A)', 'B', 'C']):
                    print(f"{param}: {p0[i]:.6f}")
                print("\nParameter bounds:")
                print("Lower:", bounds[0])
                print("Upper:", bounds[1])
                print("\nInput data statistics:")  # データの状態も出力
                print(f"t range: [{t.min():.3f}, {t.max():.3f}]")
                print(f"y range: [{y.min():.3f}, {y.max():.3f}]")
                raise

            return FittingResult(
                success=True,
                parameters={
                    'tc': popt[0],
                    'beta': popt[1],
                    'omega': popt[2],
                    'phi': popt[3],
                    'A': np.exp(popt[4]),  # 元の空間に戻す
                    'B': popt[5],
                    'C': popt[6]
                },
                residuals=residuals,
                r_squared=r_squared,
                statistical_significance=assess_statistical_significance(y, y_fit)
            )

        except Exception as e:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    def fit(self, t: np.ndarray, y: np.ndarray) -> FittingResult:
        """2段階フィッティングの実行"""
        try:
            power_result = self.fit_power_law(t, y)
            if not power_result.success:
                raise ValueError("Power law fitting failed")
            
            full_result = self.fit_logarithm_periodic(t, y, power_result.parameters)
            if not full_result.success:
                raise ValueError("Logarithm periodic fitting failed")
            
            return full_result

        except Exception as e:
            return FittingResult(
                success=False,
                parameters={},
                residuals=np.inf,
                r_squared=0,
                statistical_significance={},
                error_message=str(e)
            )

    def check_stability(self, times, prices, window_size=30, step=5, data=None, symbol=None):
        """パラメータの安定性分析"""
        tc_estimates = []
        windows = []
        
        for i in range(0, len(times) - window_size, step):
            window_times = times[i:i+window_size]
            window_prices = prices[i:i+window_size]
            
            try:
                result = self.fit(window_times, window_prices)
                if result.success:
                    tc_estimates.append(result.parameters['tc'])
                    windows.append(window_times[-1])
            except Exception as e:
                print(f"Window {i} fitting failed: {str(e)}")
                continue
        
        if not tc_estimates:
            print("No successful fits in stability analysis")
            return None, None, None, None
            
        tc_mean = np.mean(tc_estimates)
        tc_std = np.std(tc_estimates)
        tc_cv = tc_std / tc_mean
        window_consistency = max(0, 1 - 2 * tc_cv)
        
        return tc_mean, tc_std, tc_cv, window_consistency