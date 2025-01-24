# Sornette Model Market Analysis

金融市場における対数周期的な振る舞いを分析し、潜在的な市場の臨界点を予測するツール。Didier Sornette の研究に基づく実装。

## 主な機能

- 株価の対数周期性分析
- 複数時間枠での分析（6ヶ月/1年/2年）
- フィッティング品質の評価
- 予測の安定性分析
- 臨界点の予測と警告レベルの判定

## 使用方法

1. 環境設定
```bash
pip install -r requirements.txt

    銘柄リストの準備

bash

python get_market_symbols.py

    分析実行

bash

python stock-analysis.py

出力データ

    分析レポート（JSON）
    グラフ画像（PNG）
    分析結果サマリー（CSV）

ファイル構造

    stock-analysis.py: メイン分析スクリプト
    market_symbols.json: 分析対象銘柄リスト

必要条件

    Python 3.8+
    yfinance
    numpy
    scipy
    pandas
    matplotlib
    scikit-learn
