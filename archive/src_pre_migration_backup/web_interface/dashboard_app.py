#!/usr/bin/env python3
"""
Webダッシュボード・ユーザーインターフェース

Flask/Streamlitベースの直感的なUXを提供
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.data_management.prediction_database import PredictionDatabase, QueryType
from src.monitoring.multi_market_monitor import MultiMarketMonitor, MarketIndex, TimeWindow

class DashboardApp:
    """ダッシュボードアプリケーション"""
    
    def __init__(self):
        self.db = PredictionDatabase()
        self.monitor = MultiMarketMonitor()
        
        # ページ設定
        st.set_page_config(
            page_title="Market Crash Prediction Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def run(self):
        """メインアプリケーションの実行"""
        
        # サイドバー
        self.render_sidebar()
        
        # メインコンテンツ
        page = st.session_state.get('page', 'リアルタイム監視')
        
        if page == 'リアルタイム監視':
            self.render_realtime_monitoring()
        elif page == '履歴分析':
            self.render_historical_analysis()
        elif page == 'トレンド追跡':
            self.render_trend_tracking()
        elif page == '予測精度':
            self.render_accuracy_analysis()
        elif page == 'データ管理':
            self.render_data_management()
    
    def render_sidebar(self):
        """サイドバーの描画"""
        
        with st.sidebar:
            st.title("🎯 Market Prediction")
            st.markdown("---")
            
            # ページ選択
            page = st.selectbox(
                "ページを選択",
                ['リアルタイム監視', '履歴分析', 'トレンド追跡', '予測精度', 'データ管理']
            )
            st.session_state['page'] = page
            
            st.markdown("---")
            
            # クイック統計
            stats = self.db.get_database_stats()
            st.subheader("📊 データ統計")
            st.metric("総予測数", stats['predictions_count'])
            st.metric("アラート数", stats['alert_history_count'])
            st.metric("DB サイズ", f"{stats['database_size_mb']} MB")
            
            # 最新分析実行
            st.markdown("---")
            if st.button("🔄 最新分析実行"):
                with st.spinner("分析実行中..."):
                    self.run_latest_analysis()
                st.success("分析完了！")
                st.experimental_rerun()
    
    def render_realtime_monitoring(self):
        """リアルタイム監視ページ"""
        
        st.title("🚨 リアルタイム市場監視")
        
        # アラートダッシュボード
        alert_data = self.db.get_alert_dashboard()
        
        # アクティブアラート
        if alert_data['active_alerts']:
            st.subheader("⚠️ アクティブアラート")
            
            alert_df = pd.DataFrame(alert_data['active_alerts'])
            
            # 危険度別に色分け
            def get_risk_color(alert_type):
                colors = {
                    'HIGH_RISK': '🔴',
                    'MEDIUM_RISK': '🟡', 
                    'TREND_CHANGE': '🔵'
                }
                return colors.get(alert_type, '⚪')
            
            for _, alert in alert_df.iterrows():
                risk_color = get_risk_color(alert['alert_type'])
                
                with st.expander(f"{risk_color} {alert['market']} - tc: {alert['tc_value']:.3f}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("予測日", alert['predicted_date'][:10])
                    with col2:
                        st.metric("信頼度", f"{alert['confidence_score']:.2f}")
                    with col3:
                        st.metric("発生時刻", alert['timestamp'][:16])
                    
                    if alert['message']:
                        st.info(alert['message'])
        else:
            st.info("現在、アクティブなアラートはありません。")
        
        # 現在の高リスク市場
        st.subheader("🎯 現在の高リスク市場")
        
        current_risks = self.db.get_current_risks()
        
        if current_risks:
            risk_df = pd.DataFrame(current_risks)
            
            # tcによる危険度分類
            risk_df['risk_level'] = risk_df['tc'].apply(
                lambda x: 'CRITICAL' if x < 1.1 else 
                         'HIGH' if x < 1.3 else 
                         'MEDIUM'
            )
            
            # 危険度別表示
            for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM']:
                level_data = risk_df[risk_df['risk_level'] == risk_level]
                
                if not level_data.empty:
                    risk_colors = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡'}
                    st.markdown(f"### {risk_colors[risk_level]} {risk_level} RISK")
                    
                    for _, row in level_data.iterrows():
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("市場", row['market'])
                        with col2:
                            st.metric("tc値", f"{row['tc']:.3f}")
                        with col3:
                            st.metric("予測日", row['predicted_date'][:10])
                        with col4:
                            st.metric("信頼度", f"{row['confidence_score']:.2f}")
        else:
            st.success("現在、高リスクの市場は検出されていません。")
        
        # リアルタイム市場状況
        st.subheader("📈 市場別リアルタイム状況")
        
        # 主要市場の最新tc値を取得・表示
        markets = ['NASDAQ', 'SP500', 'DJIA']
        
        market_cols = st.columns(len(markets))
        
        for i, market in enumerate(markets):
            with market_cols[i]:
                # 最新のtc値を取得
                latest_data = self.db.search_predictions({
                    'market': market,
                    'date_from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                })
                
                if latest_data:
                    latest = latest_data[0]  # 最新
                    tc_value = latest['tc']
                    
                    # tc値による状態判定
                    if tc_value < 1.1:
                        status = "🔴 CRITICAL"
                    elif tc_value < 1.3:
                        status = "🟠 WARNING"
                    elif tc_value < 1.5:
                        status = "🟡 WATCH"
                    else:
                        status = "🟢 NORMAL"
                    
                    st.metric(
                        market,
                        f"tc: {tc_value:.3f}",
                        delta=status
                    )
                else:
                    st.metric(market, "データなし")
    
    def render_historical_analysis(self):
        """履歴分析ページ"""
        
        st.title("📊 履歴分析")
        
        # 検索フィルター
        with st.expander("🔍 検索フィルター", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                market_filter = st.selectbox(
                    "市場",
                    ["全て"] + [m.value for m in MarketIndex]
                )
                
                tc_range = st.slider(
                    "tc値範囲",
                    min_value=1.0,
                    max_value=5.0,
                    value=(1.0, 3.0),
                    step=0.1
                )
            
            with col2:
                confidence_min = st.slider(
                    "最小信頼度",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.05
                )
                
                interpretation_filter = st.selectbox(
                    "tc解釈",
                    ["全て", "imminent", "actionable", "monitoring", "extended", "long_term"]
                )
            
            with col3:
                date_range = st.date_input(
                    "期間",
                    value=(datetime.now() - timedelta(days=90), datetime.now()),
                    max_value=datetime.now()
                )
        
        # 検索実行
        search_params = {
            'tc_min': tc_range[0],
            'tc_max': tc_range[1],
            'confidence_min': confidence_min
        }
        
        if market_filter != "全て":
            search_params['market'] = market_filter
        
        if interpretation_filter != "全て":
            search_params['tc_interpretation'] = interpretation_filter
        
        if len(date_range) == 2:
            search_params['date_from'] = date_range[0].strftime('%Y-%m-%d')
            search_params['date_to'] = date_range[1].strftime('%Y-%m-%d')
        
        results = self.db.search_predictions(search_params)
        
        if results:
            st.subheader(f"📋 検索結果: {len(results)}件")
            
            df = pd.DataFrame(results)
            
            # 統計サマリー
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("平均tc", f"{df['tc'].mean():.3f}")
            with col2:
                st.metric("平均信頼度", f"{df['confidence_score'].mean():.3f}")
            with col3:
                st.metric("最高R²", f"{df['r_squared'].max():.3f}")
            with col4:
                st.metric("市場数", df['market'].nunique())
            
            # 散布図
            st.subheader("📈 tc値 vs 信頼度")
            
            fig = px.scatter(
                df,
                x='tc',
                y='confidence_score',
                color='market',
                size='r_squared',
                hover_data=['predicted_date', 'tc_interpretation'],
                title="予測品質分布"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # データテーブル
            st.subheader("📋 詳細データ")
            
            display_df = df[['timestamp', 'market', 'tc', 'confidence_score', 
                           'predicted_date', 'tc_interpretation']].copy()
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['predicted_date'] = pd.to_datetime(display_df['predicted_date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True)
            
            # エクスポート
            if st.button("📄 CSV エクスポート"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="ダウンロード",
                    data=csv,
                    file_name=f"prediction_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        else:
            st.info("検索条件に一致するデータがありません。")
    
    def render_trend_tracking(self):
        """トレンド追跡ページ"""
        
        st.title("📈 トレンド追跡")
        
        # 市場・期間選択
        col1, col2 = st.columns(2)
        
        with col1:
            selected_market = st.selectbox(
                "市場選択",
                [m.value for m in MarketIndex]
            )
        
        with col2:
            selected_window = st.selectbox(
                "分析期間",
                [f"{w.value}日" for w in TimeWindow]
            )
            window_days = int(selected_window.split('日')[0])
        
        # トレンド分析実行
        trend_data = self.db.get_market_trend(selected_market, window_days)
        
        if trend_data.get('status') == 'no_data':
            st.warning("選択した市場・期間のデータがありません。")
            return
        
        # トレンド概要
        st.subheader("📊 トレンド概要")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("最新tc", f"{trend_data['latest_tc']:.3f}")
        with col2:
            trend_value = trend_data['tc_trend']
            trend_delta = "↗️" if trend_value > 0 else "↘️" if trend_value < 0 else "➡️"
            st.metric("トレンド", f"{trend_value:.4f}", delta=trend_delta)
        with col3:
            velocity = trend_data['tc_velocity']
            velocity_delta = "⚡" if abs(velocity) > 0.01 else "📈"
            st.metric("変化率", f"{velocity:.4f}", delta=velocity_delta)
        with col4:
            interpretation_icons = {
                'approaching_critical': '🚨',
                'moving_away': '📈',
                'stable': '📊'
            }
            icon = interpretation_icons.get(trend_data['interpretation'], '❓')
            st.metric("解釈", trend_data['interpretation'], delta=icon)
        
        # 時系列チャート
        if trend_data['history']:
            st.subheader("📈 tc値の時系列変化")
            
            df = pd.DataFrame(trend_data['history'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            fig = go.Figure()
            
            # tc値のライン
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['tc'],
                mode='lines+markers',
                name='tc値',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))
            
            # 危険ライン
            fig.add_hline(y=1.1, line_dash="dash", line_color="red", 
                         annotation_text="差し迫った危機")
            fig.add_hline(y=1.3, line_dash="dash", line_color="orange", 
                         annotation_text="アクション推奨")
            fig.add_hline(y=1.5, line_dash="dash", line_color="yellow", 
                         annotation_text="監視継続")
            
            fig.update_layout(
                title=f"{selected_market} - tc値トレンド ({selected_window})",
                xaxis_title="日時",
                yaxis_title="tc値",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 信頼度チャート
            st.subheader("📊 信頼度の変化")
            
            fig2 = px.line(
                df,
                x='timestamp',
                y='confidence_score',
                title="信頼度スコアの推移"
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    
    def render_accuracy_analysis(self):
        """予測精度分析ページ"""
        
        st.title("🎯 予測精度分析")
        
        # 精度統計取得
        accuracy_stats = self.db.get_prediction_accuracy_stats()
        
        if accuracy_stats.get('status') == 'no_validation_data':
            st.warning("検証済みの予測データがありません。")
            return
        
        # 全体統計
        st.subheader("📊 全体統計")
        
        overall = accuracy_stats['overall_stats']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("検証済み予測数", overall['total_validated_predictions'])
        with col2:
            st.metric("平均精度", f"{overall['average_accuracy']:.3f}")
        with col3:
            st.metric("高精度率", f"{overall['high_accuracy_rate']:.1%}")
        
        # 市場別精度
        st.subheader("📈 市場別精度")
        
        market_df = pd.DataFrame(accuracy_stats['by_market'])
        
        if not market_df.empty:
            fig = px.bar(
                market_df,
                x='market',
                y='avg_accuracy',
                color='tc_interpretation',
                title="市場・解釈別の平均精度"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 詳細テーブル
            st.dataframe(market_df, use_container_width=True)
        
        # tc解釈別精度
        st.subheader("🎯 tc解釈別精度")
        
        interpretation_stats = accuracy_stats['by_interpretation']
        
        if interpretation_stats:
            interp_df = pd.DataFrame.from_dict(interpretation_stats, orient='index')
            interp_df.reset_index(inplace=True)
            interp_df.rename(columns={'index': 'tc_interpretation'}, inplace=True)
            
            fig = px.pie(
                interp_df,
                values='total_predictions',
                names='tc_interpretation',
                title="tc解釈別の予測分布"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_data_management(self):
        """データ管理ページ"""
        
        st.title("🗄️ データ管理")
        
        # データベース統計
        stats = self.db.get_database_stats()
        
        st.subheader("📊 データベース統計")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("予測データ", f"{stats['predictions_count']:,}")
        with col2:
            st.metric("市場イベント", f"{stats['market_events_count']:,}")
        with col3:
            st.metric("アラート履歴", f"{stats['alert_history_count']:,}")
        
        # データ範囲
        if stats['data_range']['latest']:
            st.info(f"データ範囲: {stats['data_range']['oldest'][:10]} ～ {stats['data_range']['latest'][:10]}")
        
        # 市場別統計
        if stats['by_market']:
            st.subheader("📈 市場別データ数")
            
            market_df = pd.DataFrame(stats['by_market'])
            
            fig = px.bar(
                market_df,
                x='market',
                y='prediction_count',
                title="市場別予測データ数"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # データ管理操作
        st.subheader("🛠️ データ管理操作")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**データエクスポート**")
            
            export_type = st.selectbox(
                "エクスポートタイプ",
                ["current_risks", "historical_accuracy", "trend_analysis", "search_results"]
            )
            
            export_format = st.selectbox(
                "フォーマット",
                ["json", "csv"]
            )
            
            if st.button("📄 エクスポート実行"):
                try:
                    if export_type == "trend_analysis":
                        filepath = self.db.export_data(
                            QueryType.TREND_ANALYSIS,
                            export_format,
                            market="NASDAQ",
                            window_days=730
                        )
                    else:
                        filepath = self.db.export_data(
                            getattr(QueryType, export_type.upper()),
                            export_format
                        )
                    
                    st.success(f"エクスポート完了: {filepath}")
                    
                    # ダウンロードリンク
                    with open(filepath, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="📁 ダウンロード",
                            data=f.read(),
                            file_name=os.path.basename(filepath),
                            mime="application/json" if export_format == "json" else "text/csv"
                        )
                        
                except Exception as e:
                    st.error(f"エクスポートエラー: {str(e)}")
        
        with col2:
            st.markdown("**データクリーンアップ**")
            
            days_to_keep = st.number_input(
                "保持日数",
                min_value=30,
                max_value=1095,
                value=365,
                step=30
            )
            
            if st.button("🧹 古いデータを削除"):
                try:
                    self.db.cleanup_old_data(days_to_keep)
                    st.success(f"{days_to_keep}日より古いデータを削除しました。")
                    st.experimental_rerun()
                    
                except Exception as e:
                    st.error(f"クリーンアップエラー: {str(e)}")
    
    def run_latest_analysis(self):
        """最新分析の実行"""
        
        # 主要市場の分析を実行
        snapshot = self.monitor.run_full_analysis(parallel=False)
        
        # 結果をデータベースに保存
        for result in snapshot.results:
            from src.data_management.prediction_database import PredictionRecord
            
            record = PredictionRecord(
                market=result.market.value,
                window_days=result.window_days,
                start_date=result.start_date,
                end_date=result.end_date,
                tc=result.tc,
                beta=result.beta,
                omega=result.omega,
                r_squared=result.r_squared,
                rmse=result.rmse,
                predicted_date=result.predicted_date,
                tc_interpretation=result.tc_interpretation.value,
                confidence_score=result.confidence_score
            )
            
            self.db.save_prediction(record)
            
            # 高リスクの場合はアラート生成
            if result.tc < 1.3 and result.confidence_score > 0.7:
                alert_type = "HIGH_RISK" if result.tc < 1.1 else "MEDIUM_RISK"
                self.db.save_alert(
                    alert_type,
                    result.market.value,
                    result.tc,
                    result.predicted_date,
                    result.confidence_score,
                    f"tc={result.tc:.3f}の{result.tc_interpretation.value}リスクを検出"
                )

def main():
    """メイン実行関数"""
    app = DashboardApp()
    app.run()

if __name__ == "__main__":
    main()