# プロジェクトツール

## 📁 ディレクトリ構成

### tools/
プロジェクトで使用する各種ツールとユーティリティ

```
tools/
├── README.md                    # このファイル
├── pdf_converter.py             # PDF→テキスト変換ツール
└── validation/                  # 検証・デバッグツール
    └── debug_beta_issue.py      # β値問題分析ツール
```

## 🔧 各ツールの説明

### pdf_converter.py
- **目的**: PDFファイルをテキストファイルに変換（Context lowエラー回避）
- **使用法**: `python tools/pdf_converter.py <PDF_PATH>`
- **出力**: テキストファイルとセクション別ファイル

### validation/debug_beta_issue.py  
- **目的**: β値系統誤差の詳細分析とデバッグ
- **機能**: 
  - 合成データでの論文パラメータ再現テスト
  - ノイズレベル別の誤差分析
  - グローバル最適化テスト
  - LPPL関数挙動の可視化
- **使用法**: `python tools/validation/debug_beta_issue.py`

## 📋 整理方針

### ファイル配置ルール
1. **tools/**: 汎用ツール・ユーティリティ
2. **tests/**: 単体テスト・統合テスト
3. **plots/**: 生成される図表・グラフ
4. **analysis_results/**: 分析結果の保存

### 出力ファイル管理
- **プロット**: `plots/validation/` に保存
- **検証結果**: `analysis_results/validation/` に保存
- **ログ**: `analysis_results/logs/` に保存

## ⚠️ 注意事項

- ツール実行前に必要な依存関係がインストールされていることを確認
- PDFツールは `Context low` エラー回避のため、必ずテキスト変換を完了してから使用
- 検証ツールは論文の検証に影響するため、実行結果は慎重に評価すること