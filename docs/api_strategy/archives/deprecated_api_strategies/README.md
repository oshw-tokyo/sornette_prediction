# 廃止されたAPI戦略文書

**アーカイブ日**: 2025-10-08
**理由**: FRED優先 + Twelve Data補完戦略の確定により、代替案検討文書を廃止

---

## 📁 アーカイブ文書

### 1. api_alternatives_analysis.md
- **内容**: API代替候補の分析報告
- **作成日**: 2025-08-08
- **廃止理由**: FRED優先戦略確定により、代替API検討は不要に
- **参照目的**: 過去の評価判断の根拠確認

### 2. alternative_api_implementation_plan.md
- **内容**: 代替API実装計画
- **作成日**: 2025-08-10
- **廃止理由**: 実施せず、FRED優先戦略を採用
- **参照目的**: 検討された代替手法の記録

### 3. catalog_api_migration_plan.md
- **内容**: カタログAPI移行計画
- **作成日**: 2025-08-10
- **廃止理由**: 移行完了、参考資料化
- **参照目的**: 移行時の設計判断・実施手順の記録

### 4. stable_version_strategy.md
- **内容**: 安定版戦略v1
- **作成日**: 2025-08-10
- **廃止理由**: v2（current_strategy.md）に更新
- **参照目的**: 戦略進化の過程確認

### 5. twelve_data_coverage_analysis.md
- **内容**: Twelve Data カバレッジ分析
- **作成日**: 2025-08-10
- **廃止理由**: current_strategy.mdに統合
- **参照目的**: Twelve Data選定の詳細根拠

---

## 🔄 現在のAPI戦略

アーカイブされた文書の検討結果を踏まえ、以下の戦略が確定しました：

### 現在適用中のドキュメント

**[docs/api_strategy/current_strategy.md](../../current_strategy.md)**
- FRED優先 + Twelve Data補完戦略
- データソース優先順位
- 銘柄配分（FRED 24銘柄 + Twelve Data 56銘柄）
- API制限管理・運用ガイド

**[docs/api_strategy/evaluation_history.md](../../evaluation_history.md)**
- 各種データソースAPI の実装試行結果
- 問題点の記録・ナレッジ蓄積
- API評価サマリー

---

## 📚 参照ガイド

### アーカイブ文書を参照すべき場合

1. **過去の検討経緯の確認**
   - なぜFREDが最優先になったか（api_alternatives_analysis.md）
   - 代替案として何が検討されたか（alternative_api_implementation_plan.md）

2. **移行時の設計判断の理解**
   - カタログ移行の実施手順（catalog_api_migration_plan.md）
   - 戦略の進化過程（stable_version_strategy.md → v2）

3. **Twelve Data選定根拠の詳細**
   - カバレッジ分析の詳細（twelve_data_coverage_analysis.md）
   - 銘柄選定の基準

### 参照方法

```markdown
<!-- 他の文書からの参照例 -->
FRED優先戦略の選定根拠については、以下のアーカイブ文書を参照:
- [API代替候補分析](../api_strategy/archives/deprecated_api_strategies/api_alternatives_analysis.md)
- [Twelve Dataカバレッジ分析](../api_strategy/archives/deprecated_api_strategies/twelve_data_coverage_analysis.md)
```

---

## ⚠️ 注意事項

1. **戦略は確定済み**: これらの代替案は実施されていません
2. **参考目的のみ**: 設計判断の理解・歴史的経緯の確認用です
3. **将来削除予定**: 参照価値がなくなった時点で完全削除される可能性があります

---

**管理**: [docs/api_strategy/README.md](../../README.md)
**関連アーカイブ**: [docs/progress_management/archives/](../../../progress_management/archives/)
**最終更新**: 2025-10-08
