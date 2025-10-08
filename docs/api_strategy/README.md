# API戦略ドキュメント

**最終更新**: 2025-10-08
**管理**: プロジェクトオーナー + Claude Code

---

## 📚 ドキュメント構成

### 現在適用中の戦略

#### 1. [current_strategy.md](current_strategy.md)
**FRED優先 + Twelve Data補完戦略**
- 現在適用中のAPI戦略の詳細
- データソース優先順位
- 銘柄配分（FRED 24銘柄 + Twelve Data 56銘柄）
- API制限管理・運用ガイド

**最終更新**: 2025-10-08

### API評価フレームワーク

#### 2. [evaluation_framework.md](evaluation_framework.md)
**新API追加時の評価基準**
- API割り当て戦略ガイド
- 100点満点の評価システム（信頼性40点、アクセス性30点、専門性20点、統合性10点）
- 専門分野マッチング・負荷分散の考慮
- 新規APIプロバイダー追加時の決定アルゴリズム

**作成日**: 2025-08-09
**配置変更**: 2025-10-09 (docs/ 直下から移動)

### 過去の試行・評価記録

#### 3. [evaluation_history.md](evaluation_history.md)
**API評価・試行の履歴**
- 各種データソースAPI の実装試行結果
- 問題点の記録・ナレッジ蓄積
- API評価サマリー（Twelve Data, FRED, Binance, CoinGecko, Alpha Vantage, Finnhub）
- 実装上の課題と解決策

**作成日**: 2025-08-10

---

## 🗂️ アーカイブ文書

以下の文書は現在の戦略確定により、参考資料として [archives/deprecated_api_strategies/](archives/deprecated_api_strategies/) に移動しました：

### 廃止された代替案・検討文書

1. **api_alternatives_analysis.md** (2025-08-08)
   - API代替候補の分析報告
   - → 結論: FRED優先戦略確定により不要

2. **alternative_api_implementation_plan.md** (2025-08-10)
   - 代替API実装計画
   - → 実施せず、FRED優先戦略を採用

3. **catalog_api_migration_plan.md** (2025-08-10)
   - カタログAPI移行計画
   - → 移行完了、参考資料化

4. **stable_version_strategy.md** (2025-08-10)
   - 安定版戦略v1
   - → v2（current_strategy.md）に更新

5. **twelve_data_coverage_analysis.md** (2025-08-10)
   - Twelve Data カバレッジ分析
   - → current_strategy.mdに統合

---

## 🎯 現在の戦略概要

### データソース優先順位

1. **FRED（最優先）**:
   - 政府公式データ
   - API制限なし
   - 最高品質・信頼性

2. **Twelve Data（補完）**:
   - FREDにない銘柄（仮想通貨、個別株式）
   - レート制限管理必要（800 req/日）

### 銘柄配分

| データソース | 銘柄数 | 内訳 |
|------------|--------|------|
| **FRED** | 24銘柄 | 経済指標14 + 米国株式指数10 |
| **Twelve Data** | 56銘柄 | 仮想通貨36 + 個別株式20 |
| **合計** | 80銘柄 | - |

**失敗銘柄の修正状況**:
- NASDAQFIN: カタログから削除予定（FREDシリーズ不存在）
- GOLDAMGBD228NLBM: シンボル名確認・修正必要
- MATIC: POL/USD に更新（2024年9月ティッカー変更）
- EOS: カタログから削除予定（Twelve Data サポート終了）

詳細: [workspace_for_claude/failed_symbols_analysis.md](../../workspace_for_claude/failed_symbols_analysis.md)

---

## 📖 関連ドキュメント

### API実装・運用

- [evaluation_framework.md](evaluation_framework.md) - API評価フレームワーク（本ディレクトリ内）

### データソース管理

- [infrastructure/data_sources/market_data_catalog.json](../../infrastructure/data_sources/market_data_catalog.json) - 80銘柄カタログ定義
- [infrastructure/data_sources/unified_data_client.py](../../infrastructure/data_sources/unified_data_client.py) - FRED + Twelve Data統合クライアント
- [infrastructure/data_sources/api_rate_limiter.py](../../infrastructure/data_sources/api_rate_limiter.py) - API制限管理

---

## 🔄 更新履歴

### 2025-10-09
- api_assignment_strategy.md を evaluation_framework.md としてディレクトリ内に統合
- ドキュメント構成整理（docs/ 直下からの移動完了）

### 2025-10-08
- ドキュメント統合（7ファイル → 3ファイル）
- current_strategy.md, evaluation_history.md にリネーム・更新
- アーカイブ構造の整理

### 2025-08-10
- FRED優先戦略確定（stable_version_strategy_v2.md）
- API評価ナレッジベース作成（api_evaluation_knowledge_base.md）
- Twelve Data カバレッジ分析完了

### 2025-08-08
- API代替候補分析完了
- CoinGecko制限、Alpha Vantage制限確認

---

**参照**: [docs/README.md](../README.md) - プロジェクト全体ドキュメント索引
**管理**: [docs/progress_management/](../progress_management/) - 進捗管理システム
