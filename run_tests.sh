#!/bin/bash

# 必要なディレクトリの作成
echo "Creating necessary directories..."
mkdir -p analysis_results/{plots,summaries,metrics,raw_data,logs}
mkdir -p tests/{fitting,analysis,logging,reproducibility_validation}

# __init__.pyファイルの作成
echo "Creating __init__.py files..."
touch src/__init__.py
touch tests/__init__.py
touch tests/fitting/__init__.py
touch tests/analysis/__init__.py
touch tests/logging/__init__.py
touch tests/reproducibility_validation/__init__.py

# PYTHONPATHの設定と確認
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
echo "PYTHONPATH set to: $PYTHONPATH"

# テストの実行（カテゴリごと）
echo "Running tests..."

echo "Testing fitting modules..."
python -m unittest discover -s tests/fitting -p "test_*.py" -v

echo "Testing analysis modules..."
python -m unittest discover -s tests/analysis -p "test_*.py" -v

echo "Testing logging modules..."
python -m unittest discover -s tests/logging -p "test_*.py" -v

echo "Testing reproducibility validation..."
python -m unittest discover -s tests/reproducibility_validation -p "test_*.py" -v

# 全体の結果の確認
if [ $? -eq 0 ]; then
    echo "All tests passed successfully!"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi