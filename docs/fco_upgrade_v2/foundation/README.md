# Foundation - FCO共通基盤文書

このディレクトリには、カスタムFCOとBoulder LPPLS FCOの両方に適用される共通基盤文書が含まれています。

---

## 📌 **カスタムFCO移行計画（最優先）**

### MIGRATION_PLAN_CUSTOM_FCO.md

**目的**: Boulder LPPLS FCO（0% Confidence問題）から、過去LPPL実装ベースのカスタムFCOへの移行計画

**状態**: ✅ 計画策定完了 → Phase 1実装開始準備

**実装フェーズ**:
- Phase 1: 過去実装復元・単一窓検証（2-3日）
- Phase 2: 多重窓解析統合（1週間、126窓）
- Phase 3: DB/フロントエンド統合（2-3日）
- Phase 4: 最終検証・最適化（3-5日）

**成功基準**:
- Phase 1: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし
- Phase 2: Confidence > 30%, positive_bubble, 精度達成率測定

**関連文書**:
- テスト仕様: `workspace_for_claude/CUSTOM_FCO_REPRODUCIBILITY_TEST_PLAN.md`
- 科学的根拠: `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md`
- 調査結果: `workspace_for_claude/CORRECTED_FINDING_actual_results.md`

---

## 📚 **技術仕様文書**

### DS-LPPLS指標仕様

**ds_lppls_indicators_detailed_specification.md** (435行)
- DS-LPPLS Confidence定義
- DS-LPPLS Trust指標
- フィルタリング条件（Damping, Oscillation等）
- バブルタイプ判定（positive_bubble/no_bubble）

### 技術実装計画

**technical_implementation_plan.md** (710行)
- FCO完全実装計画（Phase 1-3）
- Boulder LPPLS統合戦略
- パフォーマンス最適化手法
- エラーハンドリング戦略

### 複数窓分析説明

**multi_window_fitting_explanation.md** (202行)
- 時間窓の生成（750→125日、5日刻み、126窓）
- 各窓での独立フィッティング
- 適格フィット判定基準
- Confidence計算方法

---

## 🔍 **分析・戦略文書**

### Boulder LPPLS統合分析

**boulder_integration_analysis.md** (138行)
- Boulder LPPLSライブラリの評価
- 統合時の技術的課題
- 互換性確保の戦略

### 実装戦略推奨

**implementation_strategy_recommendation.md** (336行)
- 段階的実装アプローチ
- リスク管理戦略
- テスト駆動開発方針

### リポジトリ管理助言

**repository_management_advice.md** (265行)
- コードベース整理方針
- ドキュメント管理戦略
- バージョン管理ベストプラクティス

### 論文再現テスト戦略

**paper_reproduction_test_strategy.md** (154行)
- 1987年ブラックマンデー検証戦略
- 2000年ドットコムバブル検証戦略
- 2008年リーマンショック検証戦略

---

## 🚀 **全126窓データ保存戦略**

### 全窓実装ロードマップ

**full_window_implementation_roadmap.md** (994行)
- 6週間実装計画
- Phase 1-6詳細スケジュール
- データベーススキーマ設計
- API仕様拡張

### 全窓保存戦略詳細

**full_window_storage_strategy.md** (606行)
- SQLiteストレージ設計
- データ圧縮・最適化戦略
- クエリパフォーマンス最適化
- 将来的なPostgreSQL移行計画

---

## 📂 **ディレクトリ構成**

```
foundation/
├── README.md (このファイル)
├── MIGRATION_PLAN_CUSTOM_FCO.md  ← 📌 最優先参照（カスタムFCO移行計画）
├── ds_lppls_indicators_detailed_specification.md
├── technical_implementation_plan.md
├── multi_window_fitting_explanation.md
├── boulder_integration_analysis.md
├── implementation_strategy_recommendation.md
├── repository_management_advice.md
├── paper_reproduction_test_strategy.md
├── full_window_implementation_roadmap.md
└── full_window_storage_strategy.md
```

---

## 🔗 **関連ディレクトリ**

- **v2.1_webapp/**: React + FastAPI Webアプリケーション層（Boulder LPPLS FCO使用中）
- **data_engine/**: fco-daily CLIツール層（Boulder LPPLS FCO使用中）
- **archives/**: 完了済み・非推奨文書のアーカイブ

---

## ⚠️ **実装時の注意**

1. **カスタムFCO移行中**: 現在Phase 1実装開始準備中
2. **v2.1とData Engineは自動切替**: Phase 3完了後、`fco_engine.py`置き換えで自動的にカスタムFCO使用
3. **インターフェース互換性**: APIエンドポイント・CLIコマンド変更なし
4. **文書更新**: カスタムFCO実装完了後、v2.1/data_engine文書の実装部分を更新

---

*管理者: プロジェクトオーナー + Claude Code*
*最終更新: 2025-10-11*
