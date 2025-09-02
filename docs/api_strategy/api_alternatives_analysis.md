# 金融データAPI代替候補分析報告

## 📊 現在のAPI状況 (2025年8月)

### 1. **FRED (Federal Reserve Economic Data)** ✅ 最優秀
- **制限**: なし（無制限）
- **料金**: 完全無料
- **カバー範囲**: 米国インデックス、一部仮想通貨、経済指標
- **長所**: 高品質、安定、公的機関運営
- **短所**: 個別株式なし、米国中心

### 2. **Alpha Vantage** ⚠️ 制限あり
- **制限**: 500コール/日、5コール/分
- **料金**: 無料プラン制限あり、有料プラン$49.99/月〜
- **カバー範囲**: 株式、為替、仮想通貨、テクニカル指標
- **長所**: 幅広いカバー範囲、良質なデータ
- **短所**: 厳しいレート制限

### 3. **Yahoo Finance (yfinance)** ❌ 実質使用不可
- **制限**: 非常に厳しい（429エラー頻発）
- **料金**: 無料（公式APIなし）
- **問題点**: 2024年頃からアクセス制限強化、信頼性低下

## 🔍 代替API候補詳細

### 📈 **推奨候補 TOP 5**

#### 1. **Polygon.io** ⭐⭐⭐⭐⭐
```
料金: 無料プラン（5 API calls/分）
     Basic $99/月（無制限）
カバー: 米国株式、オプション、為替、仮想通貨
特徴: WebSocket対応、リアルタイム、2年分の履歴データ（無料）
URL: https://polygon.io/
```

#### 2. **Twelve Data** ⭐⭐⭐⭐⭐
```
料金: 無料プラン（800 API calls/日、8 calls/分）
     Grow $29/月（6,000 calls/日）
カバー: 株式、為替、仮想通貨、ETF、インデックス
特徴: 技術指標計算API、WebSocket対応
URL: https://twelvedata.com/
```

#### 3. **IEX Cloud** ⭐⭐⭐⭐
```
料金: 無料プラン（50,000メッセージ/月）
     Launch $9/月（500,000メッセージ）
カバー: 米国株式、為替、仮想通貨
特徴: 高速、信頼性高、RESTful API
URL: https://iexcloud.io/
```

#### 4. **Marketstack** ⭐⭐⭐⭐
```
料金: 無料プラン（1,000 calls/月）
     Basic $14.99/月（10,000 calls/月）
カバー: 世界72取引所、株式、ETF、インデックス
特徴: EOD/リアルタイム、125,000+ティッカー
URL: https://marketstack.com/
```

#### 5. **Finnhub** ⭐⭐⭐⭐
```
料金: 無料プラン（60 calls/分）
     Market Data $49.99/月
カバー: 株式、為替、仮想通貨、経済指標
特徴: WebSocket、企業ニュース、センチメント分析
URL: https://finnhub.io/
```

## 🌍 その他の選択肢

### 6. **Tiingo**
- 無料プラン: 500リクエスト/時、20リクエスト/分
- カバー: 米国株式、仮想通貨、ニュース
- 特徴: EOD無料、IEXリアルタイム統合

### 7. **EOD Historical Data**
- 無料プラン: 20 calls/日
- All World $79.99/月
- カバー: 150,000+ ティッカー、60+ 取引所

### 8. **Quandl (Nasdaq Data Link)**
- 料金: データセット別課金
- カバー: 金融、経済、代替データ
- 特徴: 高品質、機関投資家向け

### 9. **CoinGecko API** (仮想通貨特化)
- 無料プラン: 10-50 calls/分
- Pro $129/月
- カバー: 13,000+ 仮想通貨

### 10. **CoinMarketCap API** (仮想通貨特化)
- 無料プラン: 10,000 calls/月
- Hobbyist $29/月
- カバー: 仮想通貨全般

## 📊 プロジェクトへの推奨構成

### **最適な組み合わせ案**

#### **Option A: 無料最大化**
```
1. FRED (無制限) - インデックス、経済指標
2. Twelve Data (800/日) - 個別株式、補完データ
3. CoinGecko (無料) - 仮想通貨
```

#### **Option B: バランス型** 💰
```
1. FRED (無制限) - インデックス基盤
2. Polygon.io Basic ($99/月) - 株式全般
3. 既存Alpha Vantage - フォールバック
```

#### **Option C: 高品質優先** 💎
```
1. FRED (無制限) - インデックス
2. IEX Cloud Launch ($9/月) - 米国株式
3. Twelve Data Grow ($29/月) - 国際市場
```

## 🔧 実装推奨事項

### 1. **優先実装順序**
```python
1. Twelve Data統合 (Alpha Vantage代替として最適)
   - 無料枠が広い (800 calls/日 vs 500)
   - 分あたり制限が緩い (8 vs 5)
   - カバー範囲が広い

2. Polygon.io評価版実装
   - 高品質データ
   - WebSocket対応で効率的

3. IEX Cloud バックアップ
   - 信頼性高い
   - 無料枠十分
```

### 2. **Yahoo Finance対策**
```python
# yfinanceは完全に廃止推奨
# 既存実装があれば、以下への移行:
- インデックス → FRED
- 個別株式 → Twelve Data
- 仮想通貨 → CoinGecko
```

### 3. **API管理戦略**
```python
class UnifiedDataClient:
    providers = {
        'fred': FREDClient(),          # 無制限
        'twelve': TwelveDataClient(),   # 800/日
        'polygon': PolygonClient(),     # 有料オプション
        'iex': IEXClient(),             # バックアップ
    }
    
    def get_data_with_fallback(symbol):
        # 優先順位付きフォールバック
        for provider in get_providers_for_symbol(symbol):
            if provider.can_fetch(symbol):
                return provider.fetch(symbol)
```

## 📈 コスト・ベネフィット分析

| プラン | 月額費用 | カバー銘柄数 | API制限 | 推奨度 |
|--------|----------|-------------|---------|--------|
| 無料最大化 | $0 | 1,000+ | 制限あり | ⭐⭐⭐ |
| Twelve Data単独 | $29 | 10,000+ | 6,000/日 | ⭐⭐⭐⭐ |
| Polygon.io単独 | $99 | 無制限 | 無制限 | ⭐⭐⭐⭐⭐ |
| 組み合わせ | $38 | 20,000+ | 十分 | ⭐⭐⭐⭐ |

## 🎯 結論・推奨

1. **即座の対応**: Twelve Data無料プランの追加実装
2. **短期目標**: Yahoo Finance完全廃止、Twelve Data移行
3. **中期目標**: Polygon.io評価、必要に応じて有料化検討
4. **長期目標**: データソース多様化による安定性向上

**最重要**: Alpha Vantageの制限問題は、Twelve Dataへの部分移行で即座に改善可能（800 vs 500 calls/日）