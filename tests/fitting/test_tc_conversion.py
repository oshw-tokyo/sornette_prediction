"""
tc→日付変換のテストコード (Issue I128)

【テスト目的】
- convert_tc_to_date() 関数の正確性を検証
- フィッティング期間を正しく反映しているか
- 窓サイズごとに異なる変換比率を使用しているか
- 1987年ブラックマンデーでの検証

【科学的根拠】
- LPPL時間正規化: t ∈ [0, 1]
- tc値の正しい解釈: (tc - 1.0) × フィッティング期間の暦日数
- Issue I128で発見された問題の修正検証

【実装日】2025-10-12
"""

import pytest
from datetime import datetime
from core.fitting.lppl_utils import convert_tc_to_date


def test_tc_conversion_750day_window():
    """750営業日窓（約3年）でのtc変換テスト"""
    first_date = '2021-10-19'
    last_date = '2024-10-19'
    tc = 1.2

    result = convert_tc_to_date(tc, first_date, last_date)

    # 期待値: 2025-05-26付近（1096暦日 × 0.2 ≈ 219日後）
    expected = datetime(2025, 5, 26)
    assert result is not None
    assert result.date() == expected.date(), f"Expected {expected.date()}, got {result.date()}"


def test_tc_conversion_125day_window():
    """125営業日窓（約半年）でのtc変換テスト"""
    first_date = '2024-04-19'
    last_date = '2024-10-19'
    tc = 1.2

    result = convert_tc_to_date(tc, first_date, last_date)

    # 期待値: 2024-11-24付近（183暦日 × 0.2 ≈ 37日後）
    expected = datetime(2024, 11, 24)
    assert result is not None
    assert result.date() == expected.date(), f"Expected {expected.date()}, got {result.date()}"


def test_tc_conversion_1987_blackmonday():
    """1987年ブラックマンデーでのtc変換テスト"""
    first_date = '1983-11-03'
    last_date = '1987-10-19'
    tc = 1.2128

    result = convert_tc_to_date(tc, first_date, last_date)

    # 期待値: 1988-08-21付近（1446暦日 × 0.2128 ≈ 308日後）
    expected = datetime(1988, 8, 21)
    assert result is not None
    assert result.date() == expected.date(), f"Expected {expected.date()}, got {result.date()}"


def test_tc_conversion_different_windows_same_tc():
    """同じtc値でも窓サイズが異なると予測日が異なることを確認"""
    tc = 1.2

    # 750日窓
    result_750 = convert_tc_to_date(tc, '2021-10-19', '2024-10-19')

    # 125日窓
    result_125 = convert_tc_to_date(tc, '2024-04-19', '2024-10-19')

    # 予測日が異なることを確認
    assert result_750 is not None
    assert result_125 is not None
    assert result_750 != result_125, "同じtc値でも窓サイズが異なると予測日が異なるべき"
    assert result_750 > result_125, "750日窓の方が遠い未来を予測すべき"


def test_tc_conversion_tc_less_than_1():
    """tc <= 1.0の場合はNoneを返す"""
    result = convert_tc_to_date(0.95, '2024-01-01', '2024-10-19')
    assert result is None, "tc <= 1.0の場合はNoneを返すべき"


def test_tc_conversion_tc_equals_1():
    """tc = 1.0の場合はNoneを返す"""
    result = convert_tc_to_date(1.0, '2024-01-01', '2024-10-19')
    assert result is None, "tc = 1.0の場合はNoneを返すべき"


def test_tc_conversion_time_precision():
    """時間精度が正しく計算されることを確認"""
    first_date = '2024-01-01'
    last_date = '2024-12-31'  # 365日
    tc = 1.1  # 0.1 × 365 = 36.5日後

    result_with_time = convert_tc_to_date(tc, first_date, last_date, include_time=True)
    result_without_time = convert_tc_to_date(tc, first_date, last_date, include_time=False)

    assert result_with_time is not None
    assert result_without_time is not None

    # include_time=True の場合、時間精度が含まれる
    # 0.5日 = 12時間
    assert result_with_time.hour == 12, "0.5日分の12時間が含まれるべき"

    # 日付部分は同じはず
    assert result_with_time.date() == result_without_time.date()


def test_tc_conversion_pandas_timestamp_input():
    """pandas.Timestampを入力として受け取れることを確認"""
    import pandas as pd

    first_date = pd.Timestamp('2024-01-01')
    last_date = pd.Timestamp('2024-12-31')
    tc = 1.2

    result = convert_tc_to_date(tc, first_date, last_date)

    assert result is not None
    assert isinstance(result, datetime)


def test_tc_conversion_datetime_input():
    """datetimeオブジェクトを入力として受け取れることを確認"""
    first_date = datetime(2024, 1, 1)
    last_date = datetime(2024, 12, 31)
    tc = 1.2

    result = convert_tc_to_date(tc, first_date, last_date)

    assert result is not None
    assert isinstance(result, datetime)


def test_tc_conversion_string_input():
    """文字列を入力として受け取れることを確認"""
    first_date = '2024-01-01'
    last_date = '2024-12-31'
    tc = 1.2

    result = convert_tc_to_date(tc, first_date, last_date)

    assert result is not None
    assert isinstance(result, datetime)


# 実行時のサマリー表示
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
