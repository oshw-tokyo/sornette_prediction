#!/bin/bash
# LPPL分析ダッシュボード起動スクリプト（統一版）
# プロジェクト方針に従い、entry_points/main.pyを経由して起動

echo "🎯 LPPL分析ダッシュボード起動"
echo "================================"

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
    echo "   You can use: python entry_points/main.py analyze ALL"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Dashboard startup cancelled."
        exit 1
    fi
fi

echo "🚀 ダッシュボード起動中..."
echo "🔗 URL: http://localhost:8501"
echo "📝 終了する場合は Ctrl+C を押してください"
echo "================================"

# 統一エントリーポイント経由で起動
python entry_points/main.py dashboard --type main