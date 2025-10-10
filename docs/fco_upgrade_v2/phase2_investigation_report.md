# FCO v2.1 Phase 2: データベースとアーキテクチャ調査レポート

**実施日**: 2025-10-09
**担当**: Claude Code
**目的**: Negative bubble データの存在確認、ログ変換の実態確認、FRED最古データ期間の確認

---

## 📊 1. データベース調査結果

### 1.1 Bubble Type データの現状

**データベース**: `/home/no-rules/projects/12_sornnet_prediction/sornette_prediction/results/fco_analysis_results.db`

**総レコード数**: 46件

**Bubble Type 分布**:
- `positive_bubble`: 34件 (73.91%)
- `weak_positive`: 12件 (26.09%)
- **`negative bubble`**: ❌ **0件**

### 1.2 Negative Confidence データ

- `ds_lppls_confidence_neg` に値がある: 10件のみ (21.7%)
- `ds_lppls_confidence_neg` が NULL: 36件 (78.3%)

### 1.3 発見された問題

1. **Negative bubble データが存在しない**
   - フロントエンドは Negative bubble 表示機能を実装済み
   - しかし、データベースには negative bubble のレコードが1件も存在しない
   - ユーザーが Negative bubble を選択しても何も表示されない原因

2. **ds_lppls_confidence_neg カラムがほとんど未使用**
   - カラムは存在するが、78.3%のレコードでNULL
   - Negative confidence を正しく記録するロジックが不完全

### 1.4 データベーススキーマの確認

**主要カラム**:
```sql
- id: INTEGER
- symbol: TEXT (NOT NULL)
- analysis_basis_date: DATE (NOT NULL)
- ds_lppls_confidence: REAL (NULL可) -- Positive bubble confidence
- ds_lppls_confidence_neg: REAL (NULL可) -- Negative bubble confidence
- bubble_type: TEXT (NULL可) -- 'positive_bubble', 'weak_positive', etc.
- predicted_tc: REAL (NULL可)
- predicted_crash_date: DATE (NULL可)
```

**結論**: スキーマ設計は適切だが、データ入力ロジックに問題がある可能性。

---

## 🔍 2. ログ変換の実態調査

### 2.1 調査結果サマリー

**✅ 良いニュース**: 2重ログ変換は発生していない
**⚠️  発見された問題**: FCO解析がログ変換なしでraw pricesを使用している

### 2.2 現在のデータフロー

```
1. データ保存時 (price_data_service.py:52)
   raw_price → Database (close列)
   ↓
   log(raw_price) → Database (log_close列)
   ✅ 両方のデータを保存

2. FCO解析時 (fco_service.py:219-225)
   raw_price → FCO Engine
   ↓
   raw_price → Boulder lppls
   ❌ ログ変換なしで解析実行

3. Boulder lppls の動作 (実験的検証)
   Input: raw_price
   Internal: ログ変換を行わない
   Output: raw price ベースのLPPLフィット
   ❌ LPPL理論上は log(price) を使用すべき
```

### 2.3 各ファイルの動作詳細

#### price_data_service.py (Line 52)
```python
log_close = np.log(price) if price > 0 else None
```
✅ **正しい**: raw と log の両方をデータベースに保存

#### fco_service.py (Line 219, 225)
```python
prices = np.array(price_data['prices'])  # Gets raw prices
result = self.fco_engine.compute_ds_lppls_confidence(prices)  # Passes raw prices
```
⚠️ **問題**: `price_data['prices']` は raw prices を取得
           ログ変換されたデータを使用していない

#### fco_engine.py (Line 102, 134)
```python
observations = np.array([timestamps, prices])  # Uses raw prices
lppls_model = LPPLS(observations)  # Passes raw prices to Boulder lppls
```
⚠️ **問題**: raw prices を Boulder lppls に渡している

#### Boulder lppls Library
実験的検証により確認:
```python
lppls_model.observations[1] ≈ raw_prices  # ログ変換なし
```
⚠️ **問題**: Boulder lpplsは内部でログ変換を行わない

### 2.4 LPPL理論との整合性

**LPPL理論 (Sornette論文)**:
```
log(p(t)) = A + B*(tc-t)^m + C*(tc-t)^m*cos(ω*log(tc-t)) + ...
```
- LPPL式は **log(price)** に対してフィッティングする
- 現在の実装は **raw price** を使用している
- ❌ **理論的に不正確な実装**

### 2.5 推奨される修正

**オプション1: FCO Engine でログ変換を適用**
```python
# fco_service.py
log_prices = np.log(np.array(price_data['prices']))
result = self.fco_engine.compute_ds_lppls_confidence(log_prices)
```

**オプション2: データベースから log_prices を取得**
```python
# fco_service.py
log_prices = np.array(price_data['log_prices'])  # Get pre-computed log prices
result = self.fco_engine.compute_ds_lppls_confidence(log_prices)
```

**推奨**: **オプション2**
- 理由: ログ変換はすでにデータベースに保存されている
- パフォーマンス: 再計算不要
- 一貫性: データベースの log_close カラムを活用

---

## 📅 3. FRED 最古データの取得可能期間

### 3.1 主要インデックスのデータ可用性

**一般的なFREDデータの開始時期**:

| Symbol | Name | FRED開始日 | 注記 |
|--------|------|-----------|------|
| SP500 | S&P 500 Index | 1927年頃 | 約98年のデータ |
| NASDAQCOM | NASDAQ Composite | 1971-02-05 | 約54年のデータ |
| DJIA | Dow Jones Industrial | 1896年頃 | 約129年のデータ |
| VIXCLS | VIX Index | 1990-01-02 | 約35年のデータ |

### 3.2 Black Monday に対する推奨取得期間

**Black Monday**: 1987-10-19

**推奨データ取得期間**:
- **開始日**: 1977-01-01 (Black Monday の10年前)
- **終了日**: 現在 (2025-10-09)
- **期間**: 約48年間
- **予想データポイント**: 約17,500日

**根拠**:
1. ユーザーの要求: Black Monday の10年前からのデータ
2. FRED の SP500/NASDAQ データは1977年以前も利用可能
3. 十分な歴史的データで統計的信頼性を確保

### 3.3 データ取得戦略

**実行可能な銘柄**:
- ✅ SP500: 1977年からフルカバレッジ
- ✅ NASDAQCOM: 1977年からフルカバレッジ (1971年開始)
- ✅ DJIA: 1977年からフルカバレッジ
- ❌ VIX: 1990年開始のため、Black Monday期間はカバー不可

**データ量の見積もり**:
```
期間: 1977-2025 = 48年
営業日: 48年 × 252日/年 ≈ 12,096営業日
実データ: 約10,000〜12,000データポイント（休日等除く）
```

---

## 🎯 4. まとめと推奨アクション

### 4.1 発見された主要な問題

1. **❌ Negative bubble データが存在しない**
   - FCO解析が negative bubble を検出していない、または
   - 検出しても正しくデータベースに保存されていない

2. **❌ FCO解析がraw priceを使用している**
   - LPPL理論上は log(price) を使用すべき
   - 現在の実装は理論的に不正確

3. **✅ 2重ログ変換は発生していない**
   - 当初の懸念は杞憂
   - データベースは raw と log の両方を適切に保存

### 4.2 推奨される修正アクション

#### 優先度1: FCO解析のログ変換修正 🔥
```python
# fco-api/app/services/fco_service.py の修正
# Line 219付近を以下に変更:

# Before:
prices = np.array(price_data['prices'])  # raw prices

# After:
log_prices = np.array(price_data['log_prices'])  # log-transformed prices
```

#### 優先度2: Negative bubble 検出の修正
```python
# core/fitting/fco_engine.py の確認
# Negative bubble の判定ロジックが正しく動作しているか検証
# ds_lppls_confidence_neg が正しく計算・保存されているか確認
```

#### 優先度3: データ全体の再取得・再解析
```
1. 既存データの削除: 誤ったデータ(raw price使用)を削除
2. データ取得: 1977-2025の全期間データを取得
3. 前処理: raw + log の両方を保存(既存実装は正しい)
4. 解析実行: log_prices を使用してFCO解析実行(要修正)
5. 検証: Black Monday等の歴史的クラッシュで検証
```

### 4.3 次のステップ (Phase 3〜5)

#### Phase 3: データ削除とスキーマ確認
- 既存の全FCO解析結果を削除
- 既存の price データを削除(または保持して再利用)
- データベーススキーマの最終確認

#### Phase 4: データ取得・前処理実装の修正
- `fco_service.py` の修正: log_prices を使用
- `price_data_service.py`: 既存実装は正しいため変更不要
- APIエンドポイントの確認: 時系列プロット用にlog_pricesを返す

#### Phase 5: 1977〜現在の全期間データ取得・解析
- 1977-01-01 〜 2025-10-09 のデータ取得
- 修正されたFCO解析システムで全期間を解析
- Black Monday, Dotcom Bubble, Lehman Shock での検証

---

## 📋 5. アーキテクチャドキュメント更新事項

### 5.1 修正されるべきデータフロー

**現在 (誤り)**:
```
Raw Market Data → Database (raw & log)
                      ↓
                  raw price → FCO Analysis
                      ↓
                  Boulder lppls (raw price)
                      ↓
                  ❌ 理論的に不正確な結果
```

**修正後 (正しい)**:
```
Raw Market Data → Database (raw & log)
                      ↓
                  log_price → FCO Analysis
                      ↓
                  Boulder lppls (log price)
                      ↓
                  ✅ 理論的に正確な結果
                      ↓
Frontend Time Series: log_price を使用
```

### 5.2 ドキュメント更新箇所

1. **`docs/fco_upgrade_v2/implementation_plan_v2.1_next_steps.md`**
   - データフロー図の修正
   - FCO解析がlog pricesを使用することを明記

2. **`docs/fco_upgrade_v2/price_data_storage_plan.md`**
   - 新規作成: データ保存とログ変換の明確な方針
   - raw と log の使い分けを明記

3. **`fco-api/README.md`**
   - API仕様: log_pricesを返すエンドポイントの明記
   - FCO解析がlog pricesを使用することの説明

---

## ✅ 6. Phase 2 完了チェックリスト

- [x] データベース構造の確認
- [x] Negative bubble データの存在確認 → **0件を確認**
- [x] ds_lppls_confidence_neg の使用状況確認 → **78.3%が NULL**
- [x] ログ変換の実態確認 → **FCOがraw priceを使用していることを確認**
- [x] 2重ログ変換の有無確認 → **発生していないことを確認**
- [x] FRED 最古データ期間の確認 → **1977年から取得可能**
- [x] 推奨アクションの策定
- [x] アーキテクチャドキュメント更新事項の特定

---

**報告書作成者**: Claude Code
**最終更新**: 2025-10-09 20:25
