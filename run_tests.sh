#!/bin/bash

# テスト用ディレクトリの作成
mkdir -p analysis_results/plots
mkdir -p analysis_results/summaries
mkdir -p analysis_results/metrics
mkdir -p analysis_results/raw_data

# PYTHONPATHの設定
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# __init__.pyが存在しない場合は作成
touch src/__init__.py

# 現在のPYTHONPATHを確認
echo $PYTHONPATH

# テストの実行
PYTHONPATH=$PYTHONPATH:$(pwd) python -m unittest discover -s tests -p "test_*.py" -v

# テスト結果の表示
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed."
    exit 1
fi