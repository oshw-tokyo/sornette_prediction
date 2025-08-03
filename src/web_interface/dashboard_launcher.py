#!/usr/bin/env python3
"""
ダッシュボード統合ランチャー
複数のダッシュボードから選択して起動
"""

import streamlit as st
import subprocess
import sys
import os

def main():
    """メインランチャー画面"""
    st.set_page_config(
        page_title="LPPL Dashboard Launcher",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 LPPL Prediction Dashboard Launcher")
    st.markdown("---")
    
    # ダッシュボード選択
    dashboard_options = {
        "Symbol Analysis": {
            "description": "銘柄別の詳細分析ダッシュボード",
            "features": [
                "📈 価格チャートと予測履歴の重ね表示",
                "📊 予測傾向の散布図分析",
                "📋 パラメータ詳細テーブル",
                "⏰ 時間精度での予測日時表示"
            ],
            "script": "symbol_visualization_dashboard.py"
        },
        "General Analysis": {
            "description": "汎用分析ダッシュボード（既存）",
            "features": [
                "📊 分析結果概要",
                "🔍 詳細分析結果",
                "📈 可視化表示",
                "⚙️ 設定管理"
            ],
            "script": "analysis_dashboard.py"
        }
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Symbol Analysis Dashboard")
        st.write(dashboard_options["Symbol Analysis"]["description"])
        
        st.write("**Features:**")
        for feature in dashboard_options["Symbol Analysis"]["features"]:
            st.write(f"- {feature}")
        
        if st.button("🚀 Launch Symbol Dashboard", type="primary"):
            st.success("Symbol Dashboard launched!")
            st.info("Check terminal for Streamlit URL (usually http://localhost:8501)")
            
            # Streamlit実行
            script_path = os.path.join(os.path.dirname(__file__), "symbol_visualization_dashboard.py")
            subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", script_path,
                "--server.port", "8501"
            ])
    
    with col2:
        st.subheader("📈 General Analysis Dashboard")
        st.write(dashboard_options["General Analysis"]["description"])
        
        st.write("**Features:**")
        for feature in dashboard_options["General Analysis"]["features"]:
            st.write(f"- {feature}")
        
        if st.button("🚀 Launch General Dashboard"):
            st.success("General Dashboard launched!")
            st.info("Check terminal for Streamlit URL (usually http://localhost:8502)")
            
            # Streamlit実行
            script_path = os.path.join(os.path.dirname(__file__), "analysis_dashboard.py")
            subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", script_path,
                "--server.port", "8502"
            ])
    
    st.markdown("---")
    
    # システム情報
    st.subheader("🔧 System Information")
    
    # データベース確認
    db_path = "results/analysis_results.db"
    if os.path.exists(db_path):
        st.success(f"✅ Database found: {db_path}")
        db_size = os.path.getsize(db_path)
        st.info(f"📊 Database size: {db_size / 1024:.1f} KB")
    else:
        st.warning(f"⚠️ Database not found: {db_path}")
        st.info("💡 Run some analysis first: `python examples/basic_analysis.py`")
    
    # 結果ディレクトリ確認
    results_dir = "results"
    if os.path.exists(results_dir):
        files = os.listdir(results_dir)
        st.info(f"📁 Results directory contains {len(files)} files")
    else:
        st.warning(f"⚠️ Results directory not found")

if __name__ == "__main__":
    main()