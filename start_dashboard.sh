#!/bin/bash
# LPPL分析ダッシュボード起動スクリプト

echo "🎯 LPPL分析ダッシュボード起動"
echo "================================"

# Streamlit設定を環境変数で指定
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ダッシュボード起動
echo "🚀 ダッシュボード起動中..."
echo "🔗 URL: http://localhost:8501"
echo "📝 終了する場合は Ctrl+C を押してください"
echo "================================"

streamlit run src/web_interface/analysis_dashboard.py \
    --server.port=8501 \
    --server.address=localhost \
    --server.headless=true \
    --browser.gatherUsageStats=false