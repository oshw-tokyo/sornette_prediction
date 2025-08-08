# 論文アーカイブディレクトリ

## ⚠️ 重要な注意事項

**PDFファイルの直接読み込みは禁止されています**

Claude Codeでの作業中、PDFファイルの直接読み込みは「Context low」エラーを引き起こし、システムがスタックします。このため、すべての論文はテキスト形式に変換されています。

## 📁 ディレクトリ構造

```
papers/
├── README.md                    # このファイル
├── extracted_texts/             # テキスト変換済み論文（作業用）
│   ├── *_extracted.txt         # メイン抽出テキスト
│   └── *_extracted_Header.txt  # セクション別テキスト
└── pdf_archive/                 # 元のPDFファイル（参照専用）
    └── *.pdf                    # オリジナルPDF（直接読み込み禁止）
```

## 📚 利用可能な論文（テキスト版）

### 1. 基本理論・実装の核となる論文
- **sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt**
  - 式(54): LPPLの基本形
  - パラメータ: β = 0.33 ± 0.03, ω = 6-8
  - 1987年ブラックマンデーの検証

### 2. 総合レビュー・手法論
- **sornette_2001_0106520v1_a_recent- review_and_assessment_extracted.txt**
  - 総合的なレビューと理論背景
  - パラメータ推定手法の詳細

### 3. 初期の理論論文
- **Sornette_1999_9903321_descrete_scale_extracted.txt**
  - 離散スケール不変性の理論
- **Sornette_1999_9907270v1_log_periodic_extracted.txt**
  - 対数周期振動の基礎理論

### 4. 拡張・応用論文
- **sornette_2002_0201458v1_non-parametric_tests_extracted.txt**
  - q微分を用いた非パラメトリック検定
- **sornette_2012_1212.2833v1_extracted.txt**
  - 最新の改良手法と不動産バブル分析
- **sornette_2018_arXiv_cond-mat_0002059v1_extracted.txt**
  - 日経平均予測の検証

### 5. 日本語資料
- **日本でのレポート＿FTRI_RM_01411_extracted.txt**
  - 日本市場での応用事例

## 🔧 使用方法

### 論文を参照する場合
```python
# 正しい方法: テキストファイルを読む
with open('papers/extracted_texts/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt', 'r') as f:
    content = f.read()

# ❌ 間違った方法: PDFを直接読む（エラーになります）
# with open('papers/pdf_archive/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble.pdf', 'rb') as f:
```

### Claude Codeでの参照
```
Readツールで以下のパスを指定：
papers/extracted_texts/[論文名]_extracted.txt
```

## 📊 変換情報

| 元PDF | テキストサイズ | 削減率 |
|-------|---------------|--------|
| Sornette_1999_9903321 | 68KB | 81% |
| Sornette_1999_9907270v1 | 63KB | 90% |
| sornette_2001_0106520v1 | 102KB | 81% |
| sornette_2004_0301543v1 | 312KB | 86% |
| sornette_2012_1212.2833v1 | 80KB | 96% |

## ⚡ トラブルシューティング

### PDFを誤って読み込んでしまった場合
1. セッションを終了
2. 新しいセッションを開始
3. テキスト版ファイルを使用

### テキストファイルが見つからない場合
`pdf_converter.py`スクリプトを使用して再変換：
```bash
python pdf_converter.py papers/pdf_archive/[論文名].pdf
```

---
*最終更新: 2025-08-01*