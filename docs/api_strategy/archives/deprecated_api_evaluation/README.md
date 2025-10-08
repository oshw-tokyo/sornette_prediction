# Deprecated API Evaluation Documents Archive

**アーカイブ日**: 2025-10-08
**理由**: Alpha Vantage、CoinGecko評価文書（現在は不使用、FRED + Twelve Data採用）

---

## 📁 アーカイブ文書

### 1. api_priority_matrix.md
**アーカイブ日**: 2025-10-08
**作成日**: 不明
**内容**: API優先順位マトリックス（Alpha Vantage、CoinGecko評価含む）

**廃止API言及**:
- Alpha Vantage: 4箇所
- CoinGecko: 22箇所

**現在のAPI戦略**: [../current_strategy.md](../current_strategy.md) - FRED優先 + Twelve Data補完

**参照目的**:
- 将来的にFRED外の銘柄を追加する場合の評価参考
- 過去のAPI選定プロセスの記録
- Alpha Vantage、CoinGeckoの特性理解

---

### 2. api_integration_guide.md
**アーカイブ日**: 2025-10-08
**作成日**: 不明
**内容**: API統合ガイド（FRED、Alpha Vantage、CoinGecko）

**廃止API言及**:
- Alpha Vantage: 9箇所
- CoinGecko: 23箇所

**現在の統合ガイド**: [../current_strategy.md](../current_strategy.md) - FRED + Twelve Data統合戦略

**参照目的**:
- Alpha Vantage、CoinGeckoの実装詳細（将来再検討時）
- 過去の統合アーキテクチャの記録
- フォールバック戦略の参考

---

## 🔍 参照タイミング

これらのアーカイブ文書は以下の場合に参照されます：

1. **FRED外銘柄の追加**: 仮想通貨・個別株式をTwelve Data以外で取得する検討時
2. **API障害時**: Twelve Dataに問題が発生し、代替API検討時
3. **コスト最適化**: 無料APIでの実装可能性検討時
4. **過去の意思決定**: なぜAlpha Vantage/CoinGeckoを不採用にしたかの確認時

---

## ✅ 現在のAPI戦略（2025年10月時点）

### 採用API
```
FRED (Federal Reserve Economic Data)
├── 経済指標: 14銘柄
├── 米国株式指数: 10銘柄
└── 特徴: 無制限・無料・最高品質

Twelve Data
├── 仮想通貨: 36銘柄
├── 個別株式: 20銘柄
└── 特徴: FRED補完・800req/日
```

### 不採用API（アーカイブ対象）
```
Alpha Vantage
└── 理由: レート制限厳しい（500req/日）、データ品質FRED劣る

CoinGecko
└── 理由: 仮想通貨特化、Twelve Dataで代替可能
```

---

## 📋 関連ドキュメント

### 現行戦略
- [docs/api_strategy/current_strategy.md](../current_strategy.md) - FRED優先 + Twelve Data補完
- [docs/api_strategy/evaluation_history.md](../evaluation_history.md) - API評価履歴

### 実装
- `infrastructure/data_sources/fred_data_client.py` - FREDクライアント
- `infrastructure/data_sources/twelvedata_client.py` - Twelve Dataクライアント
- `infrastructure/data_sources/unified_data_client.py` - 統合クライアント
- `infrastructure/data_sources/market_data_catalog.json` - 80銘柄カタログ

---

**管理**: [docs/api_strategy/](../../) - API戦略ドキュメント索引
**最終更新**: 2025-10-08
