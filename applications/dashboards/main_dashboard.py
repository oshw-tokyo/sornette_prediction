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

from infrastructure.database.results_database import ResultsDatabase

class SymbolAnalysisDashboard:
    """Symbol-Based Analysis Dashboard"""
    
    def __init__(self):
        self.db = ResultsDatabase()
        self.market_catalog = self.load_market_catalog()
        
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
    
    def get_symbol_price_data(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get symbol price data (placeholder - would need actual data client)"""
        # This would need to be implemented with actual data client
        # For now, return None to indicate no price data available
        return None
    
    def render_price_predictions_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 1: Price Chart with Crash Prediction Lines"""
        
        st.header(f"📈 {symbol} - Price History with Predictions")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        # Display latest prediction metrics
        latest = analysis_data.iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if pd.notna(latest.get('predicted_crash_date')):
                crash_date = latest['predicted_crash_date']
                if hasattr(crash_date, 'to_pydatetime'):
                    crash_date = crash_date.to_pydatetime()
                st.metric(
                    "Predicted Crash Date",
                    crash_date.strftime('%Y-%m-%d %H:%M'),
                    help="Converted from tc value to actual date/time"
                )
            else:
                st.metric("Predicted Crash Date", "N/A")
        
        with col2:
            st.metric(
                "Model Fit (R²)",
                f"{latest['r_squared']:.3f}" if pd.notna(latest.get('r_squared')) else "N/A",
                help="Goodness of fit - higher values indicate better model reliability"
            )
        
        with col3:
            st.metric(
                "Quality",
                latest.get('quality', 'N/A'),
                help="Analysis quality assessment"
            )
        
        # Try to get price data for chart
        price_data = self.get_symbol_price_data(symbol)
        
        if price_data is not None and not price_data.empty:
            # Create price chart with prediction lines
            fig = go.Figure()
            
            # Price data
            fig.add_trace(go.Scatter(
                x=price_data.index,
                y=price_data['Close'],
                mode='lines',
                name='Price',
                line=dict(color='blue', width=2)
            ))
            
            # Add prediction lines
            valid_predictions = analysis_data.dropna(subset=['predicted_crash_date'])
            for i, (_, pred) in enumerate(valid_predictions.head(10).iterrows()):
                pred_date = pred['predicted_crash_date']
                if hasattr(pred_date, 'to_pydatetime'):
                    pred_date = pred_date.to_pydatetime()
                
                # Add vertical line for prediction
                fig.add_shape(
                    type="line",
                    x0=pred_date,
                    x1=pred_date,
                    y0=0,
                    y1=1,
                    yref="paper",
                    line=dict(color=f'rgba(255, {100-i*10}, {100-i*10}, 0.7)', width=2, dash="dash")
                )
            
            fig.update_layout(
                title=f"{symbol} - Price History with Crash Predictions",
                xaxis_title="Date",
                yaxis_title="Price",
                height=600,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Price data not available. Showing prediction information only.")
            
            # Show prediction timeline without price data
            valid_predictions = analysis_data.dropna(subset=['predicted_crash_date'])
            if not valid_predictions.empty:
                st.subheader("🔮 Crash Prediction Timeline")
                
                for i, (_, pred) in enumerate(valid_predictions.head(5).iterrows()):
                    pred_date = pred['predicted_crash_date']
                    if hasattr(pred_date, 'to_pydatetime'):
                        pred_date = pred_date.to_pydatetime()
                    
                    days_to_crash = (pred_date - datetime.now()).days
                    
                    if days_to_crash <= 30:
                        emoji = "🚨"
                        color = "red"
                    elif days_to_crash <= 90:
                        emoji = "⚠️"
                        color = "orange"
                    else:
                        emoji = "📅"
                        color = "blue"
                    
                    st.markdown(
                        f"{emoji} **{pred_date.strftime('%Y-%m-%d %H:%M')}** "
                        f"({days_to_crash} days) - R²: {pred.get('r_squared', 0):.3f}"
                    )
    
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
        
        # Add data period information
        data_period_info = []
        for _, row in display_df.iterrows():
            try:
                # Get data period start and end
                data_start = None
                data_end = None
                period_days = None
                
                # Find data period end
                for col in ['data_period_end', 'data_end', 'end_date']:
                    if col in display_df.columns and pd.notna(row.get(col)):
                        data_end = pd.to_datetime(row[col]).strftime('%Y-%m-%d')
                        break
                
                # Find data period start
                for col in ['data_period_start', 'data_start', 'start_date']:
                    if col in display_df.columns and pd.notna(row.get(col)):
                        data_start = pd.to_datetime(row[col]).strftime('%Y-%m-%d')
                        break
                
                # Find period days
                for col in ['window_days', 'data_points', 'period_days']:
                    if col in display_df.columns and pd.notna(row.get(col)):
                        period_days = f"{int(row[col])} days"
                        break
                
                if data_start and data_end:
                    period_info = f"{data_start} to {data_end}"
                elif data_end and period_days:
                    period_info = f"~{period_days} to {data_end}"
                else:
                    period_info = period_days or 'N/A'
                
                data_period_info.append(period_info)
                
            except Exception:
                data_period_info.append('N/A')
        
        display_df['data_period'] = data_period_info
        
        # Define column priority for display (left to right)
        priority_columns = [
            'predicted_crash_date_formatted',  # Most important
            'r_squared',
            'confidence',
            'data_period',
            'tc',
            'beta', 'omega', 'phi',
            'A', 'B', 'C',
            'rmse', 'quality'
        ]
        
        # Select existing columns in priority order
        existing_columns = [col for col in priority_columns if col in display_df.columns]
        
        # Add analysis_date if available
        if 'analysis_date' in display_df.columns:
            existing_columns.insert(1, 'analysis_date')
        
        final_df = display_df[existing_columns].copy()
        
        # Sort by predicted crash date (earliest first)
        if 'predicted_crash_date' in analysis_data.columns:
            sort_col = 'predicted_crash_date'
            final_df = final_df.loc[analysis_data.sort_values(sort_col, na_position='last').index]
        
        # Format numeric columns
        numeric_columns = ['r_squared', 'confidence', 'tc', 'beta', 'omega', 'phi', 'A', 'B', 'C', 'rmse']
        for col in numeric_columns:
            if col in final_df.columns:
                final_df[col] = final_df[col].apply(
                    lambda x: f"{x:.4f}" if pd.notna(x) else 'N/A'
                )
        
        # Display the table
        st.subheader("📊 Analysis Results (sorted by predicted crash date)")
        
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
                "analysis_date": st.column_config.DatetimeColumn(
                    "📅 Analysis Date",
                    help="When the analysis was performed"
                ),
                "r_squared": st.column_config.TextColumn(
                    "📊 R² Score",
                    help="Model fit quality (higher = better)"
                ),
                "confidence": st.column_config.TextColumn(
                    "✅ Confidence",
                    help="Prediction confidence level"
                ),
                "data_period": st.column_config.TextColumn(
                    "📊 Data Period",
                    help="Period of data used for analysis",
                    width="medium"
                ),
                "tc": st.column_config.TextColumn(
                    "🔢 tc Ratio",
                    help="Critical time ratio (for reference)"
                ),
                "quality": st.column_config.TextColumn(
                    "✅ Quality",
                    help="Analysis quality assessment"
                )
            }
        )
        
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