# 安定版戦略 v2 - FRED優先 + Twelve Data補完

**決定日**: 2025-08-10  
**バージョン**: v1.0-stable  
**基本方針**: FRED優先原則 + Twelve Dataによる補完・拡張

## 🎯 データソース優先順位

### 優先原則
1. **FRED最優先**: 政府公式データ・制限なし・最高品質
2. **Twelve Data補完**: FREDにない銘柄を補完

### 重複銘柄の取り扱い
- **SP500, NASDAQCOM等**: FRED継続（変更なし）
- **仮想通貨・個別株式**: Twelve Data使用（FREDに存在しない）

## 📊 最終的な銘柄配分

### FRED担当（24銘柄）- 完全維持

#### 経済指標（14銘柄）
```
DGS2, DGS10, DGS30, DFF (金利)
CPIAUCSL, CPILFESL (物価)
DCOILWTICO, DCOILBRENTEU (原油)
DEXJPUS, DEXUSEU, DEXUSUK (為替)
VIXCLS, GOLDAMGBD228NLBM, CBBTCUSD (その他)
```

#### 米国株式指数（10銘柄）
```
SP500, NASDAQCOM, DJIA (主要指数)
DJTA, DJUA (ダウ輸送・公益)
NASDAQ100, NASDAQBANK, NASDAQFIN, NASDAQSOX, NASDAQTRAN (NASDAQ系)
```

### Twelve Data担当（補完銘柄のみ）

#### 仮想通貨（36銘柄）- CBBTCUSDはFRED優先
```
Tier 1: ETH, BNB, XRP, SOL, USDC, USDT, ADA, AVAX, DOT
Tier 2: LINK, MATIC, UNI, LTC, ATOM, ALGO, VET, FIL, AAVE, CRV
Tier 3: DOGE, SHIB, SAND, MANA, AXS, ENJ, COMP, SUSHI, 1INCH, BAT
        XMR, ZEC, DASH, EOS, TRX, XTZ, FLR
```
**注**: BTCはFREDのCBBTCUSDを優先使用

#### 個別株式（20銘柄）- 新規追加
```
Tech: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, NFLX
Finance: JPM, BAC, WFC, GS
Others: WMT, XOM, JNJ, PG, V, MA, DIS, MCD
```

## 🔧 カタログ更新方針

### 重複銘柄の処理例（BTCの場合）
```json
"CBBTCUSD": {
  "display_name": "Bitcoin (FRED Official)",
  "category": "crypto_assets",
  "data_sources": {
    "primary": {
      "provider": "fred",
      "symbol": "CBBTCUSD",
      "evaluation_score": 95
    }
  }
},
"BTC": {
  "display_name": "Bitcoin (Twelve Data)",
  "category": "crypto_assets_tier1",
  "data_sources": {
    "primary": {
      "provider": "twelvedata",
      "symbol": "BTC/USD",
      "evaluation_score": 88
    }
  },
  "note": "FREDのCBBTCUSDを優先使用推奨"
}
```

### 株式指数の取り扱い（SP500の場合）
```json
"SP500": {
  "display_name": "S&P 500 Index",
  "category": "us_major_indices",
  "data_sources": {
    "primary": {
      "provider": "fred",
      "symbol": "SP500",
      "evaluation_score": 95
    }
  },
  "note": "FRED公式データ・変更不要"
}
```

### 新規追加銘柄（AAPLの場合）
```json
"AAPL": {
  "display_name": "Apple Inc",
  "category": "us_tech_stocks",
  "data_sources": {
    "primary": {
      "provider": "twelvedata",
      "symbol": "AAPL",
      "evaluation_score": 88
    }
  }
}
```

## 📋 実装上の注意事項

### 1. 統合クライアントでの優先順位実装
```python
# 擬似コード
def get_symbol_data(symbol):
    # FREDシンボルリスト
    fred_symbols = ['SP500', 'NASDAQCOM', 'CBBTCUSD', ...]
    
    if symbol in fred_symbols:
        return fred_client.get_data(symbol)  # FRED優先
    else:
        return twelvedata_client.get_data(symbol)  # Twelve Data使用
```

### 2. ユーザー向け表示
- **ダッシュボード**: データソース明示（FRED/Twelve Data）
- **分析結果**: 使用データソースの記録
- **ドキュメント**: 優先順位の明確な説明

### 3. バックフィル実行時の考慮
- **FRED銘柄**: 制限なしで一括取得
- **Twelve Data銘柄**: レート制限考慮して段階的取得

## ⚠️ 重要な確認事項

### FRED継続利用の利点
1. **制限なし**: API制限を気にせず利用可能
2. **公式データ**: 米国政府提供の最高品質
3. **実績**: 既存システムで安定動作確認済み
4. **論文再現**: 1987年検証で使用実績あり

### Twelve Data追加の利点
1. **銘柄拡張**: 仮想通貨・個別株式の追加
2. **統一API**: 一つのAPIで多様な銘柄対応
3. **将来性**: 更なる銘柄追加が容易

## 🎯 最終的な構成

### 総銘柄数: 80銘柄
- **FRED**: 24銘柄（既存維持）
- **Twelve Data**: 56銘柄（新規追加）
- **重複**: CBBTCUSD/BTC（FREDのCBBTCUSD優先）

### データソース評価
| Provider | 銘柄数 | 評価スコア | 制限 | 役割 |
|----------|--------|------------|------|------|
| FRED | 24 | 95/100 | なし | 主力・優先 |
| Twelve Data | 56 | 88/100 | 800req/日 | 補完・拡張 |

## 📅 実装手順

### Step 1: カタログ整理
1. FRED銘柄の確認・維持
2. Twelve Data銘柄の追加
3. 重複銘柄の優先順位明示

### Step 2: 統合クライアント修正
1. FRED優先ロジック実装
2. 銘柄判定機能追加
3. エラーハンドリング

### Step 3: 検証
1. FRED銘柄の継続動作確認
2. Twelve Data新規銘柄テスト
3. 論文再現テスト（1987年）

---
**決定**: FRED優先原則 + Twelve Data補完による安定版実装
**重要**: SP500, NASDAQCOM等はFRED継続、仮想通貨・個別株式はTwelve Data使用