from src.fitting.fitter import LogPeriodicFitter
from src.fitting.parameters import FittingParameterManager
from src.logging.analysis_logger import AnalysisLogger
from .historical_crashes import CrashCase, get_crash_case

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class CrashValidator:
    """クラッシュケースの再現性を検証するクラス"""
    
    def __init__(self):
        self.fitter = LogPeriodicFitter()
        self.param_manager = FittingParameterManager()
        self.logger = AnalysisLogger()

    def validate_crash(self, crash_id: str) -> bool:
        """
        特定のクラッシュケースの再現性を検証

        Parameters:
        -----------
        crash_id : str
            検証するクラッシュのID
            
        Returns:
        --------
        bool
            検証が成功したかどうか
        """
        try:
            crash_case = get_crash_case(crash_id)
        except KeyError as e:
            self.logger.error(str(e))
            return False

        # データ取得
        data = self._get_crash_data(crash_case)
        if data is None or data.empty:
            self.logger.error(f"Failed to get data for crash case {crash_id}")
            return False

        # フィッティング実行
        result = self._perform_fitting(data)
        if not result.success:
            self.logger.error(f"Fitting failed for crash case {crash_id}")
            return False

        # 結果の検証
        return self._validate_results(result, crash_case)

    def _get_crash_data(self, crash_case: CrashCase) -> pd.DataFrame:
        """クラッシュ期間のデータを取得"""
        try:
            data = yf.download(
                crash_case.symbol,
                start=crash_case.period.start_date,
                end=crash_case.period.end_date
            )
            if data.empty:
                self.logger.error(f"No data retrieved for {crash_case.symbol}")
                return None
                
            return data
            
        except Exception as e:
            self.logger.error(f"Error downloading data: {str(e)}")
            return None
        
    def _perform_fitting(self, data: pd.DataFrame):
        """フィッティングを実行"""
        # データの前処理
        prices = data['Close'].values.flatten()
        prices = np.log(prices)  # 対数変換（論文の手法に従う）
        t = np.arange(len(data))
        
        # 正規化（フィッティングの数値的安定性向上のため）
        t = (t - t[0]) / (t[-1] - t[0])  # [0,1]の範囲に正規化
        prices = (prices - np.mean(prices)) / np.std(prices)  # 標準化
        
        self.logger.info(f"データ準備完了: t.shape={t.shape}, prices.shape={prices.shape}")
        self.logger.info(f"データ範囲: 価格[{prices.min():.2f}-{prices.max():.2f}]")

        return self.fitter.fit_with_multiple_initializations(
            t=t,
            y=prices,
            n_tries=20  # 試行回数を増やして良い結果を得やすくする
        )

    def _validate_results(self, result, crash_case: CrashCase) -> bool:
        """フィッティング結果を検証"""
        params = crash_case.parameters
        m_error = abs(result.parameters['m'] - params.m)
        omega_error = abs(result.parameters['omega'] - params.omega)

        is_valid = (m_error < params.tolerance_m and 
                   omega_error < params.tolerance_omega)

        # 詳細な結果をログに記録
        self.logger.info(
            f"\nValidation results for {crash_case.name}:\n"
            f"Period: {crash_case.period.start_date.date()} - {crash_case.period.end_date.date()}\n"
            f"Parameter comparison:\n"
            f"  m: {result.parameters['m']:.3f} (expected: {params.m}, error: {m_error:.3f})\n"
            f"  ω: {result.parameters['omega']:.3f} (expected: {params.omega}, error: {omega_error:.3f})\n"
            f"Validity: {'✓ PASS' if is_valid else '✗ FAIL'}\n"
            f"Reference: {crash_case.reference}"
        )

        return is_valid