# FCO Level Upgrade v2.0 ドキュメント

このディレクトリには、ETH Zurich FCO (Financial Crisis Observatory) レベルへのアップグレードに関する技術仕様と実装計画が含まれています。

## 📁 ドキュメント構成

### 実装計画・分析 ⭐ NEW
1. **fco_implementation_gap_analysis.md** 
   - FCO実装ギャップ分析と実装要件
   - 必須実装機能のチェックリスト
   - 移行戦略と後方互換性
   - 技術的課題と対策

2. **boulder_integration_analysis.md**
   - Boulder lpplsコード分析結果
   - FCOとBoulderの関係性明確化
   - LPPLS数式の互換性確認
   - 統合の容易性評価

### 技術仕様
3. **ds_lppls_indicators_detailed_specification.md**
   - DS-LPPLS Confidence/Trust指標の詳細仕様
   - 正確な計算式（126時間窓での成功率）
   - フィルタリング条件（Damping ≥ 1.0等）

4. **technical_implementation_plan.md**
   - FCOレベル機能の完全な技術実装計画
   - MultiWindowLPPLAnalyzer実装例
   - DS-LPPLS指標の段階的実装

5. **comparison_fco_vs_current_implementation.md**
   - FCO方式と現在の実装の詳細比較
   - 統合型マルチウィンドウ vs 時系列蓄積型の違い
   - 統計的信頼性と情報の質の比較

6. **multi_window_fitting_explanation.md**
   - 複数ウィンドウフィッティングの詳細説明
   - FCO方式（126窓同時分析）の仕組み

### 戦略・管理
7. **implementation_strategy_recommendation.md**
   - Boulder lpplsライブラリ活用戦略
   - ハイブリッドアプローチの推奨
   - 現在の実装との統合方法

8. **repository_management_advice.md**
   - リポジトリ管理戦略の推奨事項
   - ブランチ戦略 vs 新規リポジトリの比較

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