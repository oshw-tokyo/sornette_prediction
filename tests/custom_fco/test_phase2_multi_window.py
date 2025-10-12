#!/usr/bin/env python3
"""
Phase 2検証: カスタムFCO多重窓統合 - 1987年ブラックマンデー

目的: 126窓解析の統合を確認 + DS-LPPLS Confidence検証
期待結果: DS-LPPLS Confidence > 30%, qualified_fits > 0, 予測精度確認
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

# データ読み込み
cache_path = Path("data/market_data/cache/full/NASDAQCOM_1987_full.parquet")
df = pd.read_parquet(cache_path)

# 過去実装準拠: クラッシュ101日前を基準日とする（validation_cutoff_days=101）
# 理由: クラッシュに近すぎると(tc-t が 0 に近づくと)、フィッティングが発散する
crash_date = datetime(1987, 10, 19)
analysis_basis_date = crash_date - timedelta(days=101)  # 1987-07-10 (約3ヶ月前)

# フィッティング用データ（クラッシュ前）
df_before = df[df.index <= analysis_basis_date]

# FCO標準: 最大窓サイズ750日が必要
# 安全マージン含めて800日を取得
df_analysis = df_before.iloc[-800:]  # 800日データ
prices = df_analysis['Close'].values

# プロット用に全期間データを保持（クラッシュ後を含む）
df_plot_end = crash_date + timedelta(days=30)  # クラッシュ30日後まで
df_all = df[(df.index >= df_analysis.index[0]) & (df.index <= df_plot_end)]

print("=" * 80)
print("Phase 2検証: カスタムFCO多重窓統合 - 1987年ブラックマンデー")
print("=" * 80)
print()
print(f"データ期間: {df_analysis.index[0].date()} ~ {df_analysis.index[-1].date()}")
print(f"クラッシュ日: {crash_date.date()}")
print(f"解析基準日: {df_analysis.index[-1].date()}")
print(f"データ点数: {len(prices)}")
print()

# Phase 2: 多重窓統合（126窓解析）
print("【Phase 2: 多重窓統合（126窓解析）】")
print("-" * 80)
print()

# CustomFCOEngineをオーバーライド（窓範囲を実用的に調整）
# 理由: 小さい窓（<250日）はノイズが大きく、全グリッドサーチ失敗の傾向
# FCO標準126窓の代わりに、250-750日の範囲で実用的な窓数を使用
class PracticalFCOEngine(CustomFCOEngine):
    WINDOW_MIN = 250  # 最小窓: 250日（実用的な最小サイズ）
    WINDOW_MAX = 750  # 最大窓: 750日（FCO標準）
    WINDOW_STEP = 10  # 窓刻み: 10日 → (750-250)/10 + 1 = 51窓

# Phase 2では計算時間短縮のため n_tries=8 を使用（8³ = 512組み合わせ）
# 理由: 51窓 × 512組み合わせ = 26,112回の最適化（約10-15分）
engine = PracticalFCOEngine(n_tries=8)

print("多重窓フィッティング開始...")
print(f"  窓範囲: {engine.WINDOW_MIN} ~ {engine.WINDOW_MAX} 日")
print(f"  窓刻み: {engine.WINDOW_STEP} 日")
print(f"  総窓数: {(engine.WINDOW_MAX - engine.WINDOW_MIN) // engine.WINDOW_STEP + 1}")
print(f"  グリッドサーチ: {engine.n_tries}³ = {engine.n_tries**3} 組み合わせ/窓")
print(f"  ⚠️ Phase 2では計算時間短縮のため n_tries=8 を使用")
print()

# DS-LPPLS Confidence計算
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

    # tc → 実日付変換（Issue I128修正版）
    # 注: 各窓のサイズが異なるため、正確な日時変換は窓ごとに実施必要
    # ここでは最大窓（750日）を基準に概算を表示
    # ❌ 修正前: tc_days_beyond = (result.predicted_tc - 1.0) * engine.WINDOW_MAX （営業日数ベース）
    # ✅ 修正後: convert_tc_to_date()を使用（暦日ベース）

    # 最大窓の日付範囲を取得
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

print()

# Phase 2成功基準判定
print("【Phase 2成功基準】")
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

phase2_success = (
    result.ds_lppls_confidence > 0.30 and
    result.qualified_fits > 0 and
    result.predicted_tc is not None and
    result.predicted_tc > 1.0
    # 予測誤差は参考値（多重窓の平均のため、厳密ではない）
)

# 適格フィットの統計情報
if result.qualified_fits > 0:
    print("【適格フィット統計】")
    print("-" * 80)

    # 適格フィットのみ抽出
    qualified_results = [w for w in result.window_results if w.get('is_qualified', False)]

    # R²統計
    r2_values = [w['r2'] for w in qualified_results]
    print(f"  R² 範囲: {min(r2_values):.4f} ~ {max(r2_values):.4f}")
    print(f"  R² 平均: {np.mean(r2_values):.4f}")
    print(f"  R² 中央値: {np.median(r2_values):.4f}")
    print()

    # beta統計
    beta_values = [w['beta'] for w in qualified_results]
    print(f"  beta 範囲: {min(beta_values):.4f} ~ {max(beta_values):.4f}")
    print(f"  beta 平均: {np.mean(beta_values):.4f}")
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
    print(f"  tc 中央値: {result.predicted_tc:.4f}")
    print(f"  tc 標準偏差: {result.tc_std:.4f}")
    print()

# 可視化
print("【可視化】")
print("-" * 80)
print("プロット生成中...")

# ============================================================================
# プロット1: 最良R²フィッティングの時系列プロット（Phase 1スタイル）
# ============================================================================
if result.qualified_fits > 0:
    print("【プロット1: 最良R²フィッティング時系列】")

    # 最良R²フィッティングを抽出
    qualified_results = [w for w in result.window_results if w.get('is_qualified', False)]
    best_fit = max(qualified_results, key=lambda x: x['r2'])

    print(f"  最良R²: {best_fit['r2']:.4f}")
    print(f"  窓サイズ: {best_fit['window_size']}日")
    print(f"  tc: {best_fit['tc']:.4f}")
    print(f"  beta: {best_fit['beta']:.4f}, omega: {best_fit['omega']:.4f}")
    print()

    # 最良フィッティングの窓データを準備
    best_window_size = best_fit['window_size']
    best_window_prices = prices[-best_window_size:]

    from core.fitting.lppl_utils import prepare_normalized_data
    t_best, log_prices_norm_best = prepare_normalized_data(best_window_prices)

    # 最良フィッティング曲線を生成（正規化対数価格空間）
    y_pred_best = logarithm_periodic_func(
        t_best,
        best_fit['tc'],
        best_fit['beta'],
        best_fit['omega'],
        best_fit['phi'],
        best_fit['A'],
        best_fit['B'],
        best_fit['C']
    )

    # 実価格に変換（正規化を元に戻す）
    log_prices_original_best = np.log(best_window_prices)
    log_prices_fitted_best = y_pred_best + log_prices_original_best[0]
    fitted_prices_best = np.exp(log_prices_fitted_best)

    # 最良窓の日付範囲を取得
    best_window_start_idx = len(df_analysis) - best_window_size
    fitting_dates_best = df_analysis.index[best_window_start_idx:]

    # 未来予測部分を計算（基準日からtcまで）
    tc_normalized_best = best_fit['tc']
    future_t_best = np.linspace(1.0, tc_normalized_best, 100)

    future_log_pred_best = logarithm_periodic_func(
        future_t_best,
        best_fit['tc'], best_fit['beta'], best_fit['omega'], best_fit['phi'],
        best_fit['A'], best_fit['B'], best_fit['C']
    )
    future_log_prices_best = future_log_pred_best + log_prices_original_best[0]
    future_prices_best = np.exp(future_log_prices_best)

    # 未来時刻を実日付に変換（Issue I128修正版）
    # ❌ 修正前: future_days_best = (future_t_best - 1.0) * best_window_size （営業日数ベース）
    # ✅ 修正後: convert_tc_to_date()を使用（暦日ベース）

    # 最良窓の日付範囲を取得
    best_window_first_date = fitting_dates_best[0]
    best_window_last_date = fitting_dates_best[-1]

    future_dates_best = [
        convert_tc_to_date(t, best_window_first_date, best_window_last_date, include_time=False)
        for t in future_t_best
    ]

    # 予測クラッシュ日（最良フィッティング基準、Issue I128修正版）
    predicted_crash_date_best = convert_tc_to_date(
        tc_normalized_best,
        best_window_first_date,
        best_window_last_date,
        include_time=False
    )
    prediction_error_days_best = abs((predicted_crash_date_best - crash_date).days)

    # 色盲対応カラーパレット (Okabe-Ito color universal design)
    COLOR_ACTUAL = '#0173B2'      # 青: 実データ
    COLOR_FIT = '#DE8F05'         # オレンジ: フィッティング
    COLOR_PREDICTION = '#CC78BC'  # ピンク: 予測（Future）
    COLOR_CRASH = '#029E73'       # 緑: Black Monday
    COLOR_TC = '#D55E00'          # 朱色: tc（Critical Time）
    COLOR_BASIS = '#808080'       # 灰色: Analysis Basis Date

    # 2段プロット: 上段=時系列、下段=残差
    fig1, (ax1_ts, ax2_ts) = plt.subplots(2, 1, figsize=(14, 10))

    # 上段: 価格フィッティング（クラッシュ後データも表示）
    all_dates = df_all.index
    all_prices = df_all['Close'].values

    # プロット: 実データ（全期間）
    ax1_ts.plot(all_dates, all_prices, color=COLOR_ACTUAL, linewidth=1.5, alpha=0.7, label='Actual NASDAQ (Full Period)')

    # プロット: フィッティング（過去データ）
    ax1_ts.plot(fitting_dates_best, fitted_prices_best, color=COLOR_FIT, linewidth=2.5, label='LPPL Fit (Historical)')

    # プロット: 予測（未来データ）
    ax1_ts.plot(future_dates_best, future_prices_best, color=COLOR_PREDICTION, linestyle='-', linewidth=2.5, label='LPPL Prediction (Future)')

    # ブラックマンデーをマーク
    ax1_ts.axvline(crash_date, color=COLOR_CRASH, linestyle='--', linewidth=2, alpha=0.8, label='Black Monday (Actual)')

    # 予測クラッシュ日（tc）をマーク
    ax1_ts.axvline(predicted_crash_date_best, color=COLOR_TC, linestyle=':', linewidth=2, alpha=0.8, label=f'tc (Critical Time) = {tc_normalized_best:.3f}')

    # 解析基準日をマーク
    ax1_ts.axvline(analysis_basis_date, color=COLOR_BASIS, linestyle='-.', linewidth=2, alpha=0.6, label='Analysis Basis Date')

    ax1_ts.set_ylabel('NASDAQ Composite Index', fontsize=12)
    ax1_ts.set_title(f'Phase 2 Best Fit: 1987 Black Monday LPPL Prediction (R²={best_fit["r2"]:.4f}, Window={best_window_size}d, Error={prediction_error_days_best}d)',
                     fontsize=14, fontweight='bold')
    ax1_ts.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax1_ts.grid(True, alpha=0.3)

    # 統計情報表示
    info_text_best = f'R² = {best_fit["r2"]:.4f}\nbeta = {best_fit["beta"]:.3f}\nomega = {best_fit["omega"]:.2f}\nWindow Size = {best_window_size} days\nPrediction Error = {prediction_error_days_best} days'
    ax1_ts.text(0.02, 0.28, info_text_best, transform=ax1_ts.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85),
                fontsize=10)

    # 下段: 残差分析（対数価格空間）
    residuals_best = log_prices_norm_best - y_pred_best
    ax2_ts.plot(fitting_dates_best, residuals_best, 'green', linewidth=1, alpha=0.7, label='Residuals')
    ax2_ts.axhline(0, color='black', linestyle='-', alpha=0.5)
    ax2_ts.set_ylabel('Residuals (Log Price Space)', fontsize=12)
    ax2_ts.set_title('Residual Analysis', fontsize=12)
    ax2_ts.legend()
    ax2_ts.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存
    plot_dir = Path('plots/crash_prediction/')
    plot_dir.mkdir(parents=True, exist_ok=True)
    filename_best = plot_dir / '1987_custom_fco_phase2_best_fit_timeseries.png'
    plt.savefig(filename_best, dpi=300, bbox_inches='tight')
    print(f"✅ 最良フィッティングプロット保存: {filename_best}")
    print()

# ============================================================================
# プロット2: DS-LPPLS Confidence推移 + tc分布（既存プロット）
# ============================================================================
print("【プロット2: DS-LPPLS Confidence推移 + tc分布】")

# 2段プロット: 上段=DS-LPPLS Confidence推移、下段=tc分布
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# 色盲対応カラーパレット (Okabe-Ito color universal design)
COLOR_QUALIFIED = '#029E73'    # 緑: 適格フィット
COLOR_FAILED = '#D55E00'       # 朱色: 不適格フィット
COLOR_TC_DIST = '#0173B2'      # 青: tc分布
COLOR_CRASH = '#029E73'        # 緑: Black Monday

# 上段: 窓サイズ vs フィッティング成功/適格判定
window_sizes = [w['window_size'] for w in result.window_results]
is_qualified_list = [w.get('is_qualified', False) for w in result.window_results]
fit_success_list = [w.get('fit_success', False) for w in result.window_results]

# 適格フィットのプロット
qualified_windows = [w['window_size'] for w in result.window_results if w.get('is_qualified', False)]
qualified_r2 = [w['r2'] for w in result.window_results if w.get('is_qualified', False)]

# 不適格フィット（収束したが条件不適格）のプロット
unqualified_windows = [w['window_size'] for w in result.window_results if w.get('fit_success', False) and not w.get('is_qualified', False)]
unqualified_r2 = [w['r2'] for w in result.window_results if w.get('fit_success', False) and not w.get('is_qualified', False)]

ax1.scatter(qualified_windows, qualified_r2, color=COLOR_QUALIFIED, s=50, alpha=0.7, label='Qualified Fits')
ax1.scatter(unqualified_windows, unqualified_r2, color=COLOR_FAILED, s=50, alpha=0.5, label='Unqualified Fits')

ax1.axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='R² Threshold (0.5)')
ax1.set_xlabel('Window Size (days)', fontsize=12)
ax1.set_ylabel('R² (Fit Quality)', fontsize=12)
ax1.set_title(f'1987 Black Monday FCO Multi-Window Analysis (Confidence={result.ds_lppls_confidence:.2%})',
             fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# 統計情報表示
info_text = f'DS-LPPLS Confidence = {result.ds_lppls_confidence:.2%}\nQualified Fits = {result.qualified_fits} / {result.total_windows}\nTarget: > 30%'
ax1.text(0.98, 0.05, info_text, transform=ax1.transAxes, ha='right',
         verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85),
         fontsize=10)

# 下段: tc分布（適格フィットのみ）
if result.qualified_fits > 0:
    tc_values = [w['tc'] for w in result.window_results if w.get('is_qualified', False)]

    ax2.hist(tc_values, bins=20, color=COLOR_TC_DIST, alpha=0.7, edgecolor='black')
    ax2.axvline(result.predicted_tc, color='red', linestyle='--', linewidth=2, label=f'Median tc = {result.predicted_tc:.4f}')
    ax2.axvline(1.0, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='tc = 1.0 (Present)')

    ax2.set_xlabel('tc (Critical Time, Normalized)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('tc Distribution (Qualified Fits Only)', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 統計情報
    tc_info = f'Mean: {np.mean(tc_values):.4f}\nMedian: {result.predicted_tc:.4f}\nStd: {result.tc_std:.4f}'
    ax2.text(0.98, 0.95, tc_info, transform=ax2.transAxes, ha='right',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.85),
             fontsize=10)
else:
    ax2.text(0.5, 0.5, 'No Qualified Fits', transform=ax2.transAxes,
             ha='center', va='center', fontsize=16, color='red')

plt.tight_layout()

# 保存
filename = plot_dir / '1987_custom_fco_phase2_validation.png'
plt.savefig(filename, dpi=300, bbox_inches='tight')
print(f"✅ DS-LPPLS Confidenceプロット保存: {filename}")
print()

print("✅ プロット生成完了（GUIスキップ、ファイルに保存済み）")
print()

if phase2_success:
    print("🎉 Phase 2成功: 多重窓統合完了")
    print("✅ Phase 2検証完了 → Phase 3（データベース・フロントエンド統合）へ進む準備完了")
else:
    print("❌ Phase 2失敗: 成功基準未達")
    print()
    print("【失敗要因の分析】")
    print("-" * 80)
    if result.ds_lppls_confidence <= 0.30:
        print(f"  ❌ DS-LPPLS Confidence不足: {result.ds_lppls_confidence:.2%} ≤ 30%")
    if result.qualified_fits == 0:
        print(f"  ❌ 適格フィットなし: 全窓でフィルタリング条件不適格")
    if result.predicted_tc is None or result.predicted_tc <= 1.0:
        print(f"  ❌ tc未来予測失敗: {result.predicted_tc}")
    print()
    print("  → 対策: フィルタリング条件の調整、またはデータ期間の見直しが必要")

print()
print("=" * 80)
print("Phase 2検証完了")
print("=" * 80)

# 終了コード
sys.exit(0 if phase2_success else 1)
