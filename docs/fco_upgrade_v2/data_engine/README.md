# FCO Data Engine (fco-daily CLI System)

**実装状況**: ✅ 完了・稼働中
**レイヤー**: データ管理・分析エンジン層
**技術**: Pythonコマンドラインツール

---

## 🎯 このディレクトリについて

このディレクトリには、**FCO Data Engine（fco-dailyシステム）** のアーキテクチャ文書が含まれています。

> ⚠️ **重要**: このシステムは **Webアプリケーション層（v2.1）とは異なるコンポーネント** です。
> 両者は並行稼働しており、異なるバージョン体系を持っています。

---

## 📊 システム概要

### Data Engine (v3) とは？

FCO Data Engineは、全履歴市場データの管理と自動分析を行うCLIツールです。

**主要機能**:
- **全履歴データキャッシュ**: Parquet形式で最大40年分のデータを保存
- **スマート更新システム**: 市場休業日を自動判定して差分更新
- **FCO/LPPL分離**: FCO（全履歴）とLPPL（2年）のデータを分離管理
- **自動リトライ**: 最大3回の指数バックオフリトライ
- **日次分析スケジューラー**: cronジョブで自動実行可能

---

## 🏗️ アーキテクチャ

```
[Market Data Sources (FRED/Twelve Data)]
        ↓
[MarketDataDownloader] (for_fco=True)
        ↓
data/market_data/cache/full/*.parquet (全履歴40年)
        ↓
[FCODailyAnalyzer]
        ↓
├─ FCOEngine (126窓分析)
└─ results/fco_analysis_results.db (分析結果保存)
```

**特徴**:
- **高速アクセス**: Parquetキャッシュで2.1msの読み込み速度
- **完全分離**: FCO用とLPPL用のデータを完全分離
- **スケーラビリティ**: 81銘柄で約40MBのストレージ

---

## 🚀 使用方法

### 基本コマンド

```bash
# FCO日次分析（自動更新付き）
python entry_points/main.py fco-daily run

# データ更新のみ
python entry_points/main.py fco-daily update

# 失敗した更新の再試行
python entry_points/main.py fco-daily retry

# データ鮮度確認
python entry_points/main.py fco-daily check

# システム状態確認
python entry_points/main.py fco-daily status
```

### オプション

```bash
# 更新をスキップして分析のみ
python entry_points/main.py fco-daily run --skip-update

# 特定銘柄のみ処理
python entry_points/main.py fco-daily run --symbols SP500 BTC
```

---

## 📁 このディレクトリの文書

| 文書名 | 行数 | 内容 |
|-------|-----|------|
| **usage_guide.md** | 234行 | fco-dailyコマンド詳細使用ガイド ⭐ START HERE |
| **fco_v3_complete_architecture.md** | 176行 | v3システムの完全仕様・使用方法 |
| **fco_full_history_architecture.md** | 128行 | FCO/LPPL分離設計原則 |
| **full_historical_data_operation_guide.md** | 235行 | 全履歴データ運用ガイド |
| **architecture_migration_local_data_storage.md** | 193行 | ローカルストレージ移行戦略 |
| **local_db_optimization_implementation.md** | 244行 | ローカルDB最適化手法 |

---

## 🔗 v2.1 Webアプリケーションとの関係

### 現在の統合状況

**✅ 統合されている部分**:
- 共通の分析エンジン: `core/fitting/fco_engine.py`
- 共通のデータベース: `results/fco_analysis_results.db`（分析結果）
- 統一エントリーポイント: `entry_points/main.py`

**🔄 統合が必要な部分**:
- **データソース**: v3のParquetキャッシュをv2.1が利用していない
- **価格データ管理**: v2.1はSQLite、v3はParquetを使用

### 将来の統合計画

v2.1のPriceDataServiceを拡張して、v3のParquetキャッシュを優先的に使用する予定です。

**メリット**:
- 高速アクセス（2.1ms）
- 全履歴データへの即座のアクセス
- データ更新の自動化

---

## 📝 実装ファイル

### 主要ファイル
- `applications/analysis_tools/fco_daily_scheduler_v3.py` - スケジューラー
- `applications/analysis_tools/fco_daily_analyzer.py` - 分析器
- `infrastructure/market_data/data_downloader.py` - データダウンローダー
- `infrastructure/market_data/smart_data_updater.py` - スマート更新エンジン

### データ保存先
- キャッシュ: `data/market_data/cache/full/*.parquet`
- 分析結果: `results/fco_analysis_results.db`
- 状態管理: `results/fco_scheduler_state.json`

---

## 📚 関連文書

### プロジェクト全体
- **親ディレクトリREADME**: `../README.md` - FCO v2.1/v3の関係全体像
- **v2.1 Webアプリ**: `../v2.1_webapp/` - React+FastAPIシステム

### 実装ガイド
- **CLAUDE.md**: プロジェクトルート - AI向け統合ガイド
- **entry_points/main.py**: Line 775-901 - fco-dailyコマンド実装

---

## ✅ 実装完了機能

- [x] 全履歴キャッシュシステム（Parquet）
- [x] FCO/LPPL完全分離
- [x] スマート更新（市場休業日対応）
- [x] 差分更新の最適化
- [x] リトライ機能（指数バックオフ）
- [x] 時差対応（米国市場）
- [x] データ鮮度管理
- [x] 126ウィンドウ分析（FCO標準）
- [x] entry_points/main.py統合

---

**管理者**: プロジェクトオーナー + Claude Code
**最終更新**: 2025-10-09
**ステータス**: 実装完了・稼働中
