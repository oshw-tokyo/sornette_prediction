# スケジュール実行コマンドの動作仕様

## 🤔 **ユーザー質問の分析**

### **質問1**: `main.py schedule` の役割
- **A案**: スケジュール設定のみ（解析は別途cron等で実行）
- **B案**: スケジュール設定 + 解析実行の統合コマンド

### **質問2**: 自動データ補完機能
- `--backfill`オプションなしでも、データ抜けを自動検出・補完するか？

---

## 🎯 **推奨設計方針**

### **1. `main.py schedule` = 解析実行コマンド**

**理由**:
- **実用性**: ユーザーが直接実行できる方が理解・運用しやすい
- **一貫性**: 他のコマンド（`analyze`, `dashboard`）と同様に実際の処理を実行
- **デバッグ性**: 手動でのスケジュール実行テストが容易

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

## 🎮 **コマンド体系の最終仕様**

### **基本実行コマンド**
```bash
# 🎯 メイン実行: 自動データ補完 + 定期分析
python entry_points/main.py schedule run
  → 前回から今回までの不足データを自動補完（最大30日分）
  → 今回の定期分析を実行
  → スケジュール状態を更新

# 📊 状態確認
python entry_points/main.py schedule status
  → 現在のスケジュール設定表示
  → 前回実行日時・次回予定日時
  → 不足データの検出結果

# 🔧 設定管理
python entry_points/main.py schedule config --frequency weekly --day saturday --hour 9
  → スケジュール設定の変更
```

### **特殊用途コマンド**
```bash
# 🏠 大量バックフィル（初回セットアップ用）
python entry_points/main.py schedule backfill --start 2024-01-01 --end 2024-12-31
  → 指定期間の全データを強制的に分析・蓄積
  → 自動補完制限を無視

# 🔄 強制実行（データ補完スキップ）
python entry_points/main.py schedule run --no-backfill
  → 不足データを無視して今回分のみ分析

# 🧹 メンテナンス
python entry_points/main.py schedule cleanup --older-than 180days
  → 古い分析結果の整理・アーカイブ
```

---

## 💡 **実用的な運用例**

### **シナリオ1: 通常の週次運用**
```bash
# 毎週土曜日09:00に自動実行（cronまたは手動）
python entry_points/main.py schedule run

# 期待される動作:
# - 前週土曜からの不足データチェック（通常は0件）
# - 今週土曜の定期分析実行
# - 16銘柄 × 1週間分 = 16件の新規分析結果
```

### **シナリオ2: 2週間後の再開**
```bash
# 2週間ぶりの実行
python entry_points/main.py schedule run

# 期待される動作:
# - 2週間分の不足データを自動検出（2期間）
# - 自動補完: 1週間前 + 2週間前の分析実行
# - 今回分の分析実行
# - 合計: 16銘柄 × 3週間分 = 48件の新規分析結果
```

### **シナリオ3: 長期中断後の復旧**
```bash
# 3ヶ月ぶりの実行
python entry_points/main.py schedule run

# 期待される動作:
# - 90日分の不足データを検出
# - 自動補完制限(30日)を超過
# - 警告メッセージ + 手動バックフィル推奨
# - 今回分のみ分析実行

# 手動での復旧:
python entry_points/main.py schedule backfill --start 2024-10-01
python entry_points/main.py schedule run
```

---

## 🔍 **設計の利点**

### **1. ユーザーフレンドリー**
- **シンプル**: `schedule run` だけで適切に動作
- **自動修復**: 小さな中断は自動で対応
- **明確な警告**: 大きな問題は明確にエラー表示

### **2. 運用安全性**
- **制限付き自動化**: 暴走防止の安全装置
- **段階的対応**: 軽微→警告→手動操作
- **状態の透明性**: 何が実行されるか事前に確認可能

### **3. 拡張性**
- **設定可能**: 頻度・制限値の調整可能
- **モジュラー**: 各機能が独立・テスト可能
- **ログ充実**: 詳細な実行履歴

---

## 📋 **要件定義への影響**

この仕様により、以下が明確化されました：

1. **`schedule run`**: メイン実行コマンド（解析実行）
2. **自動データ補完**: 制限付きで自動実行（最大30日分）
3. **安全装置**: 大量バックフィルは手動実行を要求
4. **運用簡素化**: 基本的に1コマンドで完結