# カタログAPI移行計画

**目的**: CoinGecko/Alpha Vantage制限問題を解決するため、Twelve Data/Finnhubを最優先にカタログを更新

## 🎯 API評価スコアリング結果

| API | 総合スコア | レート制限 | 銘柄カバレッジ | データ品質 | APIキー取得 | 実装複雑度 |
|-----|-----------|-----------|----------------|------------|-------------|------------|
| **Twelve Data** | 88/100 | 20/25 | 23/25 | 18/20 | 15/15 | 12/15 |
| **Binance** | 85/100 | 25/25 | 20/25 | 20/20 | 10/15 | 10/15 |
| **Finnhub** | 75/100 | 12/25 | 18/25 | 17/20 | 15/15 | 13/15 |
| **CoinGecko** | 60/100 | 8/25 | 15/25 | 15/20 | 12/15 | 10/15 |
| **Alpha Vantage** | 55/100 | 5/25 | 12/25 | 16/20 | 12/15 | 10/15 |

## 📊 銘柄別API割り当て戦略

### 仮想通貨 (37銘柄)
**最優先**: Twelve Data (BTC/USD, ETH/USD形式)
**セカンダリ**: Binance API (2025-08-12以降)
**バックアップ**: CoinGecko (現行)

### 米国株式 (20銘柄)
**最優先**: Twelve Data (AAPL, MSFT形式)
**セカンダリ**: Finnhub (AAPL形式) ※制限あり
**バックアップ**: Alpha Vantage (現行)

### FRED経済指標 (24銘柄)
**変更なし**: FRED (制限なし、高品質継続)

## 🔧 実装方針

### Phase 1: Twelve Data移行（即座実行可能）

#### 1.1 仮想通貨銘柄の移行
```json
"BTC": {
  "display_name": "Bitcoin",
  "data_sources": {
    "primary": {
      "provider": "twelvedata",
      "symbol": "BTC/USD",
      "evaluation_score": 88
    },
    "secondary": {
      "provider": "coingecko", 
      "symbol": "bitcoin",
      "evaluation_score": 60
    }
  }
}
```

#### 1.2 株式銘柄の移行
```json
"AAPL": {
  "display_name": "Apple Inc",
  "data_sources": {
    "primary": {
      "provider": "twelvedata",
      "symbol": "AAPL",
      "evaluation_score": 88
    },
    "secondary": {
      "provider": "alpha_vantage",
      "symbol": "AAPL", 
      "evaluation_score": 55
    }
  }
}
```

### Phase 2: Binance API統合（2025-08-12以降）

#### 2.1 仮想通貨のBinance優先設定
```json
"BTC": {
  "data_sources": {
    "primary": {
      "provider": "binance",
      "symbol": "BTCUSDT",
      "evaluation_score": 85
    },
    "secondary": {
      "provider": "twelvedata",
      "symbol": "BTC/USD",
      "evaluation_score": 88  
    },
    "tertiary": {
      "provider": "coingecko",
      "symbol": "bitcoin",
      "evaluation_score": 60
    }
  }
}
```

### Phase 3: フォールバック戦略最適化

#### 3.1 動的プロバイダー選択
- API制限到達時の自動切り替え
- レスポンス時間ベースの最適化
- エラー頻度による信頼度評価

## 📋 移行手順

### Step 1: 重要銘柄の先行移行
**対象**: BTC, ETH, USDT, USDC, AAPL, MSFT, NASDAQCOM, SP500

1. カタログ更新（primary→twelvedata）
2. 統合テスト実行
3. 論文再現テスト（1987年ブラックマンデー）確認
4. データ品質検証

### Step 2: 全銘柄の段階的移行
**対象**: 残り73銘柄

1. カテゴリ別移行（crypto_tier1 → crypto_tier2 → us_indices → international）
2. 各カテゴリ移行後の検証実行
3. エラー・制限状況の監視

### Step 3: 旧API廃止
**対象**: CoinGecko, Alpha Vantage

1. バックアップ位置への格下げ
2. 利用状況監視（フォールバック頻度）
3. 段階的な削除検討

## ⚠️ リスク管理

### 技術リスク
- **Twelve Data制限**: 800req/日の制限管理
- **データ互換性**: データ形式の統一化
- **レスポンス時間**: API応答時間の違い

### 運用リスク
- **APIキー管理**: 複数APIキーの安全な管理
- **コスト管理**: 無料プラン制限の監視
- **依存性リスク**: 単一API障害時の影響

### 緩和策
- **段階的移行**: 一度に大きな変更を避ける
- **バックアップ維持**: 旧APIを当面バックアップとして保持
- **監視強化**: API使用量・エラー率の継続監視

## 📅 タイムライン

### Week 1 (現在)
- [x] API評価・選定完了
- [x] TwelveData/Finnhub実装完了
- [ ] 重要銘柄カタログ更新
- [ ] 統合テスト実行

### Week 2
- [ ] 全銘柄カタログ移行
- [ ] 包括的データ検証
- [ ] パフォーマンステスト

### Week 3 (Binance API利用可能後)
- [ ] Binance API統合
- [ ] 仮想通貨データの最適化
- [ ] フォールバック戦略調整

## 🎯 期待効果

### データ取得率向上
- **仮想通貨**: 40.5% → 95%+（BTC/ETH等主要通貨確保）
- **株式**: 85% → 95%+（制限解消）
- **総合**: 49.4% → 90%+

### システム安定性向上
- **レート制限**: 大幅な制限緩和
- **エラー率**: API品質向上により低下
- **レスポンス**: より高速なデータ取得

### 分析精度向上
- **データ完全性**: 欠損データの大幅削減
- **時系列一貫性**: 高品質データソースによる改善
- **予測信頼性**: 包括的データによる精度向上

---
**次回アクション**: 重要銘柄のカタログ更新実行