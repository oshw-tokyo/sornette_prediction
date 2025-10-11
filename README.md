# Sornette Model Market Analysis

金融市場における対数周期的な振る舞いを分析し、潜在的な市場の臨界点を予測するツール。Didier Sornette の研究に基づく実装。

## 🚀 プロジェクト概要

**目的**: Sornette対数周期パワー法則（LPPL）モデルを用いて金融市場のクラッシュを事前に予測し、実際の取引で収益を上げるシステムの構築

**現在のステータス**: 実装改善フェーズ（論文再現性の確立）

## 📊 進捗管理とClaude Codeとの協働

このプロジェクトは生成AI（Claude Code）との協働を前提として設計されています。

### 進捗・Issue管理
- **[現在の進捗状況](./docs/progress_management/CURRENT_PROGRESS.md)** - タスクの進行状況を確認
- **[アクティブなIssue](./docs/progress_management/CURRENT_ISSUES.md)** - 現在の問題と対策状況
- **[管理システムガイド](./docs/progress_management/README.md)** - 進捗管理の仕組み

### 技術ドキュメント
- **[数学的基礎](./docs/mathematical_foundation.md)** - LPPLモデルの理論と数式（論文参照指示あり）
- **[実装戦略](./docs/implementation_strategy.md)** - システム設計と開発方針
- **[論文アーカイブ（テキスト版）](./papers/extracted_texts/)** - 実装の科学的根拠となる原論文（テキスト変換済み）
- **⚠️ 重要**: PDFファイルは`Context low`エラーを避けるため、必ずテキスト版を参照してください

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

### 2. 銘柄リストの準備
```bash
python src/get_market_symbols.py
```

### 3. 分析実行
```bash
# 基本的な市場分析
python src/analysis/market_analysis.py

# 過去のクラッシュ検証
python -m src.reproducibility_validation.crash_1987_validator
```

## 📁 プロジェクト構造

```
sornette_prediction/
├── README.md                          # このファイル
├── docs/                              # ドキュメント
│   ├── progress_management/           # 進捗・Issue管理システム
│   ├── mathematical_foundation.md     # 数学的基礎（論文再現結果含む）
│   └── implementation_strategy.md     # 実装戦略
├── src/                               # ソースコード
│   ├── fitting/                       # LPPLフィッティング
│   ├── analysis/                      # 市場分析
│   ├── reproducibility_validation/    # 論文再現性検証
│   └── visualization/                 # 可視化
├── tests/                             # テストコード
│   └── reproducibility/               # 再現性テスト
├── tools/                             # プロジェクトツール
│   ├── pdf_converter.py               # PDF変換ツール
│   └── validation/                    # 検証・デバッグツール
├── plots/                             # 生成された図表
│   └── validation/                    # 検証結果の図表
└── papers/                            # 論文アーカイブ
    ├── extracted_texts/               # テキスト変換済み論文（作業用）
    └── pdf_archive/                   # 元PDFファイル（直接読み込み禁止）
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
