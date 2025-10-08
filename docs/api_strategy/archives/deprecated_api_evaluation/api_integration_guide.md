# 📊 API統合ガイド - 包括的データ取得戦略

## 📋 概要

このドキュメントは、Sornette予測システムにおける3つのAPIソース（FRED、Alpha Vantage、CoinGecko）の統合戦略と、効率的なデータ取得方針を定義します。

### 🎯 統合目標
1. **FRED優先**: 無料・無制限の公的データを最大活用
2. **領域別特化**: 仮想通貨（CoinGecko）、個別株（Alpha Vantage）
3. **レート制限管理**: 安定した大量データ取得
4. **フォールバック機能**: データ信頼性の向上

---

## 🏗️ API統合アーキテクチャ

### 統合フロー
```
カタログ銘柄
    ↓
銘柄→APIマッピング
    ↓
優先順位判定 (FRED > Alpha Vantage > CoinGecko)
    ↓
レート制限管理
    ↓
データ取得 (get_series_data統一インターフェース)
    ↓
フォールバック実行
    ↓
FRED互換形式データ
```

### 実装ファイル
- **統合管理**: `infrastructure/data_sources/unified_data_client.py`
- **レート制限**: `infrastructure/data_sources/api_rate_limiter.py`
- **カタログ定義**: `infrastructure/data_sources/market_data_catalog.json`
- **個別クライアント**:
  - `fred_data_client.py`
  - `alpha_vantage_client.py` 
  - `coingecko_client.py`

---

## 📊 API別データ対応状況

### 1. **FRED (Federal Reserve Economic Data)** 🥇

#### 📈 **対応銘柄（14銘柄）**
| カテゴリ | 銘柄コード | 表示名 | 歴史データ範囲 |
|---------|-----------|-------|---------------|
| **米国指数** | NASDAQCOM | NASDAQ Composite | 1971-present |
| | SP500 | S&P 500 Index | 1957-present |
| | NASDAQ100 | NASDAQ 100 Index | 1985-present |
| | DJIA | Dow Jones Industrial | 2015-present |
| **セクター指数** | NASDAQSOX | Semiconductor Index | 1993-present |
| | NASDAQRSBLCN | Blockchain Economy Index | 2018-present |
| | DJTA | Transportation Average | 2015-present |
| | DJUA | Utility Average | 2015-present |
| **仮想通貨** | CBBTCUSD | Bitcoin (Coinbase) | 2014-12-01 to present |
| | CBETHUSD | Ethereum (Coinbase) | 2016-05-18 to present |
| **ボラティリティ** | VIXCLS | VIX Volatility Index | 1990-present |
| | GVZCLS | Gold ETF Volatility | 2008-present |
| | OVXCLS | Oil ETF Volatility | 2007-present |
| **REIT** | REITTMA | REIT Mortgage Assets | 1945-present |

#### ⚡ **制限・特徴**
- **レート制限**: 120 calls/min, 10,000 calls/day
- **コスト**: 完全無料
- **品質**: 公的機関データ、最高品質
- **APIキー取得**: https://fred.stlouisfed.org/docs/api/api_key.html

---

### 2. **Alpha Vantage** 🥈

#### 📈 **対応銘柄（2銘柄）**
| カテゴリ | 銘柄コード | 表示名 | 歴史データ範囲 |
|---------|-----------|-------|---------------|
| **個別株** | AAPL | Apple Inc. | 1980-present |
| | TSLA | Tesla Inc. | 2010-present |

#### ⚡ **制限・特徴**
- **レート制限**: 5 calls/min, 500 calls/day
- **コスト**: 無料版制限あり、有料版$49.99/月〜
- **品質**: 良質な個別株データ
- **APIキー取得**: https://www.alphavantage.co/support/#api-key

#### 💡 **拡張可能銘柄（実装済みマッピング）**
- MSFT, GOOGL, AMZN, NVDA, META, NFLX

---

### 3. **CoinGecko** 🥉

#### 📈 **対応銘柄（6銘柄）**
| カテゴリ | 銘柄コード | 表示名 | 歴史データ範囲 |
|---------|-----------|-------|---------------|
| **Layer-1仮想通貨** | BNB | Binance Coin | 2017-present |
| | SOL | Solana | 2020-present |
| | ADA | Cardano | 2017-present |
| **Meme仮想通貨** | DOGE | Dogecoin | 2013-present |
| **FRED補完** | BTC | Bitcoin (CoinGecko) | 2013-present *(フォールバック)* |
| | ETH | Ethereum (CoinGecko) | 2015-present *(フォールバック)* |

#### ⚡ **制限・特徴**
- **レート制限**: 20 calls/min (無料版), 500 calls/min (Pro)
- **コスト**: 無料版制限あり、Pro版$129/月
- **品質**: 市場集約データ、リアルタイム
- **特記**: 実測値では3秒間隔推奨（無料版）

#### 💡 **拡張可能銘柄（20種類サポート）**
- XRP, DOT, AVAX, SHIB, LINK, TRX, MATIC, UNI, ALGO, VET, ATOM, LTC, BCH, XLM等

---

## 🎯 API優先順位戦略

### 優先順位決定ロジック
1. **FRED最優先**: 公的機関データ、無制限アクセス
2. **Alpha Vantage補完**: 個別株式専用
3. **CoinGecko補完**: 仮想通貨拡張・フォールバック

### 銘柄タイプ別優先順位
```python
銘柄マッピング = {
    # FRED優先（公的指数）
    'NASDAQCOM': {'fred': 'NASDAQCOM', 'alpha_vantage': '^IXIC'},
    'SP500': {'fred': 'SP500', 'alpha_vantage': 'SPY'},
    
    # FRED優先（仮想通貨、フォールバック付き）
    'CBBTCUSD': {'fred': 'CBBTCUSD', 'coingecko': 'BTC'},
    'CBETHUSD': {'fred': 'CBETHUSD', 'coingecko': 'ETH'},
    
    # CoinGecko専用（仮想通貨拡張）
    'BNB': {'coingecko': 'BNB'},
    'SOL': {'coingecko': 'SOL'},
    'ADA': {'coingecko': 'ADA'},
    'DOGE': {'coingecko': 'DOGE'},
    
    # Alpha Vantage専用（個別株）
    'AAPL': {'alpha_vantage': 'AAPL'},
    'TSLA': {'alpha_vantage': 'TSLA'},
}
```

---

## ⏱️ レート制限管理

### 実装済み制限設定
```json
{
    "fred": {
        "requests_per_minute": 120,
        "requests_per_day": 10000,
        "interval": "0.5秒"
    },
    "alpha_vantage": {
        "requests_per_minute": 5, 
        "requests_per_day": 500,
        "interval": "12秒"
    },
    "coingecko": {
        "requests_per_minute": 20,
        "requests_per_day": 28800,
        "interval": "3秒"
    }
}
```

### 制限管理機能
- **APIRateLimiter**: プログレスバー付き自動待機
- **履歴永続化**: 24時間のリクエスト履歴保持
- **推定完了時間**: 大量データ取得の時間予測
- **エラーハンドリング**: 429エラーの自動リトライ

---

## 📈 データ取得効率化戦略

### 1. **バッチ処理最適化**
```python
# 推奨: APIソース別グループ化
fred_symbols = ['NASDAQCOM', 'SP500', 'CBBTCUSD', 'CBETHUSD']
coingecko_symbols = ['BNB', 'SOL', 'ADA', 'DOGE'] 
alpha_vantage_symbols = ['AAPL', 'TSLA']

# 各ソース別に連続実行（制限管理自動化）
```

### 2. **時間帯別実行**
- **FRED**: 制限緩和のため任意時間実行可能
- **Alpha Vantage**: レート制限厳しいため分散実行
- **CoinGecko**: 大量取得時は長時間確保

### 3. **フォールバック戦略**
```python
実行順序 = [
    "FRED (最優先・高速)",
    "Alpha Vantage (制限あり・重要銘柄)",
    "CoinGecko (補完・仮想通貨拡張)"
]
```

---

## 🛠️ 実装ガイド

### 基本的な使用方法
```python
from infrastructure.data_sources.unified_data_client import UnifiedDataClient

# クライアント初期化
client = UnifiedDataClient()

# 単一銘柄取得
data, source = client.get_data_with_fallback(
    'CBBTCUSD', '2024-01-01', '2024-12-31'
)

# 複数銘柄取得（制限管理自動化）
symbols = ['NASDAQCOM', 'BNB', 'AAPL']
results = client.get_multiple_symbols(symbols, '2024-01-01', '2024-12-31')
```

### crash_alert_systemでの統合利用
```python
# 既存システムでの使用例
self.data_client = UnifiedDataClient()
self.rate_limiter = APIRateLimiter()

# API制限チェック + データ取得
self.rate_limiter.check_and_wait('fred', 1)
data, source = self.data_client.get_data_with_fallback(symbol, start, end)
```

---

## 📊 推奨データ取得プロファイル

### Profile A: 高頻度分析（日次実行）
```python
推奨銘柄 = [
    'CBBTCUSD',    # Bitcoin (FRED)
    'NASDAQCOM',   # NASDAQ (FRED) 
    'SP500',       # S&P500 (FRED)
]
制限考慮 = "FRED中心で制限なし、高速実行可能"
```

### Profile B: 包括分析（日次実行）
```python
推奨銘柄 = [
    # FRED (制限なし)
    'CBBTCUSD', 'CBETHUSD', 'NASDAQCOM', 'SP500', 'NASDAQ100',
    'NASDAQSOX', 'DJIA', 'VIXCLS',
    
    # CoinGecko (制限あり)
    'BNB', 'SOL', 'ADA', 'DOGE',
    
    # Alpha Vantage (制限厳しい)
    'AAPL', 'TSLA'
]
実行時間 = "約15-20分（制限待機含む）"
```

### Profile C: 完全分析（月次実行）
```python
全銘柄 = "カタログ全20銘柄"
実行時間 = "約30-45分"
推奨 = "夜間バッチ処理"
```

---

## ⚠️ 制限・注意事項

### 1. **APIキー管理**
```bash
# 環境変数設定（必須）
export FRED_API_KEY="your_fred_api_key"
export ALPHA_VANTAGE_KEY="your_alpha_vantage_key"
# export COINGECKO_API_KEY="your_pro_key"  # Pro版のみ
```

### 2. **データ品質考慮**
- **FRED**: 最高品質、公的データ
- **Alpha Vantage**: 商業データ、一般的に良質
- **CoinGecko**: 市場集約データ、変動あり

### 3. **制限対策**
- **429エラー**: 自動リトライ実装済み
- **大量取得**: 時間をかけて段階実行
- **Pro版推奨**: 本格運用時はPro APIキー検討

---

## 🎯 今後の拡張計画

### Phase 1: 現在（実装完了）
- ✅ 3つのAPIソース統合
- ✅ 20銘柄対応
- ✅ レート制限管理

### Phase 2: 短期拡張
- 🔄 Individual stocks追加（MSFT, GOOGL, AMZN等）
- 🔄 国際指数対応検討
- 🔄 Pro版API導入

### Phase 3: 長期戦略
- 📋 代替APIソース評価（Twelve Data, Polygon.io）
- 📋 リアルタイムデータ対応
- 📋 WebSocket統合

---

## 📚 関連ドキュメント

- **カタログ仕様**: `market_data_catalog.json`
- **数学的基礎**: `docs/mathematical_foundation.md`
- **実装戦略**: `docs/implementation_strategy.md`
- **API代替調査**: `workspace_for_claude/api_alternatives_analysis.md`

---

**最終更新**: 2025-08-08  
**バージョン**: v3.0.0 (CoinGecko統合版)  
**メンテナ**: Claude Code System