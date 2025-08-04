#!/bin/bash
# LPPL分析ダッシュボード起動スクリプト
# プロジェクト方針に従い、entry_points/main.pyを経由して起動

echo "🎯 LPPL分析ダッシュボード起動"
echo "================================"
echo "🚀 ダッシュボード起動中..."
echo "🔗 URL: http://localhost:8501"
echo "📝 終了する場合は Ctrl+C を押してください"
echo "================================"

# 統一エントリーポイント経由で起動
python entry_points/main.py dashboard --type main