# 📊 価格データローカル保存実装計画

**作成日**: 2025-01-15
**ステータス**: 実装計画策定中

## 🎯 概要

FCO v2.1システムにおいて、価格データをローカルデータベースに保存し、APIパフォーマンスを向上させる実装計画。

## 📐 データベース設計

### 新規テーブル: `market_price_data`

```sql
CREATE TABLE IF NOT EXISTS market_price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume REAL,
    -- ログスケール変換済みデータ（計算負荷削減用）
    log_close REAL,  -- = log(close)

    -- データソース情報
    data_source TEXT,  -- 'fred', 'twelvedata', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス用
    UNIQUE(symbol, date)
);

-- パフォーマンス用インデックス
CREATE INDEX idx_price_symbol_date ON market_price_data(symbol, date);
CREATE INDEX idx_price_date ON market_price_data(date);
```

### LPPLフィット結果保存テーブル: `lppl_fitted_curves`

```sql
CREATE TABLE IF NOT EXISTS lppl_fitted_curves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,  -- fco_analysis_results.id
    symbol TEXT NOT NULL,

    -- フィット期間
    fit_start_date DATE NOT NULL,
    fit_end_date DATE NOT NULL,
    num_points INTEGER NOT NULL,

    -- LPPLパラメータ（再計算用）
    tc REAL,      -- Critical time
    m REAL,       -- Power law exponent
    omega REAL,   -- Log-periodic frequency
    phi REAL,     -- Phase
    a REAL,       -- Linear parameter
    b REAL,       -- Power law amplitude
    c REAL,       -- Log-periodic amplitude

    -- フィット品質
    r_squared REAL,
    rmse REAL,

    -- フィット済み曲線データ（JSON配列）
    fitted_values TEXT,  -- JSON array of fitted log prices

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (analysis_id) REFERENCES fco_analysis_results(id),
    UNIQUE(analysis_id, symbol, fit_end_date)
);
```

## 🔄 実装フェーズ

### Phase 1: 価格データ保存機能（現在）

1. **データ取得時の保存**
```python
def fetch_and_store_price_data(symbol: str, start_date: date, end_date: date):
    # 1. データ取得
    prices = data_client.get_historical_prices(symbol, start_date, end_date)

    # 2. ログスケール変換
    prices['log_close'] = np.log(prices['close'])

    # 3. データベースに保存（UPSERT）
    for _, row in prices.iterrows():
        db.execute("""
            INSERT OR REPLACE INTO market_price_data
            (symbol, date, close, log_close, data_source)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, row['date'], row['close'], row['log_close'], source))
```

2. **FCO分析実行時のデータ利用**
```python
def get_price_data_for_analysis(symbol: str, end_date: date, days: int):
    # ローカルDBから取得を優先
    prices = db.query("""
        SELECT date, close, log_close
        FROM market_price_data
        WHERE symbol = ? AND date <= ?
        ORDER BY date DESC
        LIMIT ?
    """, (symbol, end_date, days))

    if len(prices) < days:
        # 不足分を外部APIから取得して保存
        fetch_missing_data(symbol, prices)

    return prices
```

### Phase 2: LPPLフィット結果のキャッシュ（次ステップ）

```python
def save_lppl_fit_result(analysis_id: int, symbol: str, params: dict, fitted_values: np.array):
    """LPPLフィット結果を保存"""
    db.execute("""
        INSERT INTO lppl_fitted_curves
        (analysis_id, symbol, tc, m, omega, phi, a, b, c,
         r_squared, fitted_values, fit_end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        analysis_id, symbol, params['tc'], params['m'],
        params['omega'], params['phi'], params['a'],
        params['b'], params['c'], params['r_squared'],
        json.dumps(fitted_values.tolist()),
        params['fit_end_date']
    ))
```

### Phase 3: API最適化（将来）

```python
def get_price_series_with_lppl_optimized(symbol: str, analysis_id: int):
    # 1. キャッシュ済みLPPLフィットを取得
    cached_fit = db.query("""
        SELECT * FROM lppl_fitted_curves
        WHERE analysis_id = ? AND symbol = ?
    """, (analysis_id, symbol))

    if cached_fit:
        # キャッシュから返す（高速）
        return {
            'prices': get_cached_prices(symbol, cached_fit['fit_end_date']),
            'lppl_fit': json.loads(cached_fit['fitted_values']),
            'params': extract_params(cached_fit)
        }
    else:
        # 計算して保存
        result = calculate_lppl_fit(symbol, analysis_id)
        save_lppl_fit_result(analysis_id, symbol, result)
        return result
```

## 📊 メリット

1. **パフォーマンス向上**
   - 外部API呼び出し削減
   - ログスケール変換の事前計算
   - LPPLフィット結果のキャッシュ

2. **データの一貫性**
   - 分析時点のデータを保持
   - 再現性の確保

3. **コスト削減**
   - 外部APIの利用制限回避
   - レート制限の影響軽減

## 🚀 実装優先順位

1. **即座に実装**（Phase 1）
   - `market_price_data`テーブル作成
   - 価格データ保存機能
   - ログスケール事前計算

2. **次の実装**（Phase 2）
   - `lppl_fitted_curves`テーブル作成
   - フィット結果のキャッシュ

3. **将来の最適化**（Phase 3）
   - インデックス最適化
   - データ圧縮
   - 古いデータのアーカイブ

## 📝 注意事項

- 初期はシンプルな実装を優先
- データ量の増加を監視
- 定期的なバックアップを実施

---

**次のアクション**:
1. `market_price_data`テーブルの作成
2. データ取得・保存機能の実装
3. APIエンドポイントの更新（ローカルDBからデータ取得）