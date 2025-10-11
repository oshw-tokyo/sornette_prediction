# FCO vs 過去LPPL実装 - 科学的手法差分抽出

**作成日**: 2025-10-11
**担当**: Claude Code
**目的**: 代替策実装（過去LPPL→FCOアップグレード）のための完全差分抽出

---

## 📋 概要

本文書は、ユーザー要求2.2に従い、FCO実装と過去LPPL実装の科学的手法の差分を**もれなく抽出**したものです。
代替策実装時には、これらの差分を考慮しながら、繰り返し再現性テストを実施します。

---

## 🔬 比較対象

### FCO実装（現在・問題あり）
- **ファイル**: `core/fitting/fco_engine.py` (2025-10-11版)
- **外部ライブラリ**: Boulder LPPLS v0.6.20
- **結果**: 0% Confidence（1987年ブラックマンデー）
- **状態**: フィッティング収束失敗

### 過去LPPL実装（成功実績あり）
- **ファイル**: `archive/src_pre_migration_backup/fitting/fitter.py`
- **外部ライブラリ**: なし（scipy.optimize.curve_fit使用）
- **結果**: 100/100スコア（1987年ブラックマンデー）
- **状態**: 実証済み

---

## 🔍 科学的手法の差分（カテゴリ別）

### 1. **時間正規化方式**

#### 過去LPPL実装
```python
# Line 28: 時間を [0, 1] に正規化
t = np.linspace(0, 1, len(prices))
```

**特徴**:
- 時間範囲を常に [0, 1] に正規化
- データ長に依存しない統一スケール
- tc > 1.0 で未来予測を保証

#### FCO実装
```python
# Line 219-221: インデックスベース（連番）
if timestamps is None:
    timestamps = np.arange(n)  # 0, 1, 2, ..., 999
```

**特徴**:
- 連番インデックス（0, 1, 2, ...）
- データ長に応じてスケールが変化
- tc > len(prices) で未来予測

**科学的影響**:
- パラメータスケールが異なる
- 時間単位検証では両方式とも失敗（Boulder LPPLSの問題）
- 過去実装は正規化により数値安定性が高い

---

### 2. **フィッティングアルゴリズム**

#### 過去LPPL実装
```python
# Line 98-110: scipy.optimize.curve_fit with bounds
popt, pcov = curve_fit(
    logarithm_periodic_func,
    t, y,
    p0=p0,
    bounds=bounds,  # ← 明示的境界条件
    method='trf',   # ← Trust Region Reflective
    ftol=1e-6,
    xtol=1e-6,
    gtol=1e-6,
    loss='soft_l1',  # ← ロバスト損失関数
    max_nfev=50000
)
```

**特徴**:
- **境界付き最適化**: パラメータを範囲内に制約
- **アルゴリズム**: Trust Region Reflective（境界対応）
- **損失関数**: soft_l1（外れ値にロバスト）
- **最大評価回数**: 50,000回（高精度）

#### FCO実装
```python
# Boulder LPPLS内部（lppls/lppls.py:166-178）
result = minimize(
    self.func_restricted,
    seed,
    method='Nelder-Mead',  # ← シンプレックス法
    # bounds なし（無制約最適化）
)
```

**特徴**:
- **無制約最適化**: 境界条件なし
- **アルゴリズム**: Nelder-Mead（シンプレックス法）
- **初期値**: ランダム生成
- **試行回数**: max_searches回（デフォルト25）

**科学的影響**:
- **境界なし → パラメータ発散**: m=2.2, ω=188.7（範囲外）
- **Nelder-Mead → 局所最小**: 初期値依存性が高い
- **ランダム初期値 → 収束不安定**: 良い初期値を見つけにくい

---

### 3. **初期値決定戦略**

#### 過去LPPL実装
```python
# Line 53-56: グリッドサーチによる体系的探索
tc_values = np.linspace(1.01, 1.5, n_tries)     # tc ∈ [1.01, 1.5]
beta_values = np.linspace(0.30, 0.45, n_tries)  # beta ∈ [0.30, 0.45]
omega_values = np.linspace(5.0, 8.0, n_tries)   # omega ∈ [5.0, 8.0]

# Line 69-72: 3重ループで全組み合わせを試行
for i, tc in enumerate(tc_values):
    for j, beta in enumerate(beta_values):
        for k, omega in enumerate(omega_values):
            # 各組み合わせでフィッティング
```

**特徴**:
- **グリッドサーチ**: tc, beta, omega の組み合わせを体系的に探索
- **試行回数**: n_tries³（例: 10³ = 1000回）
- **網羅性**: パラメータ空間を均等にカバー

#### FCO実装
```python
# Boulder LPPLS内部（lppls/lppls.py:131-145）
for i in range(0, max_searches):
    # ランダム初期値生成
    init_limits = [
        (tc_init_min, tc_init_max),  # tc ∈ [t2-0.2Δt, t2+0.2Δt]
        (0, m_max),                   # m ∈ [0, 1.0]
        (w_min, w_max),               # w ∈ [2.0, 15.0]
        # ...
    ]
    seed = [random.uniform(a[0], a[1]) for a in init_limits]
```

**特徴**:
- **ランダムサンプリング**: 一様分布からランダムに初期値生成
- **試行回数**: max_searches回（例: 25回）
- **網羅性**: 運任せ（良い領域を見逃す可能性）

**科学的影響**:
- **グリッドサーチ → 確実性**: 良い初期値を必ず探索
- **ランダムサーチ → 不確実性**: 良い初期値を見逃す可能性
- **試行回数**: 1000回 vs 25回（40倍の差）

---

### 4. **境界条件（パラメータ制約）**

#### 過去LPPL実装
```python
# Line 64-67: 明示的境界条件
bounds = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower bounds
    [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]   # upper bounds
)
# パラメータ順: [tc, beta, omega, phi, log(A), B, C]
```

**パラメータ制約**:
| パラメータ | 下限 | 上限 | 科学的意味 |
|-----------|------|------|-----------|
| tc | 1.01 | 1.5 | 未来予測（t∈[0,1]の外） |
| beta (β) | 0.3 | 0.7 | べき乗指数（典型値） |
| omega (ω) | 5.0 | 8.0 | 角周波数（観測可能範囲） |
| phi (φ) | -8π | 8π | 位相 |
| log(A) | -10 | 10 | オフセット |
| B | -10 | 10 | 振幅 |
| C | -2.0 | 2.0 | 振幅 |

#### FCO実装
```python
# Boulder LPPLS: 境界条件なし（無制約最適化）
# 事後フィルタリングのみ:
# - m ∈ (0.0, 1.0)
# - ω ∈ (2.0, 15.0)
# - tc ∈ [t2-60, t2+252]
```

**特徴**:
- **最適化中**: 制約なし
- **最適化後**: 範囲外を棄却

**科学的影響**:
- **境界付き → 収束保証**: パラメータが範囲内に保たれる
- **無制約 → 発散リスク**: 極端な値に収束する可能性
- **事後フィルタ → 手遅れ**: 既に収束済みの結果を棄却（無駄）

---

### 5. **LPPLS数式の形式**

#### 過去LPPL実装
```python
# logarithm_periodic_func (utils.py内と推測)
# 式(54): Critical Market Crashes論文準拠
# log(p(t)) = A + B*(tc-t)^β + C*(tc-t)^β*cos(ω*log(tc-t) + φ)
```

**数式パラメータ**:
- **7パラメータ**: tc, β, ω, φ, A, B, C
- **理論準拠**: Sornette論文式(54)

#### FCO実装
```python
# Boulder LPPLS (lppls.py:39-45)
@staticmethod
@njit
def lppls(t, tc, m, w, a, b, c1, c2):
    dt = np.abs(tc - t) + 1e-8
    return a + np.power(dt, m) * (
        b + ((c1 * np.cos(w * np.log(dt))) + (c2 * np.sin(w * np.log(dt))))
    )
```

**数式パラメータ**:
- **7パラメータ**: tc, m, w, a, b, c1, c2
- **変換**:
  - m = β
  - c1 = C * cos(φ), c2 = -C * sin(φ)

**科学的影響**:
- **数学的同等性**: 両者は同じLPPLモデル
- **パラメータ表現の違い**: (C, φ) ↔ (c1, c2)
- **理論的差異なし**: 数学的には同じ

---

### 6. **品質評価指標**

#### 過去LPPL実装
```python
# Line 114: R²計算
residuals, r_squared = calculate_fit_metrics(y, y_fit)

# Line 136: 統計的有意性評価
statistical_significance=assess_statistical_significance(y, y_fit)
```

**評価指標**:
- **R²**: 決定係数（フィット品質）
- **統計的有意性**: p値、信頼区間等

#### FCO実装
```python
# Boulder LPPLS: R²は外部で計算
# フィルタリング条件（FCO標準）:
# - Damping > 0.5
# - Oscillation > 2.5
# - m ∈ (0, 1)
# - ω ∈ (2, 15)
# - tc ∈ [t2-60, t2+252]
```

**評価指標**:
- **Damping**: D = m * |B| / (ω * |C|)
- **Oscillation**: O = (ω/2π) * log((tc-t1)/(tc-t2))
- **R²**: 別途計算

**科学的影響**:
- **FCO標準**: ETH Zurich FCO準拠の評価基準
- **より厳格**: Damping/Oscillation追加条件
- **理論的根拠**: クラッシュハザード率h(t)の非負性

---

### 7. **多重窓解析**

#### 過去LPPL実装
```python
# 単一窓のみ
# 全データ（または指定期間）を1つの窓としてフィッティング
```

**特徴**:
- **窓数**: 1
- **目的**: 単一の最良フィットを見つける
- **出力**: 1つのフィッティング結果

#### FCO実装
```python
# Line 260-285: 多重時間窓ループ
for window_size in range(750, 125-1, -5):  # 126窓
    # 各窓サイズでフィッティング
    window_observations = observations[:, -window_size:]

    # tc未来制約付きフィッティング
    fit_params = self._fit_lppls_with_future_constraint(
        window_observations,
        max_searches=25
    )
```

**特徴**:
- **窓数**: 126（窓サイズ: 750→125日、5日刻み）
- **目的**: 複数窓の合意による信頼性評価
- **出力**: DS-LPPLS Confidence指標

**科学的影響**:
- **単一窓 → シンプル**: 1つの予測
- **多重窓 → ロバスト**: 複数窓の合意による信頼性
- **FCO標準**: ETH Zurich FCOの核心的手法

---

## 📊 差分サマリーテーブル

| 項目 | 過去LPPL実装 | FCO実装 | 影響度 |
|------|------------|---------|--------|
| **時間正規化** | [0, 1] | インデックス | 中 |
| **最適化** | curve_fit (TRF, bounds) | minimize (Nelder-Mead, 無制約) | **高** |
| **初期値戦略** | グリッドサーチ（1000回） | ランダム（25回） | **高** |
| **境界条件** | 明示的境界（7パラメータ） | なし（事後フィルタのみ） | **高** |
| **損失関数** | soft_l1（ロバスト） | 標準二乗誤差 | 中 |
| **LPPLS数式** | 式(54): A+B*(tc-t)^β+... | 同等（パラメータ表現違い） | 低 |
| **品質評価** | R² + 統計的有意性 | Damping + Oscillation + R² | 中 |
| **多重窓** | 単一窓 | 126窓（FCO標準） | **高** |
| **結果** | 100/100スコア | 0% Confidence | - |

---

## 🎯 代替策実装時の統合方針

### Phase 1: 過去実装の復元・単一窓検証

**統合すべき要素**:
1. ✅ 時間正規化 [0, 1]
2. ✅ 境界付き最適化（curve_fit with bounds）
3. ✅ グリッドサーチ初期値戦略
4. ✅ soft_l1損失関数
5. ✅ LPPLS数式（Sornette式(54)）

**検証方法**:
- 1987年ブラックマンデー単一窓でR² > 0.9達成
- tc > 1.0（未来予測）を確認

### Phase 2: FCO多重窓解析統合

**追加すべき要素**:
1. ✅ 126窓ループ（750→125日、5日刻み）
2. ✅ 窓ごとの時間正規化
3. ✅ FCO標準フィルタリング（Damping, Oscillation）
4. ✅ DS-LPPLS Confidence計算

**統合時の注意点**:
- 各窓で独立に時間正規化 [0, 1]
- tc > 1.0 → 実日付への変換（tc_real = t2 + (tc-1.0)*window_size）
- フィルタリング条件の適切な変換

### Phase 3: データベース・フロントエンド整合性

**既存システムとの整合性**:
1. **入力**:
   - 現在: `prices: np.ndarray`
   - 変更なし（過去実装も同じ）

2. **出力**:
   - 現在: `FCOAnalysisResult` (dataclass)
   - 変更なし（DS-LPPLS Confidence等）

3. **データベーススキーマ**:
   - 現在: 全126窓のデータ保存
   - 変更なし（過去実装統合後も同じデータ構造）

4. **フロントエンド**:
   - React + FastAPIフロントエンド開発中
   - APIエンドポイント変更なし

---

## 🧪 再現性テスト戦略

### テストケース

1. **1987年ブラックマンデー** (最優先)
   - 期待: DS-LPPLS Confidence > 30%
   - 基準日: 1987-09-04（42日前）

2. **2000年ドットコムバブル**
   - 期待: Confidence > 20%
   - 定性的検証

3. **新規バリデーションケース**
   - 2008年リーマンショック等

### テスト実行タイミング

- Phase 1完了後: 単一窓で100/100スコア確認
- Phase 2実装中: 各窓数で段階的確認（10窓→50窓→126窓）
- Phase 3完了後: 全統合システムで最終確認

---

## 📝 実装時のコメント記載方針

ユーザー要求に従い、以下の点についてコード内に詳細コメントを記載:

### 1. 科学的重要性
```python
# 【科学的根拠】Boulder vs 過去実装の境界条件比較
# - 過去実装: tc ∈ [1.01, 1.5], β ∈ [0.3, 0.7], ω ∈ [5.0, 8.0]
# - Boulder標準: tc ∈ [t2-60, t2+252], m ∈ [0, 1.0], ω ∈ [2.0, 15.0]
# - 本実装: 過去実装の範囲を採用（100/100スコア実績に基づく）
# - 根拠: archive/src_pre_migration_backup/fitting/fitter.py:64-67
```

### 2. データフロー・単位
```python
# 【時間単位の定義】
# - 入力: 実日付データ（len=1000点）
# - 正規化: t ∈ [0, 1]（過去実装準拠）
# - フィッティング: 正規化時間でLPPLS最適化
# - tc: 正規化時間での臨界時刻（tc > 1.0で未来予測）
# - 出力: 実日付への逆変換（tc_real_days = (tc - 1.0) * window_size）
```

### 3. 定義・境界条件
```python
# 【パラメータ境界条件】
# 以下の境界は archive/src_pre_migration_backup/fitting/fitter.py:64-67 に基づく
# - 科学的妥当性: Sornette論文の典型値範囲
# - 実証的裏付け: 1987年ブラックマンデー 100/100スコア達成
# ⚠️ むやみに変更しないこと - 再現性テスト必須
bounds = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
    [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]   # upper
)
```

### 4. むやみな変更の防止
```python
# ⚠️ 【重要】このセクションは科学的再現性の中核です
# - 変更前に必ず再現性テストを実施すること
# - 過去実装（100/100スコア）との整合性を維持すること
# - 変更履歴: 必ずgitコミットメッセージに科学的根拠を記載
# - 参照: docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md
```

---

## 🔗 関連ドキュメント

### 過去実装
- `archive/src_pre_migration_backup/fitting/fitter.py` - 過去の成功実装

### 現在のFCO実装
- `core/fitting/fco_engine.py` - 現在のFCO実装（問題あり）

### 調査レポート
- `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md` - 時間単位調査
- `docs/progress_management/FCO_IMPROVEMENT_IMPLEMENTATION_SUMMARY.md` - 実装サマリー
- `docs/progress_management/ALTERNATIVE_SOLUTION_PAST_LPPL_TO_FCO.md` - 代替策提案

### 移行計画
- `docs/progress_management/MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md` - 実装移行計画（次に作成）

---

**作成者**: Claude Code
**最終更新**: 2025-10-11
**ステータス**: 差分抽出完了 → 移行計画作成フェーズへ
