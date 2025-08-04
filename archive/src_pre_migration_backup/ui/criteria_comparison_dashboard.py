#!/usr/bin/env python3
"""
選択基準比較ダッシュボード

複数の選択基準による結果をUI上で比較・フィルタリングし、
ユーザーが最適な基準を選択できる機能を提供
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import warnings
warnings.filterwarnings('ignore')

class CriteriaComparisonDashboard:
    """選択基準比較ダッシュボード"""
    
    def __init__(self, db):
        """
        Args:
            db: PredictionDatabase instance
        """
        self.db = db
        self.criteria_descriptions = {
            'r_squared_max': {
                'name': 'R²最大化',
                'description': '統計的説明力を最重視（現状方式）',
                'color': '#1f77b4',
                'icon': '📊'
            },
            'multi_criteria': {
                'name': '多基準評価',
                'description': '統計品質・理論値・実用性・安定性の総合評価',
                'color': '#ff7f0e',
                'icon': '⚖️'
            },
            'theoretical_best': {
                'name': '理論値最適',
                'description': 'Sornette理論の典型値に最も近い結果',
                'color': '#2ca02c',
                'icon': '🔬'
            },
            'practical_focus': {
                'name': '実用性重視',
                'description': 'tc≤1.5の実用的な予測を優先',
                'color': '#d62728',
                'icon': '🎯'
            },
            'conservative': {
                'name': '保守的選択',
                'description': '高い信頼性と安定性を重視',
                'color': '#9467bd',
                'icon': '🛡️'
            }
        }
    
    def render_dashboard(self):
        """ダッシュボードのメイン表示"""
        
        st.set_page_config(
            page_title="LPPL選択基準比較ダッシュボード",
            page_icon="📊",
            layout="wide"
        )
        
        st.title("🎯 LPPL選択基準比較ダッシュボード")
        st.markdown("複数のフィッティング結果選択基準を比較し、最適な基準を選択できます。")
        
        # サイドバー：フィルタリングオプション
        self._render_sidebar()
        
        # メインコンテンツ
        if st.session_state.get('analysis_data'):
            self._render_main_content()
        else:
            self._render_welcome_screen()
    
    def _render_sidebar(self):
        """サイドバーのレンダリング"""
        
        with st.sidebar:
            st.header("🔍 分析設定")
            
            # 市場選択
            markets = ['NASDAQ', 'SP500', 'DJIA', 'BTC', 'NIKKEI']
            selected_market = st.selectbox(
                "市場", 
                markets,
                index=0,
                key="selected_market"
            )
            
            # 期間選択
            windows = [365, 730, 1095, 1825]
            window_labels = ['1年', '2年', '3年', '5年']
            selected_window = st.selectbox(
                "分析期間",
                windows,
                format_func=lambda x: f"{x}日 ({window_labels[windows.index(x)]})",
                index=1,
                key="selected_window"
            )
            
            # 期間設定
            days_back = st.slider(
                "分析対象期間（過去N日）",
                min_value=7,
                max_value=365,
                value=90,
                key="days_back"
            )
            
            # 分析実行ボタン
            if st.button("🔍 分析実行", use_container_width=True):
                self._load_analysis_data(selected_market, selected_window, days_back)
            
            st.divider()
            
            # 選択基準フィルター
            st.subheader("📊 表示基準選択")
            
            selected_criteria = []
            for criteria_key, info in self.criteria_descriptions.items():
                if st.checkbox(
                    f"{info['icon']} {info['name']}", 
                    value=True,
                    key=f"criteria_{criteria_key}"
                ):
                    selected_criteria.append(criteria_key)
            
            st.session_state['selected_criteria'] = selected_criteria
            
            if st.session_state.get('analysis_data'):
                st.divider()
                
                # 詳細設定
                st.subheader("⚙️ 表示設定")
                
                show_confidence = st.checkbox("信頼度表示", value=True)
                show_theory_diff = st.checkbox("理論値との差分表示", value=False)
                show_trend = st.checkbox("時系列トレンド表示", value=True)
                
                st.session_state.update({
                    'show_confidence': show_confidence,
                    'show_theory_diff': show_theory_diff,
                    'show_trend': show_trend
                })
    
    def _load_analysis_data(self, market: str, window_days: int, days_back: int):
        """分析データの読み込み"""
        
        with st.spinner("データを読み込み中..."):
            try:
                # 多基準結果の取得
                multi_criteria_data = self.db.get_multi_criteria_results(
                    market=market,
                    window_days=window_days,
                    days_back=days_back
                )
                
                # 基準別比較データの取得
                comparison_data = self.db.get_criteria_comparison(
                    market=market,
                    window_days=window_days,
                    days_back=days_back
                )
                
                st.session_state['analysis_data'] = {
                    'market': market,
                    'window_days': window_days,
                    'days_back': days_back,
                    'multi_criteria': multi_criteria_data,
                    'comparison': comparison_data,
                    'loaded_at': datetime.now()
                }
                
                st.success(f"✅ {market} / {window_days}日 のデータを読み込みました")\n                
            except Exception as e:\n                st.error(f"❌ データ読み込みエラー: {str(e)}")
    
    def _render_welcome_screen(self):
        """ウェルカムスクリーンの表示"""
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ### 🎯 複数基準選択システムへようこそ
            
            このダッシュボードでは、LPPLフィッティングの複数選択基準を比較できます：
            """)
            
            for criteria_key, info in self.criteria_descriptions.items():
                st.markdown(f"""
                **{info['icon']} {info['name']}**
                
                {info['description']}
                """)
            
            st.markdown("""
            ---
            **使用方法：**
            1. サイドバーで市場と分析期間を選択
            2. "分析実行"ボタンをクリック
            3. 各基準の結果を比較・検討
            """)
    
    def _render_main_content(self):
        """メインコンテンツの表示"""
        
        data = st.session_state['analysis_data']
        
        # ヘッダー情報
        st.markdown(f"""
        ### 📊 {data['market']} / {data['window_days']}日 分析結果
        **分析期間**: 過去{data['days_back']}日 | **更新**: {data['loaded_at'].strftime('%Y-%m-%d %H:%M')}
        """)
        
        if data['multi_criteria']['status'] == 'no_data':
            st.warning("📭 指定期間内にデータが見つかりませんでした。")
            return
        
        # タブレイアウト
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎯 最新結果比較", 
            "📈 時系列トレンド", 
            "📊 統計サマリー", 
            "🔍 詳細分析"
        ])
        
        with tab1:
            self._render_latest_comparison()
        
        with tab2:
            self._render_trend_analysis()
        
        with tab3:
            self._render_statistics_summary()
        
        with tab4:
            self._render_detailed_analysis()
    
    def _render_latest_comparison(self):
        """最新結果比較の表示"""
        
        data = st.session_state['analysis_data']
        sessions = data['multi_criteria']['sessions']
        
        if not sessions:
            st.warning("比較可能なセッションがありません。")
            return
        
        # 最新セッションの取得
        latest_session_id = max(sessions.keys(), 
                              key=lambda x: sessions[x]['session_info']['timestamp'])
        latest_session = sessions[latest_session_id]
        
        st.subheader(f"🕐 最新分析結果 ({latest_session['session_info']['timestamp'][:10]})")
        
        # 選択された基準での結果比較
        selected_criteria = st.session_state.get('selected_criteria', list(self.criteria_descriptions.keys()))
        
        comparison_df = []
        for criteria in selected_criteria:
            if criteria in latest_session['selections']:
                result = latest_session['selections'][criteria]
                info = self.criteria_descriptions[criteria]
                
                comparison_df.append({
                    '選択基準': f"{info['icon']} {info['name']}",
                    'tc値': f"{result['tc']:.3f}",
                    'β値': f"{result['beta']:.3f}",
                    'ω値': f"{result['omega']:.2f}",
                    'R²': f"{result['r_squared']:.4f}",
                    'RMSE': f"{result['rmse']:.4f}",
                    '予測日': result['predicted_date'][:10],
                    '解釈': result['tc_interpretation'],
                    '信頼度': f"{result['confidence_score']:.3f}"
                })
        
        if comparison_df:
            df = pd.DataFrame(comparison_df)
            
            # カラーマッピング
            def color_tc(val):
                tc_val = float(val)
                if tc_val <= 1.2:
                    return 'background-color: #ffeeee'  # 薄い赤
                elif tc_val <= 1.5:
                    return 'background-color: #fff4e6'  # 薄いオレンジ
                else:
                    return 'background-color: #f0fff0'  # 薄い緑
            
            # スタイル付きテーブル表示
            styled_df = df.style.applymap(color_tc, subset=['tc値'])
            st.dataframe(styled_df, use_container_width=True)
            
            # tc値の比較チャート
            self._render_tc_comparison_chart(comparison_df)
    
    def _render_tc_comparison_chart(self, comparison_data: List[Dict]):
        """tc値比較チャートの表示"""
        
        fig = go.Figure()
        
        for i, row in enumerate(comparison_data):
            criteria_name = row['選択基準'].split(' ', 1)[1]  # アイコンを除去
            tc_val = float(row['tc値'])
            confidence = float(row['信頼度'])
            
            # 基準に応じた色設定
            color = None
            for key, info in self.criteria_descriptions.items():
                if info['name'] in criteria_name:
                    color = info['color']
                    break
            
            fig.add_trace(go.Bar(
                x=[criteria_name],
                y=[tc_val],
                marker_color=color,
                opacity=confidence,  # 信頼度で透明度調整
                text=f"tc={tc_val:.3f}<br>信頼度={confidence:.2f}",
                textposition="auto",
                name=criteria_name
            ))
        
        # tc値の実用性ゾーン表示
        fig.add_hline(y=1.2, line_dash="dash", line_color="red", 
                     annotation_text="実用的予測限界 (tc=1.2)")
        fig.add_hline(y=1.5, line_dash="dot", line_color="orange", 
                     annotation_text="監視推奨上限 (tc=1.5)")
        
        fig.update_layout(
            title="📊 tc値比較（実用性ゾーン付き）",
            xaxis_title="選択基準",
            yaxis_title="tc値",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_trend_analysis(self):
        """時系列トレンド分析の表示"""
        
        data = st.session_state['analysis_data']
        
        if data['comparison']['status'] == 'no_data':
            st.warning("トレンドデータがありません。")
            return
        
        trend_data = data['comparison']['trend_data']
        df = pd.DataFrame(trend_data)
        
        if df.empty:
            st.warning("トレンドデータが空です。")
            return
        
        # 日付変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 選択された基準でフィルタ
        selected_criteria = st.session_state.get('selected_criteria', list(self.criteria_descriptions.keys()))
        df_filtered = df[df['selection_criteria'].isin(selected_criteria)]
        
        # tc値の時系列プロット
        fig = go.Figure()
        
        for criteria in selected_criteria:
            criteria_data = df_filtered[df_filtered['selection_criteria'] == criteria]
            if not criteria_data.empty:
                info = self.criteria_descriptions.get(criteria, {})
                
                fig.add_trace(go.Scatter(
                    x=criteria_data['timestamp'],
                    y=criteria_data['tc'],
                    mode='lines+markers',
                    name=f"{info.get('icon', '')} {info.get('name', criteria)}",
                    line=dict(color=info.get('color', '#1f77b4')),
                    hovertemplate="<b>%{fullData.name}</b><br>" +
                                "日時: %{x}<br>" +
                                "tc値: %{y:.3f}<br>" +
                                "<extra></extra>"
                ))
        
        # 実用性ゾーン表示
        fig.add_hline(y=1.2, line_dash="dash", line_color="red", opacity=0.5,
                     annotation_text="実用的予測限界")
        fig.add_hline(y=1.5, line_dash="dot", line_color="orange", opacity=0.5,
                     annotation_text="監視推奨上限")
        
        fig.update_layout(
            title="📈 tc値時系列トレンド",
            xaxis_title="日時",
            yaxis_title="tc値",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # R²値の時系列プロット
        self._render_r2_trend(df_filtered)
    
    def _render_r2_trend(self, df: pd.DataFrame):
        """R²値トレンドの表示"""
        
        fig = go.Figure()
        
        selected_criteria = st.session_state.get('selected_criteria', [])
        
        for criteria in selected_criteria:
            criteria_data = df[df['selection_criteria'] == criteria]
            if not criteria_data.empty:
                info = self.criteria_descriptions.get(criteria, {})
                
                fig.add_trace(go.Scatter(
                    x=criteria_data['timestamp'],
                    y=criteria_data['r_squared'],
                    mode='lines+markers',
                    name=f"{info.get('icon', '')} {info.get('name', criteria)}",
                    line=dict(color=info.get('color', '#1f77b4')),
                    yaxis='y2'
                ))
        
        fig.update_layout(
            title="📊 R²値時系列トレンド",
            xaxis_title="日時",
            yaxis=dict(title="R²値", side='left'),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_statistics_summary(self):
        """統計サマリーの表示"""
        
        data = st.session_state['analysis_data']
        
        if data['comparison']['status'] == 'no_data':
            st.warning("統計データがありません。")
            return
        
        stats_data = data['comparison']['criteria_stats']
        df = pd.DataFrame(stats_data)
        
        # 選択された基準でフィルタ
        selected_criteria = st.session_state.get('selected_criteria', list(self.criteria_descriptions.keys()))
        df_filtered = df[df['selection_criteria'].isin(selected_criteria)]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 基準別統計")
            
            # 統計表の作成
            summary_df = []
            for _, row in df_filtered.iterrows():
                criteria = row['selection_criteria']
                info = self.criteria_descriptions.get(criteria, {})
                
                summary_df.append({
                    '基準': f"{info.get('icon', '')} {info.get('name', criteria)}",
                    '選択回数': int(row['selection_count']),
                    '平均tc': f"{row['avg_tc']:.3f}",
                    '平均R²': f"{row['avg_r_squared']:.4f}",
                    '平均信頼度': f"{row['avg_confidence']:.3f}",
                    'tc範囲': f"{row['min_tc']:.2f} - {row['max_tc']:.2f}"
                })
            
            if summary_df:
                st.dataframe(pd.DataFrame(summary_df), use_container_width=True)
        
        with col2:
            st.subheader("🎯 選択頻度分布")
            
            # 選択頻度の円グラフ
            if not df_filtered.empty:
                fig = go.Figure(data=[go.Pie(
                    labels=[self.criteria_descriptions.get(row['selection_criteria'], {}).get('name', row['selection_criteria']) 
                           for _, row in df_filtered.iterrows()],
                    values=df_filtered['selection_count'],
                    marker_colors=[self.criteria_descriptions.get(row['selection_criteria'], {}).get('color', '#1f77b4') 
                                 for _, row in df_filtered.iterrows()],
                    textinfo='label+percent'
                )])
                
                fig.update_layout(
                    title="選択基準別使用頻度",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def _render_detailed_analysis(self):
        """詳細分析の表示"""
        
        st.subheader("🔍 詳細分析")
        
        data = st.session_state['analysis_data']
        sessions = data['multi_criteria']['sessions']
        
        # セッション選択
        session_options = {
            session_id: f"{session_data['session_info']['timestamp'][:16]} - " +
                       f"{session_data['session_info']['total_candidates']}候補中" +
                       f"{session_data['session_info']['successful_candidates']}成功"
            for session_id, session_data in sessions.items()
        }
        
        if session_options:
            selected_session_id = st.selectbox(
                "分析セッション選択",
                options=list(session_options.keys()),
                format_func=lambda x: session_options[x],
                key="selected_session"
            )
            
            selected_session = sessions[selected_session_id]
            
            # セッション詳細情報
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "総候補数",
                    selected_session['session_info']['total_candidates']
                )
            
            with col2:
                st.metric(
                    "成功候補数",
                    selected_session['session_info']['successful_candidates']
                )
            
            with col3:
                success_rate = (selected_session['session_info']['successful_candidates'] / 
                              selected_session['session_info']['total_candidates'] * 100)
                st.metric(
                    "成功率",
                    f"{success_rate:.1f}%"
                )
            
            # 基準別詳細結果
            st.subheader("📋 基準別詳細結果")
            
            for criteria, result in selected_session['selections'].items():
                if criteria in st.session_state.get('selected_criteria', []):
                    info = self.criteria_descriptions.get(criteria, {})
                    
                    with st.expander(f"{info.get('icon', '')} {info.get('name', criteria)} - tc={result['tc']:.3f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"""
                            **パラメータ値:**
                            - tc: {result['tc']:.4f}
                            - β: {result['beta']:.4f}
                            - ω: {result['omega']:.2f}
                            
                            **統計品質:**
                            - R²: {result['r_squared']:.4f}
                            - RMSE: {result['rmse']:.4f}
                            """)
                        
                        with col2:
                            st.markdown(f"""
                            **予測情報:**
                            - 予測日: {result['predicted_date'][:10]}
                            - 解釈: {result['tc_interpretation']}
                            - 信頼度: {result['confidence_score']:.3f}
                            """)
                        
                        # 選択スコア詳細（存在する場合）
                        if result.get('selection_scores'):
                            st.markdown("**選択スコア詳細:**")
                            score_df = pd.DataFrame([result['selection_scores']]).T
                            score_df.columns = ['スコア']
                            st.dataframe(score_df)

# 使用例・テスト関数
def example_usage():
    """使用例の実演"""
    from src.data_management.prediction_database import PredictionDatabase
    
    # データベース接続
    db = PredictionDatabase("demo_predictions.db")
    
    # ダッシュボード起動
    dashboard = CriteriaComparisonDashboard(db)
    dashboard.render_dashboard()

if __name__ == "__main__":
    example_usage()