#!/usr/bin/env python3
"""
2008年リーマンショック - カスタムFCO多重窓検証 (Issue I133)

目的: O/D閾値（O>2.5, D>0.5）の妥当性を2008年リーマンショックで検証
期待結果: DS-LPPLS Confidence > 30%, 予測精度確認

実装仕様（2025-10-13更新）:
- 126窓多重窓解析（125-750日、5日刻み、FCO標準準拠）
- 複数分析基準日（クラッシュから30/45/60/90日前）
- 各基準日でDS-LPPLS Confidence計算
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.fitting.custom_fco_engine import CustomFCOEngine, LPPL_BOUNDS
from core.fitting.lppl_utils import logarithm_periodic_func, convert_tc_to_date

# データ読み込み（NASDAQ100を使用、SP500は2015年以降のみ）
cache_path = Path("data/market_data/cache/full/NASDAQ100_full.parquet")

if not cache_path.exists():
    print(f"❌ エラー: キャッシュファイルが見つかりません: {cache_path}")
    print("まず全銘柄解析を実行してキャッシュを作成してください:")
    print("  python entry_points/main.py analyze NASDAQ100")
    sys.exit(1)

# フルデータ読み込み
df = pd.read_parquet(cache_path)

# 必要な期間のみフィルタリング（2005-2010年）
data_start = datetime(2005, 1, 1)
data_end = datetime(2010, 12, 31)
df = df[(df.index >= data_start) & (df.index <= data_end)]

if df.empty:
    print(f"❌ エラー: 期間 {data_start.date()} ~ {data_end.date()} のデータが存在しません")
    sys.exit(1)

# 2008年リーマンショックの設定
# リーマン・ブラザーズ破綻: 2008-09-15
crash_date = datetime(2008, 9, 15)

# 複数分析基準日（クラッシュから30/45/60/90日前）
basis_days_before = [30, 45, 60, 90]

print("=" * 80)
print("2008年リーマンショック - カスタムFCO多重窓検証 (Issue I133)")
print("=" * 80)
print()
print(f"データ期間: {df.index[0].date()} ~ {df.index[-1].date()}")
print(f"リーマン破綻日: {crash_date.date()}")
print(f"分析基準日: クラッシュから {basis_days_before} 日前")
print()

# カスタムFCO多重窓解析（51窓: 250-750日、10日刻み、実用的サイズ）
# 注: FCO標準は126窓（125-750日、5日刻み）だが、計算時間を考慮して51窓で実施
class PracticalFCOEngine(CustomFCOEngine):
    WINDOW_MIN = 250  # 最小窓: 250日（実用的な最小サイズ）
    WINDOW_MAX = 750  # 最大窓: 750日（FCO標準）
    WINDOW_STEP = 10  # 窓刻み: 10日 → 51窓

# Phase 2では計算時間短縮のため n_tries=8 を使用
engine = PracticalFCOEngine(n_tries=8)

print("【カスタムFCO多重窓解析】")
print("-" * 80)
print(f"  窓範囲: {engine.WINDOW_MIN} ~ {engine.WINDOW_MAX} 日 (FCO標準)")
print(f"  窓刻み: {engine.WINDOW_STEP} 日")
print(f"  総窓数: {(engine.WINDOW_MAX - engine.WINDOW_MIN) // engine.WINDOW_STEP + 1}")
print(f"  グリッドサーチ: {engine.n_tries}³ = {engine.n_tries**3} 組み合わせ/窓")
print()

# 各基準日で解析
results_by_basis = {}

for days_before in basis_days_before:
    analysis_basis_date = crash_date - timedelta(days=days_before)

    print("=" * 80)
    print(f"分析基準日: {analysis_basis_date.date()} (クラッシュ{days_before}日前)")
    print("=" * 80)
    print()

    # フィッティング用データ（クラッシュ前）
    df_before = df[df.index <= analysis_basis_date]

    # FCO標準: 最大窓750日が必要 + 安全マージン50日
    if len(df_before) < 800:
        print(f"⚠️ 警告: データ不足（{len(df_before)}日 < 800日必要）")
        print(f"  → この基準日はスキップします")
        print()
        continue

    df_analysis = df_before.iloc[-800:]  # 800日データ
    prices = df_analysis['Close'].values

    print(f"データ期間: {df_analysis.index[0].date()} ~ {df_analysis.index[-1].date()}")
    print(f"データ点数: {len(prices)}")
    print()

    # DS-LPPLS Confidence計算
    print("多重窓フィッティング開始...")
    result = engine.compute_ds_lppls_confidence(prices)

    print()
    print("✅ 多重窓解析完了")
    print()

    # 結果表示
    print("【DS-LPPLS Confidence結果】")
    print("-" * 80)
    print(f"  DS-LPPLS Confidence: {result.ds_lppls_confidence:.2%}")
    print(f"  適格フィット数: {result.qualified_fits} / {result.total_windows}")
    print()

    if result.predicted_tc is not None:
        print(f"  予測tc (中央値): {result.predicted_tc:.4f}")
        print(f"  tc標準偏差: {result.tc_std:.4f}")

        # tc → 実日付変換（最大窓750日基準）
        max_window_start_idx = len(df_analysis) - engine.WINDOW_MAX
        first_date_max_window = df_analysis.index[max_window_start_idx]
        last_date_max_window = df_analysis.index[-1]

        predicted_crash_date = convert_tc_to_date(
            result.predicted_tc,
            first_date_max_window,
            last_date_max_window,
            include_time=False
        )
        tc_days_beyond = (predicted_crash_date - last_date_max_window.to_pydatetime()).days
        prediction_error_days = abs((predicted_crash_date - crash_date).days)

        print()
        print("【予測クラッシュ日（概算、750日窓基準）】")
        print("-" * 80)
        print(f"  予測tc: {result.predicted_tc:.4f} (正規化時間)")
        print(f"  解析基準日の先: {tc_days_beyond:.1f} 日")
        print(f"  予測クラッシュ日: {predicted_crash_date.date()}")
        print(f"  実際のクラッシュ日: {crash_date.date()}")
        print(f"  予測誤差: {(predicted_crash_date - crash_date).days} 日 (絶対値: {prediction_error_days}日)")
    else:
        print("  ⚠️ 適格フィットなし（予測tcなし）")
        prediction_error_days = None
        predicted_crash_date = None

    print()

    # 成功基準判定
    print("【検証成功基準（Issue I133）】")
    print("-" * 80)
    print(f"  DS-LPPLS Confidence > 30%: {'✅ PASS' if result.ds_lppls_confidence > 0.30 else '❌ FAIL'} (実測: {result.ds_lppls_confidence:.2%})")
    print(f"  適格フィット数 > 0: {'✅ PASS' if result.qualified_fits > 0 else '❌ FAIL'} (実測: {result.qualified_fits})")

    if result.predicted_tc is not None:
        print(f"  予測tc > 1.0: {'✅ PASS' if result.predicted_tc > 1.0 else '❌ FAIL'} (実測: {result.predicted_tc:.4f})")
        print(f"  予測誤差 ≤ 60日: {'✅ PASS' if prediction_error_days <= 60 else '⚠️ WARNING'} (実測: {prediction_error_days}日)")
    else:
        print(f"  予測tc > 1.0: ❌ FAIL (適格フィットなし)")
        print(f"  予測誤差 ≤ 60日: ❌ FAIL (適格フィットなし)")

    print()

    validation_success = (
        result.ds_lppls_confidence > 0.30 and
        result.qualified_fits > 0 and
        result.predicted_tc is not None and
        result.predicted_tc > 1.0
    )

    # 結果保存
    results_by_basis[days_before] = {
        'result': result,
        'analysis_basis_date': analysis_basis_date,
        'predicted_crash_date': predicted_crash_date,
        'prediction_error_days': prediction_error_days,
        'validation_success': validation_success
    }

    # 適格フィットの統計情報
    if result.qualified_fits > 0:
        print("【適格フィット統計】")
        print("-" * 80)

        qualified_results = [w for w in result.window_results if w.get('is_qualified', False)]

        # R²統計
        r2_values = [w['r2'] for w in qualified_results]
        print(f"  R² 範囲: {min(r2_values):.4f} ~ {max(r2_values):.4f}")
        print(f"  R² 平均: {np.mean(r2_values):.4f}")
        print()

        # omega統計
        omega_values = [w['omega'] for w in qualified_results]
        print(f"  omega 範囲: {min(omega_values):.4f} ~ {max(omega_values):.4f}")
        print(f"  omega 平均: {np.mean(omega_values):.4f}")
        print()

        # tc統計
        tc_values = [w['tc'] for w in qualified_results]
        print(f"  tc 範囲: {min(tc_values):.4f} ~ {max(tc_values):.4f}")
        print(f"  tc 平均: {np.mean(tc_values):.4f}")
        print()

    print()

# 全基準日の結果サマリー
print("=" * 80)
print("全基準日の結果サマリー")
print("=" * 80)
print()

summary_table = []
for days_before in basis_days_before:
    if days_before in results_by_basis:
        r = results_by_basis[days_before]
        summary_table.append({
            '基準日': f"{days_before}日前",
            'Confidence': f"{r['result'].ds_lppls_confidence:.2%}",
            '適格フィット': f"{r['result'].qualified_fits}/{r['result'].total_windows}",
            '予測誤差': f"{r['prediction_error_days']}日" if r['prediction_error_days'] else "N/A",
            '判定': "✅ PASS" if r['validation_success'] else "❌ FAIL"
        })

if summary_table:
    import pandas as pd
    summary_df = pd.DataFrame(summary_table)
    print(summary_df.to_string(index=False))
    print()

# 総合判定
successful_bases = sum(1 for r in results_by_basis.values() if r['validation_success'])
print(f"成功基準達成: {successful_bases} / {len(results_by_basis)} 基準日")
print()

if successful_bases >= len(results_by_basis) * 0.5:
    print("🎉 2008年リーマンショック検証成功")
    print("✅ O/D閾値が2008年リーマンショックで妥当であることを確認")
    overall_success = True
else:
    print("❌ 2008年リーマンショック検証失敗")
    print("⚠️ 複数の基準日でConfidence目標未達")
    overall_success = False

print()
print("=" * 80)
print("2008年リーマンショック検証完了")
print("=" * 80)

# 終了コード
sys.exit(0 if overall_success else 1)
