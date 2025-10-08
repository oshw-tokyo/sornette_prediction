# FCO 全126窓保存戦略 - 正式仕様書

**策定日**: 2025-10-08
**対象**: FRED symbols (23銘柄) による全窓データ保存
**戦略**: SQLite 全窓保存 → 将来的に PostgreSQL 移行

---

## 📋 Executive Summary

### 戦略決定

**2025-10-08に以下の戦略を正式決定**:

- **全126窓のデータを保存** (代表窓のみではなく)
- **対象**: FRED symbols 23銘柄のみ（初期フェーズ）
- **データベース**: 当面は SQLite（50GB以下）
- **将来計画**: データ量が50GBを超えた時点で PostgreSQL へ移行

### 定量的根拠

**データサイズ見積もり** (FRED 23銘柄、50年分):

| コンポーネント | 容量 | 割合 |
|--------------|------|------|
| **price_data** | 0.04 GB | 0.6% |
| **fco_analysis_results** | 0.06 GB | 0.8% |
| **fco_window_fits** | 7.15 GB | 98.6% |
| **合計** | **7.24 GB** | 100% |

**歴史的クラッシュデータ含む** (1987, 2000, 2008, 2020 - 21年分):
- 総容量: **9.38 GB**
- 結論: **SQLiteで十分対応可能** ✅

### 参照元

この戦略は以下の詳細分析に基づいています:
- [workspace_for_claude/fred_only_full_window_storage_final_report.md](../../workspace_for_claude/fred_only_full_window_storage_final_report.md) - データサイズ詳細見積もり
- [workspace_for_claude/sqlite_to_postgresql_migration_guide.md](../../workspace_for_claude/sqlite_to_postgresql_migration_guide.md) - PostgreSQL移行計画

---

## 🎯 1. 戦略の背景と目的

### 1.1 現状の課題

**現在の実装** (代表窓のみ保存):
- FCO分析で126窓をフィッティング
- **最も信頼性の高い1窓のみ**をデータベースに保存
- 残り125窓のデータは破棄

**問題点**:
1. **分析精度の検証不可**: R²分布、tc予測の分散が不明
2. **時間的クラスタリング不可**: 予測収束パターンの分析に制約
3. **詳細診断不可**: フィッティング品質の詳細評価が困難

### 1.2 全窓保存の目的

**科学的価値**:
- **予測品質の可視化**: R²分布、信頼区間の正確な評価
- **時間的収束分析**: 複数窓の予測クラッシュ日の収束度
- **フィッティング診断**: 異常値・外れ値の検出

**実装価値**:
- **UI拡張**: 全窓データの詳細表示タブ追加
- **分析機能強化**: クラスタリング・統計的分析の実装
- **デバッグ効率化**: フィッティングの品質確認が容易に

---

## 🗄️ 2. データベーススキーマ拡張

### 2.1 新規追加フィールド

`fco_window_fits` テーブルに以下のフィールドを追加:

| フィールド名 | 型 | 説明 | 現状 |
|-------------|----|----|------|
| **window_start_date** | TEXT | 窓の開始日 (YYYY-MM-DD) | ❌ 未実装 |
| **window_end_date** | TEXT | 窓の終了日 (YYYY-MM-DD) | ❌ 未実装 |
| **window_days** | INTEGER | 窓サイズ（日数） | ❌ 未実装 |
| **r_squared** | REAL | 決定係数（フィッティング品質） | ⚠️ 実装済みだがNULL |
| **is_representative** | INTEGER | FCO選出の代表窓フラグ (0/1) | ❌ 未実装 |

### 2.2 スキーマ変更SQL

```sql
-- Phase 1: スキーマ拡張
ALTER TABLE fco_window_fits ADD COLUMN window_start_date TEXT;
ALTER TABLE fco_window_fits ADD COLUMN window_end_date TEXT;
ALTER TABLE fco_window_fits ADD COLUMN window_days INTEGER;
ALTER TABLE fco_window_fits ADD COLUMN is_representative INTEGER DEFAULT 0;

-- r_squaredは既に存在するが、NULLデータを修正
-- (FCOエンジン修正で自動的に埋まる)

-- Phase 2: インデックス追加（パフォーマンス最適化）
CREATE INDEX IF NOT EXISTS idx_window_dates
    ON fco_window_fits(window_start_date, window_end_date);
CREATE INDEX IF NOT EXISTS idx_representative
    ON fco_window_fits(is_representative);
CREATE INDEX IF NOT EXISTS idx_r_squared
    ON fco_window_fits(r_squared);
```

### 2.3 データ例

**全窓保存後のデータ構造**:

```sql
-- 1つの分析 (analysis_id=123) に対して126行のデータ
SELECT
    analysis_id,
    window_size,
    window_days,
    r_squared,
    is_representative,
    tc_datetime
FROM fco_window_fits
WHERE analysis_id = 123
ORDER BY window_end_date DESC
LIMIT 5;

-- 結果例:
-- analysis_id | window_size | window_days | r_squared | is_representative | tc_datetime
-- ------------|-------------|-------------|-----------|-------------------|-------------
-- 123         | 1460        | 1460        | 0.95      | 1                 | 2025-11-15
-- 123         | 1440        | 1440        | 0.93      | 0                 | 2025-11-18
-- 123         | 1420        | 1420        | 0.91      | 0                 | 2025-11-20
-- 123         | 1400        | 1400        | 0.89      | 0                 | 2025-11-22
-- 123         | 1380        | 1380        | 0.87      | 0                 | 2025-11-25
```

---

## 💾 3. ストレージ容量計画

### 3.1 FRED Symbols (23銘柄) データサイズ

#### A. 基本データ (50年分)

**price_data** (市場価格データ):
- 23銘柄 × 50年 × 365日 × 100 bytes/row = **0.04 GB**

**fco_analysis_results** (分析メタデータ):
- 23銘柄 × 50年 × 52週 × 500 bytes/row = **0.06 GB**

**fco_window_fits** (全126窓データ):
- 23銘柄 × 50年 × 52週 × 126窓 × 1,200 bytes/row = **7.15 GB**

**小計**: **7.24 GB**

#### B. 歴史的クラッシュデータ (21年分)

主要クラッシュイベントの追加分析:
- 1987年ブラックマンデー: 3年分
- 2000年ドットコムバブル: 5年分
- 2008年金融危機: 8年分
- 2020年COVID-19: 5年分

**追加容量**: **+2.14 GB**

**総計**: **9.38 GB**

### 3.2 将来的な拡張シナリオ

| シナリオ | 銘柄数 | 期間 | 容量 | DB推奨 |
|---------|--------|------|------|--------|
| **現在** (FRED only) | 23 | 50年 | 7.24 GB | SQLite ✅ |
| **Phase 2** (全銘柄) | 81 | 50年 | 25.5 GB | SQLite ✅ |
| **Phase 3** (拡張) | 100 | 50年 | 31.5 GB | SQLite ✅ |
| **Phase 4** (大規模) | 200 | 50年 | 63.0 GB | PostgreSQL 🔄 |

**結論**:
- FRED 23銘柄 → **SQLiteで十分** (7.24 GB)
- 全81銘柄 → **まだSQLiteで可能** (25.5 GB)
- 200銘柄以上 → **PostgreSQL移行を検討** (50GB超)

---

## 🚀 4. 実装フェーズ

### Phase 1: データベーススキーマ拡張 (Week 1)

**タスク**:
- [ ] スキーマ変更SQLの作成・テスト
- [ ] マイグレーションスクリプトの実装
- [ ] テストデータでの検証

**成果物**:
- `infrastructure/database/migrations/add_full_window_fields.sql`
- `infrastructure/database/schema_migration.py`

**検証**:
```bash
# テスト用DBで実行
python infrastructure/database/schema_migration.py --test

# 本番DBへの適用
python infrastructure/database/schema_migration.py --apply
```

---

### Phase 2: FCOエンジン修正 (Week 2-3)

**変更箇所**: `core/fitting/fco_engine.py`

#### A. 全窓保存ロジックの追加

**現在の実装** (代表窓のみ):
```python
# fco_engine.py 内 (簡略化)
best_fit = select_best_window(all_fits)
save_to_database(best_fit)  # 1窓のみ
```

**新実装** (全126窓):
```python
# fco_engine.py 内 (簡略化)
best_fit = select_best_window(all_fits)

for fit in all_fits:
    fit['is_representative'] = (fit == best_fit)
    fit['window_start_date'] = calculate_start_date(fit)
    fit['window_end_date'] = calculate_end_date(fit)
    fit['window_days'] = fit['window_size']
    save_to_database(fit)  # 全126窓保存
```

#### B. フィールド自動設定

**追加する計算ロジック**:
```python
def calculate_window_dates(fit_result, price_data):
    """
    窓の開始日・終了日を計算

    Parameters:
    -----------
    fit_result : dict
        フィッティング結果
    price_data : pd.DataFrame
        市場価格データ

    Returns:
    --------
    dict
        window_start_date, window_end_date, window_days を含む
    """
    window_size = fit_result['window_size']
    end_date = price_data.index[-1]  # 最終日
    start_date = end_date - pd.Timedelta(days=window_size)

    return {
        'window_start_date': start_date.strftime('%Y-%m-%d'),
        'window_end_date': end_date.strftime('%Y-%m-%d'),
        'window_days': window_size
    }
```

**タスク**:
- [ ] `save_all_windows()` メソッドの実装
- [ ] 窓日付計算ロジックの追加
- [ ] r_squared の自動保存（現在NULL問題の修正）
- [ ] is_representative フラグの設定
- [ ] 既存機能の後方互換性テスト

**成果物**:
- 修正版 `core/fitting/fco_engine.py`
- 単体テスト `tests/fitting/test_fco_full_window_save.py`

**検証**:
```bash
# 単体テスト
pytest tests/fitting/test_fco_full_window_save.py -v

# 1銘柄での実行テスト
python entry_points/main.py analyze SP500 --save-all-windows

# データベース確認
sqlite3 results/fco_analysis_results.db \
  "SELECT COUNT(*) FROM fco_window_fits WHERE analysis_id = (SELECT MAX(id) FROM fco_analysis_results);"
# 期待結果: 126
```

---

### Phase 3: 歴史的データバックフィル (Week 4)

**目的**: 過去のクラッシュイベントの全窓データ生成

#### A. 対象クラッシュイベント

| イベント | 期間 | 銘柄 | 分析回数 |
|---------|------|------|---------|
| 1987年ブラックマンデー | 1985-1990 (5年) | SP500 | 260回 |
| 2000年ドットコムバブル | 1998-2003 (5年) | NASDAQCOM | 260回 |
| 2008年金融危機 | 2005-2013 (8年) | SP500, DJIA | 416回 × 2 |
| 2020年COVID-19 | 2018-2023 (5年) | SP500, VIX | 260回 × 2 |

**合計**: 約1,976分析 × 126窓 = **248,976レコード**

#### B. バックフィル実行

**スクリプト**: `infrastructure/database/backfill_historical_crashes.py`

```python
#!/usr/bin/env python3
"""
歴史的クラッシュイベントの全窓データバックフィル
"""

CRASH_EVENTS = [
    {
        'name': '1987_black_monday',
        'symbol': 'SP500',
        'start_date': '1985-01-01',
        'end_date': '1990-12-31',
        'frequency': 'weekly'
    },
    {
        'name': '2000_dotcom_bubble',
        'symbol': 'NASDAQCOM',
        'start_date': '1998-01-01',
        'end_date': '2003-12-31',
        'frequency': 'weekly'
    },
    # ... 他のイベント
]

def backfill_crash_event(event):
    """単一クラッシュイベントのバックフィル"""
    dates = pd.date_range(
        start=event['start_date'],
        end=event['end_date'],
        freq='W'  # 週次
    )

    for date in dates:
        run_fco_analysis(
            symbol=event['symbol'],
            basis_date=date,
            save_all_windows=True
        )

if __name__ == '__main__':
    for event in CRASH_EVENTS:
        print(f"Backfilling: {event['name']}")
        backfill_crash_event(event)
```

**実行**:
```bash
# 実行前の容量確認
du -sh results/fco_analysis_results.db

# バックフィル実行（数時間かかる）
python infrastructure/database/backfill_historical_crashes.py

# 実行後の容量確認
du -sh results/fco_analysis_results.db
# 期待: +2.14 GB
```

**タスク**:
- [ ] バックフィルスクリプトの作成
- [ ] 1987年ブラックマンデーデータ生成
- [ ] 2000年ドットコムバブルデータ生成
- [ ] 2008年金融危機データ生成
- [ ] 2020年COVID-19データ生成
- [ ] データ整合性検証

---

### Phase 4: API/UI拡張 (Week 5-6)

#### A. FastAPI エンドポイント追加

**新規API**: `GET /api/v1/fco/analysis/{analysis_id}/all-windows`

```python
# fco-api/app/api/v1/endpoints/fco.py

@router.get("/analysis/{analysis_id}/all-windows")
async def get_all_windows(analysis_id: int):
    """
    全126窓のフィッティング結果を取得

    Returns:
    --------
    {
        "analysis_id": int,
        "symbol": str,
        "analysis_basis_date": str,
        "total_windows": int,
        "representative_window": {...},
        "all_windows": [
            {
                "window_size": int,
                "window_start_date": str,
                "window_end_date": str,
                "window_days": int,
                "r_squared": float,
                "is_representative": bool,
                "tc_datetime": str,
                "m": float,
                "omega": float,
                "phi": float,
                ...
            },
            ...
        ],
        "statistics": {
            "avg_r_squared": float,
            "std_r_squared": float,
            "tc_prediction_range_days": int,
            "confidence_score": float
        }
    }
    """
    # 実装詳細は省略
```

#### B. React UI 拡張

**新規タブ**: "All Windows Analysis"

**コンポーネント構成**:
```
FCOAnalysisDetail.tsx
├── OverviewTab (既存)
├── R²DistributionTab (新規)
│   ├── HistogramChart (R²分布ヒストグラム)
│   └── StatisticsTable (統計サマリー)
├── tcPredictionsTab (新規)
│   ├── ScatterPlot (窓サイズ vs tc予測日)
│   └── ConvergenceAnalysis (収束度評価)
└── ParametersTab (既存)
    └── AllWindowsTable (全126窓の詳細テーブル)
```

**参照**:
- UI設計の詳細は [workspace_for_claude/fco_all_windows_ui_concept.md](../../workspace_for_claude/fco_all_windows_ui_concept.md) を参照

**タスク**:
- [ ] FastAPI endpoint 実装
- [ ] React 新規タブコンポーネント作成
- [ ] R²分布ヒストグラムの実装
- [ ] tc予測scatter plotの実装
- [ ] 統計サマリーテーブルの実装

**注意**: フロントエンド要件は実装時にユーザーと相談しながら決定

---

## 📊 5. データ品質保証

### 5.1 データ整合性検証

**検証スクリプト**: `infrastructure/database/validate_full_window_data.py`

```python
#!/usr/bin/env python3
"""
全窓データの整合性検証
"""

def validate_window_counts():
    """各分析が126窓を持つか確認"""
    query = """
        SELECT
            analysis_id,
            COUNT(*) as window_count
        FROM fco_window_fits
        GROUP BY analysis_id
        HAVING window_count != 126
    """
    # 期待: 0行（全分析が126窓）

def validate_representative_flags():
    """各分析が1つのみ代表窓を持つか確認"""
    query = """
        SELECT
            analysis_id,
            SUM(is_representative) as rep_count
        FROM fco_window_fits
        GROUP BY analysis_id
        HAVING rep_count != 1
    """
    # 期待: 0行（各分析が1つの代表窓）

def validate_r_squared_values():
    """R²値がNULLでないか確認"""
    query = """
        SELECT COUNT(*)
        FROM fco_window_fits
        WHERE r_squared IS NULL
    """
    # 期待: 0行
```

### 5.2 パフォーマンステスト

**目標**:
- 単一分析の保存時間: < 5秒 (126窓)
- 全窓データ取得時間: < 1秒
- データベース容量: < 10 GB (FRED 23銘柄、50年分)

**ベンチマーク**:
```bash
# 保存速度テスト
time python entry_points/main.py analyze SP500 --save-all-windows

# 取得速度テスト
time curl http://localhost:8000/api/v1/fco/analysis/123/all-windows
```

---

## 🔄 6. PostgreSQL 移行計画（将来）

### 6.1 移行トリガー

以下のいずれかの条件を満たした場合に PostgreSQL 移行を検討:

1. **データベース容量 > 50 GB**
2. **銘柄数 > 200**
3. **同時ユーザー数 > 1,000**
4. **複数サーバー展開の必要性**

### 6.2 移行手順（概要）

**ツール**: pgloader (自動変換・移行)

```bash
# PostgreSQL環境構築
docker-compose up -d postgres

# pgloaderで自動移行
pgloader sqlite:///results/fco_analysis_results.db \
         postgresql://user:password@localhost/fco_production

# 所要時間: 10GB → 約30分
```

**詳細**: [workspace_for_claude/sqlite_to_postgresql_migration_guide.md](../../workspace_for_claude/sqlite_to_postgresql_migration_guide.md)

### 6.3 移行時のアプリケーション修正

**必要な変更箇所**:
- データベース接続設定（環境変数で切り替え可能に設計）
- 一部のSQL文法調整（AUTOINCREMENT → SERIAL等）

**影響範囲**: 小（数時間〜1日の作業）

---

## 📚 7. 関連ドキュメント

### 実装関連
- [technical_implementation_plan.md](technical_implementation_plan.md) - FCO v2.1 技術実装詳細
- [ds_lppls_indicators_detailed_specification.md](ds_lppls_indicators_detailed_specification.md) - DS-LPPLS指標仕様
- [fco_v2.1_architecture.md](fco_v2.1_architecture.md) - システムアーキテクチャ

### データベース関連
- [fco_database_migration_strategy.md](fco_database_migration_strategy.md) - FCOデータベース移行戦略（旧版）
- [price_data_storage_plan.md](price_data_storage_plan.md) - 価格データ保存計画

### 分析結果（workspace_for_claude/）
- [fred_only_full_window_storage_final_report.md](../../workspace_for_claude/fred_only_full_window_storage_final_report.md) - データサイズ詳細見積もり
- [fco_all_windows_ui_concept.md](../../workspace_for_claude/fco_all_windows_ui_concept.md) - UI設計コンセプト
- [sqlite_to_postgresql_migration_guide.md](../../workspace_for_claude/sqlite_to_postgresql_migration_guide.md) - PostgreSQL移行ガイド
- [full_window_storage_business_value_analysis.md](../../workspace_for_claude/full_window_storage_business_value_analysis.md) - ビジネス価値分析

---

## 🎯 8. 成功基準

### Phase 1-4 完了時の検証項目

**データ品質**:
- [ ] 各分析が正確に126窓のデータを保持
- [ ] 各分析が1つのみ代表窓フラグを持つ
- [ ] R²値がすべて正常に保存されている
- [ ] 窓日付が正確に計算されている

**パフォーマンス**:
- [ ] 単一分析の保存時間 < 5秒
- [ ] 全窓データ取得時間 < 1秒
- [ ] データベース容量が予測範囲内 (< 10 GB)

**機能**:
- [ ] FastAPI エンドポイントが正常動作
- [ ] React UI が全窓データを正しく表示
- [ ] 歴史的クラッシュデータが正確に生成されている

**科学的検証**:
- [ ] 1987年ブラックマンデー検証スコア維持 (100/100)
- [ ] DS-LPPLS Confidence 指標が正常計算

---

**策定**: プロジェクトオーナー + Claude Code
**参照**: [docs/fco_upgrade_v2/README.md](README.md) - FCO v2.1 アップグレード文書索引
**最終更新**: 2025-10-08
