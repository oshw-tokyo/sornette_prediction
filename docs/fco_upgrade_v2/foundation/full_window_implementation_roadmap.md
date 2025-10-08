# FCO 全窓保存実装ロードマップ

**作成日**: 2025-10-08
**期間**: Week 1-6 (約6週間)
**前提**: [full_window_storage_strategy.md](full_window_storage_strategy.md) の戦略に基づく

---

## 📅 全体スケジュール

| Phase | 期間 | 主要タスク | 成果物 |
|-------|------|-----------|--------|
| **Phase 1** | Week 1 (5日) | DBスキーマ拡張 | マイグレーションSQL |
| **Phase 2** | Week 2-3 (10日) | FCOエンジン修正 | 全窓保存機能 |
| **Phase 3** | Week 4 (5日) | 歴史的データバックフィル | クラッシュデータ |
| **Phase 4** | Week 5-6 (10日) | API/UI拡張 | 全窓表示機能 |

**合計**: 30営業日 (約6週間)

---

## 🔧 Phase 1: データベーススキーマ拡張 (Week 1)

### Day 1-2: スキーマ設計とSQL作成

#### タスク 1.1: スキーマ変更SQLの作成

**ファイル**: `infrastructure/database/migrations/001_add_full_window_fields.sql`

```sql
-- FCO 全窓保存のためのスキーマ拡張
-- 実行日: 2025-10-XX
-- 対象テーブル: fco_window_fits

BEGIN TRANSACTION;

-- 1. 新規フィールド追加
ALTER TABLE fco_window_fits ADD COLUMN window_start_date TEXT;
ALTER TABLE fco_window_fits ADD COLUMN window_end_date TEXT;
ALTER TABLE fco_window_fits ADD COLUMN window_days INTEGER;
ALTER TABLE fco_window_fits ADD COLUMN is_representative INTEGER DEFAULT 0;

-- 2. インデックス作成（パフォーマンス最適化）
CREATE INDEX IF NOT EXISTS idx_window_dates
    ON fco_window_fits(window_start_date, window_end_date);

CREATE INDEX IF NOT EXISTS idx_representative
    ON fco_window_fits(is_representative);

CREATE INDEX IF NOT EXISTS idx_r_squared
    ON fco_window_fits(r_squared);

-- 3. データ整合性チェック用ビュー
CREATE VIEW IF NOT EXISTS v_window_integrity AS
SELECT
    analysis_id,
    COUNT(*) as window_count,
    SUM(is_representative) as representative_count,
    COUNT(CASE WHEN r_squared IS NULL THEN 1 END) as null_r_squared_count
FROM fco_window_fits
GROUP BY analysis_id;

COMMIT;
```

**チェックリスト**:
- [ ] SQL構文の検証（sqlite3コマンドで確認）
- [ ] バックアップ手順の文書化
- [ ] ロールバックSQLの準備

---

#### タスク 1.2: マイグレーションスクリプトの実装

**ファイル**: `infrastructure/database/schema_migration.py`

```python
#!/usr/bin/env python3
"""
FCO全窓保存スキーマ移行スクリプト

Usage:
    # テストモード（dry-run）
    python infrastructure/database/schema_migration.py --test

    # 本番実行
    python infrastructure/database/schema_migration.py --apply

    # ロールバック
    python infrastructure/database/schema_migration.py --rollback
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path('results/fco_analysis_results.db')
BACKUP_DIR = Path('results/backups')
MIGRATION_SQL = Path('infrastructure/database/migrations/001_add_full_window_fields.sql')

def backup_database():
    """データベースのバックアップ作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'fco_analysis_results_pre_migration_{timestamp}.db'

    print(f"📦 Creating backup: {backup_path}")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path

def apply_migration(dry_run=False):
    """マイグレーションSQL適用"""
    print(f"📄 Reading migration SQL: {MIGRATION_SQL}")
    sql = MIGRATION_SQL.read_text()

    if dry_run:
        print("🔍 DRY-RUN MODE: Would execute following SQL:")
        print(sql)
        return

    # バックアップ作成
    backup_path = backup_database()

    # マイグレーション実行
    print("🔧 Applying migration...")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(sql)
        print("✅ Migration applied successfully")

        # 検証
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"📊 Created indexes: {indexes}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"🔄 Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, DB_PATH)
        raise
    finally:
        conn.close()

def verify_migration():
    """マイグレーション結果の検証"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # フィールド存在確認
    cursor.execute("PRAGMA table_info(fco_window_fits)")
    columns = [row[1] for row in cursor.fetchall()]

    required_columns = ['window_start_date', 'window_end_date', 'window_days', 'is_representative']
    missing = [col for col in required_columns if col not in columns]

    if missing:
        print(f"⚠️  Missing columns: {missing}")
        return False

    print("✅ All required columns exist")

    # インデックス確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='fco_window_fits'")
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"📊 Indexes: {indexes}")

    conn.close()
    return True

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='FCO Database Schema Migration')
    parser.add_argument('--test', action='store_true', help='Dry-run mode')
    parser.add_argument('--apply', action='store_true', help='Apply migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback to latest backup')
    args = parser.parse_args()

    if args.test:
        apply_migration(dry_run=True)
    elif args.apply:
        apply_migration(dry_run=False)
        verify_migration()
    elif args.rollback:
        # ロールバック実装（省略）
        pass
    else:
        parser.print_help()
```

**チェックリスト**:
- [ ] スクリプトの単体テスト
- [ ] テストDBでのdry-run実行
- [ ] バックアップ・ロールバック機能の検証

---

### Day 3-5: 検証とドキュメント作成

#### タスク 1.3: マイグレーションテスト

**テストシナリオ**:

1. **空DBでのテスト**
   ```bash
   # 新規DBでテスト
   cp results/fco_analysis_results.db results/test_empty.db
   sqlite3 results/test_empty.db "DELETE FROM fco_window_fits;"
   python infrastructure/database/schema_migration.py --apply
   ```

2. **既存データありDBでのテスト**
   ```bash
   # 既存データ保持確認
   python infrastructure/database/schema_migration.py --apply
   sqlite3 results/fco_analysis_results.db "SELECT COUNT(*) FROM fco_window_fits;"
   # 期待: データ消失なし
   ```

3. **ロールバックテスト**
   ```bash
   # ロールバック実行
   python infrastructure/database/schema_migration.py --rollback
   # 期待: バックアップから復元成功
   ```

**チェックリスト**:
- [ ] 空DBでのマイグレーション成功
- [ ] 既存データ保持の確認
- [ ] ロールバック機能の動作確認
- [ ] パフォーマンス影響の測定（インデックス追加前後）

---

#### タスク 1.4: ドキュメント更新

**更新対象**:
- `infrastructure/database/README.md` - マイグレーション手順の追加
- `CLAUDE.md` - スキーマ変更の記録
- `docs/progress_management/CURRENT_PROGRESS.md` - Phase 1完了記録

**チェックリスト**:
- [ ] マイグレーション手順書の作成
- [ ] トラブルシューティングガイドの追加
- [ ] ロールバック手順の文書化

---

### Phase 1 完了基準

- [ ] マイグレーションSQL作成完了
- [ ] マイグレーションスクリプト実装完了
- [ ] テストDB・本番DBでの検証完了
- [ ] 全データ整合性確認済み
- [ ] ドキュメント更新完了

---

## 🔄 Phase 2: FCOエンジン修正 (Week 2-3)

### Week 2: 全窓保存ロジックの実装

#### タスク 2.1: コア機能の実装

**ファイル**: `core/fitting/fco_engine.py`

**主要変更箇所**:

```python
class FCOEngine:
    """FCO分析エンジン（全窓保存対応版）"""

    def analyze(self, symbol: str, basis_date: str, save_all_windows: bool = True):
        """
        FCO分析実行

        Parameters:
        -----------
        symbol : str
            銘柄シンボル
        basis_date : str
            分析基準日 (YYYY-MM-DD)
        save_all_windows : bool, default=True
            全窓保存フラグ（Trueで全126窓保存）

        Returns:
        --------
        dict
            分析結果（代表窓のみを返す）
        """
        # 価格データ取得
        price_data = self._fetch_price_data(symbol, basis_date)

        # 全126窓のフィッティング実行
        all_fits = self._fit_all_windows(price_data)

        # DS-LPPLS Confidenceで最適窓選択
        best_fit = self._select_best_window(all_fits)

        # データベース保存
        if save_all_windows:
            self._save_all_windows(all_fits, best_fit, symbol, basis_date, price_data)
        else:
            # 従来方式（代表窓のみ）
            self._save_representative_only(best_fit, symbol, basis_date)

        return best_fit

    def _save_all_windows(self, all_fits, best_fit, symbol, basis_date, price_data):
        """全126窓をデータベースに保存"""
        analysis_id = self._create_analysis_record(symbol, basis_date)

        for fit in all_fits:
            # 窓日付計算
            window_dates = self._calculate_window_dates(fit, price_data)

            # 代表窓フラグ設定
            fit['is_representative'] = 1 if fit == best_fit else 0

            # フィールド追加
            fit.update(window_dates)

            # データベース保存
            self._save_window_fit(analysis_id, fit)

        print(f"✅ Saved {len(all_fits)} windows for analysis_id={analysis_id}")

    def _calculate_window_dates(self, fit, price_data):
        """
        窓の開始日・終了日を計算

        Parameters:
        -----------
        fit : dict
            フィッティング結果
        price_data : pd.DataFrame
            価格データ

        Returns:
        --------
        dict
            {
                'window_start_date': str (YYYY-MM-DD),
                'window_end_date': str (YYYY-MM-DD),
                'window_days': int
            }
        """
        window_size = fit['window_size']
        end_date = price_data.index[-1]
        start_date = end_date - pd.Timedelta(days=window_size)

        return {
            'window_start_date': start_date.strftime('%Y-%m-%d'),
            'window_end_date': end_date.strftime('%Y-%m-%d'),
            'window_days': window_size
        }
```

**チェックリスト**:
- [ ] `_save_all_windows()` メソッド実装
- [ ] `_calculate_window_dates()` メソッド実装
- [ ] `is_representative` フラグ設定ロジック
- [ ] r_squared 自動保存の修正（現在NULL問題）

---

#### タスク 2.2: 単体テストの作成

**ファイル**: `tests/fitting/test_fco_full_window_save.py`

```python
import pytest
import sqlite3
from core.fitting.fco_engine import FCOEngine

class TestFCOFullWindowSave:
    """FCO全窓保存機能のテスト"""

    def test_all_windows_saved(self, test_db):
        """全126窓が保存されることを確認"""
        engine = FCOEngine()
        result = engine.analyze('SP500', '2025-01-01', save_all_windows=True)

        # データベース確認
        conn = sqlite3.connect(test_db)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM fco_window_fits WHERE analysis_id = ?",
            (result['analysis_id'],)
        )
        count = cursor.fetchone()[0]

        assert count == 126, f"Expected 126 windows, got {count}"

    def test_representative_flag(self, test_db):
        """代表窓フラグが正しく設定されることを確認"""
        engine = FCOEngine()
        result = engine.analyze('SP500', '2025-01-01', save_all_windows=True)

        # 代表窓が1つのみであることを確認
        conn = sqlite3.connect(test_db)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM fco_window_fits WHERE analysis_id = ? AND is_representative = 1",
            (result['analysis_id'],)
        )
        rep_count = cursor.fetchone()[0]

        assert rep_count == 1, f"Expected 1 representative window, got {rep_count}"

    def test_window_dates(self, test_db):
        """窓日付が正しく計算されることを確認"""
        engine = FCOEngine()
        result = engine.analyze('SP500', '2025-01-01', save_all_windows=True)

        # 窓日付の存在確認
        conn = sqlite3.connect(test_db)
        cursor = conn.execute(
            """SELECT window_start_date, window_end_date, window_days
               FROM fco_window_fits
               WHERE analysis_id = ?
               LIMIT 1""",
            (result['analysis_id'],)
        )
        row = cursor.fetchone()

        assert row[0] is not None, "window_start_date is NULL"
        assert row[1] is not None, "window_end_date is NULL"
        assert row[2] is not None, "window_days is NULL"

    def test_r_squared_not_null(self, test_db):
        """R²値がNULLでないことを確認"""
        engine = FCOEngine()
        result = engine.analyze('SP500', '2025-01-01', save_all_windows=True)

        # NULL R²の確認
        conn = sqlite3.connect(test_db)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM fco_window_fits WHERE analysis_id = ? AND r_squared IS NULL",
            (result['analysis_id'],)
        )
        null_count = cursor.fetchone()[0]

        assert null_count == 0, f"Found {null_count} NULL r_squared values"
```

**チェックリスト**:
- [ ] 全126窓保存のテスト
- [ ] 代表窓フラグのテスト
- [ ] 窓日付計算のテスト
- [ ] R²値保存のテスト
- [ ] 後方互換性テスト（save_all_windows=Falseでも動作）

---

### Week 3: 統合テストと調整

#### タスク 2.3: 実データでの検証

**検証シナリオ**:

1. **単一銘柄での実行**
   ```bash
   python entry_points/main.py analyze SP500 --save-all-windows
   ```

2. **データベース確認**
   ```bash
   sqlite3 results/fco_analysis_results.db <<EOF
   SELECT
       analysis_id,
       COUNT(*) as window_count,
       SUM(is_representative) as rep_count
   FROM fco_window_fits
   WHERE analysis_id = (SELECT MAX(id) FROM fco_analysis_results)
   GROUP BY analysis_id;
   EOF
   ```
   期待結果: `window_count=126, rep_count=1`

3. **パフォーマンス測定**
   ```bash
   time python entry_points/main.py analyze SP500 --save-all-windows
   ```
   目標: < 5秒

**チェックリスト**:
- [ ] SP500での検証成功
- [ ] NASDAQCOM での検証成功
- [ ] 仮想通貨銘柄（BTC）での検証成功
- [ ] パフォーマンス目標達成
- [ ] メモリ使用量の確認

---

#### タスク 2.4: 論文再現テスト

**最重要検証**: 1987年ブラックマンデー検証スコアの維持

```bash
# 論文再現テスト実行
python entry_points/main.py validate --crash 1987

# 期待結果: 100/100スコア維持
```

**チェックリスト**:
- [ ] 1987年ブラックマンデー検証スコア = 100/100
- [ ] DS-LPPLS Confidence 指標の正常計算
- [ ] tc予測日の精度維持

---

### Phase 2 完了基準

- [ ] FCOエンジン全窓保存機能実装完了
- [ ] 単体テスト全パス
- [ ] 実データでの検証成功
- [ ] 論文再現テスト維持（100/100）
- [ ] パフォーマンス目標達成（< 5秒）
- [ ] ドキュメント更新完了

---

## 📊 Phase 3: 歴史的データバックフィル (Week 4)

### Day 1-2: バックフィルスクリプト実装

#### タスク 3.1: スクリプト作成

**ファイル**: `infrastructure/database/backfill_historical_crashes.py`

```python
#!/usr/bin/env python3
"""
歴史的クラッシュイベントの全窓データバックフィル

Usage:
    # 全イベント実行
    python infrastructure/database/backfill_historical_crashes.py --all

    # 特定イベントのみ
    python infrastructure/database/backfill_historical_crashes.py --event 1987_black_monday

    # Dry-run
    python infrastructure/database/backfill_historical_crashes.py --all --dry-run
"""

import pandas as pd
from datetime import datetime
from core.fitting.fco_engine import FCOEngine

CRASH_EVENTS = {
    '1987_black_monday': {
        'symbol': 'SP500',
        'start_date': '1985-01-01',
        'end_date': '1990-12-31',
        'description': '1987年ブラックマンデー'
    },
    '2000_dotcom_bubble': {
        'symbol': 'NASDAQCOM',
        'start_date': '1998-01-01',
        'end_date': '2003-12-31',
        'description': '2000年ドットコムバブル'
    },
    '2008_financial_crisis': {
        'symbols': ['SP500', 'DJIA'],
        'start_date': '2005-01-01',
        'end_date': '2013-12-31',
        'description': '2008年金融危機'
    },
    '2020_covid19': {
        'symbols': ['SP500', 'VIXCLS'],
        'start_date': '2018-01-01',
        'end_date': '2023-12-31',
        'description': '2020年COVID-19'
    }
}

def backfill_event(event_name, dry_run=False):
    """単一イベントのバックフィル"""
    event = CRASH_EVENTS[event_name]
    print(f"\n{'='*60}")
    print(f"📊 Backfilling: {event['description']}")
    print(f"{'='*60}")

    # 週次日付生成
    dates = pd.date_range(
        start=event['start_date'],
        end=event['end_date'],
        freq='W'  # 週次
    )

    # 銘柄リスト取得
    symbols = event.get('symbols', [event.get('symbol')])

    total_analyses = len(symbols) * len(dates)
    print(f"📈 Symbols: {symbols}")
    print(f"📅 Period: {event['start_date']} - {event['end_date']}")
    print(f"🔢 Total analyses: {total_analyses}")

    if dry_run:
        print("🔍 DRY-RUN MODE: Skipping actual execution")
        return

    engine = FCOEngine()
    completed = 0

    for symbol in symbols:
        print(f"\n🎯 Analyzing {symbol}...")
        for date in dates:
            try:
                engine.analyze(
                    symbol=symbol,
                    basis_date=date.strftime('%Y-%m-%d'),
                    save_all_windows=True
                )
                completed += 1
                if completed % 10 == 0:
                    print(f"  ✅ Progress: {completed}/{total_analyses} ({completed/total_analyses*100:.1f}%)")
            except Exception as e:
                print(f"  ❌ Error at {date}: {e}")
                continue

    print(f"\n✅ Completed: {completed}/{total_analyses} analyses")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Historical Crash Data Backfill')
    parser.add_argument('--all', action='store_true', help='Backfill all events')
    parser.add_argument('--event', choices=CRASH_EVENTS.keys(), help='Specific event to backfill')
    parser.add_argument('--dry-run', action='store_true', help='Dry-run mode')
    args = parser.parse_args()

    if args.all:
        for event_name in CRASH_EVENTS.keys():
            backfill_event(event_name, dry_run=args.dry_run)
    elif args.event:
        backfill_event(args.event, dry_run=args.dry_run)
    else:
        parser.print_help()
```

**チェックリスト**:
- [ ] スクリプト実装完了
- [ ] dry-runモードのテスト
- [ ] エラーハンドリングの実装
- [ ] 進捗表示機能の実装

---

### Day 3-5: バックフィル実行

#### タスク 3.2: 段階的実行

**実行順序** (リスク軽減のため):

1. **1987年ブラックマンデー** (最小データ)
   ```bash
   python infrastructure/database/backfill_historical_crashes.py --event 1987_black_monday
   ```
   期待時間: 1-2時間

2. **2020年COVID-19**
   ```bash
   python infrastructure/database/backfill_historical_crashes.py --event 2020_covid19
   ```
   期待時間: 2-3時間

3. **2000年ドットコムバブル**
   ```bash
   python infrastructure/database/backfill_historical_crashes.py --event 2000_dotcom_bubble
   ```
   期待時間: 2-3時間

4. **2008年金融危機** (最大データ)
   ```bash
   python infrastructure/database/backfill_historical_crashes.py --event 2008_financial_crisis
   ```
   期待時間: 3-4時間

**チェックリスト**:
- [ ] 1987年ブラックマンデーデータ生成完了
- [ ] 2020年COVID-19データ生成完了
- [ ] 2000年ドットコムバブルデータ生成完了
- [ ] 2008年金融危機データ生成完了
- [ ] データ整合性検証完了

---

#### タスク 3.3: データ整合性検証

**検証スクリプト**: `infrastructure/database/validate_backfill_data.py`

```python
#!/usr/bin/env python3
"""バックフィルデータの整合性検証"""

import sqlite3

DB_PATH = 'results/fco_analysis_results.db'

def validate_window_counts():
    """全分析が126窓を持つか確認"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT
            analysis_id,
            COUNT(*) as window_count
        FROM fco_window_fits
        GROUP BY analysis_id
        HAVING window_count != 126
    """)
    invalid = cursor.fetchall()

    if invalid:
        print(f"⚠️  {len(invalid)} analyses have invalid window count:")
        for row in invalid:
            print(f"  analysis_id={row[0]}, window_count={row[1]}")
        return False
    else:
        print("✅ All analyses have 126 windows")
        return True

def validate_representative_flags():
    """各分析が1つのみ代表窓を持つか確認"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT
            analysis_id,
            SUM(is_representative) as rep_count
        FROM fco_window_fits
        GROUP BY analysis_id
        HAVING rep_count != 1
    """)
    invalid = cursor.fetchall()

    if invalid:
        print(f"⚠️  {len(invalid)} analyses have invalid representative count:")
        for row in invalid:
            print(f"  analysis_id={row[0]}, rep_count={row[1]}")
        return False
    else:
        print("✅ All analyses have exactly 1 representative window")
        return True

def validate_null_values():
    """NULL値がないか確認"""
    conn = sqlite3.connect(DB_PATH)

    # R²値のNULL確認
    cursor = conn.execute("""
        SELECT COUNT(*) FROM fco_window_fits WHERE r_squared IS NULL
    """)
    null_r_squared = cursor.fetchone()[0]

    # 窓日付のNULL確認
    cursor = conn.execute("""
        SELECT COUNT(*) FROM fco_window_fits
        WHERE window_start_date IS NULL OR window_end_date IS NULL OR window_days IS NULL
    """)
    null_dates = cursor.fetchone()[0]

    if null_r_squared > 0:
        print(f"⚠️  {null_r_squared} records have NULL r_squared")
    if null_dates > 0:
        print(f"⚠️  {null_dates} records have NULL window dates")

    if null_r_squared == 0 and null_dates == 0:
        print("✅ No NULL values found")
        return True
    return False

if __name__ == '__main__':
    print("🔍 Validating backfill data integrity...\n")

    results = [
        validate_window_counts(),
        validate_representative_flags(),
        validate_null_values()
    ]

    if all(results):
        print("\n✅ All validations passed!")
    else:
        print("\n❌ Some validations failed")
        exit(1)
```

**チェックリスト**:
- [ ] 窓数検証（全分析が126窓）
- [ ] 代表窓フラグ検証（各分析が1つのみ）
- [ ] NULL値検証（r_squared, 窓日付）
- [ ] データベース容量確認（+2.14 GB程度）

---

### Phase 3 完了基準

- [ ] 全4イベントのバックフィル完了
- [ ] データ整合性検証全パス
- [ ] データベース容量が予測範囲内
- [ ] ドキュメント更新完了

---

## 🎨 Phase 4: API/UI拡張 (Week 5-6)

### Week 5: FastAPI エンドポイント実装

#### タスク 4.1: API実装

**ファイル**: `fco-api/app/api/v1/endpoints/fco.py`

**新規エンドポイント**:

```python
@router.get("/analysis/{analysis_id}/all-windows", response_model=AllWindowsResponse)
async def get_all_windows(analysis_id: int, db: Session = Depends(get_db)):
    """
    全126窓のフィッティング結果を取得

    Parameters:
    -----------
    analysis_id : int
        分析ID

    Returns:
    --------
    AllWindowsResponse
        全窓データ + 統計サマリー
    """
    # 分析基本情報取得
    analysis = db.query(FCOAnalysisResult).filter(
        FCOAnalysisResult.id == analysis_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # 全窓データ取得
    all_windows = db.query(FCOWindowFit).filter(
        FCOWindowFit.analysis_id == analysis_id
    ).order_by(FCOWindowFit.window_size.desc()).all()

    # 代表窓取得
    representative = next((w for w in all_windows if w.is_representative), None)

    # 統計計算
    r_squared_values = [w.r_squared for w in all_windows if w.r_squared is not None]
    tc_dates = [w.tc_datetime for w in all_windows if w.tc_datetime]

    statistics = {
        'total_windows': len(all_windows),
        'avg_r_squared': sum(r_squared_values) / len(r_squared_values) if r_squared_values else 0,
        'std_r_squared': np.std(r_squared_values) if r_squared_values else 0,
        'tc_prediction_range_days': (max(tc_dates) - min(tc_dates)).days if len(tc_dates) >= 2 else 0,
        'confidence_score': analysis.ds_lppls_confidence
    }

    return AllWindowsResponse(
        analysis_id=analysis_id,
        symbol=analysis.symbol,
        analysis_basis_date=analysis.analysis_basis_date,
        representative_window=representative,
        all_windows=all_windows,
        statistics=statistics
    )
```

**チェックリスト**:
- [ ] エンドポイント実装
- [ ] Response model定義（Pydantic）
- [ ] データベースクエリ最適化
- [ ] エラーハンドリング
- [ ] API ドキュメント更新（Swagger）

---

### Week 6: React UI実装

#### タスク 4.2: 新規タブコンポーネント作成

**コンポーネント構成**:

```
fco-dashboard-frontend/components/
├── FCOAnalysisDetail.tsx (既存 - タブ追加)
└── fco/
    ├── AllWindowsTab.tsx (新規)
    ├── R2DistributionChart.tsx (新規)
    ├── TcPredictionsScatterPlot.tsx (新規)
    └── AllWindowsTable.tsx (新規)
```

**実装優先順位** (ユーザー要件確認しながら):

1. **AllWindowsTable** (最優先)
   - 全126窓の詳細テーブル表示
   - ソート・フィルタ機能

2. **R2DistributionChart** (高優先度)
   - R²分布ヒストグラム
   - 統計サマリー

3. **TcPredictionsScatterPlot** (中優先度)
   - 窓サイズ vs tc予測日の散布図
   - 収束パターンの可視化

**注意**: フロントエンド要件は実装時にユーザーと相談しながら決定

**チェックリスト**:
- [ ] AllWindowsTab基本実装
- [ ] データ取得ロジック実装
- [ ] 表示コンポーネント実装（優先順位順）
- [ ] レスポンシブ対応
- [ ] エラーハンドリング

---

### Phase 4 完了基準

- [ ] FastAPI エンドポイント実装完了
- [ ] React UI実装完了（最低限AllWindowsTable）
- [ ] 統合テスト完了
- [ ] ユーザー受け入れテスト（UAT）完了
- [ ] ドキュメント更新完了

---

## ✅ 全体完了基準

### データ品質

- [ ] 各分析が正確に126窓のデータを保持
- [ ] 各分析が1つのみ代表窓フラグを持つ
- [ ] R²値がすべて正常に保存されている
- [ ] 窓日付が正確に計算されている

### パフォーマンス

- [ ] 単一分析の保存時間 < 5秒
- [ ] 全窓データ取得時間 < 1秒
- [ ] データベース容量が予測範囲内 (< 10 GB)

### 機能

- [ ] FastAPI エンドポイントが正常動作
- [ ] React UI が全窓データを正しく表示
- [ ] 歴史的クラッシュデータが正確に生成されている

### 科学的検証

- [ ] 1987年ブラックマンデー検証スコア維持 (100/100)
- [ ] DS-LPPLS Confidence 指標が正常計算

---

## 📝 実装中の注意事項

### 1. 論文再現保護

**各Phase完了時に必ず実行**:
```bash
python entry_points/main.py validate --crash 1987
# 期待: 100/100スコア維持
```

### 2. バックアップ戦略

**Phase移行前に必ずバックアップ**:
```bash
# データベースバックアップ
cp results/fco_analysis_results.db results/backups/fco_analysis_results_$(date +%Y%m%d).db
```

### 3. 段階的リリース

- Phase 1完了後、本番DBへのマイグレーション
- Phase 2完了後、FRED 1-2銘柄で実運用テスト
- Phase 3完了後、歴史的データの段階的公開
- Phase 4完了後、全機能リリース

### 4. ユーザーコミュニケーション

- フロントエンド要件は実装時に確認
- パフォーマンス問題発生時は即座に報告
- 不明点は実装前に必ず確認

---

**策定**: プロジェクトオーナー + Claude Code
**参照**: [full_window_storage_strategy.md](full_window_storage_strategy.md) - 全窓保存戦略仕様書
**最終更新**: 2025-10-08
