# 代替策: 過去LPPL実装のFCOレベルアップグレード

**作成日**: 2025-10-11
**状態**: 検討中
**優先度**: HIGH
**関連Issue**: I124

---

## 📋 背景

### 問題の経緯
1. **現在のFCO実装**: DS-LPPLS Confidence 0% (1987年ブラックマンデー検証)
2. **改善試行**: 多重試行+tc未来制約フィルタリング実装 → **依然として0%**
3. **根本原因**: Boulder LPPLSフィッティングがBoulder標準範囲外のパラメータを生成

### 診断結果
```
窓0の分析結果:
- tc: 1619.2 (t2=999より620日未来) ✅ tc未来制約達成
- m: 2.2 (範囲外: 0.0-1.0) ❌ Boulder標準違反
- w: 188.7 (範囲外: 2.0-15.0) ❌ Boulder標準違反
- oscillation: 23.0 (>2.5) ✅ 合格
- damping: 1.26 (>0.5) ✅ 合格

結論: tc未来制約は機能、しかしm/ω範囲外で全て失格
```

### 試行済みアプローチ
1. ✅ Boulder LPPLS標準フィルタリング実装
2. ✅ Sornette 30日要件追加
3. ✅ 多重試行+tc未来制約フィルタリング
4. ❌ **全て0% Confidence**

---

## 🎯 代替策の概要

### アプローチ: 過去のLPPL実装をFCOレベルにアップグレード

**基本方針**:
- 過去の成功実装（100/100スコア達成）を基盤とする
- FCO標準の多重時間窓解析（126窓）を統合
- DS-LPPLS Confidence/Trust指標を実装

### 過去の成功実装の特徴
**ファイル**: `archive/src_pre_migration_backup/fitting/fitter.py`

#### 1. 時間正規化
```python
t = np.linspace(0, 1, len(prices))  # [0,1]に正規化
```

#### 2. 明示的境界条件
```python
bounds = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # tc >= 1.01で未来保証
    [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]
)
```

#### 3. グリッドサーチ + 最適化
```python
# グリッドサーチで初期値決定
tc_values = np.linspace(1.01, 1.5, n_tries)
beta_values = np.linspace(0.30, 0.45, n_tries)
omega_values = np.linspace(5.0, 8.0, n_tries)

# scipy.optimize.minimize with bounds
result = minimize(
    cost_function,
    initial_guess,
    method='L-BFGS-B',
    bounds=bounds
)
```

#### 4. 品質評価
```python
# R²計算
ss_res = np.sum((log_prices - fitted) ** 2)
ss_tot = np.sum((log_prices - np.mean(log_prices)) ** 2)
r2 = 1 - (ss_res / ss_tot)
```

### 現在のFCO実装の利点
**ファイル**: `core/fitting/fco_engine.py`

#### 1. 多重時間窓解析
```python
# 126窓（125-750日、5日ステップ）
for window_size in range(750, 125-1, -5):
    # 各窓でLPPLSフィッティング
```

#### 2. DS-LPPLS指標
```python
# Positive/Negative bubble confidence
ds_lppls_confidence = (qualified_fits / total_windows) * 100
```

#### 3. Boulder標準フィルタリング
```python
# Oscillation, Damping, m/ω範囲チェック
is_qualified = (
    tc_in_range and
    FILTER_M_MIN < m < FILTER_M_MAX and
    FILTER_OMEGA_MIN < w < FILTER_OMEGA_MAX and
    O > FILTER_OSCILLATION_MIN and
    damping > FILTER_DAMPING_MIN
)
```

---

## 🛠️ 実装計画

### Phase 1: 過去実装の復元・検証
**作業内容**:
1. `archive/src_pre_migration_backup/fitting/fitter.py`のロジック抽出
2. 時間正規化+境界条件付きフィッティング関数作成
3. 1987年ブラックマンデー単一窓検証

**期待結果**:
- 単一窓でR² > 0.9達成
- tc未来予測成功（tc > 1.0）

### Phase 2: 多重窓解析統合
**作業内容**:
1. FCO 126窓ループに過去実装フィッティング統合
2. 各窓で時間正規化+境界条件付きフィッティング実行
3. 窓サイズごとに正規化時間調整

**実装例**:
```python
for window_size in range(750, 125-1, -5):
    # 窓データ切り出し
    window_prices = prices[-window_size:]

    # 時間正規化
    t_normalized = np.linspace(0, 1, window_size)
    log_prices_normalized = np.log(window_prices)

    # 過去実装のフィッティング
    result = legacy_lppl_fit(
        t_normalized,
        log_prices_normalized,
        tc_bounds=(1.01, 1.5),  # 未来保証
        beta_bounds=(0.3, 0.7),
        omega_bounds=(5.0, 8.0)
    )

    # 日付変換（正規化時間 → 実日付）
    if result.tc > 1.0:
        days_beyond = (result.tc - 1.0) * window_size
        predicted_crash_date = analysis_basis_date + timedelta(days=days_beyond)
```

### Phase 3: フィルタリング条件調整
**作業内容**:
1. 過去実装のパラメータ範囲とBoulder標準の整合性確認
2. フィルタリング条件を過去実装基準に調整
3. DS-LPPLS Confidence計算ロジック適用

**調整内容**:
```python
# 過去実装準拠のフィルタリング
FILTER_M_MIN = 0.3  # 過去: 0.3-0.7
FILTER_M_MAX = 0.7
FILTER_OMEGA_MIN = 5.0  # 過去: 5.0-8.0
FILTER_OMEGA_MAX = 8.0

# tc未来制約（正規化時間）
MIN_TC_NORMALIZED = 1.01  # tc > 1.0で未来保証
```

### Phase 4: 検証・最適化
**作業内容**:
1. 1987年ブラックマンデー: DS-LPPLS Confidence 30%以上達成
2. 2000年ドットコムバブル検証
3. パラメータチューニング

**成功基準**:
- 1987年: Confidence 30%以上
- 2000年: Confidence 20%以上
- 100/100スコア維持

---

## 📊 予想される課題と対策

### 課題1: 時間正規化とFCO多重窓の整合性
**問題**: 各窓サイズで正規化範囲が異なる
**対策**: 窓サイズごとに適切なtc範囲を動的計算

### 課題2: パラメータ範囲の違い
**問題**: 過去実装(0.3-0.7)とBoulder標準(0.0-1.0)の不一致
**対策**: 科学的妥当性を検証後、過去実装範囲を優先

### 課題3: 計算時間
**問題**: グリッドサーチ+最適化で時間増加
**対策**: 並列化・試行回数最適化

---

## 🎯 期待効果

### 成功時
- ✅ 1987年ブラックマンデー: DS-LPPLS Confidence 30%以上
- ✅ 過去の100/100スコア実装との整合性
- ✅ FCO標準の多重窓解析実現
- ✅ 科学的妥当性の担保

### リスク
- ⚠️ 実装期間: 2-3週間
- ⚠️ Boulder LPPLS標準からの逸脱
- ⚠️ 未知のエッジケース

---

## 📝 次のアクション

### 優先度1: ユーザー承認
- **内容**: この代替策の実施可否確認
- **判断基準**: 実装期間・科学的妥当性・保守性

### 優先度2: Phase 1実装（承認後）
- **作業**: 過去実装復元・単一窓検証
- **期間**: 2-3日
- **成果物**: 時間正規化+境界条件付きフィッティング関数

### 優先度3: 完全統合（Phase 1成功後）
- **作業**: FCO多重窓解析統合
- **期間**: 1-2週間
- **成果物**: FCOレベルアップグレード版

---

## 🔗 関連ドキュメント

- **過去の成功実装**: `archive/src_pre_migration_backup/fitting/fitter.py`
- **FCO現在実装**: `core/fitting/fco_engine.py`
- **調査レポート**: `workspace_for_claude/FINAL_ROOT_CAUSE_ANALYSIS_REPORT.md`
- **Boulder統合レポート**: `workspace_for_claude/boulder_lppls_integration_report.md`

---

**作成者**: Claude Code
**最終更新**: 2025-10-11
**ステータス**: ユーザー承認待ち
