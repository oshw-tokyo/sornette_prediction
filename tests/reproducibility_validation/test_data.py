import numpy as np
from datetime import datetime, timedelta
import pandas as pd

def generate_test_crash_data(
    start_date: datetime,
    end_date: datetime,
    tc: float,
    m: float,
    omega: float,
    noise_level: float = 0.01
) -> pd.DataFrame:
    """テスト用のクラッシュデータを生成"""
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    t = np.linspace(0, 1, len(dates))
    
    # パラメータ設定
    A = 1.0
    B = -0.5
    C = 0.1
    phi = 0.0
    
    # 対数周期関数の生成
    dt = tc - t
    prices = A + B * np.power(dt, m) * (1 + C * np.cos(omega * np.log(dt) + phi))
    
    # ノイズの追加
    prices += np.random.normal(0, noise_level, len(t))
    
    # 指数変換して実際の価格スケールに
    prices = np.exp(prices)
    
    return pd.DataFrame({'Close': prices}, index=dates)

def get_test_crash_case(
    start_date: datetime = datetime(1987, 1, 1),
    end_date: datetime = datetime(1987, 10, 19),
    tc: float = 1.1,
    m: float = 0.45,
    omega: float = 6.36
) -> pd.DataFrame:
    """テスト用のクラッシュケースを生成"""
    return generate_test_crash_data(
        start_date=start_date,
        end_date=end_date,
        tc=tc,
        m=m,
        omega=omega
    )