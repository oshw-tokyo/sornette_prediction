# FCO Level Upgrade v2.0 ドキュメント

このディレクトリには、ETH Zurich FCO (Financial Crisis Observatory) レベルへのアップグレードに関する技術仕様と実装計画が含まれています。

## 📁 ドキュメント構成

### 1. **ds_lppls_indicators_detailed_specification.md**
- DS-LPPLS Confidence/Trust指標の詳細仕様
- 正確な計算式（126時間窓での成功率）
- フィルタリング条件（Damping ≥ 1.0等）
- 実装可能なPythonコードサンプル
- Boulder Investment Technologies実装への参照

### 2. **technical_implementation_plan.md**
- FCOレベル機能の完全な技術実装計画
- MultiWindowLPPLAnalyzer実装例
- DS-LPPLS指標の段階的実装
- 日本市場向けカスタマイズ
- パフォーマンス最適化戦略

### 3. **implementation_strategy_recommendation.md**
- Boulder lpplsライブラリ活用戦略
- ハイブリッドアプローチの推奨
- 現在の実装との統合方法
- リスク管理と移行計画
- 日本市場向け最適化

### 4. **repository_management_advice.md**
- リポジトリ管理戦略の推奨事項
- ブランチ戦略 vs 新規リポジトリの比較
- 段階的移行計画
- バージョニング戦略
- Boulder Investment Technologiesの成功事例

## 🎯 実装の優先順位

### Phase 1: 基礎実装（1-2週間）
- DS-LPPLS Confidence基本実装
- 126時間窓の生成
- 基本的なフィルタリング条件

### Phase 2: 統合実装（3-4週間）
- Boulder lpplsとのハイブリッド実装
- CMA-ES最適化の導入
- 並列処理の実装

### Phase 3: 高度な機能（1-2ヶ月）
- DS-LPPLS Trust指標
- ブートストラップ法
- 日本市場向け最適化

## 📊 主要な技術的差分

| 機能 | 現在の実装 (v1.5) | FCOレベル (v2.0) |
|------|------------------|-----------------|
| 時間窓数 | 1（固定365日） | 126（125-750日） |
| 信頼性指標 | R²のみ | DS-LPPLS Confidence/Trust |
| 最適化手法 | scipy.curve_fit | CMA-ES + Quantile Regression |
| スケール分類 | なし | 短期/中期/長期 |
| 並列処理 | なし | マルチスレッド対応 |

## 🔗 関連リソース

- **Boulder Investment Technologies LPPLS**: https://github.com/Boulder-Investment-Technologies/lppls
- **ETH Zurich FCO**: https://emeritus.er.ethz.ch/financial-crisis-observatory.html
- **主要論文**: Sornette & Johansen (2010), Demos & Sornette (2019)

## 📝 更新履歴

- 2025-09-02: 初版作成、workspace_for_claudeから移動
- FCOレベルアップグレード計画の正式文書化

---

*管理者: プロジェクトオーナー + Claude Code*