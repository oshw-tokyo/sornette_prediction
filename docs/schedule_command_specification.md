# 定期解析システム(`scheduled-analysis`)コマンドの動作仕様

## ✅ **実装済み仕様（2025-08-05現在）**

本ドキュメントは、現在動作している `scheduled-analysis` コマンドの実装を正とした仕様書です。

### **コマンド基本構造**
```bash
python entry_points/main.py scheduled-analysis [subcommand] [options]
```

### **サブコマンド一覧**
- `configure`: スケジュール設定・管理
- `run`: 定期解析実行（自動バックフィル込み）
- `status`: システム状態確認
- `backfill`: 手動過去データ補完
- `errors`: エラー解析・監視
- `cleanup`: 古いエラーログ削除

### **2. 自動データ補完機能の統合**

**基本方針**:
```bash
# 通常のスケジュール実行で自動的にデータ補完
python entry_points/main.py schedule run
  ↓
  1. 前回実行日からの不足データを自動検出
  2. 不足期間のデータを自動補完（最大30日分）
  3. 最新の予定分析を実行
```

---

## 🔧 **詳細動作仕様**

### **A. `schedule run` コマンドの動作フロー**

```python
def schedule_run():
    """スケジュール分析の実行"""
    
    # 1. スケジュール設定読み込み
    config = load_active_schedule_config()
    
    # 2. 前回実行日の確認
    last_run_date = get_last_successful_run_date(config.schedule_name)
    
    # 3. 不足データの自動検出
    missing_periods = detect_missing_analysis_periods(
        last_run_date, config.frequency
    )
    
    # 4. 自動データ補完（制限あり）
    if missing_periods:
        if len(missing_periods) <= AUTO_BACKFILL_LIMIT:  # 例: 30日分
            print(f"🔄 自動データ補完: {len(missing_periods)}期間")
            for period in missing_periods:
                run_analysis_for_period(period, config.symbols)
        else:
            print(f"⚠️ 不足データが多すぎます({len(missing_periods)}期間)")
            print(f"手動バックフィル実行を推奨: --backfill --start {missing_periods[0]}")
            return
    
    # 5. 今回の定期分析実行
    current_period = calculate_current_analysis_period(config.frequency)
    run_analysis_for_period(current_period, config.symbols)
    
    # 6. スケジュール状態更新
    update_schedule_last_run(config.schedule_name, datetime.now())
```

### **B. 自動補完の制限ルール**

**安全装置**:
```python
AUTO_BACKFILL_LIMIT = 30  # 最大30日分（約4週間）の自動補完

def should_auto_backfill(missing_periods: List[str]) -> bool:
    """自動補完すべきかの判定"""
    
    # 1. 期間数制限
    if len(missing_periods) > AUTO_BACKFILL_LIMIT:
        return False
    
    # 2. 最古データの制限（例：90日以内）
    oldest_missing = datetime.strptime(missing_periods[0], '%Y-%m-%d')
    if (datetime.now() - oldest_missing).days > 90:
        return False
    
    # 3. API制限考慮（週次なら問題なし）
    estimated_api_calls = len(missing_periods) * len(symbols)
    if estimated_api_calls > DAILY_API_LIMIT * 0.8:  # 80%上限
        return False
    
    return True
```

---

## 🎮 **実装済みコマンド体系**

### **1. スケジュール設定 (`configure`)**
```bash
# Source×Frequency分離設計による設定
python entry_points/main.py scheduled-analysis configure \
  --source fred --frequency weekly --symbols NASDAQCOM,SP500

python entry_points/main.py scheduled-analysis configure \
  --source alpha_vantage --frequency daily --symbols AAPL,MSFT

# 実装済み設定:
# - fred_weekly: NASDAQCOM, SP500 (土曜日実行)
# - alpha_vantage_daily: AAPL, MSFT (日次実行)
```

### **2. 定期解析実行 (`run`)**
```bash
# 新方式: source×frequency指定
python entry_points/main.py scheduled-analysis run \
  --source fred --frequency weekly

# 旧方式互換: スケジュール名直接指定
python entry_points/main.py scheduled-analysis run \
  --schedule fred_weekly

# 自動実行内容:
# - 前回実行からの不足データ自動検出
# - 自動バックフィル（制限付き）
# - 今回の定期分析実行
# - スケジュール状態更新
```

### **3. システム状態確認 (`status`)**
```bash
python entry_points/main.py scheduled-analysis status

# 表示内容:
# - アクティブスケジュール一覧
# - 各スケジュールの頻度・銘柄数・最終実行日
# - 有効/無効状態
```

### **4. 手動バックフィル (`backfill`)**
```bash
# 週次スケジュールのバックフィル（曜日自動調整）
python entry_points/main.py scheduled-analysis backfill \
  --start 2024-01-01 --schedule fred_weekly

# 特徴:
# - 週次スケジュールは指定日を適切な曜日（土曜日）に自動調整
# - バックフィルバッチIDによる実行追跡
# - 科学的整合性確保（同一曜日での分析基準日）
```

### **5. エラー解析・監視 (`errors`)**
```bash
# 直近エラーの解析
python entry_points/main.py scheduled-analysis errors --days 7

# エラーカテゴリ:
# - API_ERROR, DATA_ERROR, ANALYSIS_ERROR, DATABASE_ERROR, SYSTEM_ERROR
# - 重要度別の集計・サマリー表示
```

### **6. メンテナンス (`cleanup`)**
```bash
# 古いエラーログの削除
python entry_points/main.py scheduled-analysis cleanup --days 90
```

---

## 💡 **実装済み運用例**

### **シナリオ1: 週次スケジュールの通常運用**
```bash
# 毎週土曜日の実行（手動またはcron）
python entry_points/main.py scheduled-analysis run --schedule fred_weekly

# 実際の動作（2025-08-05確認済み）:
# - 前週土曜からの不足データ自動検出
# - 今週土曜の定期分析実行（NASDAQCOM, SP500）
# - analysis_basis_date = 土曜日、basis_day_of_week = 5
# - 2銘柄 × 1週間分 = 2件の新規分析結果
```

### **シナリオ2: 日次スケジュールの通常運用**
```bash
# 毎日の実行
python entry_points/main.py scheduled-analysis run --schedule alpha_vantage_daily

# 実際の動作（2025-08-05確認済み）:
# - 前日からの不足データ自動検出
# - 当日の定期分析実行（AAPL, MSFT）
# - analysis_basis_date = 実行日、basis_day_of_week = 0-6
# - 2銘柄 × 1日分 = 2件の新規分析結果
```

### **シナリオ3: バックフィルによる初期データ生成**
```bash
# テスト完了済み（2025-08-05）
python entry_points/main.py scheduled-analysis backfill \
  --start 2025-07-15 --schedule fred_weekly

# 実際の動作確認済み:
# - 指定日（2025-07-15火）→適切な土曜日（2025-07-19）に自動調整
# - 科学的整合性確保（同一曜日での分析基準日）
# - バックフィルバッチID付与による追跡可能
# - データベースに正常保存確認済み
```

### **シナリオ4: 混在頻度データの管理**
```bash
# 現在の実装済み状況（2025-08-05）
python entry_points/main.py scheduled-analysis status

# 表示例:
# アクティブスケジュール: 2
#   - fred_weekly:
#     頻度: weekly, 銘柄数: 2, 最終実行: 2025-08-04, 有効: ✅
#   - alpha_vantage_daily:
#     頻度: daily, 銘柄数: 2, 最終実行: 2025-08-04, 有効: ✅

# データベース状況:
# - 6件の分析データ（週次4件、日次2件）
# - 曜日メタデータによる適切な分類
# - 混在データの識別・管理可能
```

---

## 🔍 **実装済み設計の利点**

### **1. Source×Frequency分離設計**
- **明確な概念分離**: データソース性質と実行頻度の独立管理
- **拡張性確保**: 新しいソース・頻度追加時の一貫性
- **ユーザー理解性**: 何をどの頻度で実行するかが明確

### **2. 科学的整合性の確保**
- **曜日整合性**: 週次分析の基準日曜日統一（土曜日）
- **分析基準日概念**: フィッティング期間最終日の明確な定義
- **メタデータ管理**: 曜日・頻度情報による適切なデータ分類

### **3. 実運用対応**
- **エラーハンドリング**: 包括的エラー分類・監視システム
- **自動バックフィル**: 制限付き自動データ補完
- **状態管理**: 詳細な実行履歴・スケジュール状態追跡

### **4. テスト完了済み機能**
- **フレッシュデータベーステスト**: 6件の分析データ生成確認
- **曜日調整機能**: バックフィル時の自動曜日調整動作確認
- **混在頻度管理**: 週次・日次データの同時管理機能確認

---

## 📋 **実装完了確認事項**

以下の機能が完全実装・テスト完了済み（2025-08-05）：

1. ✅ **`scheduled-analysis configure`**: Source×Frequency設定システム
2. ✅ **`scheduled-analysis run`**: 自動バックフィル付き定期解析実行
3. ✅ **`scheduled-analysis status`**: システム状態確認・監視
4. ✅ **`scheduled-analysis backfill`**: 曜日整合性確保の手動バックフィル
5. ✅ **`scheduled-analysis errors`**: 包括的エラー解析・監視システム
6. ✅ **`scheduled-analysis cleanup`**: メンテナンス機能
7. ✅ **科学的整合性**: 分析基準日概念・曜日メタデータ管理
8. ✅ **データベース統合**: SQLiteでの混在頻度データ管理

**システム状態**: 完全運用可能・本格利用段階