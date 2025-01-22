from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from datetime import timedelta

from ..config.validation_settings import get_validation_settings

# historical_crashes.py の CrashPeriod クラスを修正
@dataclass
class CrashPeriod:
    """クラッシュ期間を定義するデータクラス"""
    start_date: datetime
    end_date: datetime
    crash_date: datetime
    pre_crash_peak_date: Optional[datetime] = None
    validation_cutoff_days: int = 30  # クラッシュ前の何日前までのデータを使用するか
    description: str = ""
    
    @property
    def validation_end_date(self) -> datetime:
        """検証用の終了日を計算"""
        return self.crash_date - timedelta(days=self.validation_cutoff_days)

    def get_validation_period(self) -> Tuple[datetime, datetime]:
        """検証用の期間を取得"""
        return self.start_date, self.validation_end_date

@dataclass
class CrashParameters:
    """クラッシュのパラメータを定義するデータクラス"""
    # 基本パラメータ（論文から）
    m: float           # べき指数
    omega: float       # 対数周期の角振動数
    phi: Optional[float] = None  # 位相（論文によって報告されない場合もある）
    
    # 許容誤差
    tolerance_m: float = 0.05    # べき指数の許容誤差
    tolerance_omega: float = 0.3  # 角振動数の許容誤差
    tolerance_phi: float = 0.5    # 位相の許容誤差
    
    # その他のパラメータ（報告されている場合）
    A: Optional[float] = None
    B: Optional[float] = None
    C: Optional[float] = None

@dataclass
class CrashMetrics:
    """クラッシュの定量的指標"""
    price_drop_percentage: float  # 価格下落率
    duration_days: int           # 下落期間（日数）
    pre_crash_peak: float       # クラッシュ前のピーク価格
    post_crash_bottom: float    # クラッシュ後の最安値

class CrashCase:
    """クラッシュケースの完全な定義"""
    def __init__(self, id: str, name: str, symbol: str, period: CrashPeriod,
                 parameters: CrashParameters, metrics: CrashMetrics,
                 reference: str, notes: str = ""):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.period = period
        self.parameters = parameters
        self.metrics = metrics
        self.reference = reference
        self.notes = notes
        
        # 検証設定の適用
        settings = get_validation_settings(self.id)
        self.period.validation_cutoff_days = settings['validation_cutoff_days']

# 1987年10月のクラッシュ定義
# historical_crashes.py の CRASH_1987_10 の定義を修正
CRASH_1987_10 = CrashCase(
    id='1987-10',
    name='Black Monday Crash',
    symbol='^GSPC',  # S&P500
    
    period=CrashPeriod(
        start_date=datetime(1985, 7, 1),
        end_date=datetime(1987, 9, 19),    # クラッシュ30日前
        crash_date=datetime(1987, 10, 19),
        pre_crash_peak_date=datetime(1987, 8, 25),
        validation_cutoff_days=30,
        description="The crash culminated in Black Monday on October 19, 1987"
    ),
    
    parameters=CrashParameters(
        m=0.33,
        omega=7.4,
        phi=2.0,
        tolerance_m=0.03,
        tolerance_omega=0.2,
        tolerance_phi=0.3
    ),
    
    metrics=CrashMetrics(
        price_drop_percentage=22.6,
        duration_days=1,
        pre_crash_peak=2722.42,
        post_crash_bottom=1738.74
    ),
    
    reference="Sornette, D., Johansen, A., & Bouchaud, J. P. (1996). "
              "Stock market crashes, precursors and replicas. "
              "Journal de Physique I, 6(1), 167-175.",
              
    notes="This crash was notable for its global nature and the role of "
          "portfolio insurance in potentially amplifying the decline."
)
# 既知のクラッシュケースの辞書
CRASH_CASES = {
    '1987-10': CRASH_1987_10,
    # 今後、他のクラッシュケースを追加
    # '1929-10': CRASH_1929_10,  # 将来の実装用
    # '1997-10': CRASH_1997_10,  # 将来の実装用
    # '2000-04': CRASH_2000_04,  # 将来の実装用
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
        valid_ids = list(CRASH_CASES.keys())
        raise KeyError(
            f"Crash case '{crash_id}' not found. "
            f"Available cases: {valid_ids}"
        )
    return CRASH_CASES[crash_id]

def list_available_crashes() -> List[Dict]:
    """
    利用可能なクラッシュケースの一覧を返す

    Returns:
    --------
    List[Dict]
        各クラッシュケースの基本情報のリスト
    """
    return [
        {
            'id': k,
            'name': v.name,
            'date': v.period.crash_date,
            'market': v.symbol
        }
        for k, v in CRASH_CASES.items()
    ]