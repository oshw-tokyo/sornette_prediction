# 定期スケジュール分析システム - 要件定義書

## 📋 **1. システム概要**

### 🎯 **目的**
- 市場データの定期的な自動分析による継続的なクラッシュ予測
- 手動実行から自動スケジュール実行への移行
- 時系列での予測精度変化の追跡・可視化

### 🔄 **現在のシステムからの移行**
```
[現在] 手動実行 → 最新データのみ分析 → 単発の予測結果
[目標] スケジュール実行 → 継続的データ蓄積 → 時系列予測データベース
```

---

## 📊 **2. 理論的基盤・分析基準日の考え方**

### 🧮 **LPPL分析の時間軸設計**

**基本原理**:
```
分析基準日 = フィッティング期間の最終日
予測対象期間 = 分析基準日以降
実行日 = 分析基準日 + 1日以上（土曜日など）
```

**具体例**:
```
スケジュール実行: 2025-01-04(土) 09:00
├── データ取得期間: 2024-01-04 〜 2025-01-03 (365日間)
├── 分析基準日: 2025-01-03 (金曜日・最後の取引日)
├── フィッティング対象: 2024-01-04〜2025-01-03の価格変動
└── 予測対象: 2025-01-04以降のクラッシュ時期

投資判断への適用:
"2025-01-03時点のデータに基づく2025-01-04以降の予測"
→ 2025-01-04の投資判断に利用可能
```

### ✅ **理論的妥当性**
1. **因果関係の保持**: 過去データ→未来予測の時間順序が正しい
2. **実用性**: 分析結果がリアルタイム投資判断に利用可能
3. **科学的整合性**: Sornette論文の時系列分析手法に準拠

---

## 🚨 **3. 潜在的課題と対策**

### A. **データ更新タイミング課題**
**問題**: 
- 土曜日実行時に金曜日のFREDデータが未更新の可能性
- Alpha Vantage APIの夜間更新タイミング

**対策**:
```python
def validate_data_freshness(symbol: str, expected_date: str) -> bool:
    """データ最新性の検証"""
    latest_available = api_client.get_latest_date(symbol)
    if latest_available < expected_date:
        logger.warning(f"{symbol}: 期待日{expected_date}のデータ未更新")
        return False
    return True
```

### B. **市場休場日・祝日対応**
**問題**: 
- 連休でデータが数日古い状態
- 国際市場の休場日の違い

**対策**:
```python
def get_last_trading_day(target_date: str, market: str = "US") -> str:
    """最後の取引日を自動取得"""
    # pandas_market_calendarsまたは独自ロジックで実装
    pass
```

### C. **予測結果の時効管理**
**問題**: 
- 古い予測がダッシュボードに残存
- tc値の信頼性低下

**対策**:
```sql
-- 30日以上古い予測を無効化
UPDATE analysis_results 
SET is_expired = 1 
WHERE analysis_date < DATE('now', '-30 days')
```

---

## 🏗️ **4. システム設計要件**

### A. **スケジュール管理システム**

**🆕 新規テーブル設計**:
```sql
CREATE TABLE schedule_config (
    id INTEGER PRIMARY KEY,
    schedule_name TEXT UNIQUE,
    frequency TEXT,  -- 'daily', 'weekly', 'monthly'
    day_of_week INTEGER,  -- 0=月曜, 6=日曜
    hour INTEGER,
    minute INTEGER,
    timezone TEXT,
    symbols TEXT,  -- JSON配列形式
    enabled BOOLEAN DEFAULT 1,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- デフォルト設定例
INSERT INTO schedule_config VALUES (
    1, 'fred_weekly', 'weekly', 6, 9, 0, 'UTC', 
    '["NASDAQCOM", "SP500", "NASDAQ100"]', 1, NULL, NULL, CURRENT_TIMESTAMP
);
```

### B. **分析実行履歴管理**

**🔧 既存テーブル拡張**:
```sql
-- analysis_resultsテーブルに追加カラム
ALTER TABLE analysis_results ADD COLUMN schedule_name TEXT;
ALTER TABLE analysis_results ADD COLUMN analysis_basis_date DATE;  -- 分析基準日
ALTER TABLE analysis_results ADD COLUMN is_scheduled BOOLEAN DEFAULT 0;
ALTER TABLE analysis_results ADD COLUMN backfill_batch_id TEXT;  -- バックフィル識別
ALTER TABLE analysis_results ADD COLUMN is_expired BOOLEAN DEFAULT 0;
```

### C. **差分実行・重複回避システム**

**重複チェック関数**:
```python
def check_analysis_exists(symbol: str, basis_date: str, 
                         window_days: int = 365) -> bool:
    """指定条件での分析済みチェック"""
    query = """
    SELECT COUNT(*) FROM analysis_results 
    WHERE symbol = ? 
    AND analysis_basis_date = ? 
    AND window_days = ?
    AND is_expired = 0
    """
    # 既に同じ条件で分析済みならスキップ
```

### D. **バックフィル（過去データ蓄積）システム**

**初回実行時の過去データ収集**:
```python
def run_backfill_analysis(start_date: str, end_date: str, 
                         symbols: List[str]) -> str:
    """
    指定期間の過去分析を実行
    
    Args:
        start_date: バックフィル開始日 (例: "2024-01-01")
        end_date: バックフィル終了日 (例: "2025-01-01") 
        symbols: 対象銘柄リスト
        
    Returns:
        str: バックフィルバッチID
    """
    batch_id = f"backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 週次で過去データを分析
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    while current_date <= end:
        analysis_basis_date = current_date.strftime('%Y-%m-%d')
        
        for symbol in symbols:
            if not check_analysis_exists(symbol, analysis_basis_date):
                run_single_analysis(symbol, analysis_basis_date, 
                                  batch_id=batch_id)
        
        current_date += timedelta(days=7)  # 週次進行
    
    return batch_id
```

---

## ⚙️ **5. 実装仕様**

### A. **コマンド動作仕様** 🎯

**基本実行コマンド**:
```bash
# メイン実行: 自動データ補完 + 定期分析
python entry_points/main.py schedule run
  → 前回から今回までの不足データを自動補完（最大30日分）
  → 今回の定期分析を実行
  → スケジュール状態を更新
```

**自動データ補完の安全装置**:
```python
AUTO_BACKFILL_LIMIT = 30  # 最大30日分の自動補完

def should_auto_backfill(missing_periods: List[str]) -> bool:
    # 1. 期間数制限: 30日分以内
    # 2. 最古データ制限: 90日以内
    # 3. API制限考慮: 日次制限の80%以内
```

### B. **スケジューラー設計**

**メインスケジューラークラス**:
```python
class LPPLScheduler:
    def __init__(self, config_db_path: str):
        self.config_db = config_db_path
        self.alert_system = CrashAlertSystem()
    
    def run_scheduled_analysis(self, schedule_name: str) -> Dict:
        """指定スケジュールの分析実行（自動データ補完付き）"""
        config = self.get_schedule_config(schedule_name)
        
        # 分析基準日の算出
        basis_date = self.calculate_analysis_basis_date(
            config.frequency, config.day_of_week
        )
        
        # 重複チェック
        symbols_to_analyze = self.filter_unanalyzed_symbols(
            config.symbols, basis_date
        )
        
        # 分析実行
        results = []
        for symbol in symbols_to_analyze:
            result = self.run_single_scheduled_analysis(
                symbol, basis_date, schedule_name
            )
            results.append(result)
        
        # スケジュール設定更新
        self.update_schedule_status(schedule_name, datetime.now())
        
        return {
            'schedule_name': schedule_name,
            'basis_date': basis_date,
            'analyzed_symbols': len(results),
            'results': results
        }
```

### B. **既存システム統合**

**crash_alert_system.py拡張**:
```python
# 既存のrun_catalog_analysis()を拡張
def run_scheduled_catalog_analysis(self, schedule_name: str, 
                                 basis_date: str) -> Dict:
    """スケジュール実行専用のカタログ分析"""
    
    # 重複チェック付きの分析実行
    # 分析基準日の明示的設定
    # スケジュール名の記録
```

### C. **設定可能なスケジュール頻度**

**対応パターン**:
- **毎日**: `frequency='daily', hour=9, minute=0`
- **週次**: `frequency='weekly', day_of_week=6, hour=9`  
- **月次**: `frequency='monthly', day_of_month=1, hour=9`
- **カスタム**: cron式対応も可能

---

## 🎯 **6. 段階的実装計画**

### Phase 1: データベース拡張 (Week 1)
- [ ] スケジュール設定テーブル作成
- [ ] analysis_results テーブル拡張
- [ ] 重複チェック機能実装

### Phase 2: スケジューラー実装 (Week 2)  
- [ ] LPPLScheduler クラス作成
- [ ] 既存システム統合（crash_alert_system拡張）
- [ ] 分析基準日算出ロジック

### Phase 3: バックフィル機能 (Week 3)
- [ ] 過去データ一括分析機能
- [ ] バックフィル管理システム
- [ ] 進捗監視機能

### Phase 4: 運用機能 (Week 4)
- [ ] エラーハンドリング・リトライ
- [ ] 通知システム（成功・失敗通知）
- [ ] ダッシュボード時系列表示対応

---

## 📊 **7. 期待される効果**

### A. **運用効率化**
- 手動実行からの脱却
- 24時間無人運用可能
- 分析漏れの防止

### B. **分析品質向上**
- 一貫した分析条件での実行
- 時系列での予測精度変化追跡
- 複数銘柄の同期分析

### C. **投資判断支援強化**
- リアルタイムでの最新予測提供
- 歴史的な予測精度データ蓄積
- トレンド分析機能

---

## 🔍 **8. 未解決課題・今後の検討事項**

### A. **技術的課題**
- [ ] API制限とスケジュール頻度の最適化
- [ ] 大量データ処理時のパフォーマンス
- [ ] 障害時の自動復旧メカニズム

### B. **運用課題**  
- [ ] データ保存容量の増加対策
- [ ] 古いデータの整理方針
- [ ] システムメンテナンス時の処理

### C. **機能拡張**
- [ ] 複数タイムフレーム分析（日次・週次・月次）
- [ ] アラート条件のカスタマイズ
- [ ] 他の予測モデルとの統合