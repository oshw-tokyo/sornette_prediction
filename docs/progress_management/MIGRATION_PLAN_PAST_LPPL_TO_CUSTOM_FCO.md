# 移行計画: 過去LPPL実装 → カスタムFCO実装

**作成日**: 2025-10-11
**担当**: Claude Code
**優先度**: HIGH
**関連Issue**: I124
**状態**: 計画策定完了 → ユーザー承認待ち

---

## 📋 移行計画概要

本計画は、過去のLPPL実装（100/100スコア達成）をベースに、FCOレベル（126窓多重時間窓解析 + DS-LPPLS指標）にアップグレードする移行計画です。

**重要**: Boulder LPPLS（MIT License, 外部ライブラリ）は使用せず、**自前のFCO実装**を構築します。

---

## 🎯 移行戦略

### 基本方針

1. **ファイルごと置き換え方式**
   - 既存 `core/fitting/fco_engine.py` を直接修正せず、新規ファイルとして実装
   - 実装完了後に`fco_engine.py`をファイルごと置き換え
   - 旧ファイルは`fco_engine_boulder.py.bak`としてバックアップ

2. **段階的実装 + 継続的検証**
   - 各Phase完了時に再現性テスト実施
   - Phase 1: 単一窓で100/100スコア達成を確認
   - Phase 2: 多重窓統合を段階的に実装（10→50→126窓）
   - Phase 3: 完全統合後の最終検証

3. **科学的妥当性の保証**
   - 過去実装の数学的ロジックを厳密に保持
   - 境界条件・最適化手法を変更しない
   - コード内に科学的根拠を詳細コメント

---

## 📐 実装フェーズ

### Phase 1: 過去実装の復元・単一窓検証 (2-3日)

#### 目的
過去のLPPL実装を新しいアーキテクチャで復元し、単一窓で100/100スコア達成を確認

#### 作業内容

1. **新規ファイル作成**
   - `core/fitting/custom_fco_engine.py` - 新FCOエンジン
   - `core/fitting/lppl_optimizer.py` - LPPL最適化ロジック
   - `core/fitting/lppl_utils.py` - ユーティリティ関数

2. **LPPL数式の実装** (`lppl_utils.py`)
   ```python
   def logarithm_periodic_func(t, tc, beta, omega, phi, log_A, B, C):
       """
       Sornette論文式(54): LPPL数式

       log(p(t)) = A + B*(tc-t)^β + C*(tc-t)^β*cos(ω*log(tc-t) + φ)

       Args:
           t: 正規化時間 [0, 1]
           tc: 臨界時刻（tc > 1.0で未来予測）
           beta: べき乗指数 (典型値: 0.3-0.7)
           omega: 角周波数 (典型値: 5.0-8.0)
           phi: 位相 (-8π ~ 8π)
           log_A: オフセット（対数）
           B: 振幅パラメータ
           C: 振幅パラメータ

       Returns:
           log(price): 対数価格

       【科学的根拠】
       - 出典: "Why Stock Markets Crash" (Sornette, 2003), 式(54)
       - 実証: archive/src_pre_migration_backup/fitting/utils.py
       - 実績: 1987年ブラックマンデー 100/100スコア達成

       ⚠️ この数式は科学的再現性の根幹です。むやみに変更しないこと。
       """
       dt = tc - t
       if np.any(dt <= 0):
           # tc <= t の場合は無限大を返す（フィッティング失敗）
           return np.full_like(t, np.inf)

       power_law_term = np.power(dt, beta)
       oscillation_term = np.cos(omega * np.log(dt) + phi)

       return np.exp(log_A) + B * power_law_term + C * power_law_term * oscillation_term
   ```

3. **グリッドサーチ最適化の実装** (`lppl_optimizer.py`)
   ```python
   def fit_lppl_grid_search(
       t: np.ndarray,
       log_prices: np.ndarray,
       n_tries: int = 10
   ) -> Dict[str, float]:
       """
       グリッドサーチ + 境界付き最適化によるLPPLフィッティング

       【アルゴリズム】
       1. グリッドサーチ: tc, beta, omega の組み合わせを体系的に探索
       2. 境界付き最適化: scipy.optimize.curve_fit with bounds
       3. ロバスト損失関数: loss='soft_l1'（外れ値耐性）

       【科学的根拠】
       - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:36-157
       - 成功実績: 1987年ブラックマンデー 100/100スコア
       - Boulder LPPLSとの違い: 境界条件付き最適化（vs 無制約）

       ⚠️ パラメータ境界は過去実装の値を厳守すること
       """
       # グリッドサーチによる初期値生成
       tc_values = np.linspace(1.01, 1.5, n_tries)
       beta_values = np.linspace(0.30, 0.45, n_tries)
       omega_values = np.linspace(5.0, 8.0, n_tries)

       # 境界条件（過去実装準拠）
       bounds = (
           [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
           [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]   # upper
       )

       best_result = None
       best_r2 = -np.inf

       for tc in tc_values:
           for beta in beta_values:
               for omega in omega_values:
                   p0 = [tc, beta, omega, 0.0, np.log(np.mean(np.exp(log_prices))),
                         (log_prices[-1]-log_prices[0])/(t[-1]-t[0]), 0.1]

                   try:
                       popt, pcov = curve_fit(
                           logarithm_periodic_func,
                           t, log_prices,
                           p0=p0,
                           bounds=bounds,
                           method='trf',  # Trust Region Reflective
                           ftol=1e-6, xtol=1e-6, gtol=1e-6,
                           loss='soft_l1',  # ロバスト損失関数
                           max_nfev=50000
                       )

                       # R²計算
                       y_fit = logarithm_periodic_func(t, *popt)
                       r2 = 1 - np.sum((log_prices - y_fit)**2) / np.sum((log_prices - np.mean(log_prices))**2)

                       if r2 > best_r2:
                           best_r2 = r2
                           best_result = {
                               'tc': popt[0],
                               'beta': popt[1],
                               'omega': popt[2],
                               'phi': popt[3],
                               'A': np.exp(popt[4]),
                               'B': popt[5],
                               'C': popt[6],
                               'r2': r2
                           }
                   except Exception:
                       continue

       if best_result is None:
           raise ValueError("All grid search attempts failed")

       return best_result
   ```

4. **単一窓FCOエンジン** (`custom_fco_engine.py`)
   ```python
   class CustomFCOEngine:
       """
       カスタムFCOエンジン（過去LPPL実装ベース）

       【実装方針】
       - Phase 1: 単一窓のみ（過去実装復元）
       - Phase 2: 多重窓統合（126窓）
       - Phase 3: DS-LPPLS指標統合
       """

       def fit_single_window(self, prices: np.ndarray) -> Dict[str, float]:
           """
           単一窓でのLPPLSフィッティング

           【時間単位の定義】
           - 入力: 生の価格データ（任意長）
           - 正規化: t ∈ [0, 1]
           - フィッティング: 正規化時間でLPPLS最適化
           - tc: 正規化時間での臨界時刻（tc > 1.0で未来予測）
           - 出力: 実日付への逆変換（後でPhase 2で実装）

           ⚠️ 時間正規化は過去実装の [0, 1] を厳守
           """
           # 時間正規化
           t = np.linspace(0, 1, len(prices))
           log_prices = np.log(prices) - np.log(prices[0])

           # グリッドサーチ最適化
           result = fit_lppl_grid_search(t, log_prices, n_tries=10)

           return result
   ```

5. **再現性テスト実装**
   - `tests/custom_fco/test_1987_black_monday_single_window.py`
   - 期待結果: R² > 0.9, tc > 1.0

#### 成功基準
- ✅ 1987年ブラックマンデー単一窓: R² > 0.9
- ✅ tc > 1.0（未来予測）
- ✅ 100/100スコア達成（過去実装と同等）

---

### Phase 2: 多重窓解析統合 (1週間)

#### 目的
単一窓フィッティングを126窓に拡張し、DS-LPPLS指標を計算

#### 作業内容

1. **多重窓ループ実装** (`custom_fco_engine.py`)
   ```python
   def compute_ds_lppls_confidence(self, prices: np.ndarray) -> FCOAnalysisResult:
       """
       多重時間窓解析によるDS-LPPLS Confidence計算

       【FCO標準手法】
       - 窓サイズ: 750 → 125日（5日刻み）→ 126窓
       - 各窓: 独立にLPPLSフィッティング
       - フィルタリング: FCO標準条件（Damping, Oscillation等）
       - Confidence: 適格フィット率 * 100

       【時間単位の変換】
       各窓で:
       1. 時間正規化: t ∈ [0, 1]
       2. フィッティング: tc（正規化時間）
       3. 実日付変換: tc_real_days = (tc - 1.0) * window_size
       4. クラッシュ予測日: analysis_basis_date + timedelta(days=tc_real_days)
       """
       window_results = []
       qualified_fits = 0

       for window_size in range(750, 125-1, -5):  # 126窓
           # 窓データ切り出し
           window_prices = prices[-window_size:]

           # 時間正規化
           t = np.linspace(0, 1, window_size)
           log_prices = np.log(window_prices) - np.log(window_prices[0])

           # グリッドサーチフィッティング
           try:
               result = fit_lppl_grid_search(t, log_prices, n_tries=10)
           except Exception:
               continue

           # tc未来制約チェック
           if result['tc'] < 1.01:  # tc <= 1.0は過去予測（不適格）
               continue

           # Damping & Oscillation計算（FCO標準）
           m = result['beta']
           w = result['omega']
           B = result['B']
           C = result['C']

           # ⚠️ 注意: 過去実装では beta と表記、FCOでは m と表記（同じ物理量）
           damping = m * abs(B) / (w * abs(C)) if w != 0 and C != 0 else 0

           t1 = 0.0  # 正規化時間の開始
           t2 = 1.0  # 正規化時間の終了
           tc = result['tc']
           oscillation = (w / (2 * np.pi)) * np.log((tc - t1) / (tc - t2)) if tc > t2 else 0

           # FCO標準フィルタリング
           is_qualified = (
               0.3 < m < 0.7 and      # 過去実装の範囲（Boulder標準より狭い）
               5.0 < w < 8.0 and      # 過去実装の範囲（Boulder標準より狭い）
               damping > 0.5 and
               oscillation > 2.5 and
               result['r2'] > 0.5     # R²閾値（調整可能）
           )

           if is_qualified:
               qualified_fits += 1

           # 実日付変換
           tc_real_days = (tc - 1.0) * window_size
           predicted_crash_date = None  # Phase 3で実装

           window_results.append({
               'window_size': window_size,
               'tc_normalized': tc,
               'tc_real_days': tc_real_days,
               'beta': m,
               'omega': w,
               'r2': result['r2'],
               'damping': damping,
               'oscillation': oscillation,
               'is_qualified': is_qualified
           })

       ds_lppls_confidence = (qualified_fits / len(window_results)) * 100

       # バブルタイプ判定（既存ロジック流用）
       bubble_type = 'positive_bubble' if ds_lppls_confidence > 25 else 'no_bubble'

       return FCOAnalysisResult(
           ds_lppls_confidence=ds_lppls_confidence,
           bubble_type=bubble_type,
           window_results=window_results,
           total_windows=len(window_results),
           trust_indicator=ds_lppls_confidence  # 簡易版
       )
   ```

2. **段階的検証**
   - 10窓: 基本動作確認
   - 50窓: 中規模動作確認
   - 126窓: 完全動作確認

3. **フィルタリング条件の調整**
   - m, ω範囲: 過去実装準拠 vs Boulder標準
   - R²閾値: データに応じて調整
   - Damping/Oscillation: FCO標準維持

#### 成功基準
- ✅ 1987年ブラックマンデー: DS-LPPLS Confidence > 30%
- ✅ バブルタイプ: positive_bubble判定
- ✅ 全126窓でフィッティング正常動作

---

### Phase 3: データベース・フロントエンド統合 (2-3日)

#### 目的
既存のデータベーススキーマ・フロントエンドとの整合性確保

#### 作業内容

1. **入力インターフェース統合**
   - 現在: `FCOEngine.compute_ds_lppls_confidence(prices)`
   - 変更なし（同じシグネチャ）

2. **出力インターフェース統合**
   - 現在: `FCOAnalysisResult` (dataclass)
   - 変更なし（同じデータ構造）

3. **データベース保存**
   - 現在: 全126窓データ保存
   - 変更なし（同じスキーマ）

4. **日時変換の統合**
   - tc_normalized → tc_real_days → predicted_crash_date
   - `infrastructure/database/integration_helpers.py` の既存ロジック流用

5. **フロントエンドAPI統合**
   - FastAPI エンドポイント変更なし
   - React フロントエンド変更なし

#### 成功基準
- ✅ データベース保存正常動作
- ✅ フロントエンド表示正常動作
- ✅ APIエンドポイント後方互換性維持

---

### Phase 4: 最終検証・最適化 (3-5日)

#### 目的
完全統合システムでの最終検証・パフォーマンス最適化

#### 作業内容

1. **歴史的クラッシュ検証**
   - 1987年ブラックマンデー: Confidence > 30%
   - 2000年ドットコムバブル: Confidence > 20%
   - 2008年リーマンショック: 新規検証

2. **パフォーマンス最適化**
   - グリッドサーチ並列化（multiprocessing）
   - NumPyベクトル化最適化
   - キャッシング戦略

3. **エラーハンドリング強化**
   - フィッティング失敗時のフォールバック
   - データ異常検出
   - ログ記録強化

4. **ドキュメント整備**
   - API仕様書更新
   - ユーザーガイド更新
   - 開発者向けドキュメント更新

#### 成功基準
- ✅ 全歴史的クラッシュで目標Confidence達成
- ✅ パフォーマンス: 単一銘柄解析 < 30秒
- ✅ 論文再現テスト: `python entry_points/main.py validate --crash 1987 --fco` 成功

---

## ⚠️ 重要な注意事項

### 1. FCOコード置き換え戦略

**現在のFCO実装箇所には保護コメントあり**:
```python
# ⚠️ 【重要】このコードはFCO標準実装です。むやみに変更しないこと
```

**移行時の対応**:
- これらのコメントは**古いFCO（Boulder LPPLS）を保護するため**のもの
- 新しいカスタムFCO実装では、**これらのコメントを更新**する
- 例:
  ```python
  # ⚠️ 【重要】このコードはカスタムFCO実装（過去LPPL準拠）です
  # - 実装根拠: archive/src_pre_migration_backup/fitting/fitter.py
  # - 実証実績: 1987年ブラックマンデー 100/100スコア
  # - むやみに変更しないこと - 科学的再現性の根幹
  # - 変更時は必ず再現性テスト実施
  ```

### 2. ファイルごと置き換え方式の手順

```bash
# Phase 1-3完了後、最終置き換え時:

# 1. 旧実装をバックアップ
mv core/fitting/fco_engine.py core/fitting/fco_engine_boulder.py.bak

# 2. 新実装をリネーム
mv core/fitting/custom_fco_engine.py core/fitting/fco_engine.py

# 3. インポート文の更新
# 既存コード:
#   from core.fitting.fco_engine import FCOEngine
# → 変更なし（ファイル名が同じ）

# 4. 再現性テスト実行
python entry_points/main.py validate --crash 1987 --fco

# 5. 成功を確認後、Gitコミット
git add core/fitting/fco_engine.py
git commit -m "✨ カスタムFCO実装完了 (過去LPPL準拠)"
```

### 3. 科学的コメントの記載

**コード内に以下を必ず記載**:

1. **科学的根拠**
   ```python
   # 【科学的根拠】
   # - 理論: Sornette (2003) "Why Stock Markets Crash", 式(54)
   # - 実装元: archive/src_pre_migration_backup/fitting/fitter.py:64-67
   # - 実証実績: 1987年ブラックマンデー 100/100スコア
   ```

2. **データフロー・単位**
   ```python
   # 【時間単位の定義】
   # - 入力: 実日付価格データ（例: 1000点）
   # - 正規化: t ∈ [0, 1]
   # - フィッティング: 正規化時間でLPPLS最適化
   # - tc: 正規化時間（tc > 1.0で未来予測）
   # - 出力変換: tc_real_days = (tc - 1.0) * window_size
   ```

3. **パラメータ定義・境界条件**
   ```python
   # 【パラメータ境界条件】
   # 以下は archive/src_pre_migration_backup/fitting/fitter.py:64-67 準拠
   bounds = (
       [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
       [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]   # upper
   )
   # tc:    1.01-1.5  (未来予測、正規化時間)
   # beta:  0.3-0.7   (べき乗指数、典型値)
   # omega: 5.0-8.0   (角周波数、観測可能範囲)
   ```

4. **むやみな変更の防止**
   ```python
   # ⚠️ 【重要】科学的再現性の中核です
   # - 変更前に必ず再現性テスト実施
   # - 過去実装（100/100）との整合性維持
   # - 変更履歴: Gitコミットに科学的根拠記載必須
   # - 参照: docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md
   ```

---

## 📊 工数見積もり

| Phase | 作業内容 | 工数 | 成果物 |
|-------|---------|------|--------|
| **Phase 1** | 過去実装復元・単一窓検証 | 2-3日 | 単一窓100/100スコア達成 |
| **Phase 2** | 多重窓解析統合 | 1週間 | 126窓FCO実装完了 |
| **Phase 3** | DB/フロントエンド統合 | 2-3日 | 完全統合動作確認 |
| **Phase 4** | 最終検証・最適化 | 3-5日 | 本番リリース準備完了 |
| **合計** | - | **2-3週間** | カスタムFCO実装完成 |

---

## 🔗 関連ドキュメント

### 科学的根拠
- `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md` - 科学的手法差分
- `archive/src_pre_migration_backup/fitting/fitter.py` - 過去の成功実装

### 調査結果
- `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md` - 時間単位調査
- `docs/progress_management/FCO_IMPROVEMENT_IMPLEMENTATION_SUMMARY.md` - 実装サマリー
- `docs/progress_management/ALTERNATIVE_SOLUTION_PAST_LPPL_TO_FCO.md` - 代替策提案

### 現在のFCO実装
- `core/fitting/fco_engine.py` - 現在のFCO実装（Boulder LPPLS準拠、問題あり）

### テスト・検証
- `tests/custom_fco/` - カスタムFCO用テストディレクトリ（Phase 1で作成）

---

## 📝 次のアクション

### 優先度1: ユーザー承認
- **内容**: この移行計画の承認
- **判断基準**: 工数・リスク・科学的妥当性

### 優先度2: ドキュメント整理（本計画作成と並行実施）
- **内容**: 既存FCO移行計画のアーカイブ・参照整合性確保
- **成果物**: 混乱のないドキュメント構造

### 優先度3: Phase 1実装開始（承認後）
- **作業**: 過去実装復元・単一窓検証
- **期間**: 2-3日
- **成果物**: 単一窓100/100スコア達成

---

**作成者**: Claude Code
**最終更新**: 2025-10-11
**ステータス**: 計画策定完了 → ユーザー承認待ち
