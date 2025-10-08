# 安定版戦略 - FRED + Twelve Data

**決定日**: 2025-08-10  
**バージョン**: v1.0-stable  
**基本方針**: FRED（経済指標）+ Twelve Data（株式・仮想通貨）による安定運用

## 🎯 安定版の定義

### データソース構成
- **FRED**: 24銘柄（経済指標・為替・原油等）- 制限なし・高品質
- **Twelve Data**: 57銘柄（仮想通貨37 + 株式20）- 800req/日制限管理

### 合計対象銘柄: 81銘柄

## 📊 銘柄カテゴリ別配分

### FRED担当（24銘柄）- 変更なし

#### 経済指標（14銘柄）
- **金利**: DGS2, DGS10, DGS30, DFF
- **物価**: CPIAUCSL, CPILFESL, DCOILWTICO, DCOILBRENTEU
- **為替**: DEXJPUS, DEXUSEU, DEXUSUK
- **その他**: VIXCLS, GOLDAMGBD228NLBM, CBBTCUSD

#### 米国株式指数（10銘柄）
- **主要指数**: SP500, NASDAQCOM, DJIA
- **セクター指数**: DJTA, DJUA, NASDAQ100, NASDAQBANK, NASDAQFIN, NASDAQSOX, NASDAQTRAN

### Twelve Data担当（57銘柄）

#### 仮想通貨（37銘柄）
**Tier 1 - 基軸通貨（10銘柄）**:
- BTC, ETH, BNB, XRP, SOL, USDC, USDT, ADA, AVAX, DOT

**Tier 2 - DeFi・スケーリング（10銘柄）**:
- LINK, MATIC, UNI, LTC, ATOM, ALGO, VET, FIL, AAVE, CRV

**Tier 3 - その他（17銘柄）**:
- DOGE, SHIB, SAND, MANA, AXS, ENJ, COMP, SUSHI, 1INCH, BAT
- XMR, ZEC, DASH, EOS, TRX, XTZ, FLR

#### 株式（20銘柄）
**テクノロジー（8銘柄）**:
- AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, NFLX

**金融（4銘柄）**:
- JPM, BAC, WFC, GS

**その他セクター（8銘柄）**:
- WMT, XOM, JNJ, PG, V, MA, DIS, MCD

## 🔧 実装計画

### Phase 1: カタログ更新（即座実行）

#### 1.1 仮想通貨銘柄の更新例
```json
"BTC": {
  "display_name": "Bitcoin",
  "category": "crypto_assets_tier1",
  "data_sources": {
    "primary": {
      "provider": "twelvedata",
      "symbol": "BTC/USD",
      "evaluation_score": 88
    }
  }
}
```

#### 1.2 株式銘柄の追加例
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

### Phase 2: 統合テスト（必須）

#### 2.1 接続テスト
- FRED: 全24銘柄のデータ取得確認
- Twelve Data: 代表10銘柄（BTC, ETH, AAPL等）確認

#### 2.2 データ品質検証
- 時系列データの完全性
- 価格データの精度
- 欠損データの確認

#### 2.3 論文再現テスト
- 1987年ブラックマンデー検証（100/100スコア維持）
- NASDAQCOM等既存銘柄の連続性確認

### Phase 3: 運用開始

#### 3.1 レート制限管理
- Twelve Data: 800req/日 → 33req/時 → 実装では30req/時（120秒間隔）
- 57銘柄 × 1日1回 = 57req/日（制限内で十分）

#### 3.2 エラーハンドリング
- API障害時の適切なログ記録
- 部分的失敗の継続処理
- リトライメカニズム

## 📋 移行チェックリスト

### ✅ 準備完了
- [x] Twelve Data APIキー設定
- [x] Twelve Dataクライアント実装
- [x] 統合クライアントへの組み込み
- [x] FREDクライアント正常動作確認

### 📝 実施予定
- [ ] market_data_catalog.json更新（81銘柄）
- [ ] 重要銘柄の動作確認（BTC, ETH, AAPL, SP500）
- [ ] backfillbatch実行による初期データ取得
- [ ] ダッシュボード表示確認
- [ ] 論文再現テスト実行

## ⚠️ リスク管理

### 技術的リスク
1. **レート制限到達**: 
   - 対策: 120秒間隔の確実な実装
   - 監視: API使用量の定期確認

2. **データ形式の違い**:
   - 対策: データ正規化処理の実装
   - 検証: 各データソースの出力確認

3. **API障害**:
   - 対策: エラーハンドリング強化
   - 代替: 必要最小限のCoinGecko/Alpha Vantage保持

### 運用リスク
1. **初期データ不足**:
   - 対策: backfillbatch実行による365日データ取得
   - 時間: 約2-3時間（レート制限考慮）

2. **ユーザー影響**:
   - 対策: 段階的移行（重要銘柄優先）
   - 通知: 移行完了の確認メッセージ

## 🎯 期待される成果

### データ取得率
- **FRED**: 100%（24/24銘柄）
- **Twelve Data**: 95%以上期待（57銘柄）
- **総合**: 90%以上（73/81銘柄以上）

### システム安定性
- **API制限**: 大幅に改善（CoinGecko 10req/分 → Twelve Data 800req/日）
- **エラー率**: 低下見込み（高品質API使用）
- **分析速度**: 向上（待機時間削減）

### 分析精度
- **データ完全性**: BTC/ETH等主要銘柄の確実な取得
- **時系列一貫性**: 単一APIによる一貫性向上
- **予測信頼性**: 包括的データによる精度向上

## 📅 タイムライン

### Day 1（今日）
- カタログ更新実施
- 重要銘柄テスト（BTC, ETH, AAPL, SP500）
- 初期動作確認

### Day 2-3
- 全銘柄のbackfillbatch実行
- データ品質検証
- ダッシュボード確認

### Day 4-5
- 論文再現テスト
- 最終調整
- 安定版リリース

## 🚀 将来拡張

### 中期（Binance API統合後）
- 仮想通貨データの高頻度更新
- リアルタイム価格監視
- 3層フォールバック実装

### 長期
- 銘柄追加（国際市場等）
- 有料API検討（必要に応じて）
- 機械学習による最適API選択

---
**決定**: FRED + Twelve Dataによる安定版実装を承認
**次回アクション**: market_data_catalog.json更新の実施