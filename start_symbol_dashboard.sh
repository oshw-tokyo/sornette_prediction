#!/bin/bash

# 銘柄別可視化ダッシュボード起動スクリプト
# Usage: ./start_symbol_dashboard.sh

echo "🚀 Starting Symbol Visualization Dashboard..."

# 仮想環境の確認
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Please activate one if needed."
fi

# 必要なディレクトリが存在するか確認
if [ ! -d "results" ]; then
    echo "📁 Creating results directory..."
    mkdir -p results
fi

# データベースファイルが存在するか確認
if [ ! -f "results/analysis_results.db" ]; then
    echo "⚠️  Database file not found. Please run some analysis first."
    echo "   You can use: python examples/basic_analysis.py"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Streamlitダッシュボード起動
echo "🌐 Starting Streamlit dashboard..."
echo "📊 Dashboard will be available at: http://localhost:8501"
echo "🔒 To stop the dashboard, press Ctrl+C"

streamlit run src/web_interface/symbol_visualization_dashboard.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.serverAddress localhost \
    --browser.serverPort 8501