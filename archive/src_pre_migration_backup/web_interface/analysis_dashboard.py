#!/usr/bin/env python3
"""
ブラウザベース分析ダッシュボード
データベースに保存された分析結果をWebインターフェースで表示
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import base64
import io
import sys
import os

# プロジェクトルートを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.results_database import ResultsDatabase
from src.database.integration_helpers import DatabaseAnalysisViewer

class AnalysisDashboard:
    """分析結果ダッシュボードクラス"""
    
    def __init__(self):
        """初期化"""
        # 統一データベースパス
        db_path = "results/analysis_results.db"
        
        self.db = ResultsDatabase(db_path)
        self.viewer = DatabaseAnalysisViewer(db_path)
        
        # 使用中のDBパスを保存（表示用）
        self.current_db_path = db_path
        
        # ページ設定
        st.set_page_config(
            page_title="LPPL Prediction Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def render_dashboard(self):
        """ダッシュボードのメイン表示"""
        # ヘッダー
        st.title("📊 LPPL Market Crash Prediction Dashboard")
        
        # データベース情報表示
        st.info(f"📁 データベース: {os.path.basename(self.current_db_path)}")
        st.markdown("---")
        
        # サイドバー
        self.render_sidebar()
        
        # メインコンテンツ
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Overview", "🔍 Analysis Results", "📊 Visualizations", "⚙️ Settings"
        ])
        
        with tab1:
            self.render_overview()
        
        with tab2:
            self.render_analysis_results()
        
        with tab3:
            self.render_visualizations()
        
        with tab4:
            self.render_settings()
    
    def render_sidebar(self):
        """サイドバーの表示"""
        st.sidebar.title("🎛️ Controls")
        
        # データベース統計
        stats = self.db.get_summary_statistics()
        
        st.sidebar.metric("Total Analyses", stats['total_analyses'])
        st.sidebar.metric("Unique Symbols", stats['unique_symbols'])
        st.sidebar.metric("Usable Rate", f"{stats['usable_rate']:.1%}")
        
        st.sidebar.markdown("---")
        
        # フィルター
        st.sidebar.subheader("🔍 Filters")
        
        # 銘柄選択
        recent_analyses = self.db.get_recent_analyses(limit=1000)
        if not recent_analyses.empty:
            symbols = ['All'] + sorted(recent_analyses['symbol'].unique().tolist())
            selected_symbol = st.sidebar.selectbox("Symbol", symbols)
            
            # 期間選択
            date_range = st.sidebar.selectbox(
                "Time Range",
                ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
            )
            
            # 品質フィルター
            quality_filter = st.sidebar.multiselect(
                "Quality Filter",
                ["high_quality", "acceptable", "unacceptable", "failed"],
                default=["high_quality", "acceptable"]
            )
            
            # セッション状態に保存
            st.session_state.selected_symbol = selected_symbol
            st.session_state.date_range = date_range
            st.session_state.quality_filter = quality_filter
        
        st.sidebar.markdown("---")
        
        # アクション
        st.sidebar.subheader("🔄 Actions")
        
        if st.sidebar.button("🔄 Refresh Data"):
            st.rerun()
        
        if st.sidebar.button("📥 Export Data"):
            self.export_data()
        
        if st.sidebar.button("🗑️ Cleanup Old Data"):
            self.cleanup_data()
    
    def render_overview(self):
        """概要タブの表示"""
        st.header("📊 Analysis Overview")
        
        # KPI表示
        col1, col2, col3, col4 = st.columns(4)
        
        stats = self.db.get_summary_statistics()
        
        with col1:
            st.metric(
                "Total Analyses",
                stats['total_analyses'],
                delta=None
            )
        
        with col2:
            st.metric(
                "Average R²",
                f"{stats['r_squared_stats']['average']:.3f}",
                delta=None
            )
        
        with col3:
            st.metric(
                "Usable Analyses",
                stats['usable_analyses'],
                delta=f"{stats['usable_rate']:.1%}"
            )
        
        with col4:
            if stats['latest_analysis']:
                latest = datetime.fromisoformat(stats['latest_analysis'])
                days_ago = (datetime.now() - latest).days
                st.metric(
                    "Last Analysis",
                    f"{days_ago} days ago",
                    delta=None
                )
        
        # 品質分布チャート
        st.subheader("📊 Quality Distribution")
        
        if stats['quality_distribution']:
            quality_df = pd.DataFrame([
                {'Quality': k, 'Count': v} 
                for k, v in stats['quality_distribution'].items()
            ])
            
            fig = px.pie(
                quality_df, 
                values='Count', 
                names='Quality',
                title="Analysis Quality Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 最近のトレンド
        st.subheader("📈 Recent Trends")
        
        recent_analyses = self.db.get_recent_analyses(limit=50)
        if not recent_analyses.empty:
            recent_analyses['analysis_date'] = pd.to_datetime(recent_analyses['analysis_date'])
            
            # R²トレンド
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=recent_analyses['analysis_date'],
                y=recent_analyses['r_squared'],
                mode='lines+markers',
                name='R² Score',
                line=dict(color='blue')
            ))
            
            fig.update_layout(
                title="R² Score Trend",
                xaxis_title="Date",
                yaxis_title="R² Score",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_analysis_results(self):
        """分析結果タブの表示"""
        st.header("🔍 Detailed Analysis Results")
        
        # フィルターの適用
        symbol_filter = getattr(st.session_state, 'selected_symbol', 'All')
        quality_filter = getattr(st.session_state, 'quality_filter', ['high_quality', 'acceptable'])
        
        # データ取得
        recent_analyses = self.db.get_recent_analyses(limit=100)
        
        if recent_analyses.empty:
            st.info("No analysis results found in database.")
            return
        
        # フィルター適用
        filtered_data = recent_analyses.copy()
        
        if symbol_filter != 'All':
            filtered_data = filtered_data[filtered_data['symbol'] == symbol_filter]
        
        if quality_filter:
            filtered_data = filtered_data[filtered_data['quality'].isin(quality_filter)]
        
        # データテーブル表示
        st.subheader(f"📋 Results ({len(filtered_data)} records)")
        
        if not filtered_data.empty:
            # 重要な列のみ表示
            display_columns = [
                'symbol', 'analysis_date', 'tc', 'beta', 'omega', 
                'r_squared', 'quality', 'confidence', 'predicted_crash_date', 'days_to_crash'
            ]
            
            display_data = filtered_data[display_columns].copy()
            display_data['analysis_date'] = pd.to_datetime(display_data['analysis_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            # フォーマット調整
            for col in ['tc', 'beta', 'omega', 'r_squared', 'confidence']:
                if col in display_data.columns:
                    display_data[col] = display_data[col].round(3)
            
            st.dataframe(
                display_data,
                use_container_width=True,
                height=400
            )
            
            # 詳細表示
            st.subheader("🔍 Detailed View")
            
            if not filtered_data.empty:
                selected_id = st.selectbox(
                    "Select Analysis for Details",
                    filtered_data['id'].tolist(),
                    format_func=lambda x: f"ID {x}: {filtered_data[filtered_data['id']==x]['symbol'].iloc[0]} - {filtered_data[filtered_data['id']==x]['analysis_date'].iloc[0]}"
                )
                
                if selected_id:
                    self.show_analysis_details(selected_id)
        
        else:
            st.warning("No data matches the current filters.")
    
    def show_analysis_details(self, analysis_id: int):
        """特定分析の詳細表示"""
        details = self.db.get_analysis_details(analysis_id)
        
        if not details:
            st.error("Analysis details not found.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 LPPL Parameters")
            st.metric("tc (Critical Time)", f"{details['tc']:.4f}")
            st.metric("β (Critical Exponent)", f"{details['beta']:.4f}")
            st.metric("ω (Angular Frequency)", f"{details['omega']:.4f}")
            st.metric("R² Score", f"{details['r_squared']:.4f}")
        
        with col2:
            st.markdown("### ⚡ Quality Assessment")
            st.metric("Quality", details['quality'])
            st.metric("Confidence", f"{details['confidence']:.1%}")
            st.metric("Usable", "✅ Yes" if details['is_usable'] else "❌ No")
            
            if details['predicted_crash_date']:
                st.metric("Predicted Date", details['predicted_crash_date'])
                if details['days_to_crash']:
                    st.metric("Days to Crash", details['days_to_crash'])
        
        # メタデータ表示
        if details.get('quality_metadata'):
            st.markdown("### 🔍 Quality Metadata")
            st.json(details['quality_metadata'])
    
    def render_visualizations(self):
        """可視化タブの表示"""
        st.header("📊 Visualizations")
        
        recent_analyses = self.db.get_recent_analyses(limit=50)
        
        if recent_analyses.empty:
            st.info("No visualizations available.")
            return
        
        # 分析選択
        analysis_options = {}
        for _, row in recent_analyses.iterrows():
            label = f"{row['symbol']} - {row['analysis_date']} (R²: {row['r_squared']:.3f})"
            analysis_options[label] = row['id']
        
        selected_analysis = st.selectbox(
            "Select Analysis for Visualization",
            list(analysis_options.keys())
        )
        
        if selected_analysis:
            analysis_id = analysis_options[selected_analysis]
            details = self.db.get_analysis_details(analysis_id)
            
            if details.get('visualizations'):
                for viz in details['visualizations']:
                    st.subheader(f"📊 {viz['chart_title'] or viz['chart_type']}")
                    
                    # 画像データ取得
                    image_data = self.db.get_visualization_image(analysis_id, viz['chart_type'])
                    
                    if image_data:
                        st.image(image_data, caption=viz['description'])
                    else:
                        st.warning(f"Image not found: {viz['file_path']}")
            else:
                st.info("No visualizations found for this analysis.")
    
    def render_settings(self):
        """設定タブの表示"""
        st.header("⚙️ Settings & Maintenance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🗄️ Database Management")
            
            if st.button("🔍 Check Database Status"):
                stats = self.db.get_summary_statistics()
                st.success(f"Database OK: {stats['total_analyses']} records")
            
            if st.button("🗑️ Cleanup Old Records"):
                days_to_keep = st.number_input("Days to keep", value=90, min_value=1)
                if st.confirm("Delete old records?"):
                    self.db.cleanup_old_records(days_to_keep)
                    st.success("Cleanup completed")
        
        with col2:
            st.subheader("📤 Export Options")
            
            if st.button("📥 Export Recent Results"):
                recent = self.db.get_recent_analyses(limit=100)
                if not recent.empty:
                    csv = recent.to_csv(index=False)
                    st.download_button(
                        "⬇️ Download CSV",
                        csv,
                        f"lppl_results_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
    
    def export_data(self):
        """データエクスポート"""
        st.sidebar.success("Export feature will be implemented")
    
    def cleanup_data(self):
        """データクリーンアップ"""
        st.sidebar.success("Cleanup feature will be implemented")


def main():
    """メイン実行関数"""
    dashboard = AnalysisDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    # Streamlit実行時の設定
    if len(sys.argv) == 1:
        # 直接実行の場合
        main()
    else:
        # streamlit run の場合
        st.set_option('deprecation.showPyplotGlobalUse', False)
        main()