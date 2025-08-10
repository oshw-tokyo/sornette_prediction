# Sornette Model Market Analysis

金融市場における対数周期的な振る舞いを分析し、潜在的な市場の臨界点を予測するツール。Didier Sornette の研究に基づく実装。

## 🚨 **重要: 論文再現の絶対保護**

**⚠️ このシステムの科学的根幹は論文再現機能です**

### 開発・変更時の必須ルール
```bash
# 変更前・後で必ず実行（統一エントリーポイント経由）
python entry_points/main.py validate --crash 1987
# 期待結果: 予測可能性スコア 100/100
```

**科学的検証が破損した場合は即座に変更を巻き戻してください。**

## 🚀 プロジェクト概要

**目的**: Sornette対数周期パワー法則（LPPL）モデルを用いて金融市場のクラッシュを事前に予測し、実際の取引で収益を上げるシステムの構築

**現在のステータス**: バックフィルバッチ実行中（78銘柄・2.6年間のLPPL分析データ蓄積）

## 📊 進捗管理とClaude Codeとの協働

このプロジェクトは生成AI（Claude Code）との協働を前提として設計されています。

### 🎯 中核ドキュメント（必須参照）
- **[Claude Code指示書](./CLAUDE.md)** - AIが最初に読むべきファイル
- **[現在の進捗状況](./docs/progress_management/CURRENT_PROGRESS.md)** - タスクの進行状況
- **[アクティブなIssue](./docs/progress_management/CURRENT_ISSUES.md)** - 現在の問題と対策（Issue I044: ドキュメント整合性）
- **[数学的基礎](./docs/mathematical_foundation.md)** - LPPLモデルの理論と数式

### 📁 プロジェクト構造（2025-08-02更新）
```
sornette_prediction/
├── CLAUDE.md                     # AI用指示書（中核ファイル参照）
├── README.md                     # このファイル
├── USER_EXECUTION_GUIDE.md       # ユーザー実行ガイド
│
├── docs/                         # ドキュメント（統合済み）
│   ├── progress_management/      # 🎯 中央管理システム
│   ├── mathematical_foundation.md # 🎯 数学的基礎
│   ├── implementation_strategy.md # 🎯 実装戦略
│   ├── api_guides/               # API戦略（統合済み）
│   ├── analysis/                 # 分析結果（統合済み）
│   └── validation_results/       # 検証結果
│
├── core/                          # 科学的中核（保護対象）
│   ├── fitting/                  # LPPLフィッティング（論文再現）
│   ├── sornette_theory/          # 理論実装
│   └── validation/               # 歴史的検証（100/100スコア保護）
│
├── applications/                 # アプリケーション層
│   ├── analysis_tools/           # 分析ツール（crash_alert_system等）
│   ├── dashboards/               # Webダッシュボード
│   └── examples/                 # 実行例・デモ
│
├── infrastructure/               # インフラ層
│   ├── data_sources/             # データ取得（78銘柄カタログ）
│   ├── database/                 # SQLite結果管理
│   └── visualization/            # 可視化ツール
│
├── entry_points/                 # 統一エントリーポイント
│   └── main.py                   # 中央コマンドインターフェース
│
├── tests/                        # テストコード
├── results/                      # 実行結果
└── papers/                       # 参照論文（テキスト版）
```

### 技術ドキュメント
- **[実装戦略](./docs/implementation_strategy.md)** - システム設計と開発方針
- **[API統合ガイド](./docs/api_guides/)** - データソース戦略
- **[論文アーカイブ（テキスト版）](./papers/extracted_texts/)** - 実装の科学的根拠
- **⚠️ 重要**: PDFファイルは`Context low`エラーを避けるため、必ずテキスト版を参照

## 🎯 現在の最優先課題

**β値の再現性問題**: 論文（[Sornette_2004](./papers/extracted_texts/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt) 式54）では0.33であるべきβ値が0.36程度になっており、グローバル最適化手法の導入により改善を図っています。

詳細は[CURRENT_ISSUES.md](./docs/progress_management/CURRENT_ISSUES.md)を参照してください。

## 💻 主な機能

- 株価の対数周期性分析（LPPL fitting）
- 複数時間枠での分析（180日/365日/730日）
- フィッティング品質の評価と統計的検証
- 予測の安定性分析
- 臨界点の予測と警告レベルの判定
- 過去のクラッシュ事例での検証（1987年ブラックマンデー等）

## 🔧 使用方法

### 1. 環境設定
```bash
pip install -r requirements.txt
```

### 2. 分析実行

**全ての実行は統一エントリーポイント（`entry_points/main.py`）から行います**：

```bash
# カタログ全銘柄の包括解析（推奨）
python entry_points/main.py analyze ALL

# 個別銘柄の分析
python entry_points/main.py analyze NASDAQCOM --period 2y

# 過去のクラッシュ検証
python entry_points/main.py validate --crash 1987

# ダッシュボード起動
python entry_points/main.py dashboard --type main
```

## 📁 プロジェクト構造（4層アーキテクチャ）

```
sornette_prediction/
├── README.md                          # このファイル
├── CLAUDE.md                          # AI開発者向け指示書（重要）
├── USER_EXECUTION_GUIDE.md            # ユーザー実行ガイド
│
├── entry_points/                      # 統一エントリーポイント
│   └── main.py                        # 全機能への中央インターフェース
│
├── core/                              # 科学的中核（保護対象）
│   ├── fitting/                       # LPPLフィッティングアルゴリズム
│   ├── sornette_theory/               # 理論実装
│   └── validation/                    # 歴史的検証（100/100スコア保護）
│
├── applications/                      # アプリケーション層
│   ├── analysis_tools/                # 分析ツール（crash_alert_system等）
│   ├── dashboards/                    # Webダッシュボード
│   └── examples/                      # 実行例・デモ
│
├── infrastructure/                    # インフラ層
│   ├── data_sources/                  # データ取得（FRED/Alpha Vantage）
│   ├── database/                      # SQLite結果管理
│   └── visualization/                 # 可視化ツール
│
├── tests/                             # テストコード
│   └── historical_crashes/            # 歴史的クラッシュ検証
│
├── docs/                              # ドキュメント
│   ├── progress_management/           # 進捗・Issue管理システム
│   ├── mathematical_foundation.md     # 数学的基礎（論文再現結果含む）
│   └── implementation_strategy.md     # 実装戦略
│
├── results/                           # 分析結果
│   └── analysis_results.db            # SQLiteデータベース
│
└── papers/                            # 論文アーカイブ
    ├── extracted_texts/               # テキスト変換済み論文
    └── pdf_archive/                   # 元PDFファイル
```

## 🗂️ ファイル整理方針

### 新しいファイルの配置ルール
1. **検証・テストスクリプト**: `tests/reproducibility/` または `tools/validation/`
2. **生成された図表**: `plots/validation/`（検証用）、`plots/analysis/`（分析用）
3. **一時的なデバッグファイル**: `_temp/`（定期的にクリーンアップ）
4. **ツール・ユーティリティ**: `tools/`

### 出力ファイル管理
- **プロット**: 種類別にサブディレクトリで管理
- **ログファイル**: `analysis_results/logs/`
- **検証結果**: `analysis_results/validation/`

## 🛠️ 技術要件

- Python 3.8+
- 主要ライブラリ: numpy, scipy, pandas, yfinance, matplotlib, scikit-learn

## 🤝 開発への参加

このプロジェクトはClaude Codeとの協働開発を想定しています。コントリビューションの際は：

1. [進捗管理システム](./docs/progress_management/)を確認
2. 関連するIssueを確認または作成
3. **科学的根拠の確認**: [papers/extracted_texts/](./papers/extracted_texts/)内の関連論文（テキスト版）を必ず参照
4. 実装前に設計を文書化
5. **論文との数値照合**: 実装結果と論文報告値を定量比較
6. テストを含めて実装

### 重要な論文参照原則
- 実装前に関連論文をReadツールで確認
- 数式の完全一致を確認
- パラメータの定量的検証を実施
- 乖離がある場合はIssueとして管理

## 📝 ライセンス

[プロジェクトライセンスを記載]

---

*最終更新: 2025-08-01*
