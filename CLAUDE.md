# Claude Code Instructions - 中核ファイル優先参照指示

## 🎯 このファイルの目的

このファイルは、Claude Code（AI）がプロジェクトを理解する際に最初に参照すべき中核ファイルを明示するものです。

## 📋 必須参照ファイル（優先順位順）

### 1. 進捗管理システム（最優先）
```
docs/progress_management/
├── README.md              # システム概要・運用ルール
├── CURRENT_PROGRESS.md    # 現在の進捗状況
└── CURRENT_ISSUES.md      # アクティブな課題
```
**重要**: タスク開始時は必ずこれらのファイルで現状を確認すること。

### 2. 数学的基礎
```
docs/mathematical_foundation.md
```
**重要**: 実装時は必ず数式と論文を確認すること。

### 3. 実装戦略
```
docs/implementation_strategy.md
```
**重要**: 新機能追加時は全体戦略との整合性を確認すること。

## 🚫 参照を避けるべきファイル

以下は統合・削除対象のため参照しないこと：
- `docs/implementation/Current_System_Architecture.md`
- `docs/implementation/Data_Sources_Analysis.md`
- `docs/implementation/Code_Cleanup_Analysis.md`
- `docs/Data_Acquisition_Strategy.md`

## 📁 プロジェクト構造（2025-08-02更新）

```
sornette_prediction/
├── CLAUDE.md                     # このファイル（AI指示）
├── README.md                     # プロジェクト概要
├── USER_EXECUTION_GUIDE.md       # ユーザー実行ガイド
│
├── docs/                         # ドキュメント（中核3ディレクトリ）
│   ├── progress_management/      # 🎯 中央管理システム
│   ├── mathematical_foundation.md # 🎯 数学的基礎
│   ├── implementation_strategy.md # 🎯 実装戦略
│   ├── api_guides/               # API統合ガイド
│   ├── analysis/                 # パラメータ分析
│   └── validation_results/       # 検証結果
│
├── src/                          # ソースコード
│   ├── main.py                   # メインエントリポイント
│   ├── fitting/                  # LPPLフィッティング
│   ├── data_sources/             # データ取得
│   ├── visualization/            # 可視化
│   └── analysis/                 # 分析モジュール
│
├── tests/                        # テストコード
├── results/                      # 実行結果
└── papers/                       # 参照論文
```

## 🔄 更新ルール

1. **新規ドキュメント作成前**: 既存の中核ファイルで対応可能か確認
2. **タスク開始時**: 必ず進捗管理システムを参照
3. **実装時**: 数学的基礎との整合性を確認
4. **完了時**: 進捗管理システムを更新

## ⚠️ 重要な注意事項

1. **ドキュメント重複を避ける**: 新規作成前に既存ファイルを必ず確認
2. **中核ファイル優先**: 情報が散在している場合は中核ファイルを信頼
3. **定期的な統合**: 関連情報は中核ファイルに集約

## 🎯 クイックスタート

Claude Code としてこのプロジェクトで作業を開始する場合：

1. このファイル（CLAUDE.md）を読む
2. `docs/progress_management/CURRENT_PROGRESS.md` で現状確認
3. `docs/progress_management/CURRENT_ISSUES.md` で課題確認
4. 必要に応じて `docs/mathematical_foundation.md` を参照

---

**最終更新**: 2025-08-02
**管理者**: プロジェクトオーナー