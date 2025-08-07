#!/usr/bin/env python3
"""
Symbol-Based Market Analysis Dashboard

Restored implementation with symbol selection sidebar and category-based classification.
Displays analysis results for selected symbols in 3 tabs with trading position prioritization.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# .envファイル自動読み込み（ダッシュボード用）
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print("✅ ダッシュボード: .env ファイル読み込み完了")
    else:
        print("⚠️ ダッシュボード: .env ファイルが見つかりません")
except ImportError:
    print("⚠️ ダッシュボード: python-dotenv がインストールされていません")

from infrastructure.database.results_database import ResultsDatabase
from infrastructure.data_sources.unified_data_client import UnifiedDataClient

class SymbolAnalysisDashboard:
    """Symbol-Based Analysis Dashboard"""
    
    def __init__(self):
        self.db = ResultsDatabase()
        self.market_catalog = self.load_market_catalog()
        self.data_client = UnifiedDataClient()
        
        # Page configuration
        st.set_page_config(
            page_title="Symbol Analysis Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def load_market_catalog(self) -> Dict:
        """Load market catalog for symbol categorization"""
        try:
            catalog_path = "infrastructure/data_sources/market_data_catalog.json"
            with open(catalog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load market catalog: {str(e)}")
            return {"symbols": {}}
    
    def get_symbols_by_category(self) -> Dict[str, List[Dict]]:
        """Organize symbols by asset class and instrument type"""
        categorized = {}
        
        if not self.market_catalog.get("symbols"):
            return categorized
        
        for symbol, info in self.market_catalog["symbols"].items():
            asset_class = info.get("asset_class", "unknown")
            instrument_type = info.get("instrument_type", "unknown")
            
            # Create category key
            category_key = f"{asset_class}_{instrument_type}"
            
            if category_key not in categorized:
                categorized[category_key] = {
                    "display_name": f"{asset_class.title()} - {instrument_type}",
                    "symbols": []
                }
            
            categorized[category_key]["symbols"].append({
                "symbol": symbol,
                "display_name": info.get("display_name", symbol),
                "description": info.get("description", ""),
                "bubble_analysis_suitability": info.get("bubble_analysis_suitability", "unknown")
            })
        
        return categorized
    
    # DEPRECATED: tc値からの日時変換はデータベース保存時に実行済みのため不要
    # 将来的に必要になる場合に備えて保持（コメントアウト）
    # def tc_to_datetime_with_hours(self, tc: float, data_end_date: datetime, window_days: int) -> datetime:
    #     """
    #     tc値を日時に変換（時間精度まで含む）
    #     NOTE: この機能はintegration_helpers.pyで実行済みのため現在は不要
    #     """
    #     # pandas.Timestampの場合はpython datetimeに変換
    #     if hasattr(data_end_date, 'to_pydatetime'):
    #         data_end_date = data_end_date.to_pydatetime()
    #     
    #     if tc > 1.0:
    #         # データ期間を超えた予測
    #         days_beyond = (tc - 1.0) * window_days
    #         days_int = int(days_beyond)
    #         hours = (days_beyond - days_int) * 24
    #         return data_end_date + timedelta(days=days_int, hours=hours)
    #     else:
    #         # データ期間内の予測
    #         days_from_start = tc * window_days
    #         days_int = int(days_from_start)
    #         hours = (days_from_start - days_int) * 24
    #         data_start_date = data_end_date - timedelta(days=window_days)
    #         return data_start_date + timedelta(days=days_int, hours=hours)
    
    def calculate_trading_priority_score(self, predicted_crash_date: datetime) -> float:
        """
        予測クラッシュ日時に基づいてトレード優先度を計算
        
        Args:
            predicted_crash_date: 予測されたクラッシュ日時
            
        Returns:
            float: 優先度スコア（高いほど緊急）
        """
        try:
            if pd.isna(predicted_crash_date):
                return 0.0
            
            now = datetime.now()
            days_to_crash = (predicted_crash_date - now).days
            
            # 日数に基づく優先度スコア
            if days_to_crash <= 0:
                return 100  # 既に過ぎている場合は最高優先度
            elif days_to_crash <= 30:
                return 90   # 1ヶ月以内
            elif days_to_crash <= 90:
                return 70   # 3ヶ月以内
            elif days_to_crash <= 180:
                return 50   # 6ヶ月以内
            elif days_to_crash <= 365:
                return 30   # 1年以内
            else:
                return 10   # 1年以上先
                
        except Exception:
            return 0.0
    
    def get_symbol_analysis_data(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        """Get analysis data for specific symbol with predicted crash dates"""
        try:
            analyses = self.db.get_recent_analyses(symbol=symbol, limit=limit)
            
            if analyses.empty:
                return pd.DataFrame()
            
            # Use database-stored predicted crash dates (no recalculation needed)
            # Convert string dates to datetime objects for processing
            if 'predicted_crash_date' in analyses.columns:
                analyses['predicted_crash_date'] = pd.to_datetime(analyses['predicted_crash_date'], errors='coerce')
            else:
                # Fallback: if column missing, create empty datetime column
                analyses['predicted_crash_date'] = pd.NaT
            
            # Calculate trading priority scores based on predicted dates
            analyses['trading_priority'] = analyses['predicted_crash_date'].apply(
                self.calculate_trading_priority_score
            )
            
            # Sort by trading priority (highest first)
            analyses = analyses.sort_values('trading_priority', ascending=False)
            
            return analyses
            
        except Exception as e:
            st.error(f"Error retrieving analysis data: {str(e)}")
            return pd.DataFrame()
    
    def render_sidebar(self):
        """Render symbol selection sidebar with categorization"""
        
        with st.sidebar:
            st.title("🎛️ Symbol Selection")
            
            # Get available symbols from database
            try:
                all_analyses = self.db.get_recent_analyses(limit=1000)
                if all_analyses.empty:
                    st.warning("No analysis data available")
                    return None
                
                available_symbols = sorted(all_analyses['symbol'].unique().tolist())
            except Exception:
                st.error("Failed to load analysis data")
                return None
            
            # Get categorized symbols
            categorized_symbols = self.get_symbols_by_category()
            
            # Symbol selection with categories
            st.subheader("📈 Select Symbol by Category")
            
            # Create category options
            category_options = ["All Symbols"] + list(categorized_symbols.keys())
            selected_category = st.selectbox(
                "Asset Category",
                category_options,
                format_func=lambda x: "All Symbols" if x == "All Symbols" 
                else categorized_symbols[x]["display_name"] if x in categorized_symbols 
                else x
            )
            
            # Filter symbols based on category
            if selected_category == "All Symbols":
                symbol_options = available_symbols
            else:
                category_symbols = [
                    s["symbol"] for s in categorized_symbols.get(selected_category, {}).get("symbols", [])
                ]
                symbol_options = [s for s in available_symbols if s in category_symbols]
            
            if not symbol_options:
                st.warning("No symbols available in selected category")
                return None
            
            # Symbol selection
            selected_symbol = st.selectbox(
                "Symbol",
                symbol_options,
                format_func=lambda x: f"{x} - {self.market_catalog.get('symbols', {}).get(x, {}).get('display_name', x)}"
            )
            
            # Display symbol info
            if selected_symbol in self.market_catalog.get("symbols", {}):
                symbol_info = self.market_catalog["symbols"][selected_symbol]
                
                st.subheader("📊 Symbol Information")
                st.info(f"**{symbol_info.get('display_name', selected_symbol)}**")
                st.write(f"**Type**: {symbol_info.get('instrument_type', 'Unknown')}")
                st.write(f"**Asset Class**: {symbol_info.get('asset_class', 'Unknown')}")
                st.write(f"**Analysis Suitability**: {symbol_info.get('bubble_analysis_suitability', 'Unknown')}")
                
                if symbol_info.get('description'):
                    with st.expander("ℹ️ Description"):
                        st.write(symbol_info['description'])
            
            # Display settings
            st.subheader("⚙️ Display Settings")
            
            # Number of results
            n_results = st.slider(
                "Number of Results",
                min_value=10,
                max_value=100,
                value=30,
                step=10
            )
            
            # Priority filtering
            priority_filter = st.selectbox(
                "Priority Filter",
                ["All", "High Priority (≤90 days)", "Medium Priority (≤180 days)", "Critical Only (≤30 days)"],
                index=0
            )
            
            return selected_symbol, n_results, priority_filter
    
    def get_symbol_price_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Get symbol price data from unified data client"""
        try:
            # データベースから最新の分析結果を取得してデータソースを特定
            latest_analysis = self.db.get_recent_analyses(symbol=symbol, limit=1)
            preferred_source = None
            if not latest_analysis.empty:
                data_source = latest_analysis.iloc[0].get('data_source')
                if data_source:
                    preferred_source = 'fred' if data_source == 'fred' else 'alpha_vantage'
            
            # 統合データクライアントからフォールバック付きでデータ取得
            data, source_used = self.data_client.get_data_with_fallback(
                symbol, start_date, end_date, preferred_source=preferred_source
            )
            
            if data is not None and len(data) > 0:
                print(f"✅ ダッシュボード用データ取得成功: {symbol} ({source_used}) - {len(data)}日分")
                return data
            else:
                print(f"❌ データ取得失敗: {symbol}")
                return None
            
        except Exception as e:
            st.error(f"データ取得エラー: {str(e)}")
            return None
    
    def compute_lppl_fit(self, prices: pd.Series, params: Dict) -> Dict:
        """Compute LPPL model fit and normalized data for visualization"""
        try:
            # 価格を対数変換
            log_prices = np.log(prices)
            N = len(prices)
            
            # 時間配列を正規化（0-1）
            t = np.linspace(0, 1, N)
            
            # LPPLパラメータ
            tc = params['tc']
            beta = params['beta'] 
            omega = params['omega']
            phi = params['phi']
            A = params['A']
            B = params['B']
            C = params['C']
            
            # LPPL関数の計算
            # log(p(t)) = A + B*(tc-t)^β + C*(tc-t)^β * cos(ω*ln(tc-t) + φ)
            tau = tc - t
            tau_power_beta = np.power(np.abs(tau), beta)
            
            # 負の値を避けるために絶対値を使用
            with np.errstate(divide='ignore', invalid='ignore'):
                log_term = np.log(np.abs(tau))
                oscillation = np.cos(omega * log_term + phi)
                
            fitted_log_prices = A + B * tau_power_beta + C * tau_power_beta * oscillation
            fitted_prices = np.exp(fitted_log_prices)
            
            # 正規化データの計算（論文再現テストの右上グラフ相当）
            # 価格データを0-1に正規化
            price_min, price_max = prices.min(), prices.max()
            normalized_prices = (prices - price_min) / (price_max - price_min)
            normalized_fitted = (fitted_prices - price_min) / (price_max - price_min)
            
            return {
                'fitted_prices': fitted_prices,
                'fitted_log_prices': fitted_log_prices,
                'normalized_prices': normalized_prices,
                'normalized_fitted': normalized_fitted,
                'time_normalized': t
            }
            
        except Exception as e:
            st.error(f"LPPL計算エラー: {str(e)}")
            return None
    
    def convert_tc_to_real_date(self, tc: float, data_start_date: str, data_end_date: str) -> datetime:
        """Convert tc value to actual prediction date"""
        try:
            start_dt = pd.to_datetime(data_start_date)
            end_dt = pd.to_datetime(data_end_date)
            
            # データ期間の日数を計算
            total_days = (end_dt - start_dt).days
            
            # tc値を実際の日付に変換
            # tc > 1の場合は未来の日付
            if tc > 1:
                days_beyond_end = (tc - 1) * total_days
                prediction_date = end_dt + timedelta(days=days_beyond_end)
            else:
                # tc < 1の場合はデータ期間内
                days_from_start = tc * total_days
                prediction_date = start_dt + timedelta(days=days_from_start)
            
            return prediction_date
            
        except Exception as e:
            st.error(f"日付変換エラー: {str(e)}")
            return datetime.now() + timedelta(days=30)  # フォールバック
    
    def render_price_predictions_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 1: Price Chart with Crash Prediction Lines (論文再現テスト右上グラフ相当)"""
        
        st.header(f"📈 {symbol} - Market Data with LPPL Predictions")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        # 最新の分析データを取得
        latest = analysis_data.iloc[0]
        
        # メトリクス表示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 最新の予測クラッシュ日を表示（tc値から変換）
            if pd.notna(latest.get('tc')):
                tc = latest['tc']
                data_start = latest.get('data_period_start')
                data_end = latest.get('data_period_end')
                
                if data_start and data_end:
                    pred_date = self.convert_tc_to_real_date(tc, data_start, data_end)
                    st.metric(
                        "Latest Crash Prediction",
                        pred_date.strftime('%Y-%m-%d'),
                        help=f"Converted from tc={tc:.4f}"
                    )
                else:
                    st.metric("Latest Crash Prediction", "N/A")
            else:
                st.metric("Latest Crash Prediction", "N/A")
        
        with col2:
            st.metric(
                "Model Fit (R²)",
                f"{latest['r_squared']:.4f}" if pd.notna(latest.get('r_squared')) else "N/A",
                help="Goodness of fit for LPPL model"
            )
        
        with col3:
            st.metric(
                "Quality",
                latest.get('quality', 'N/A'),
                help="Analysis quality assessment"
            )
        
        # 最新のフィッティングデータを使って生データを取得
        if pd.notna(latest.get('data_period_start')) and pd.notna(latest.get('data_period_end')):
            data_start = latest['data_period_start']
            data_end = latest['data_period_end']
            
            print(f"🔍 Getting price data for {symbol}: {data_start} to {data_end}")
            
            # 実際の価格データを取得
            price_data = self.get_symbol_price_data(symbol, data_start, data_end)
            
            if price_data is not None and not price_data.empty and 'Close' in price_data.columns:
                print(f"✅ Price data retrieved successfully: {len(price_data)} days for {symbol}")
                print(f"   Period: {price_data.index.min()} to {price_data.index.max()}")
                print(f"   Price range: ${price_data['Close'].min():.0f} - ${price_data['Close'].max():.0f}")
                # LPPLパラメータを抽出
                lppl_params = {
                    'tc': latest.get('tc', 1.0),
                    'beta': latest.get('beta', 0.33),
                    'omega': latest.get('omega', 6.0),
                    'phi': latest.get('phi', 0.0),
                    'A': latest.get('A', 0.0),
                    'B': latest.get('B', 0.0),
                    'C': latest.get('C', 0.0)
                }
                
                # LPPLフィッティングを計算
                lppl_results = self.compute_lppl_fit(price_data['Close'], lppl_params)
                
                if lppl_results:
                    # 論文再現テスト右上グラフに相当する正規化表示を作成
                    fig = go.Figure()
                    
                    # 正規化された実データ
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=lppl_results['normalized_prices'],
                        mode='lines',
                        name='Normalized Market Data',
                        line=dict(color='blue', width=2),
                        opacity=0.8
                    ))
                    
                    # 正規化されたLPPLフィット
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=lppl_results['normalized_fitted'],
                        mode='lines',
                        name='LPPL Fit (Normalized)',
                        line=dict(color='red', width=2.5)
                    ))
                    
                    # Number of Results で指定された数の予測線を縦線で表示
                    display_count = min(len(analysis_data), 10)  # Number of Results の値を使用
                    
                    for i, (_, pred) in enumerate(analysis_data.head(display_count).iterrows()):
                        if pd.notna(pred.get('tc')):
                            pred_tc = pred['tc']
                            pred_start = pred.get('data_period_start', data_start)
                            pred_end = pred.get('data_period_end', data_end)
                            
                            if pred_start and pred_end:
                                pred_date = self.convert_tc_to_real_date(pred_tc, pred_start, pred_end)
                                
                                # 未来の日付の場合、グラフを適切にスケールするため範囲を拡張
                                max_date = max(price_data.index.max(), pred_date)
                                
                                # 予測線を縦線で表示
                                color_intensity = max(50, 255 - i * 20)  # 色の濃度を調整
                                fig.add_shape(
                                    type="line",
                                    x0=pred_date,
                                    x1=pred_date,
                                    y0=0,
                                    y1=1,
                                    line=dict(
                                        color=f'rgba(255, {color_intensity//2}, {color_intensity//2}, 0.7)', 
                                        width=2, 
                                        dash="dash"
                                    )
                                )
                                
                                # 予測線のラベル
                                fig.add_annotation(
                                    x=pred_date,
                                    y=0.95 - i * 0.05,
                                    text=f"tc={pred_tc:.3f}",
                                    showarrow=False,
                                    font=dict(size=10, color=f'rgba(255, {color_intensity//2}, {color_intensity//2}, 0.8)'),
                                    bgcolor="rgba(255,255,255,0.7)"
                                )
                    
                    # グラフのレイアウト設定
                    fig.update_layout(
                        title=f"{symbol} - Normalized Price Data with LPPL Predictions",
                        xaxis_title="Date",
                        yaxis_title="Normalized Price",
                        height=600,
                        hovermode='x unified',
                        showlegend=True,
                        # x軸の範囲を予測線まで拡張
                        xaxis=dict(range=[
                            price_data.index.min(),
                            max(price_data.index.max(), 
                                max([self.convert_tc_to_real_date(row.get('tc', 1.0), 
                                                                 row.get('data_period_start', data_start),
                                                                 row.get('data_period_end', data_end)) 
                                     for _, row in analysis_data.head(display_count).iterrows() 
                                     if pd.notna(row.get('tc'))], default=price_data.index.max()))
                        ])
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 予測サマリーを表示
                    st.subheader("🔮 Prediction Summary")
                    
                    valid_predictions = analysis_data.head(display_count)
                    for i, (_, pred) in enumerate(valid_predictions.iterrows()):
                        if pd.notna(pred.get('tc')):
                            pred_tc = pred['tc']
                            pred_start = pred.get('data_period_start', data_start)
                            pred_end = pred.get('data_period_end', data_end)
                            
                            if pred_start and pred_end:
                                pred_date = self.convert_tc_to_real_date(pred_tc, pred_start, pred_end)
                                days_to_crash = (pred_date - datetime.now()).days
                                
                                st.markdown(
                                    f"**Prediction {i+1}:** {pred_date.strftime('%Y-%m-%d')} "
                                    f"({days_to_crash:+d} days) - "
                                    f"R²: {pred.get('r_squared', 0):.4f} - "
                                    f"tc: {pred_tc:.4f}"
                                )
                else:
                    st.error("LPPL フィッティング計算に失敗しました")
            else:
                # より詳細なエラー情報を表示
                if price_data is None:
                    st.error(f"❌ データ取得失敗: {symbol} のデータを取得できませんでした")
                    st.info(f"期間: {data_start} から {data_end}")
                    st.info("UnifiedDataClientの初期化またはAPI認証に問題がある可能性があります")
                elif price_data.empty:
                    st.warning(f"⚠️ データが空です: {symbol} の指定期間にデータがありません")
                    st.info(f"期間: {data_start} から {data_end}")
                elif 'Close' not in price_data.columns:
                    st.warning(f"⚠️ 価格列が見つかりません: {symbol} データに'Close'列がありません")
                    st.info(f"利用可能な列: {list(price_data.columns)}")
                else:
                    st.warning("❓ 不明なデータ問題が発生しました")
                    
                # データベース情報も表示
                st.subheader("📊 データベース情報")
                st.json({
                    "Symbol": symbol,
                    "Data Source": latest.get('data_source', 'N/A'),
                    "Period Start": data_start,
                    "Period End": data_end,
                    "Data Points": latest.get('data_points', 'N/A'),
                    "Analysis Basis Date": latest.get('analysis_basis_date', 'N/A')
                })
        else:
            st.error("❌ データ期間情報が不完全です")
            st.info("data_period_start または data_period_end がデータベースに保存されていません")
            st.subheader("📊 利用可能なデータベース情報")
            
            # デバッグ情報表示
            debug_info = {}
            for col in ['data_period_start', 'data_period_end', 'data_source', 'analysis_basis_date', 'data_points']:
                val = latest.get(col)
                debug_info[col] = str(val) if val is not None else "None"
            
            st.json(debug_info)
    
    def render_prediction_convergence_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 2: Prediction Convergence Analysis"""
        
        st.header(f"🎯 {symbol} - Prediction Convergence Analysis")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        valid_data = analysis_data.dropna(subset=['predicted_crash_date'])
        
        if valid_data.empty:
            st.warning("No valid prediction data available")
            return
        
        # Main scatter plot: Analysis date vs Predicted crash date
        st.subheader("📊 Crash Prediction Convergence")
        
        fig = go.Figure()
        
        # Prepare data for plotting
        plot_data = valid_data.copy()
        
        # Get data period end dates
        data_period_end_dates = []
        for _, row in plot_data.iterrows():
            for col in ['data_period_end', 'data_end', 'end_date', 'analysis_date']:
                if col in plot_data.columns and pd.notna(row.get(col)):
                    data_period_end_dates.append(pd.to_datetime(row[col]))
                    break
            else:
                data_period_end_dates.append(pd.to_datetime(row.get('analysis_date', datetime.now())))
        
        plot_data['data_period_end'] = data_period_end_dates
        
        # Convert predicted crash dates
        crash_dates = []
        for date in plot_data['predicted_crash_date']:
            if hasattr(date, 'to_pydatetime'):
                crash_dates.append(date.to_pydatetime())
            else:
                crash_dates.append(date)
        plot_data['crash_date_converted'] = crash_dates
        
        # Color by R² score
        fig.add_trace(go.Scatter(
            x=plot_data['data_period_end'],
            y=plot_data['crash_date_converted'],
            mode='markers',
            marker=dict(
                size=10,
                color=plot_data['r_squared'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="R² Score")
            ),
            text=[f"tc: {row['tc']:.3f}<br>R²: {row['r_squared']:.3f}<br>Quality: {row['quality']}" 
                  for _, row in plot_data.iterrows()],
            hovertemplate='Analysis Date: %{x}<br>Predicted Crash: %{y}<br>%{text}<extra></extra>',
            name='Predictions'
        ))
        
        fig.update_layout(
            title=f"{symbol} - Prediction Convergence Analysis",
            xaxis_title="Analysis Date (Data Period End)",
            yaxis_title="Predicted Crash Date",
            height=600,
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Analysis explanation
        with st.expander("📊 Chart Explanation"):
            st.markdown("""
            **Purpose**: Analyze whether crash predictions are converging to a specific date
            
            **Interpretation**:
            - **Horizontal axis**: Date when analysis was performed (data period end date)
            - **Vertical axis**: Predicted crash date from that analysis
            - **Color intensity**: R² score (darker = better fit)
            
            **Convergence patterns**:
            - **Converging predictions**: Points form a horizontal line → consistent crash date
            - **Diverging predictions**: Points spread vertically → unstable predictions
            - **Trend analysis**: Look for patterns as analysis dates progress
            """)
        
        # Statistics
        st.subheader("📈 Convergence Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_date = pd.Timestamp(np.mean([d.timestamp() for d in crash_dates]), unit='s')
            st.metric("Average Crash Date", avg_date.strftime('%Y-%m-%d'))
        
        with col2:
            date_range = (max(crash_dates) - min(crash_dates)).days
            st.metric("Date Range", f"{date_range} days")
        
        with col3:
            avg_r2 = plot_data['r_squared'].mean()
            st.metric("Average R²", f"{avg_r2:.3f}")
        
        with col4:
            high_quality_count = len(plot_data[plot_data['quality'] == 'high_quality'])
            st.metric("High Quality", f"{high_quality_count}/{len(plot_data)}")
    
    def render_parameters_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 3: Parameter Details Table"""
        
        st.header(f"📋 {symbol} - Parameter Details")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        # Prepare detailed parameter table
        display_df = analysis_data.copy()
        
        # Add formatted predicted crash date
        if 'predicted_crash_date' in display_df.columns:
            display_df['predicted_crash_date_formatted'] = display_df['predicted_crash_date'].apply(
                lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notna(x) else 'N/A'
            )
        else:
            display_df['predicted_crash_date_formatted'] = 'N/A'
        
        # Add fitting basis date (フィッティング基準日) - most important date
        if 'analysis_basis_date' in display_df.columns:
            display_df['fitting_basis_date_formatted'] = display_df['analysis_basis_date'].apply(
                lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else 'N/A'
            )
        elif 'data_period_end' in display_df.columns:
            # Fallback to data period end
            display_df['fitting_basis_date_formatted'] = display_df['data_period_end'].apply(
                lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else 'N/A'
            )
        else:
            display_df['fitting_basis_date_formatted'] = 'N/A'
        
        # Calculate data period (number of days used for fitting)
        data_period_days = []
        for _, row in display_df.iterrows():
            try:
                # Priority 1: Use window_days if available
                if 'window_days' in display_df.columns and pd.notna(row.get('window_days')):
                    days = int(row['window_days'])
                    data_period_days.append(f"{days} days")
                # Priority 2: Calculate from start and end dates
                elif ('data_period_start' in display_df.columns and 'data_period_end' in display_df.columns and
                      pd.notna(row.get('data_period_start')) and pd.notna(row.get('data_period_end'))):
                    start_dt = pd.to_datetime(row['data_period_start'])
                    end_dt = pd.to_datetime(row['data_period_end'])
                    days = (end_dt - start_dt).days + 1  # +1 to include both start and end
                    data_period_days.append(f"{days} days")
                # Priority 3: Use data_points as fallback
                elif 'data_points' in display_df.columns and pd.notna(row.get('data_points')):
                    points = int(row['data_points'])
                    data_period_days.append(f"{points} days")
                else:
                    data_period_days.append('N/A')
                    
            except Exception:
                data_period_days.append('N/A')
        
        display_df['data_period_days'] = data_period_days
        
        # Define column priority for display (left to right)
        priority_columns = [
            'predicted_crash_date_formatted',  # Most important
            'fitting_basis_date_formatted',    # フィッティング基準日 (replaces analysis_date)
            'data_period_days',                # Number of days (replaces data_period)
            'r_squared',
            'quality',                         # Quality and Confidence together
            'confidence',
            'tc',
            'beta', 'omega', 'phi',
            'A', 'B', 'C',
            'rmse'
        ]
        
        # Select existing columns in priority order
        existing_columns = [col for col in priority_columns if col in display_df.columns]
        
        final_df = display_df[existing_columns].copy()
        
        # Sort by fitting basis date (most recent first - analysis_basis_date)
        sort_col = None
        if 'analysis_basis_date' in analysis_data.columns:
            sort_col = 'analysis_basis_date'
        elif 'data_period_end' in analysis_data.columns:
            sort_col = 'data_period_end'
        elif 'predicted_crash_date' in analysis_data.columns:
            sort_col = 'predicted_crash_date'
        
        if sort_col:
            final_df = final_df.loc[analysis_data.sort_values(sort_col, na_position='last', ascending=False).index]
        
        # Format numeric columns
        numeric_columns = ['r_squared', 'confidence', 'tc', 'beta', 'omega', 'phi', 'A', 'B', 'C', 'rmse']
        for col in numeric_columns:
            if col in final_df.columns:
                final_df[col] = final_df[col].apply(
                    lambda x: f"{x:.4f}" if pd.notna(x) else 'N/A'
                )
        
        # Display the table
        st.subheader("📊 Analysis Results (sorted by fitting basis date)")
        
        st.dataframe(
            final_df,
            use_container_width=True,
            height=400,
            column_config={
                "predicted_crash_date_formatted": st.column_config.TextColumn(
                    "🎯 Predicted Crash Date",
                    help="Predicted crash date/time converted from tc ratio",
                    width="large"
                ),
                "fitting_basis_date_formatted": st.column_config.TextColumn(
                    "📅 Fitting Basis Date",
                    help="フィッティング基準日 - Final day of fitting period (most important for sorting)",
                    width="medium"
                ),
                "data_period_days": st.column_config.TextColumn(
                    "📊 Data Period",
                    help="Number of days used for fitting analysis",
                    width="small"
                ),
                "r_squared": st.column_config.TextColumn(
                    "📊 R² Score",
                    help="Model fit quality (higher = better, 0-1 scale)"
                ),
                "quality": st.column_config.TextColumn(
                    "🎯 Quality",
                    help="Analysis quality assessment (high_quality/acceptable/poor)"
                ),
                "confidence": st.column_config.TextColumn(
                    "✅ Confidence",
                    help="Prediction confidence level (0-1 scale, similar to Quality)"
                ),
                "tc": st.column_config.TextColumn(
                    "🔢 tc Ratio",
                    help="Critical time ratio used for crash prediction"
                )
            }
        )
        
        # Explanatory text for Quality and Confidence metrics
        st.subheader("📖 Metric Definitions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🎯 Quality Assessment:**
            - `high_quality`: R² > 0.85, stable parameters
            - `acceptable`: R² > 0.60, reasonable fit  
            - `poor`: R² < 0.60, unstable fitting
            
            Quality is determined by statistical criteria including R² score, parameter stability, and fitting convergence.
            """)
        
        with col2:
            st.markdown("""
            **✅ Confidence Level:**
            - Range: 0.0 - 1.0 (higher = more confident)
            - Based on: fitting quality, parameter consistency
            - Similar to Quality but expressed as continuous value
            
            Confidence represents the overall reliability of the LPPL model prediction for this analysis.
            """)
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_r2 = analysis_data['r_squared'].mean()
            st.metric("Average R²", f"{avg_r2:.3f}" if pd.notna(avg_r2) else "N/A")
        
        with col2:
            high_quality_count = len(analysis_data[analysis_data['quality'] == 'high_quality'])
            st.metric("High Quality", f"{high_quality_count}/{len(analysis_data)}")
        
        with col3:
            valid_predictions = len(analysis_data.dropna(subset=['predicted_crash_date']))
            st.metric("Valid Predictions", f"{valid_predictions}/{len(analysis_data)}")
        
        with col4:
            if 'predicted_crash_date' in analysis_data.columns:
                future_predictions = len(analysis_data[
                    analysis_data['predicted_crash_date'] > datetime.now()
                ])
                st.metric("Future Predictions", future_predictions)
        
        # Download functionality
        csv = final_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Parameter Data",
            data=csv,
            file_name=f"{symbol}_parameters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    def run(self):
        """Main dashboard execution"""
        
        st.title("📊 LPPL Market Analysis Dashboard")
        st.markdown("*Symbol-based analysis with trading position prioritization*")
        
        # Render sidebar and get selections
        sidebar_result = self.render_sidebar()
        
        if sidebar_result is None:
            st.info("Please select a symbol from the sidebar to view analysis results.")
            return
        
        selected_symbol, n_results, priority_filter = sidebar_result
        
        # Get analysis data
        with st.spinner(f"Loading analysis data for {selected_symbol}..."):
            analysis_data = self.get_symbol_analysis_data(selected_symbol, n_results)
        
        if analysis_data.empty:
            st.warning(f"No analysis data found for {selected_symbol}")
            return
        
        # Apply priority filter based on days to crash
        if priority_filter != "All" and 'predicted_crash_date' in analysis_data.columns:
            now = datetime.now()
            if priority_filter == "Critical Only (≤30 days)":
                analysis_data = analysis_data[
                    analysis_data['predicted_crash_date'].apply(
                        lambda x: (x - now).days <= 30 if pd.notna(x) else False
                    )
                ]
            elif priority_filter == "High Priority (≤90 days)":
                analysis_data = analysis_data[
                    analysis_data['predicted_crash_date'].apply(
                        lambda x: (x - now).days <= 90 if pd.notna(x) else False
                    )
                ]
            elif priority_filter == "Medium Priority (≤180 days)":
                analysis_data = analysis_data[
                    analysis_data['predicted_crash_date'].apply(
                        lambda x: (x - now).days <= 180 if pd.notna(x) else False
                    )
                ]
        
        if analysis_data.empty:
            st.warning("No data matches the selected priority filter")
            return
        
        # Main content tabs - restored to original 3-tab layout
        tab1, tab2, tab3 = st.tabs([
            "📈 Price & Predictions", 
            "📊 Prediction Convergence", 
            "📋 Parameters"
        ])
        
        with tab1:
            self.render_price_predictions_tab(selected_symbol, analysis_data)
        
        with tab2:
            self.render_prediction_convergence_tab(selected_symbol, analysis_data)
        
        with tab3:
            self.render_parameters_tab(selected_symbol, analysis_data)

def main():
    """Main execution function"""
    app = SymbolAnalysisDashboard()
    app.run()

if __name__ == "__main__":
    main()