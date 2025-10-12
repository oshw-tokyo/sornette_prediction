#!/usr/bin/env python3
"""
Phase 1検証: カスタムFCO単一窓フィッティング - 1987年ブラックマンデー（プロット付き）

目的: 過去実装の復元を確認（単一窓）+ 視覚的検証
期待結果: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.fitting.lppl_utils import prepare_normalized_data, logarithm_periodic_func, convert_tc_to_date
from core.fitting.lppl_optimizer import fit_lppl_grid_search, validate_lppl_parameters, check_boundary_adhesion

# 境界条件（過去実装ベース + omega拡大、lppl_optimizer.py と一致）
# archive/src_pre_migration_backup/fitting/fitter.py:64-67
# omega上限を10.0に拡大（Sornette論文で8.93の実例確認済み）
LPPL_BOUNDS = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
    [1.5,  0.7, 10.0,  8*np.pi,  10,  10,  2.0]  # upper (omega: 8.0→10.0)
)

# データ読み込み
cache_path = Path("data/market_data/cache/full/NASDAQCOM_1987_full.parquet")
df = pd.read_parquet(cache_path)

# 過去実装準拠: クラッシュ101日前を基準日とする（validation_cutoff_days=101）
# 理由: クラッシュに近すぎると(tc-t が 0 に近づくと)、フィッティングが発散する
crash_date = datetime(1987, 10, 19)
analysis_basis_date = crash_date - timedelta(days=101)  # 1987-07-10 (約3ヶ月前)

# フィッティング用データ（クラッシュ前）
df_before = df[df.index <= analysis_basis_date]
df_analysis = df_before.iloc[-500:]  # 500日データ（約2年）
prices = df_analysis['Close'].values

# プロット用に全期間データを保持（クラッシュ後を含む）
df_plot_end = crash_date + timedelta(days=30)  # クラッシュ30日後まで
df_all = df[(df.index >= df_analysis.index[0]) & (df.index <= df_plot_end)]

print("=" * 80)
print("Phase 1検証: カスタムFCO単一窓フィッティング - 1987年ブラックマンデー")
print("=" * 80)
print()
print(f"データ期間: {df_analysis.index[0].date()} ~ {df_analysis.index[-1].date()}")
print(f"クラッシュ日: {crash_date.date()}")
print(f"解析基準日: {df_analysis.index[-1].date()}")
print(f"データ点数: {len(prices)}")
print()

# Phase 1: 単一窓（全データ）でフィッティング
print("【Phase 1: 単一窓フィッティング】")
print("-" * 80)

# データ準備（時間正規化 [0, 1]）
t, log_prices_normalized = prepare_normalized_data(prices)

print(f"時間正規化: t ∈ [{t[0]:.4f}, {t[-1]:.4f}]")
print(f"対数価格範囲: [{log_prices_normalized.min():.4f}, {log_prices_normalized.max():.4f}]")
print()

# グリッドサーチフィッティング
print("グリッドサーチフィッティング開始...")
print("  試行組み合わせ: 10³ = 1000")
print()

result = fit_lppl_grid_search(t, log_prices_normalized, n_tries=10)

if result is None:
    print("❌ フィッティング失敗: 全1000組み合わせで収束せず")
    sys.exit(1)

print("✅ フィッティング成功")
print()

# 結果表示
print("【フィッティング結果】")
print("-" * 80)
print(f"  tc (正規化時間): {result['tc']:.4f}")
print(f"  tc > 1.0 (未来予測): {'✅ YES' if result['tc'] > 1.0 else '❌ NO'}")
print()
print(f"  beta (β): {result['beta']:.4f}")
print(f"  omega (ω): {result['omega']:.4f}")
print(f"  phi (φ): {result['phi']:.4f}")
print()
print(f"  A: {result['A']:.4f}")
print(f"  B: {result['B']:.4f}")
print(f"  C: {result['C']:.4f}")
print()
print(f"  R²: {result['r2']:.4f}")
print(f"  残差: {result['residuals']:.4e}")
print()

# 境界張り付きチェック（A0: ユーザーフィードバック）
has_boundary_adhesion = check_boundary_adhesion(result, LPPL_BOUNDS)

# パラメータ妥当性検証（境界条件を渡す）
is_valid = validate_lppl_parameters(result, tc_min=1.0, bounds=LPPL_BOUNDS)

print("【パラメータ妥当性検証】")
print("-" * 80)
print(f"  tc > 1.0: {'✅' if result['tc'] > 1.0 else '❌'} ({result['tc']:.4f})")
print(f"  0.05 < beta < 1.0: {'✅' if 0.05 < result['beta'] < 1.0 else '❌'} ({result['beta']:.4f})")
print(f"  1.0 < omega < 20.0: {'✅' if 1.0 < result['omega'] < 20.0 else '❌'} ({result['omega']:.4f})")
print(f"  R² > 0.5: {'✅' if result['r2'] > 0.5 else '❌'} ({result['r2']:.4f})")
print(f"  境界張り付きなし: {'❌ FAIL (張り付きあり)' if has_boundary_adhesion else '✅ PASS'}")
print()
print(f"  総合判定: {'✅ VALID' if is_valid else '❌ INVALID'}")
print()

# tc → 実日付変換（Issue I128修正版を使用）
predicted_crash_date = convert_tc_to_date(
    result['tc'],
    df_analysis.index[0],   # first_date: フィッティング開始日
    df_analysis.index[-1],  # last_date: フィッティング終了日（解析基準日）
    include_time=False
)
tc_days_beyond = (predicted_crash_date - df_analysis.index[-1].to_pydatetime()).days
prediction_error_days = abs((predicted_crash_date - crash_date).days)

# Phase 1成功基準判定（A0-A1反映）
print("【Phase 1成功基準】")
print("-" * 80)
print(f"  R² > 0.9: {'✅ PASS' if result['r2'] > 0.9 else '❌ FAIL'} (実測: {result['r2']:.4f})")
print(f"  tc > 1.0: {'✅ PASS' if result['tc'] > 1.0 else '❌ FAIL'} (実測: {result['tc']:.4f})")
print(f"  予測誤差 ≤ 35日: {'✅ PASS' if prediction_error_days <= 35 else '❌ FAIL'} (実測: {prediction_error_days}日)")
print(f"  境界張り付きなし: {'✅ PASS' if not has_boundary_adhesion else '⚠️ WARNING (張り付きあり、ただし予測精度優先)'}")
print()

phase1_success = (
    result['r2'] > 0.9 and
    result['tc'] > 1.0 and
    prediction_error_days <= 35
    # 境界張り付きは警告のみ（ユーザーフィードバック: tcを優先）
)

print("【tcの実日付変換】")
print("-" * 80)
print(f"  tc（正規化時間）: {result['tc']:.4f}")
print(f"  解析基準日の先: {tc_days_beyond:.1f} 日")
print(f"  予測クラッシュ日: {predicted_crash_date.date()}")
print(f"  実際のクラッシュ日: {crash_date.date()}")
print(f"  予測誤差: {(predicted_crash_date - crash_date).days} 日 (絶対値: {prediction_error_days}日)")
print()

# 可視化
print("【可視化】")
print("-" * 80)
print("GUIプロット生成中...")

# LPPL予測曲線を生成（正規化対数価格空間）
y_pred = logarithm_periodic_func(
    t,
    result['tc'],
    result['beta'],
    result['omega'],
    result['phi'],
    result['A'],
    result['B'],
    result['C']
)

# 実価格に変換（正規化を元に戻す）
log_prices_original = np.log(prices)  # 元の対数価格
log_prices_fitted = y_pred + log_prices_original[0]  # 正規化オフセットを戻す
fitted_prices = np.exp(log_prices_fitted)  # 実価格に変換

# プロット作成
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# 上段: 価格フィッティング（クラッシュ後データも表示）
all_dates = df_all.index
all_prices = df_all['Close'].values

fitting_dates = df_analysis.index

# 未来予測部分を計算（基準日からtcまで）
tc_normalized = result['tc']
future_t = np.linspace(1.0, tc_normalized, 100)  # 基準日（t=1.0）からtcまで

future_log_pred = logarithm_periodic_func(
    future_t,
    result['tc'], result['beta'], result['omega'], result['phi'],
    result['A'], result['B'], result['C']
)
future_log_prices = future_log_pred + log_prices_original[0]
future_prices = np.exp(future_log_prices)

# 未来時刻を実日付に変換（Issue I128修正版）
future_dates = [
    convert_tc_to_date(t, df_analysis.index[0], df_analysis.index[-1], include_time=False)
    for t in future_t
]

# 色盲対応カラーパレット (Okabe-Ito color universal design)
# https://jfly.uni-koeln.de/color/
COLOR_ACTUAL = '#0173B2'      # 青: 実データ
COLOR_FIT = '#DE8F05'         # オレンジ: フィッティング
COLOR_PREDICTION = '#CC78BC'  # ピンク: 予測（Future）
COLOR_CRASH = '#029E73'       # 緑: Black Monday
COLOR_TC = '#D55E00'          # 朱色: tc（Critical Time）
COLOR_BASIS = '#808080'       # 灰色: Analysis Basis Date

# プロット: 実データ（全期間）
ax1.plot(all_dates, all_prices, color=COLOR_ACTUAL, linewidth=1.5, alpha=0.7, label='Actual NASDAQ (Full Period)')

# プロット: フィッティング（過去データ）
ax1.plot(fitting_dates, fitted_prices, color=COLOR_FIT, linewidth=2.5, label='LPPL Fit (Historical)')

# プロット: 予測（未来データ、実線化）
ax1.plot(future_dates, future_prices, color=COLOR_PREDICTION, linestyle='-', linewidth=2.5, label='LPPL Prediction (Future)')

# ブラックマンデーをマーク（青系統）
ax1.axvline(crash_date, color=COLOR_CRASH, linestyle='--', linewidth=2, alpha=0.8, label='Black Monday (Actual)')

# 予測クラッシュ日（tc）をマーク（朱色系統）
ax1.axvline(predicted_crash_date, color=COLOR_TC, linestyle=':', linewidth=2, alpha=0.8, label=f'tc (Critical Time) = {tc_normalized:.3f}')

# 解析基準日をマーク（灰色）
ax1.axvline(analysis_basis_date, color=COLOR_BASIS, linestyle='-.', linewidth=2, alpha=0.6, label='Analysis Basis Date')

ax1.set_ylabel('NASDAQ Composite Index', fontsize=12)
ax1.set_title(f'1987 Black Monday LPPL Prediction (R²={result["r2"]:.4f}, Error={prediction_error_days} days)',
             fontsize=14, fontweight='bold')

# 凡例を左上に配置
ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax1.grid(True, alpha=0.3)

# 統計情報表示（凡例と重ならないよう左下に配置）
info_text = f'R² = {result["r2"]:.4f}\nbeta = {result["beta"]:.3f} (paper: 0.33)\nomega = {result["omega"]:.2f} (paper: 7.4)\nPrediction Error = {prediction_error_days} days'
ax1.text(0.02, 0.28, info_text, transform=ax1.transAxes,
         verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85),
         fontsize=10)

# 下段: 残差分析（対数価格空間）
residuals = log_prices_normalized - y_pred
ax2.plot(fitting_dates, residuals, 'green', linewidth=1, alpha=0.7, label='Residuals')
ax2.axhline(0, color='black', linestyle='-', alpha=0.5)
ax2.set_ylabel('Residuals (Log Price Space)', fontsize=12)
ax2.set_title('Residual Analysis', fontsize=12)
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()

# 保存
plot_dir = Path('plots/crash_prediction/')
plot_dir.mkdir(parents=True, exist_ok=True)
filename = plot_dir / '1987_custom_fco_phase1_validation.png'
plt.savefig(filename, dpi=300, bbox_inches='tight')
print(f"✅ プロット保存: {filename}")

# GUIに表示（ターミナル実行時はコメントアウト）
# plt.show()
print("✅ プロット生成完了（GUIスキップ、ファイルに保存済み）")
print()

if phase1_success:
    print("🎉 Phase 1成功: 過去実装復元完了")
    print("✅ Phase 1検証完了 → Phase 2（多重窓統合）へ進む準備完了")
    if has_boundary_adhesion:
        print()
        print("⚠️ 注意: 境界張り付きが検出されましたが、予測精度が優秀なため許容")
        print("   （ユーザーフィードバック: tcを優先）")
else:
    print("❌ Phase 1失敗: 成功基準未達")
    print()
    print("【失敗要因の分析】")
    print("-" * 80)
    if result['r2'] <= 0.9:
        print(f"  ❌ R²不足: {result['r2']:.4f} ≤ 0.9")
    if result['tc'] <= 1.0:
        print(f"  ❌ tc未来予測失敗: {result['tc']:.4f} ≤ 1.0")
    if prediction_error_days > 35:
        print(f"  ❌ 予測誤差超過: {prediction_error_days}日 > 35日")
    if has_boundary_adhesion:
        print(f"  ⚠️ 境界張り付き検出（警告のみ）:")
        print(f"     tc={result['tc']:.4f} (境界: 1.001-1.2)")
        print(f"     beta={result['beta']:.4f} (境界: 0.05-1.0)")
        print(f"     omega={result['omega']:.4f} (境界: 1.0-20.0)")
    print()
    print("  → 対策: データ期間の調整、またはグリッドサーチ範囲の見直しが必要")

print()
print("=" * 80)
print("Phase 1検証完了")
print("=" * 80)

# 終了コード
sys.exit(0 if phase1_success else 1)
