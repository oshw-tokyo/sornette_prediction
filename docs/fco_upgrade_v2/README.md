# FCO Level Upgrade ドキュメント

このディレクトリには、ETH Zurich FCO (Financial Crisis Observatory) レベルへのアップグレードに関する技術仕様と実装計画が含まれています。

---

## 🎯 2つの並行稼働システム

**重要**: このプロジェクトには2つの異なるFCOシステムが存在し、**両者は並行稼働しています**。

| システム | レイヤー | 技術 | 実装状況 | 文書 |
|---------|---------|------|----------|------|
| **FCO v2.1** | Webアプリケーション層 | React + FastAPI | 🔄 Phase 2進行中 | `v2.1_webapp/` |
| **Data Engine (v3)** | データ管理・分析エンジン層 | Python CLIツール | ✅ 実装完了・稼働中 | `data_engine/` |

---

## 📊 FCO v2.1 (Webアプリケーション層)

### 実装状況
- ✅ **Phase 1完了**: FastAPIバックエンド実装済み
- 🔄 **Phase 2進行中**: Reactフロントエンド実装中
- 📋 **Phase 3計画中**: データ可視化コンポーネント
- 📋 **Phase 4計画中**: 認証・デプロイメント

### アーキテクチャ
```
React Frontend (Next.js)
    ↓ HTTPS/REST
FastAPI Backend
    ↓
FCOService → FCOEngine (core/fitting/fco_engine.py)
    ↓
SQLite Database (results/fco_analysis_results.db)
```

### 詳細文書
→ `v2.1_webapp/` ディレクトリを参照

---

## 🚀 Data Engine - fco-daily CLI System (v3)

### 実装状況
✅ **完了・稼働中**

### 主要機能
- **全履歴データキャッシュ**: Parquet形式で最大40年分
- **スマート更新**: 市場休業日自動判定、差分更新
- **FCO/LPPL分離**: FCO（全履歴）とLPPL（2年）を完全分離
- **自動リトライ**: 指数バックオフリトライ機能
- **日次分析スケジューラー**: cronジョブで自動実行可能

### 使用方法
```bash
python entry_points/main.py fco-daily run     # FCO分析実行
python entry_points/main.py fco-daily update  # データ更新のみ
python entry_points/main.py fco-daily check   # データ鮮度確認
```

### 詳細文書
→ `data_engine/` ディレクトリを参照

---

## 🔗 両システムの統合状況

### ✅ 統合されている部分
- 共通の分析エンジン: `core/fitting/fco_engine.py`
- 共通のデータベース: `results/fco_analysis_results.db`（分析結果）
- 統一エントリーポイント: `entry_points/main.py`

### 🔄 統合が必要な部分
- **データソース**: v2.1はSQLite、Data EngineはParquetキャッシュを使用
- **価格データ管理**: 将来的にData EngineのParquetキャッシュに統一予定

---

## 🎯 最新の決定事項（2025-10-09更新）

- **全126窓データ保存**: FRED symbols (23銘柄) で全窓データ保存開始
- **データベース戦略**: SQLite使用、将来的にPostgreSQL移行
- **実装計画**: `foundation/full_window_implementation_roadmap.md`（6週間計画）
- **ディレクトリ再編成**: v2.1とData Engineを明確に分離

## 📁 ドキュメント構成（2025-10-09再編成）

### v2.1_webapp/ - Webアプリケーション層（実装中）
React + FastAPIによるWebダッシュボードの実装文書

- **fco_v2.1_architecture.md** (432行) - v2.1完全アーキテクチャ仕様
- **implementation_plan_v2.1_next_steps.md** (234行) - 次期実装計画
- **frontend_implementation_strategy.md** (143行) - React実装戦略
- **price_data_storage_plan.md** (202行) - 価格データ保存計画
- **plotly_data_format_requirements.md** (91行) - Plotly可視化要件
- **fco_dashboard_integration_guide.md** (197行) - ダッシュボード統合ガイド
- **final_tech_stack_decision.md** (106行) - 技術スタック決定記録

→ 詳細は `v2.1_webapp/` ディレクトリを参照

---

### data_engine/ - データ管理・分析エンジン層（実装完了）
fco-daily CLIツールのアーキテクチャ文書

- **README.md** - Data Engineシステム概要・使用方法 ⭐ START HERE
- **fco_v3_complete_architecture.md** (176行) - v3システム完全仕様
- **fco_full_history_architecture.md** (128行) - FCO/LPPL分離設計原則
- **full_historical_data_operation_guide.md** (235行) - 全履歴データ運用ガイド
- **architecture_migration_local_data_storage.md** (193行) - ローカルストレージ移行戦略
- **local_db_optimization_implementation.md** (244行) - ローカルDB最適化手法
- **daily_analysis_implementation_plan.md** (256行) - 日次分析実装計画

→ 詳細は `data_engine/` ディレクトリを参照

---

### foundation/ - 共通基盤文書（全バージョン共通）
v2.1とData Engineの両方に適用される技術仕様と戦略

**技術仕様**:
- **ds_lppls_indicators_detailed_specification.md** (435行) - DS-LPPLS指標詳細仕様
- **technical_implementation_plan.md** (710行) - FCO技術実装計画
- **multi_window_fitting_explanation.md** (202行) - 複数窓分析説明

**分析・戦略**:
- **fco_implementation_gap_analysis.md** (230行) - FCO実装ギャップ分析
- **boulder_integration_analysis.md** (138行) - Boulder LPPLS統合分析
- **comparison_fco_vs_current_implementation.md** (265行) - FCO比較分析
- **implementation_strategy_recommendation.md** (336行) - 実装戦略推奨
- **repository_management_advice.md** (265行) - リポジトリ管理助言
- **paper_reproduction_test_strategy.md** (154行) - 論文再現テスト戦略

**最新戦略（全126窓データ保存）**:
- **full_window_implementation_roadmap.md** (994行) - 全窓実装ロードマップ（6週間計画）
- **full_window_storage_strategy.md** (606行) - 全窓保存戦略詳細

---

### archives/ - 完了済み・アーカイブ文書
過去の実装報告書と移行計画

- **README.md** - アーカイブ文書一覧と参照方法
- **fco_implementation_summary_report.md** (188行) - FCO v2.0実装総括
- **implementation_progress_phase1.md** (148行) - Phase 1完了報告
- **phase1_html_template_completion.md** (128行) - HTMLテンプレート完了報告
- **database_migration/** - データベース移行戦略3文書（アーカイブ）

→ 詳細は `archives/README.md` を参照

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
- リアルタイム更新機能

## 📂 アーカイブ文書

実装完了済みの報告書は`archives/`ディレクトリに移動されています：
- `fco_implementation_summary_report.md` - FCO v2.0実装総括
- `implementation_progress_phase1.md` - Phase 1完了報告
- `phase1_html_template_completion.md` - HTMLテンプレート実装

詳細は `archives/README.md` を参照してください。

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

- **2025-10-09**: ディレクトリ構造再編成実施 🎯
  - **v2.1/Data Engine分離**: v2.1とData Engine(v3)を明確に分離
  - **4ディレクトリ体系**: `v2.1_webapp/`, `data_engine/`, `foundation/`, `archives/`
  - **文書移動**: 全32文書を適切なカテゴリに再配置
  - **README大幅更新**: v2.1とData Engineの関係を明確化
  - **アーカイブ拡充**: database_migration/を追加（3文書）
- **2025-10-08**: ドキュメント整理・最適化実施
  - 実装完了報告書3件をarchives/に移動
  - 日本市場データ統合セクション削除（未実装計画のため）
  - technical_implementation_plan.md圧縮（1178行→711行、467行削減）
  - 最新決定事項（全窓保存戦略）を反映
- **2025-09-02**: 初版作成、workspace_for_claudeから移動
- FCOレベルアップグレード計画の正式文書化

---

*管理者: プロジェクトオーナー + Claude Code*
*最終更新: 2025-10-09*