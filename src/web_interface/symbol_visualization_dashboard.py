#!/usr/bin/env python3
"""
銘柄別可視化ダッシュボード
各銘柄の最新価格データと予測履歴を表示
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.cm
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple
import sys
import os
try:
    from scipy.optimize import curve_fit
except ImportError:
    curve_fit = None

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# プロジェクトルートを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.results_database import ResultsDatabase
from src.data_sources.unified_data_client import UnifiedDataClient

class SymbolVisualizationDashboard:
    """銘柄別可視化ダッシュボードクラス"""
    
    def __init__(self):
        """初期化"""
        # データベース接続
        self.db_path = "results/analysis_results.db"
        self.db = ResultsDatabase(self.db_path)
        
        # データクライアント
        self.data_client = UnifiedDataClient()
        
        # ページ設定
        st.set_page_config(
            page_title="Symbol Analysis Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def tc_to_datetime_with_hours(self, tc: float, data_end_date: datetime, window_days: int) -> datetime:
        """
        tc値を日時に変換（時間精度まで含む）
        
        Args:
            tc: 正規化されたtc値
            data_end_date: データの最終日（datetime or pandas.Timestamp）
            window_days: データ期間の日数
            
        Returns:
            datetime: 予測日時（時間精度）
        """
        # pandas.Timestampの場合はpython datetimeに変換
        if hasattr(data_end_date, 'to_pydatetime'):
            data_end_date = data_end_date.to_pydatetime()
        if tc > 1.0:
            # データ期間を超えた予測
            days_beyond = (tc - 1.0) * window_days
            days_int = int(days_beyond)
            hours = (days_beyond - days_int) * 24
            return data_end_date + timedelta(days=days_int, hours=hours)
        else:
            # データ期間内の予測
            days_from_start = tc * window_days
            days_int = int(days_from_start)
            hours = (days_from_start - days_int) * 24
            data_start_date = data_end_date - timedelta(days=window_days)
            return data_start_date + timedelta(days=days_int, hours=hours)
    
    def get_symbol_latest_price_data(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        銘柄の最新価格データを取得
        
        Args:
            symbol: 銘柄コード
            days: 取得日数
            
        Returns:
            pd.DataFrame: 価格データ
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # データ取得（銘柄別に適切なソースを指定）
            if symbol == 'NASDAQCOM':
                preferred_source = 'fred'
            elif symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']:
                preferred_source = 'alpha_vantage'
            else:
                preferred_source = None
            data, source = self.data_client.get_data_with_fallback(
                symbol, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                preferred_source=preferred_source
            )
            
            if data is not None and not data.empty:
                return data
            return None
            
        except Exception as e:
            st.error(f"データ取得エラー: {str(e)}")
            return None
    
    def get_prediction_history(self, symbol: str, limit: int = 10) -> pd.DataFrame:
        """
        銘柄の予測履歴を取得
        
        Args:
            symbol: 銘柄コード
            limit: 取得件数
            
        Returns:
            pd.DataFrame: 予測履歴
        """
        try:
            # 最新の分析結果を取得
            analyses = self.db.get_recent_analyses(symbol=symbol, limit=limit)
            
            if analyses.empty:
                return pd.DataFrame()
            
            # 必要な列を抽出（存在確認付き）
            required_columns = [
                'id', 'analysis_date', 'tc', 'beta', 'omega', 'phi', 'A', 'B', 'C',
                'r_squared', 'rmse', 'quality', 'confidence',
                'predicted_crash_date', 'days_to_crash'
            ]
            
            # データ期間関連の列（複数候補）
            date_columns = ['data_period_end', 'data_end', 'end_date', 'analysis_date']
            window_columns = ['window_days', 'data_points', 'period_days']
            
            # 現在利用可能な列をログ出力
            available_cols = list(analyses.columns)
            print(f"利用可能な列: {available_cols}")
            
            # 存在する列のみ選択
            existing_columns = [col for col in required_columns if col in analyses.columns]
            result = analyses[existing_columns].copy()
            
            # データ期間終了日の列を特定
            data_end_col = None
            for col in date_columns:
                if col in analyses.columns:
                    data_end_col = col
                    break
            
            # ウィンドウサイズの列を特定
            window_col = None
            for col in window_columns:
                if col in analyses.columns:
                    window_col = col
                    break
            
            # tc値から時間精度の予測日時を計算（最適化版）
            if data_end_col and window_col:
                # ベクトル化処理で高速化
                def vectorized_tc_to_datetime(tc_series, end_date_series, window_series):
                    result_dates = []
                    for tc, end_date, window in zip(tc_series, end_date_series, window_series):
                        if pd.notna(tc):
                            try:
                                result_dates.append(self.tc_to_datetime_with_hours(tc, pd.to_datetime(end_date), window))
                            except:
                                result_dates.append(None)
                        else:
                            result_dates.append(None)
                    return result_dates
                
                result['predicted_datetime_calculated'] = vectorized_tc_to_datetime(
                    result['tc'], 
                    analyses[data_end_col], 
                    analyses[window_col]
                )
            else:
                # データ期間情報がない場合のフォールバック（最適化版）
                print(f"⚠️  データ期間列が見つかりません。フォールバック処理を実行")
                print(f"   期待する列: {date_columns}")
                print(f"   利用可能な列: {available_cols}")
                
                default_window = 365
                if 'analysis_date' in analyses.columns:
                    def vectorized_tc_to_datetime_fallback(tc_series, analysis_date_series):
                        result_dates = []
                        for tc, analysis_date in zip(tc_series, analysis_date_series):
                            if pd.notna(tc):
                                try:
                                    result_dates.append(self.tc_to_datetime_with_hours(tc, pd.to_datetime(analysis_date), default_window))
                                except:
                                    result_dates.append(None)
                            else:
                                result_dates.append(None)
                        return result_dates
                    
                    result['predicted_datetime_calculated'] = vectorized_tc_to_datetime_fallback(
                        result['tc'], 
                        analyses['analysis_date']
                    )
                else:
                    result['predicted_datetime_calculated'] = None
            
            return result
            
        except Exception as e:
            st.error(f"予測履歴取得エラー: {str(e)}")
            return pd.DataFrame()
    
    def calculate_optimal_display_range(self, 
                                      price_data: pd.DataFrame,
                                      predictions: pd.DataFrame) -> Tuple[datetime, datetime]:
        """
        tc位置を含む最適な表示範囲を計算
        
        Args:
            price_data: 価格データ
            predictions: 予測履歴
            
        Returns:
            Tuple[datetime, datetime]: 表示開始日, 表示終了日
        """
        if price_data.empty:
            return datetime.now() - timedelta(days=365), datetime.now()
        
        start_date = price_data.index.min()
        end_date = price_data.index.max()
        
        # 予測日時が存在する場合、それを含むように範囲を拡張
        if not predictions.empty and 'predicted_datetime_calculated' in predictions.columns:
            valid_predictions = predictions.dropna(subset=['predicted_datetime_calculated'])
            if not valid_predictions.empty:
                pred_dates = valid_predictions['predicted_datetime_calculated']
                earliest_pred = pred_dates.min()
                latest_pred = pred_dates.max()
                
                # 範囲を拡張（予測日時を含むように）
                # Timestamp互換性対応
                if hasattr(earliest_pred, 'to_pydatetime'):
                    earliest_pred = earliest_pred.to_pydatetime()
                if hasattr(latest_pred, 'to_pydatetime'):
                    latest_pred = latest_pred.to_pydatetime()
                
                if earliest_pred < start_date:
                    start_date = earliest_pred - timedelta(days=30)  # 少し余裕を持たせる
                if latest_pred > end_date:
                    end_date = latest_pred + timedelta(days=30)  # 少し余裕を持たせる
        
        return start_date, end_date

    def create_price_chart_with_predictions(self, 
                                          price_data: pd.DataFrame,
                                          predictions: pd.DataFrame,
                                          symbol: str) -> go.Figure:
        """
        価格チャートに予測履歴を重ねて表示
        
        Args:
            price_data: 価格データ
            predictions: 予測履歴
            symbol: 銘柄コード
            
        Returns:
            go.Figure: Plotlyチャート
        """
        fig = go.Figure()
        
        # 価格データをプロット
        fig.add_trace(go.Scatter(
            x=price_data.index,
            y=price_data['Close'],
            mode='lines',
            name='Price',
            line=dict(color='blue', width=2)
        ))
        
        # 予測履歴を時系列でグラデーション色付けして表示
        if not predictions.empty:
            n_predictions = len(predictions)
            colors = plt.cm.Reds(np.linspace(0.3, 1.0, n_predictions))
            
            for idx, (_, pred) in enumerate(predictions.iterrows()):
                if pd.notna(pred.get('predicted_datetime_calculated')):
                    # 予測日時に縦線を追加（Timestamp互換性対応）
                    pred_datetime = pred['predicted_datetime_calculated']
                    # pandas.Timestampの場合はpython datetimeに変換
                    if hasattr(pred_datetime, 'to_pydatetime'):
                        pred_datetime = pred_datetime.to_pydatetime()
                    
                    # 垂直線を描画（注釈なし）
                    fig.add_shape(
                        type="line",
                        x0=pred_datetime,
                        x1=pred_datetime,
                        y0=0,  # y軸の最小値から
                        y1=1,  # y軸の最大値まで（相対座標）
                        yref="paper",  # y軸を相対座標で指定
                        line=dict(
                            color=f'rgba({int(colors[idx][0]*255)}, {int(colors[idx][1]*255)}, {int(colors[idx][2]*255)}, 0.7)',
                            width=2,
                            dash="dash"
                        )
                    )
                    
                    # 凡例用の透明な線を追加（日付を表示）
                    fig.add_trace(go.Scatter(
                        x=[pred_datetime],
                        y=[None],  # 非表示
                        mode='lines',
                        line=dict(
                            color=f'rgba({int(colors[idx][0]*255)}, {int(colors[idx][1]*255)}, {int(colors[idx][2]*255)}, 0.7)',
                            width=2,
                            dash='dash'
                        ),
                        name=f"Crash Prediction: {pred_datetime.strftime('%Y-%m-%d')}",
                        showlegend=True,
                        visible='legendonly'  # 凡例のみ表示
                    ))
        
        # 表示範囲を予測日時を含むように最適化
        display_start, display_end = self.calculate_optimal_display_range(price_data, predictions)
        
        # レイアウト設定
        fig.update_layout(
            title=f"{symbol} - Price History with Crash Predictions",
            xaxis_title="Date",
            yaxis_title="Price",
            height=600,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(
                range=[display_start, display_end]
            ) if display_start and display_end else {}
        )
        
        return fig
    
    def create_prediction_scatter(self, predictions: pd.DataFrame, symbol: str) -> go.Figure:
        """
        予測傾向の散布図を作成
        
        Args:
            predictions: 予測履歴
            symbol: 銘柄コード
            
        Returns:
            go.Figure: Plotly散布図
        """
        fig = go.Figure()
        
        if not predictions.empty:
            # 時系列での色グラデーション
            n_predictions = len(predictions)
            colors = plt.cm.Blues(np.linspace(0.3, 1.0, n_predictions))
            
            # 散布図プロット
            for idx, (_, pred) in enumerate(predictions.iterrows()):
                if pd.notna(pred.get('predicted_datetime_calculated')):
                    # Timestamp互換性対応
                    pred_datetime = pred['predicted_datetime_calculated']
                    if hasattr(pred_datetime, 'to_pydatetime'):
                        pred_datetime = pred_datetime.to_pydatetime()
                    
                    # data_period_endカラムが存在しない場合のフォールバック
                    if 'data_period_end' in pred.index and pd.notna(pred.get('data_period_end')):
                        period_end = pred['data_period_end']
                    else:
                        # フォールバック：analysis_dateを使用
                        period_end = pred.get('analysis_date', datetime.now())
                    
                    if hasattr(period_end, 'to_pydatetime'):
                        period_end = period_end.to_pydatetime()
                    
                    fig.add_trace(go.Scatter(
                        x=[period_end],     # データ期間最終日（横軸）
                        y=[pred_datetime],  # 予測日時（縦軸）
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=f'rgba({int(colors[idx][0]*255)}, {int(colors[idx][1]*255)}, {int(colors[idx][2]*255)}, 0.8)',
                        ),
                        text=f"tc={pred['tc']:.3f}, R²={pred['r_squared']:.3f}",
                        hovertemplate='Data Period End: %{x}<br>Prediction: %{y}<br>%{text}<extra></extra>',
                        showlegend=False,
                        name='Predictions'
                    ))
        
        # フィッティング機能は一時的に無効化（安定性のため）
        
        # レイアウト設定
        fig.update_layout(
            title=f"{symbol} - Prediction Trend Analysis",
            xaxis_title="Analysis Date (Data Period End Date)",    # 解析日（データ期間最終日）
            yaxis_title="Predicted Crash Date",                   # 予測クラッシュ日付
            height=600,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="Black",
                borderwidth=1
            )
        )
        
        return fig
    
    def render_dashboard(self):
        """ダッシュボードのメイン表示"""
        st.title("📊 Symbol-Specific Crash Prediction Dashboard")
        
        # サイドバー設定
        with st.sidebar:
            st.header("🎛️ Controls")
            
            # 銘柄選択
            recent_analyses = self.db.get_recent_analyses(limit=1000)
            if not recent_analyses.empty:
                symbols = sorted(recent_analyses['symbol'].unique().tolist())
                selected_symbol = st.selectbox("Select Symbol", symbols)
                
                # 表示設定
                st.subheader("📊 Display Settings")
                
                # 表示件数
                n_predictions = st.slider(
                    "Number of Predictions to Show",
                    min_value=5,
                    max_value=50,
                    value=10,
                    step=5
                )
                
                # 表示用価格データ期間（フィッティングとは独立）
                price_days = st.selectbox(
                    "Chart Display Period",
                    options=[90, 180, 365, 730],
                    index=2,
                    format_func=lambda x: f"{x} days",
                    help="価格チャートに表示する期間（フィッティング期間とは独立）"
                )
                
                # 予測表示間隔
                # TODO: データ欠損に対するロバスト性を考慮した実装が必要
                # Issue I011: 可視化表示制御のロバスト性
                display_interval = st.selectbox(
                    "Display Interval",
                    options=["All Available", "Weekly", "Bi-weekly", "Monthly"],
                    index=1,  # Weekly を初期状態に
                    help="予測履歴の表示間隔（Weekly = 最新の週次予測のみ表示）"
                )
            else:
                st.warning("No analysis data available")
                return
        
        # メインコンテンツ
        if selected_symbol:
            # 最新価格データを取得
            with st.spinner(f"Loading price data for {selected_symbol}..."):
                price_data = self.get_symbol_latest_price_data(selected_symbol, price_days)
            
            # 予測履歴を取得
            with st.spinner(f"Loading prediction history for {selected_symbol}..."):
                predictions = self.get_prediction_history(selected_symbol, n_predictions)
            
            # タブ作成
            tab1, tab2, tab3 = st.tabs(["📈 Price & Predictions", "📊 Prediction Trend", "📋 Parameters"])
            
            with tab1:
                st.subheader(f"{selected_symbol} - Price History with Predictions")
                
                if price_data is not None and not price_data.empty:
                    # 価格チャート作成
                    price_chart = self.create_price_chart_with_predictions(
                        price_data, predictions, selected_symbol
                    )
                    st.plotly_chart(price_chart, use_container_width=True)
                    
                    # 最新予測情報
                    if not predictions.empty:
                        latest_pred = predictions.iloc[0]
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if pd.notna(latest_pred.get('predicted_datetime_calculated')):
                                crash_date = latest_pred['predicted_datetime_calculated']
                                if hasattr(crash_date, 'to_pydatetime'):
                                    crash_date = crash_date.to_pydatetime()
                                st.metric(
                                    "Predicted Crash Date",
                                    crash_date.strftime('%Y-%m-%d')
                                )
                        
                        with col2:
                            if pd.notna(latest_pred.get('r_squared')):
                                st.metric("Model Fit (R²)", f"{latest_pred['r_squared']:.3f}")
                        
                        with col3:
                            if pd.notna(latest_pred.get('tc')):
                                st.metric("tc Ratio", f"{latest_pred['tc']:.3f}")
                else:
                    st.error(f"No price data available for {selected_symbol}")
            
            with tab2:
                st.subheader(f"{selected_symbol} - Prediction Trend Analysis")
                
                if not predictions.empty:
                    # 散布図作成
                    scatter_chart = self.create_prediction_scatter(predictions, selected_symbol)
                    st.plotly_chart(scatter_chart, use_container_width=True)
                    
                    # チャート説明
                    with st.expander("📊 Chart Explanation"):
                        st.write("""
                        **目的**: クラッシュ予測の時系列パターンを視覚的に分析
                        
                        **軸の説明**:
                        - **横軸**: Analysis Date (Data Period End Date) - フィッティングに使用したデータの最終日
                        - **縦軸**: Predicted Crash Date - LPPLモデルが予測するクラッシュ日付
                        
                        **解釈**:
                        - **点の分布**: 予測の一貫性や変動を示す
                        - **時系列での変化**: 解析日が進むにつれて予測がどう変化するかを表示
                        - **色の変化**: 時系列順序を視覚的に表現
                        """)
                        
                        st.info("💡 予測日のパターンから、市場の不安定性やクラッシュリスクの変化を読み取ることができます。")
                        
                        # データソース情報（デバッグ用）
                        if not predictions.empty:
                            has_data_period_end = 'data_period_end' in predictions.columns
                            data_period_count = predictions['data_period_end'].notna().sum() if has_data_period_end else 0
                            analysis_date_count = predictions['analysis_date'].notna().sum() if 'analysis_date' in predictions.columns else 0
                            
                            st.write(f"**Data Source Info**: ")
                            st.write(f"- data_period_end available: {data_period_count}/{len(predictions)} records")
                            st.write(f"- analysis_date fallback: {analysis_date_count}/{len(predictions)} records")
                            
                            if has_data_period_end and data_period_count > 0:
                                sample_date = predictions['data_period_end'].dropna().iloc[0]
                                st.write(f"- Sample data_period_end: {sample_date}")
                            
                            sample_pred = predictions['predicted_datetime_calculated'].dropna().iloc[0]
                            st.write(f"- Sample predicted crash date: {sample_pred}")
                    
                    # 統計情報（統一フォーマット）
                    st.subheader("📊 Prediction Statistics")
                    
                    # 予測日付の統計（tc値を日付に変換）
                    crash_dates = predictions['predicted_datetime_calculated'].dropna()
                    if not crash_dates.empty:
                        # datetime変換
                        crash_dates_dt = []
                        for date in crash_dates:
                            if hasattr(date, 'to_pydatetime'):
                                crash_dates_dt.append(date.to_pydatetime())
                            else:
                                crash_dates_dt.append(date)
                        
                        # 統計情報計算用の関数
                        def calculate_stats(dates_list, r_squared_values=None):
                            if not dates_list:
                                return None, None, None, None, None
                            
                            # 平均日付
                            avg_timestamp = sum(dt.timestamp() for dt in dates_list) / len(dates_list)
                            avg_date = datetime.fromtimestamp(avg_timestamp)
                            
                            # 日付範囲
                            earliest = min(dates_list)
                            latest = max(dates_list)
                            date_range_days = (latest - earliest).days
                            
                            # R²平均値
                            avg_r2 = r_squared_values.mean() if r_squared_values is not None and not r_squared_values.empty else None
                            
                            return avg_date, date_range_days, earliest, latest, avg_r2
                        
                        # 最新N件のデータ統計
                        st.write(f"**Latest {len(crash_dates_dt)} predictions:**")
                        avg_date, date_range, earliest, latest, avg_r2 = calculate_stats(
                            crash_dates_dt, predictions['r_squared']
                        )
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("Average Date", avg_date.strftime('%Y-%m-%d'))
                        with col2:
                            st.metric("Date Range", f"{date_range} days")
                        with col3:
                            st.metric("Earliest Prediction", earliest.strftime('%Y-%m-%d'))
                        with col4:
                            st.metric("Latest Prediction", latest.strftime('%Y-%m-%d'))
                        with col5:
                            if avg_r2 is not None:
                                st.metric("Average R²", f"{avg_r2:.3f}")
                            else:
                                st.metric("Average R²", "N/A")
                        
                        # 最新1ヶ月のデータ統計
                        one_month_ago = datetime.now() - timedelta(days=30)
                        recent_predictions = predictions[
                            pd.to_datetime(predictions['analysis_date']) >= one_month_ago
                        ] if 'analysis_date' in predictions.columns else pd.DataFrame()
                        
                        if not recent_predictions.empty:
                            st.write(f"**Recent predictions (last 30 days): {len(recent_predictions)} analyses**")
                            recent_crash_dates = recent_predictions['predicted_datetime_calculated'].dropna()
                            
                            if not recent_crash_dates.empty:
                                recent_dates_dt = []
                                for date in recent_crash_dates:
                                    if hasattr(date, 'to_pydatetime'):
                                        recent_dates_dt.append(date.to_pydatetime())
                                    else:
                                        recent_dates_dt.append(date)
                                
                                recent_avg_date, recent_date_range, recent_earliest, recent_latest, recent_avg_r2 = calculate_stats(
                                    recent_dates_dt, recent_predictions['r_squared']
                                )
                                
                                col1, col2, col3, col4, col5 = st.columns(5)
                                with col1:
                                    st.metric("Average Date", recent_avg_date.strftime('%Y-%m-%d'))
                                with col2:
                                    st.metric("Date Range", f"{recent_date_range} days")
                                with col3:
                                    st.metric("Earliest Prediction", recent_earliest.strftime('%Y-%m-%d'))
                                with col4:
                                    st.metric("Latest Prediction", recent_latest.strftime('%Y-%m-%d'))
                                with col5:
                                    if recent_avg_r2 is not None:
                                        st.metric("Average R²", f"{recent_avg_r2:.3f}")
                                    else:
                                        st.metric("Average R²", "N/A")
                        else:
                            st.info("No predictions in the last 30 days")
                else:
                    st.warning(f"No prediction history available for {selected_symbol}")
            
            with tab3:
                st.subheader(f"{selected_symbol} - Parameter Details")
                
                if not predictions.empty:
                    # パラメータテーブル用のデータフレーム作成
                    display_df = predictions.copy()
                    
                    # 予測クラッシュ日付列を追加
                    if 'predicted_datetime_calculated' in display_df.columns:
                        display_df['predicted_crash_date'] = display_df['predicted_datetime_calculated'].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notna(x) else 'N/A'
                        )
                    else:
                        display_df['predicted_crash_date'] = 'N/A'
                    
                    # データ期間情報を整理（安全な処理）
                    if 'data_period_start' in display_df.columns and 'data_period_end' in display_df.columns:
                        def format_data_period(row):
                            try:
                                start_date = row['data_period_start']
                                end_date = row['data_period_end']
                                
                                if pd.notna(start_date) and pd.notna(end_date):
                                    # 既に日付文字列の場合とdatetimeオブジェクトの場合を処理
                                    if isinstance(start_date, str):
                                        start_str = start_date
                                    else:
                                        start_str = pd.to_datetime(start_date).strftime('%Y-%m-%d')
                                    
                                    if isinstance(end_date, str):
                                        end_str = end_date
                                    else:
                                        end_str = pd.to_datetime(end_date).strftime('%Y-%m-%d')
                                    
                                    return f"{start_str} to {end_str}"
                                else:
                                    return 'N/A'
                            except Exception as e:
                                print(f"Data period formatting error: {e}")
                                return 'N/A'
                        
                        display_df['data_period'] = display_df.apply(format_data_period, axis=1)
                        
                        # 個別カラムも追加（最適化版）
                        def format_date_safe(date_val):
                            try:
                                if pd.notna(date_val):
                                    if isinstance(date_val, str):
                                        return date_val
                                    else:
                                        return pd.to_datetime(date_val).strftime('%Y-%m-%d')
                                else:
                                    return 'N/A'
                            except:
                                return 'N/A'
                        
                        display_df['data_start'] = [format_date_safe(x) for x in display_df['data_period_start']]
                        display_df['data_end'] = [format_date_safe(x) for x in display_df['data_period_end']]
                        display_df['period_days'] = [f"{x} days" if pd.notna(x) else 'N/A' for x in display_df['window_days']]
                    else:
                        display_df['data_period'] = 'N/A'
                        display_df['data_start'] = 'N/A'
                        display_df['data_end'] = 'N/A'
                        display_df['period_days'] = 'N/A'
                    
                    # 重要な列順序で表示
                    priority_columns = [
                        'predicted_crash_date',    # 最重要：予測クラッシュ日付
                        'r_squared',               # 2番目：モデル適合度
                        'confidence',              # 3番目：信頼度
                        'data_start',              # 4番目：データ開始日
                        'data_end',                # 5番目：データ終了日
                        'period_days',             # 6番目：期間日数
                        'tc',                      # 7番目：tc比率値（参考）
                        'beta', 'omega', 'phi',    # その他のLPPLパラメータ
                        'A', 'B', 'C',
                        'rmse', 'quality'
                    ]
                    
                    # 存在する列のみ選択
                    existing_display_cols = [col for col in priority_columns if col in display_df.columns]
                    final_df = display_df[existing_display_cols].copy()
                    
                    # 最新データ期間でソート
                    if 'data_period_end' in predictions.columns:
                        final_df = final_df.loc[predictions.sort_values('data_period_end', ascending=False).index]
                    
                    # 数値の丸め処理
                    numeric_columns = ['r_squared', 'confidence', 'tc', 'beta', 'omega', 'phi', 'A', 'B', 'C', 'rmse']
                    for col in numeric_columns:
                        if col in final_df.columns:
                            final_df[col] = final_df[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else 'N/A')
                    
                    st.dataframe(
                        final_df,
                        use_container_width=True,
                        height=400,
                        column_config={
                            "predicted_crash_date": st.column_config.TextColumn(
                                "🎯 Predicted Crash Date",
                                help="Predicted crash date converted from tc ratio",
                            ),
                            "r_squared": st.column_config.TextColumn(
                                "📊 R² Score",
                                help="Model fit quality (higher is better)",
                            ),
                            "confidence": st.column_config.TextColumn(
                                "✅ Confidence",
                                help="Prediction confidence level",
                            ),
                            "data_start": st.column_config.TextColumn(
                                "📅 Data Start",
                                help="Start date of fitting period",
                            ),
                            "data_end": st.column_config.TextColumn(
                                "📅 Data End", 
                                help="End date of fitting period",
                            ),
                            "period_days": st.column_config.TextColumn(
                                "📊 Period Days",
                                help="Length of fitting period in days",
                            ),
                            "tc": st.column_config.TextColumn(
                                "🔢 tc Ratio",
                                help="Critical time ratio (reference)",
                            ),
                        }
                    )
                    
                    # ダウンロードボタン
                    csv = final_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Parameter History",
                        data=csv,
                        file_name=f"{selected_symbol}_parameters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(f"No parameter data available for {selected_symbol}")

def main():
    """メイン関数"""
    dashboard = SymbolVisualizationDashboard()
    dashboard.render_dashboard()

if __name__ == "__main__":
    main()