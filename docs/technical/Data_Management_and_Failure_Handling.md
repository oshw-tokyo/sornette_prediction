# データ管理とフィッティング失敗処理の詳細解説

## 📋 概要

現状の実装における、マルチマーケットの繰り返しフィッティングデータの保持方法と、フィッティング失敗時の処理について詳細に解説します。

---

## 🗄️ データ保持の仕組み

### 1. データベース設計による重複防止

#### UNIQUE制約による整合性確保
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    market TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    -- ... その他のカラム
    UNIQUE(timestamp, market, window_days)  -- 重複防止の核心
)
```

**重要な仕組み**:
- `(timestamp, market, window_days)` の組み合わせが一意
- 同日・同市場・同期間の分析結果は1件のみ保存
- 重複実行時は自動的に上書き更新

#### データ保存の実際の動作
```python
def save_prediction(self, record: PredictionRecord) -> int:
    cursor.execute("""
        INSERT OR REPLACE INTO predictions 
        (timestamp, market, window_days, ...)
        VALUES (?, ?, ?, ...)
    """, (...))
```

**動作例**:
```
2025-08-01 09:00 NASDAQ 730日 → 新規保存
2025-08-01 09:00 NASDAQ 730日 → 上書き更新（重複実行時）
2025-08-01 09:00 NASDAQ 365日 → 新規保存（期間が異なる）
2025-08-01 09:00 SP500  730日 → 新規保存（市場が異なる）
```

### 2. 実際のデータ蓄積パターン

#### 典型的な日次データ蓄積
```
日時: 2025-08-01 09:00
├── NASDAQ/365日  → tc=1.25, r²=0.85
├── NASDAQ/730日  → tc=1.33, r²=0.92
├── NASDAQ/1095日 → tc=1.47, r²=0.88
├── SP500/365日   → tc=1.18, r²=0.79
├── SP500/730日   → tc=1.29, r²=0.91
└── SP500/1095日  → tc=1.41, r²=0.87

日時: 2025-08-02 09:00
├── NASDAQ/365日  → tc=1.22, r²=0.87 (前日からの変化)
├── NASDAQ/730日  → tc=1.31, r²=0.93
└── ... (継続)
```

#### 時系列データの蓄積構造
```python
# 特定市場のトレンド追跡が可能
market_history = [
    {'date': '2025-08-01', 'tc': 1.25, 'r_squared': 0.85},
    {'date': '2025-08-02', 'tc': 1.22, 'r_squared': 0.87},
    {'date': '2025-08-03', 'tc': 1.19, 'r_squared': 0.89},
    # tc値の減少トレンド → 臨界点接近の可能性
]
```

---

## 🚫 フィッティング失敗処理の詳細

### 1. 失敗の階層的処理

#### レベル1: データ取得段階
```python
def analyze_market_window(self, market, window, end_date):
    try:
        # データ取得
        data = self.data_client.get_series_data(...)
        
        if data is None or len(data) < 100:  # 最低100日必要
            return None  # ← 失敗時はNoneを返す
            
    except Exception as e:
        print(f"エラー: {market.value}/{window.value}日 - {str(e)}")
        return None  # ← 例外時もNoneを返す
```

**失敗原因**:
- API接続エラー
- データ不足（100日未満）
- ネットワーク障害
- API制限

#### レベル2: フィッティング段階
```python
def _perform_lppl_fitting(self, data):
    best_result = None
    best_r2 = 0
    
    # 複数の初期値で試行
    for tc_init in [1.1, 1.2, 1.3, 1.5, 2.0]:
        try:
            popt, _ = curve_fit(logarithm_periodic_func, t, log_prices, ...)
            # 評価・更新
            if r_squared > best_r2:
                best_result = {...}
        except:
            continue  # ← 失敗した初期値はスキップ
    
    return best_result  # ← 全て失敗時はNoneを返す
```

**失敗原因**:
- 数値収束しない
- パラメータが境界外
- 数値不安定
- データにLPPLパターンが存在しない

#### レベル3: 品質判定段階
```python
if r_squared > best_r2:
    best_r2 = r_squared
    best_result = {...}
else:
    # R²が改善しない場合はそのまま次の初期値へ
```

**品質基準**:
- R² > 0.0（基本的な説明力）
- パラメータの物理制約満足
- 収束の安定性

### 2. 失敗時の実際の動作

#### 並列実行での失敗処理
```python
def run_full_analysis(self, parallel=True):
    results = []
    
    if parallel:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            
            for market in self.markets:
                for window in self.windows:
                    future = executor.submit(self.analyze_market_window, market, window)
                    futures.append((future, market, window))
            
            for future, market, window in futures:
                try:
                    result = future.result(timeout=60)
                    if result:  # ← 成功時のみ追加
                        results.append(result)
                        print(f"✅ {market.value}/{window.value}日: tc={result.tc:.3f}")
                except Exception as e:
                    print(f"❌ {market.value}/{window.value}日: エラー")
                    # ← 失敗はログのみ、データには含めない
```

**重要な特徴**:
- 失敗した分析は**results に含まれない**
- 成功した分析のみがデータベースに保存される
- **部分的成功**は許容される（例：8市場中6市場成功）

#### 失敗ログの例
```
🎯 マルチマーケット分析開始: 2025-08-01
   市場数: 4
   期間数: 3
   総分析数: 12

✅ NASDAQ/365日: tc=1.250
❌ NASDAQ/730日: エラー          ← フィッティング失敗
✅ NASDAQ/1095日: tc=1.470
✅ SP500/365日: tc=1.180
✅ SP500/730日: tc=1.290
❌ SP500/1095日: エラー          ← データ不足
✅ DJIA/365日: tc=1.330
✅ DJIA/730日: tc=1.410
✅ DJIA/1095日: tc=1.520
❌ BTC/365日: エラー            ← API接続失敗
❌ BTC/730日: エラー
❌ BTC/1095日: エラー

📊 分析完了: 7件の有効結果      ← 12件中7件成功
```

---

## 🔧 失敗データの補完戦略

### 1. 現状の実装での対処

#### データベース上での失敗の表現
```python
# 現在の実装では失敗データは保存されない
# → データベースに「歯抜け」が発生

# 例：2025-08-01のNASDAQ/730日が失敗した場合
predictions テーブル:
2025-08-01, NASDAQ, 365   ← 成功
2025-08-01, NASDAQ, 1095  ← 成功  
2025-08-01, SP500, 365    ← 成功
# NASDAQ/730の記録は存在しない ← 失敗により欠損
```

#### 欠損検出の方法
```python
def detect_missing_predictions(self, date: datetime) -> List[Dict]:
    """指定日の欠損データを検出"""
    
    expected_combinations = []
    for market in self.markets:
        for window in self.windows:
            expected_combinations.append((market.value, window.value))
    
    # 実際に存在するデータを取得
    existing_data = self.db.search_predictions({
        'date_from': date.strftime('%Y-%m-%d'),
        'date_to': date.strftime('%Y-%m-%d')
    })
    
    existing_combinations = set(
        (d['market'], d['window_days']) for d in existing_data
    )
    
    # 欠損を特定
    missing = []
    for market, window in expected_combinations:
        if (market, window) not in existing_combinations:
            missing.append({'market': market, 'window_days': window})
    
    return missing
```

### 2. 失敗に対する補完戦略

#### 戦略1: 再試行による補完
```python
def retry_failed_analysis(self, missing_predictions: List[Dict], max_retries: int = 3):
    """失敗した分析の再試行"""
    
    for missing in missing_predictions:
        market = MarketIndex(missing['market'])
        window = TimeWindow(missing['window_days'])
        
        for attempt in range(max_retries):
            print(f"再試行 {attempt+1}/{max_retries}: {market.value}/{window.value}日")
            
            try:
                result = self.analyze_market_window(market, window)
                if result:
                    # 成功時はデータベースに保存
                    record = self._convert_to_prediction_record(result)
                    self.db.save_prediction(record)
                    print(f"✅ 再試行成功: tc={result.tc:.3f}")
                    break
                else:
                    print(f"❌ 再試行{attempt+1}失敗")
                    
            except Exception as e:
                print(f"❌ 再試行{attempt+1}エラー: {str(e)}")
        else:
            # 全ての再試行が失敗
            print(f"🚫 {market.value}/{window.value}日: 全再試行失敗")
```

#### 戦略2: 前回値による補間
```python
def interpolate_missing_data(self, market: str, window_days: int, target_date: datetime):
    """前回成功値による補間"""
    
    # 過去の成功データを取得
    historical_data = self.db.search_predictions({
        'market': market,
        'window_days': window_days,
        'date_to': (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
    })
    
    if historical_data:
        latest = historical_data[0]  # 最新の成功データ
        
        # 補間フラグ付きで保存
        interpolated_record = PredictionRecord(
            timestamp=target_date,
            market=market,
            window_days=window_days,
            tc=latest['tc'],
            beta=latest['beta'],
            omega=latest['omega'],
            r_squared=latest['r_squared'],
            # ... その他のパラメータ
            # 補間であることを示すフラグが必要（現在の実装では未対応）
        )
        
        return interpolated_record
    
    return None
```

#### 戦略3: 失敗ログの詳細記録
```python
def record_failure_details(self, market: str, window_days: int, 
                         failure_reason: str, error_details: str):
    """失敗の詳細をログテーブルに記録"""
    
    # 新しいテーブルが必要（現在は未実装）
    failure_log = {
        'timestamp': datetime.now(),
        'market': market,
        'window_days': window_days,
        'failure_reason': failure_reason,  # 'DATA_INSUFFICIENT', 'FITTING_FAILED', 'API_ERROR'
        'error_details': error_details,
        'retry_count': 0,
        'resolved': False
    }
    
    # 失敗ログテーブルに保存（要実装）
    # self.db.save_failure_log(failure_log)
```

---

## 📊 実際の運用での影響

### 1. データ完整性への影響

#### 軽微な失敗（1-2件/日）
```python
# 例：12分析中11成功、1失敗
success_rate = 11/12 = 91.7%

影響:
- トレンド分析: 他の期間でカバー可能
- リスク検出: 複数市場・期間による冗長性
- 全体判断: 大きな影響なし
```

#### 重大な失敗（50%以上失敗）
```python
# 例：12分析中5成功、7失敗
success_rate = 5/12 = 41.7%

影響:
- データ不足によるトレンド分析困難
- リスク見逃しの可能性
- システム的な問題の可能性
- → 緊急対応が必要
```

### 2. 時系列データの一貫性

#### 断続的な失敗
```python
market_history = [
    {'date': '2025-08-01', 'tc': 1.25},  # 成功
    {'date': '2025-08-02', 'tc': None},  # 失敗 → 欠損
    {'date': '2025-08-03', 'tc': 1.19},  # 成功
]

# トレンド分析への影響
tc_trend = analyze_trend([1.25, 1.19])  # 欠損値を除外
# → 実際の変化（1.25→?→1.19）が不明
```

#### 連続的な失敗
```python
market_history = [
    {'date': '2025-08-01', 'tc': 1.25},  # 成功
    {'date': '2025-08-02', 'tc': None},  # 失敗
    {'date': '2025-08-03', 'tc': None},  # 失敗
    {'date': '2025-08-04', 'tc': None},  # 失敗
]

# → 重大なデータ断絶、要緊急対応
```

---

## 🎯 改善提案

### 1. 失敗ログテーブルの追加
```sql
CREATE TABLE failure_logs (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    market TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    failure_type TEXT NOT NULL,  -- 'DATA_ERROR', 'FITTING_FAILED', 'API_ERROR'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_date TEXT
);
```

### 2. 自動再試行システム
```python
class FailureRecoverySystem:
    def __init__(self):
        self.max_retries = 3
        self.retry_delays = [60, 300, 900]  # 1分、5分、15分後
    
    def schedule_retries(self, failed_analyses):
        for failure in failed_analyses:
            for i, delay in enumerate(self.retry_delays):
                schedule.every(delay).seconds.do(
                    self.retry_analysis, failure, attempt=i+1
                ).tag(f'retry_{failure["market"]}_{failure["window"]}')
```

### 3. データ品質監視
```python
class DataQualityMonitor:
    def check_daily_completeness(self, date):
        expected_count = len(self.markets) * len(self.windows)
        actual_count = len(self.db.get_predictions_for_date(date))
        
        completeness_rate = actual_count / expected_count
        
        if completeness_rate < 0.8:  # 80%未満で警告
            self.send_quality_alert(date, completeness_rate)
```

---

## 📋 まとめ

### 現状の実装の特徴

**✅ 長所**:
- 重複データの自動防止
- 部分的成功の許容
- 失敗時の graceful degradation

**⚠️ 課題**:
- 失敗データの詳細が記録されない
- 自動補完機能なし
- データ完整性の監視が不十分

**🎯 重要な理解**:
- 失敗したフィッティングは**データベースに残らない**
- 成功したデータのみが蓄積される
- トレンド分析では欠損値は自動的に除外される

この実装により、データの整合性は保たれますが、失敗の原因分析や自動補完機能の強化が今後の課題となります。

---

*作成日: 2025年8月2日*  
*作成者: Claude Code (Anthropic)*  
*ステータス: 現状実装の詳細解説完了*