from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

class CrashPeriod(NamedTuple):
    start_date: datetime
    end_date: datetime
    crash_date: datetime
    description: str

class CrashParameters(NamedTuple):
    m: float  # べき指数
    omega: float  # 対数周期の角振動数
    tolerance_m: float  # mの許容誤差
    tolerance_omega: float  # ωの許容誤差

@dataclass
class CrashCase:
    """クラッシュケースの完全な定義"""
    period: CrashPeriod
    parameters: CrashParameters
    symbol: str
    name: str
    reference: str  # 論文の参照情報
    additional_info: dict = None  # その他の関連情報

# 1987年10月のクラッシュの定義
CRASH_1987_10 = CrashCase(
    period=CrashPeriod(
        start_date=datetime(1985, 7, 1),
        end_date=datetime(1987, 10, 31),
        crash_date=datetime(1987, 10, 19),
        description="The crash culminated on October 19, 1987 (Black Monday)"
    ),
    parameters=CrashParameters(
        m=0.33,
        omega=7.4,
        tolerance_m=0.05,
        tolerance_omega=0.3
    ),
    symbol='^GSPC',  # S&P500
    name="Black Monday Crash",
    reference="Sornette, D., Johansen, A., & Bouchaud, J. P. (1996). Stock market crashes, precursors and replicas. Journal de Physique I, 6(1), 167-175.",
    additional_info={
        'price_drop': 0.226,  # 22.6%の下落
        'pre_crash_high': 2722.42,
        'post_crash_low': 1738.74
    }
)

# 全てのクラッシュケースをまとめたディクショナリ
CRASH_CASES = {
    '1987-10': CRASH_1987_10,
    # 今後他のクラッシュケースを追加
}

def get_crash_case(crash_id: str) -> CrashCase:
    """
    クラッシュケースを取得する

    Parameters:
    -----------
    crash_id : str
        クラッシュのID (例: '1987-10')

    Returns:
    --------
    CrashCase
        クラッシュケースの定義
    
    Raises:
    -------
    KeyError
        指定されたIDのクラッシュケースが存在しない場合
    """
    if crash_id not in CRASH_CASES:
        raise KeyError(f"Crash case '{crash_id}' not found. Available cases: {list(CRASH_CASES.keys())}")
    return CRASH_CASES[crash_id]

def list_available_crashes() -> list:
    """利用可能なクラッシュケースの一覧を返す"""
    return [(k, v.name) for k, v in CRASH_CASES.items()]