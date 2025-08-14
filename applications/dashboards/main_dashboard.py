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
from plotly.subplots import make_subplots
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
        
        # 🔧 API効率化: 価格データキャッシュ（セッション内有効）
        if 'price_data_cache' not in st.session_state:
            st.session_state.price_data_cache = {}
        if 'cache_metadata' not in st.session_state:
            st.session_state.cache_metadata = {}
        
        # 🚀 パフォーマンス最適化: フィルタープリセットをキャッシュ（2025-08-11追加）
        if 'filter_presets_cache' not in st.session_state:
            st.session_state.filter_presets_cache = self.db.get_filter_presets()
    
    def _convert_date_columns_for_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ダッシュボード表示専用の安全な日付変換
        🔒 バックエンド保護: 変換されたデータは外部に渡さず、表示のみに使用
        文字列として保存された日付をTimestamp型に変換（2025-08-11追加）
        """
        date_columns = [
            'predicted_crash_date', 'analysis_basis_date', 'data_period_start', 
            'data_period_end', 'analysis_date'
        ]
        
        # 🔒 重要: 元データを変更せず、コピーで変換（バックエンド保護）
        df_converted = df.copy()
        
        for col in date_columns:
            if col in df_converted.columns:
                try:
                    # 文字列日付をTimestamp型に変換（errors='coerce'で無効な値はNaTに）
                    df_converted[col] = pd.to_datetime(df_converted[col], errors='coerce')
                    # 静音モード: バックエンドに影響しないよう、ログ出力を削除
                except Exception as e:
                    # エラーは静音処理（バックエンドへの影響を回避）
                    pass
                    
        return df_converted

    def _ensure_date_string(self, date_value) -> str:
        """
        API呼び出し用にTimestamp/datetime オブジェクトを YYYY-MM-DD 文字列に安全変換
        🔧 FRED API修正: observation_start/end の文字列フォーマット保証
        """
        if pd.isna(date_value):
            return None
        
        if isinstance(date_value, str):
            # 既に文字列の場合（データベースから直接）
            if len(date_value) >= 10:  # YYYY-MM-DD形式確認
                return date_value[:10]  # 時間部分があれば除去
            return date_value
        
        if hasattr(date_value, 'strftime'):
            # Timestamp/datetime オブジェクトの場合
            return date_value.strftime('%Y-%m-%d')
        
        # その他の場合（予期しない型）
        return str(date_value)[:10] if str(date_value) else None
    
    def __post_init__(self):
        """Initialize Streamlit configuration after object creation"""
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
    
    def calculate_crash_date_convergence(self, crash_dates: List[datetime], basis_dates: List[datetime]) -> Tuple[str, bool]:
        """
        クラッシュ予測日の収束値を計算
        
        Args:
            crash_dates: 予測されたクラッシュ日のリスト
            basis_dates: フィッティング基準日のリスト
            
        Returns:
            Tuple[str, bool]: (収束日または"収束しない", 収束フラグ)
        """
        try:
            if not crash_dates or len(crash_dates) < 3:
                return "データ不足", False
            
            # 現在から3年以内の予測のみを有効とする
            now = datetime.now()
            three_years_later = now + timedelta(days=3*365)
            
            # フィルタリング：過去の予測と3年以上先の予測を除外
            valid_predictions = []
            for crash_date, basis_date in zip(crash_dates, basis_dates):
                if crash_date > now and crash_date <= three_years_later:
                    valid_predictions.append((crash_date, basis_date))
            
            if len(valid_predictions) < 3:
                return "収束しない", False
            
            # 基準日順にソート（新しい順）
            valid_predictions.sort(key=lambda x: x[1], reverse=True)
            recent_predictions = valid_predictions[:min(5, len(valid_predictions))]
            
            # 最新5件の予測日の標準偏差を計算
            recent_crash_dates = [pred[0] for pred in recent_predictions]
            timestamps = [d.timestamp() for d in recent_crash_dates]
            
            if len(timestamps) < 3:
                return "データ不足", False
            
            # 標準偏差を日数で計算
            mean_timestamp = np.mean(timestamps)
            std_days = np.std(timestamps) / (24 * 3600)  # 秒を日に変換
            
            # 収束判定：標準偏差が30日以内なら収束とみなす
            if std_days <= 30:
                convergence_date = datetime.fromtimestamp(mean_timestamp)
                
                # 収束傾向の確認：最新3件の予測が一定方向に向かっているか
                if len(recent_crash_dates) >= 3:
                    trend_timestamps = [d.timestamp() for d in recent_crash_dates[:3]]
                    # 時系列的に単調かどうかをチェック
                    trend_variation = np.std(np.diff(trend_timestamps)) / (24 * 3600)
                    
                    if trend_variation <= 15:  # 15日以内の変動なら安定
                        return convergence_date.strftime('%Y-%m-%d'), True
                
                return convergence_date.strftime('%Y-%m-%d'), True
            else:
                return "収束しない", False
                
        except Exception as e:
            return "計算エラー", False
    
    def calculate_multi_method_convergence(self, period_data: pd.DataFrame) -> Dict:
        """
        Multiple methods for convergence analysis
        
        Args:
            period_data: DataFrame with prediction data for the period
            
        Returns:
            Dict: Convergence metrics using multiple methods
        """
        try:
            from scipy import stats
            import numpy as np
            
            # Prepare crash dates as numeric values (days from now)
            crash_dates = []
            fitting_dates = []
            r_squared_values = []
            
            for _, row in period_data.iterrows():
                crash_date = pd.to_datetime(row['predicted_crash_date'])
                fitting_date = pd.to_datetime(row['fitting_basis_date'])
                
                # Days from now to crash
                days_to_crash = (crash_date - datetime.now()).days
                crash_dates.append(days_to_crash)
                fitting_dates.append(fitting_date)
                r_squared_values.append(row.get('r_squared', 0.5))
            
            crash_dates = np.array(crash_dates)
            r_squared_values = np.array(r_squared_values)
            
            # 1. Standard deviation method
            std_deviation = np.std(crash_dates)
            mean_days = np.mean(crash_dates)
            
            # 2. Coefficient of variation
            coefficient_variation = std_deviation / abs(mean_days) if abs(mean_days) > 0 else float('inf')
            
            # 3. Range method  
            prediction_range = np.max(crash_dates) - np.min(crash_dates)
            
            # 4. Weighted standard deviation (recent data weighted more)
            # Create exponential weights (more recent = higher weight)
            sorted_indices = np.argsort([fd for fd in fitting_dates])[::-1]  # Most recent first
            weights = np.exp(-0.1 * np.arange(len(crash_dates)))  # Exponential decay
            
            # Apply weights according to fitting date order
            weighted_crash_dates = crash_dates[sorted_indices]
            weighted_mean = np.average(weighted_crash_dates, weights=weights)
            weighted_variance = np.average((weighted_crash_dates - weighted_mean)**2, weights=weights)
            weighted_std = np.sqrt(weighted_variance)
            
            # 5. Trend analysis
            # Linear regression of crash dates over fitting dates
            fitting_timestamps = [fd.timestamp() for fd in fitting_dates]
            if len(fitting_timestamps) >= 3:
                slope, intercept, r_value, p_value, std_err = stats.linregress(fitting_timestamps, crash_dates)
                trend_r_squared = r_value**2
                trend_slope = slope * (24 * 3600)  # Convert to days per day
            else:
                trend_slope = 0
                trend_r_squared = 0
            
            # 6. Consensus date (weighted average of recent predictions)
            consensus_days = weighted_mean
            consensus_date = datetime.now() + timedelta(days=consensus_days)
            
            # 7. Convergence status based on multiple criteria
            if std_deviation < 5 and coefficient_variation < 0.05:
                convergence_status = "Excellent"
            elif std_deviation < 10 and coefficient_variation < 0.10:
                convergence_status = "Good"
            elif std_deviation < 20 and coefficient_variation < 0.20:
                convergence_status = "Moderate" 
            else:
                convergence_status = "Poor"
            
            return {
                'std_deviation': std_deviation,
                'coefficient_variation': coefficient_variation,
                'prediction_range': prediction_range,
                'weighted_std': weighted_std,
                'trend_slope': trend_slope,
                'trend_r_squared': trend_r_squared,
                'consensus_date': consensus_date,
                'convergence_status': convergence_status,
                'mean_days_to_crash': mean_days,
                'data_count': len(crash_dates)
            }
            
        except Exception as e:
            # Return default values on error
            return {
                'std_deviation': 999.0,
                'coefficient_variation': 999.0,
                'prediction_range': 999.0,
                'weighted_std': 999.0,
                'trend_slope': 0.0,
                'trend_r_squared': 0.0,
                'consensus_date': datetime.now(),
                'convergence_status': 'Error',
                'mean_days_to_crash': 0.0,
                'data_count': 0
            }
    
    def create_convergence_plot(self, period_data: pd.DataFrame, period_name: str, convergence_results: Dict):
        """
        Create a detailed convergence plot for a specific period
        
        Args:
            period_data: DataFrame with prediction data
            period_name: Name of the time period
            convergence_results: Results from calculate_multi_method_convergence
            
        Returns:
            plotly.graph_objects.Figure: Convergence analysis plot
        """
        try:
            fig = go.Figure()
            
            # Prepare data
            fitting_dates = []
            crash_dates = []
            r_squared_values = []
            quality_values = []
            
            for _, row in period_data.iterrows():
                fitting_dates.append(pd.to_datetime(row['fitting_basis_date']))
                crash_dates.append(pd.to_datetime(row['predicted_crash_date']))
                r_squared_values.append(row.get('r_squared', 0.5))
                quality_values.append(row.get('quality', 'unknown'))
            
            # Main scatter plot: fitting dates vs crash predictions
            fig.add_trace(go.Scatter(
                x=fitting_dates,
                y=crash_dates,
                mode='markers',
                marker=dict(
                    size=12,
                    color=r_squared_values,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="R² Score", x=1.02)
                ),
                name='Predictions',
                text=[f"R²: {r2:.3f}<br>Quality: {q}<br>Days to crash: {(pd.to_datetime(cd) - datetime.now()).days if pd.notna(cd) else 'N/A'}" 
                      for cd, r2, q in zip(crash_dates, r_squared_values, quality_values)],
                hovertemplate='Fitting Date: %{x}<br>Predicted Crash: %{y}<br>%{text}<extra></extra>'
            ))
            
            # Add consensus crash date line
            consensus_date = convergence_results['consensus_date']
            fig.add_hline(
                y=consensus_date,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Consensus: {consensus_date.strftime('%Y-%m-%d')}",
                annotation_position="bottom right"
            )
            
            # Add convergence bands
            std_dev_days = convergence_results['std_deviation']
            upper_band = consensus_date + timedelta(days=std_dev_days)
            lower_band = consensus_date - timedelta(days=std_dev_days)
            
            # Add upper and lower bands
            fig.add_hline(
                y=upper_band,
                line_dash="dot",
                line_color="orange",
                opacity=0.5,
                annotation_text=f"+1σ ({std_dev_days:.0f}d)",
                annotation_position="top right"
            )
            fig.add_hline(
                y=lower_band,
                line_dash="dot", 
                line_color="orange",
                opacity=0.5,
                annotation_text=f"-1σ",
                annotation_position="bottom right"
            )
            
            # Trend line if significant
            if convergence_results['trend_r_squared'] > 0.5:
                # Add trend line
                x_trend = [min(fitting_dates), max(fitting_dates)]
                trend_slope_per_sec = convergence_results['trend_slope'] / (24 * 3600)
                
                # Calculate y values for trend line
                y_start = consensus_date
                days_span = (max(fitting_dates) - min(fitting_dates)).days
                y_end = consensus_date + timedelta(days=trend_slope_per_sec * days_span)
                
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=[y_start, y_end],
                    mode='lines',
                    line=dict(color='purple', width=2, dash='dot'),
                    name=f'Trend (R²={convergence_results["trend_r_squared"]:.2f})',
                    hovertemplate='Trend Line<extra></extra>'
                ))
            
            # Layout
            fig.update_layout(
                title=f"{period_name} Convergence Analysis - Status: {convergence_results['convergence_status']}",
                xaxis_title="Fitting Basis Date",
                yaxis_title="Predicted Crash Date", 
                height=500,
                hovermode='closest',
                plot_bgcolor='rgba(240, 240, 240, 0.8)',
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            # Return empty figure on error
            fig = go.Figure()
            fig.update_layout(
                title=f"{period_name} - Plot Error: {str(e)}",
                height=400
            )
            return fig
    
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
    
    def get_symbol_analysis_data(self, symbol: str, limit: int = 50, 
                                 period_selection: Optional[Dict] = None) -> pd.DataFrame:
        """
        Get analysis data for specific symbol with predicted crash dates
        
        v2更新（2025-08-11）: Symbol選択後は全データ取得し、Displaying Periodのみでフィルタ
        """
        try:
            # 選択銘柄の全データ取得（Symbol Filters影響なし）
            analyses = self.db.get_recent_analyses(symbol=symbol, limit=None)
            
            if analyses.empty:
                return pd.DataFrame()
            
            # 🔧 表示専用の日付カラム変換（バックエンド保護）
            analyses = self._convert_date_columns_for_display(analyses)
            
            # Apply period filtering based on analysis basis date
            if period_selection:
                start_date = period_selection.get('start_date')
                end_date = period_selection.get('end_date')
                
                if start_date and end_date:
                    # Convert dates to datetime for filtering
                    start_datetime = pd.to_datetime(start_date)
                    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # End of day
                    
                    # Filter based on analysis_basis_date (priority) or data_period_end (fallback)
                    filtered_analyses = []
                    for _, row in analyses.iterrows():
                        basis_date = None
                        if pd.notna(row.get('analysis_basis_date')):
                            basis_date = pd.to_datetime(row['analysis_basis_date'])
                        elif pd.notna(row.get('data_period_end')):
                            basis_date = pd.to_datetime(row['data_period_end'])
                        
                        if basis_date and start_datetime <= basis_date <= end_datetime:
                            filtered_analyses.append(row)
                    
                    if filtered_analyses:
                        analyses = pd.DataFrame(filtered_analyses)
                    else:
                        return pd.DataFrame()  # No data in selected period
            
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
            
            # Sort by analysis basis date (newest first) for temporal consistency
            # This ensures the chronological order is maintained after filtering
            basis_date_col = []
            for _, row in analyses.iterrows():
                if pd.notna(row.get('analysis_basis_date')):
                    basis_date_col.append(pd.to_datetime(row['analysis_basis_date']))
                elif pd.notna(row.get('data_period_end')):
                    basis_date_col.append(pd.to_datetime(row['data_period_end']))
                else:
                    basis_date_col.append(pd.NaT)
            
            analyses['sort_basis_date'] = basis_date_col
            analyses = analyses.sort_values('sort_basis_date', ascending=False)
            analyses = analyses.drop('sort_basis_date', axis=1)
            
            return analyses
            
        except Exception as e:
            st.error(f"Error retrieving analysis data: {str(e)}")
            return pd.DataFrame()
    
    def render_sidebar_v2(self):
        """
        新しいサイドバー実装（2025-08-11）
        - Symbol Filters: 銘柄選択リストのみ影響
        - Displaying Period: プロット範囲のみ制御
        - Apply ボタン: 明示的更新制御
        """
        with st.sidebar:
            st.title("🔍 Analysis Controls")
            
            # === 1. Symbol Filters ===
            st.subheader("🎛️ Symbol Filters")
            
            # Get categorized symbols
            categorized_symbols = self.get_symbols_by_category()
            
            # Asset Category (最上段・独立セクション)
            st.markdown("#### 🏷️ Asset Category")
            selected_category = st.selectbox(
                "Select Asset Category",
                ["All Symbols"] + list(categorized_symbols.keys()),
                format_func=lambda x: "All Symbols" if x == "All Symbols" 
                else categorized_symbols[x]["display_name"] if x in categorized_symbols 
                else x,
                help="Filter symbols by asset category"
            )
            
            # Filter Conditions (プリセット/カスタム)
            st.markdown("#### 🔍 Filter Conditions")
            
            # フィルタープリセット
            filter_presets = st.session_state.filter_presets_cache
            preset_options = ["User Defined"] + list(filter_presets.keys())
            selected_preset = st.selectbox(
                "Filter Presets",
                preset_options,
                help="Pre-defined filter configurations for common use cases"
            )
            
            # フィルター設定の収集
            custom_filters = {}
            preset_config = None
            
            if selected_preset != "User Defined":
                # プリセット選択時
                preset_config = filter_presets[selected_preset].copy()
                preset_config.pop('description', None)
                st.info(f"**Applied**: {filter_presets[selected_preset].get('description', '')}")
            else:
                # カスタム設定時
                with st.expander("🎛️ Custom Filters", expanded=True):
                    # R²フィルター
                    col1, col2 = st.columns(2)
                    with col1:
                        min_r_squared = st.number_input("Min R²", 0.0, 1.0, 0.0, 0.01, format="%.2f")
                        if min_r_squared > 0:
                            custom_filters['min_r_squared'] = min_r_squared
                    with col2:
                        max_r_squared = st.number_input("Max R²", 0.0, 1.0, 1.0, 0.01, format="%.2f")
                        if max_r_squared < 1.0:
                            custom_filters['max_r_squared'] = max_r_squared
                    
                    # 信頼度フィルター
                    col1, col2 = st.columns(2)
                    with col1:
                        min_confidence = st.number_input("Min Confidence", 0.0, 1.0, 0.0, 0.01, format="%.2f")
                        if min_confidence > 0:
                            custom_filters['min_confidence'] = min_confidence
                    with col2:
                        max_confidence = st.number_input("Max Confidence", 0.0, 1.0, 1.0, 0.01, format="%.2f")
                        if max_confidence < 1.0:
                            custom_filters['max_confidence'] = max_confidence
                    
                    # 使用可能性
                    usable_only = st.checkbox("Usable Only", help="Show only usable analyses")
                    if usable_only:
                        custom_filters['is_usable'] = True
                    
                    # 予測日範囲
                    st.markdown("**Predicted Crash Date Range**")
                    col1, col2 = st.columns(2)
                    with col1:
                        crash_from = st.date_input(
                            "From",
                            value=(datetime.now() - timedelta(days=365)).date(),
                            help="Crash predictions after this date"
                        )
                        if crash_from:
                            custom_filters['predicted_crash_from'] = crash_from.strftime('%Y-%m-%d')
                    with col2:
                        crash_to = st.date_input(
                            "To",
                            value=(datetime.now() + timedelta(days=730)).date(),
                            help="Crash predictions before this date"
                        )
                        if crash_to:
                            custom_filters['predicted_crash_to'] = crash_to.strftime('%Y-%m-%d')
            
            # === 2. Symbol Selection (リアルタイム更新) ===
            st.subheader("📈 Select Symbol")
            
            # フィルター適用して利用可能な銘柄を取得
            try:
                available_symbols = self._get_filtered_symbols(
                    selected_category, selected_preset, preset_config, custom_filters
                )
                
                if not available_symbols:
                    st.warning("No symbols match current filters")
                    return None
                
                # Symbol選択 - NASDAQCOMをデフォルトに設定（2025-08-12）
                default_symbol = "NASDAQCOM" if "NASDAQCOM" in available_symbols else available_symbols[0] if available_symbols else None
                selected_symbol = st.selectbox(
                    "Choose Symbol",
                    available_symbols,
                    index=available_symbols.index(default_symbol) if default_symbol and default_symbol in available_symbols else 0,
                    help="Select a symbol from filtered results"
                )
                
                # 🆕 Symbol選択後にCurrently Selected Symbolを更新（無限ループ修正）
                if selected_symbol != st.session_state.get('selected_symbol_temp'):
                    st.session_state.selected_symbol_temp = selected_symbol
                    # st.rerun()を削除して無限ループを防止
                
            except Exception as e:
                st.error(f"Failed to load symbols: {str(e)}")
                return None
            
            # === 3. Currently Selected Symbol ===
            st.markdown("#### 🎯 Currently Selected")
            # 🔧 修正：リアルタイム選択状況を反映（2025-08-11）
            temp_symbol = st.session_state.get('selected_symbol_temp')
            current_symbol = st.session_state.get('current_symbol')
            
            if temp_symbol and temp_symbol != current_symbol:
                st.info(f"**{temp_symbol}** (Ready to Apply)")
            elif current_symbol:
                st.success(f"**{current_symbol}** (Active)")
            else:
                st.info("*No symbol selected yet*")
            
            # === 4. Apply Symbol Selection ===
            st.markdown("---")
            # 🔧 修正：Symbol選択状態に応じたボタン表示（2025-08-11）
            apply_disabled = not temp_symbol
            apply_button_text = "📈 **Select Symbol**" if temp_symbol else "❌ **Choose Symbol First**"
            
            if st.button(apply_button_text, type="primary", use_container_width=True, disabled=apply_disabled):
                if temp_symbol:
                    # 選択された銘柄を確定
                    st.session_state.current_symbol = temp_symbol
                    st.session_state.apply_clicked = True
                    st.success(f"Selected symbol: {temp_symbol}!")
            
            # 返却値 - Display Periodは各タブで個別管理
            current_symbol = st.session_state.get('current_symbol')
            if current_symbol and st.session_state.get('apply_clicked', False):
                # apply_clickedフラグをリセット（次回のために） - コメントアウトしてループ防止
                # st.session_state.apply_clicked = False  
                return current_symbol  # period_selectionとfiltersは削除
            else:
                return None
    
    def _get_filtered_symbols(self, category, preset, preset_config, custom_filters):
        """Symbol Filters適用して利用可能な銘柄リストを取得"""
        # カテゴリフィルター
        if category != "All Symbols":
            categorized_symbols = self.get_symbols_by_category()
            category_symbols = [
                s["symbol"] for s in categorized_symbols.get(category, {}).get("symbols", [])
            ]
        else:
            category_symbols = None
        
        # プリセット/カスタムフィルター
        if preset != "User Defined" and preset_config:
            filtered_data = self.db.apply_filter_preset(preset)
        elif custom_filters:
            filtered_data = self.db.get_filtered_analyses(**custom_filters)
        else:
            # フィルターなし
            all_analyses = self.db.get_recent_analyses(limit=100)
            filtered_data = all_analyses
        
        if filtered_data.empty:
            return []
        
        # 銘柄リスト取得
        available_symbols = sorted(filtered_data['symbol'].unique().tolist())
        
        # カテゴリでさらに絞り込み
        if category_symbols:
            available_symbols = [s for s in available_symbols if s in category_symbols]
        
        return available_symbols
    
    def _get_period_selection(self, symbol):
        """
        Displaying Period設定を取得
        修正：Symbol未選択時の安全なハンドリング（2025-08-11）
        """
        if not symbol:
            st.info("📍 Please select a symbol to configure the displaying period.")
            return None
            
        try:
            # 選択銘柄の全データ取得（Symbol Filters無視）
            all_analyses = self.db.get_recent_analyses(symbol=symbol, limit=None)
            if all_analyses.empty:
                st.warning(f"No analysis data found for {symbol}")
                return None
            
            # 基準日範囲を計算
            basis_dates = []
            for _, row in all_analyses.iterrows():
                if pd.notna(row.get('analysis_basis_date')):
                    basis_dates.append(pd.to_datetime(row['analysis_basis_date']))
                elif pd.notna(row.get('data_period_end')):
                    basis_dates.append(pd.to_datetime(row['data_period_end']))
            
            if not basis_dates:
                st.warning(f"No valid analysis dates found for {symbol}")
                return None
            
            basis_dates = sorted(basis_dates)
            min_date = basis_dates[0].date()
            max_date = basis_dates[-1].date()
            
            # デフォルト値 - 変更: 最古データから表示（2025-08-12）
            default_end = max_date
            default_start = min_date  # 最古データから表示
            
            # 期間選択UI
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "From", value=default_start,
                    min_value=min_date, max_value=max_date,
                    help="Start of analysis period"
                )
            with col2:
                end_date = st.date_input(
                    "To", value=default_end,
                    min_value=min_date, max_value=max_date,
                    help="End of analysis period"
                )
            
            if start_date > end_date:
                st.error("Start date must be earlier than end date")
                return None
            
            return {'start_date': start_date, 'end_date': end_date}
            
        except Exception as e:
            st.error(f"Error loading period data: {str(e)}")
            return None
    
    def render_sidebar(self):
        """Render symbol selection sidebar with categorization"""
        
        with st.sidebar:
            st.title("🔍 Analysis Controls")
            
            # 🆕 フィルタリング機能を最上部に配置（2025-08-11改善: Symbol Filtersに改名）
            st.subheader("🎛️ Symbol Filters")
            
            # Get categorized symbols first
            categorized_symbols = self.get_symbols_by_category()
            
            # Asset Category セクション（Symbol Filters最上段・独立セクション）
            with st.expander("🏷️ Asset Category", expanded=True):
                category_options = ["All Symbols"] + list(categorized_symbols.keys())
                selected_category = st.selectbox(
                    "Select Asset Category",
                    category_options,
                    format_func=lambda x: "All Symbols" if x == "All Symbols" 
                    else categorized_symbols[x]["display_name"] if x in categorized_symbols 
                    else x,
                    help="Filter symbols by asset category"
                )
            
            # Filter Conditions セクション（既存フィルタ・プリセット利用可能）
            with st.expander("🔍 Filter Conditions", expanded=True):
                # フィルタープリセット（キャッシュから高速取得）
                filter_presets = st.session_state.filter_presets_cache
                preset_options = ["User Defined"] + list(filter_presets.keys())
                selected_preset = st.selectbox(
                    "Filter Presets",
                    preset_options,
                    help="Pre-defined filter configurations for common use cases"
                )
                
                # プリセット設定の詳細表示＆カスタム設定
                custom_filters = {}
                preset_config = None
            
            if selected_preset != "User Defined":
                # プリセット選択時：設定内容を表示（編集不可）
                preset_config = filter_presets[selected_preset].copy()
                preset_config.pop('description', None)  # 説明文を除去
                
                st.info(f"**Applied Settings**: {filter_presets[selected_preset].get('description', '')}")
                
                # プリセット設定の詳細を展開表示（グレーアウト）
                with st.expander("📋 Current Filter Settings (Applied)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'min_r_squared' in preset_config:
                            st.text_input("Min R²", value=f"{preset_config['min_r_squared']:.2f}", disabled=True)
                        if 'min_confidence' in preset_config:
                            st.text_input("Min Confidence", value=f"{preset_config['min_confidence']:.2f}", disabled=True)
                        if 'predicted_crash_from' in preset_config:
                            st.text_input("Crash Date From", value=preset_config['predicted_crash_from'], disabled=True)
                    
                    with col2:
                        if 'is_usable' in preset_config:
                            st.checkbox("Usable Only", value=preset_config['is_usable'], disabled=True)
                        if 'limit' in preset_config:
                            st.text_input("Result Limit", value=str(preset_config['limit']), disabled=True)
                        if 'predicted_crash_to' in preset_config:
                            st.text_input("Crash Date To", value=preset_config['predicted_crash_to'], disabled=True)
                        if 'basis_date_from' in preset_config:
                            st.text_input("Analysis From", value=preset_config['basis_date_from'], disabled=True)
            else:
                # カスタム設定時：フル機能提供
                with st.expander("🎛️ Quality Filters", expanded=True):
                    # R²フィルター
                    col1, col2 = st.columns(2)
                    with col1:
                        min_r_squared = st.number_input(
                            "Min R²", min_value=0.0, max_value=1.0, 
                            step=0.01, format="%.2f", help="Minimum R-squared value threshold"
                        )
                        if min_r_squared > 0:
                            custom_filters['min_r_squared'] = min_r_squared
                    
                    with col2:
                        max_r_squared = st.number_input(
                            "Max R²", min_value=0.0, max_value=1.0, 
                            value=1.0, step=0.01, format="%.2f"
                        )
                        if max_r_squared < 1.0:
                            custom_filters['max_r_squared'] = max_r_squared
                    
                    # 信頼度フィルター
                    col1, col2 = st.columns(2)
                    with col1:
                        min_confidence = st.number_input(
                            "Min Confidence", min_value=0.0, max_value=1.0,
                            step=0.01, format="%.2f"
                        )
                        if min_confidence > 0:
                            custom_filters['min_confidence'] = min_confidence
                    
                    with col2:
                        max_confidence = st.number_input(
                            "Max Confidence", min_value=0.0, max_value=1.0,
                            value=1.0, step=0.01, format="%.2f"
                        )
                        if max_confidence < 1.0:
                            custom_filters['max_confidence'] = max_confidence
                    
                    # 使用可能性フィルター
                    usable_only = st.checkbox("Usable Only", help="Show only analyses marked as usable")
                    if usable_only:
                        custom_filters['is_usable'] = True
                
                with st.expander("📅 Date Range Filters", expanded=False):
                    # 予測日範囲フィルター（デフォルト値設定・改善版）
                    st.markdown("**Predicted Crash Date Range**")
                    
                    # デフォルト値設定（1年前〜2年先）
                    default_crash_from = (datetime.now() - timedelta(days=365)).date()  # 1年前
                    default_crash_to = (datetime.now() + timedelta(days=730)).date()    # 2年先
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        crash_from = st.date_input(
                            "Crash From", 
                            value=default_crash_from,
                            help="Show analyses predicting crashes after this date"
                        )
                        if crash_from:
                            custom_filters['predicted_crash_from'] = crash_from.strftime('%Y-%m-%d')
                    
                    with col2:
                        crash_to = st.date_input(
                            "Crash To",
                            value=default_crash_to,
                            help="Show analyses predicting crashes before this date"
                        )
                        if crash_to:
                            custom_filters['predicted_crash_to'] = crash_to.strftime('%Y-%m-%d')
                
                with st.expander("🔢 Sort Options", expanded=False):
                    # ソート設定（R²優先、順序変更）
                    sort_options = {
                        'r_squared': 'R² Value',
                        'confidence': 'Confidence', 
                        'predicted_crash_date': 'Predicted Crash Date',
                        'analysis_basis_date': 'Analysis Date',
                        'symbol': 'Symbol Name'
                    }
                    sort_by = st.selectbox(
                        "Sort By", options=list(sort_options.keys()),
                        format_func=lambda x: sort_options[x],
                        index=0  # R²がデフォルト選択（リストの最初）
                    )
                    custom_filters['sort_by'] = sort_by
                    
                    # ソート順序（改善版）
                    sort_order_options = {
                        'DESC': 'Highest First (High to Low)',
                        'ASC': 'Lowest First (Low to High)'
                    }
                    sort_order = st.selectbox(
                        "Sort Order", 
                        options=list(sort_order_options.keys()),
                        format_func=lambda x: sort_order_options[x],
                        index=0
                    )
                    custom_filters['sort_order'] = sort_order
                    
                    # 結果件数制限（最後に配置）
                    result_limit = st.number_input(
                        "Result Limit", min_value=10, max_value=1000, 
                        value=500, step=50, help="Maximum number of results to display"
                    )
                    custom_filters['limit'] = result_limit
            
            # Get available symbols from database (フィルター考慮・改善版)
            try:
                if selected_preset != "User Defined":
                    # プリセット適用時：フィルター済みデータから銘柄取得
                    filtered_data = self.db.apply_filter_preset(selected_preset)
                    if not filtered_data.empty:
                        available_symbols = sorted(filtered_data['symbol'].unique().tolist())
                    else:
                        available_symbols = []
                elif custom_filters and any(
                    v is not None and v != "" and v != 0 and v is not False 
                    for k, v in custom_filters.items() 
                    if k not in ['limit', 'sort_by', 'sort_order']  # デフォルト値は除外
                ):
                    # カスタムフィルター適用時（実際にフィルター設定がある場合のみ）
                    filtered_data = self.db.get_filtered_analyses(**custom_filters)
                    if not filtered_data.empty:
                        available_symbols = sorted(filtered_data['symbol'].unique().tolist())
                    else:
                        available_symbols = []
                else:
                    # フィルターなし（初期状態またはカスタムだが設定なし）
                    # 🚀 パフォーマンス最適化: 銘柄リストのみ取得（全データ不要）
                    if 'available_symbols_cache' not in st.session_state:
                        # 初回のみ：銘柄リストをキャッシュ
                        all_analyses = self.db.get_recent_analyses(limit=100)  # 最小限のデータ
                        if all_analyses.empty:
                            st.warning("No analysis data available")
                            return None
                        st.session_state.available_symbols_cache = sorted(all_analyses['symbol'].unique().tolist())
                    available_symbols = st.session_state.available_symbols_cache
                    
            except Exception as e:
                st.error(f"Failed to load analysis data: {str(e)}")
                return None
            
            if not available_symbols:
                st.warning("No symbols match current filter criteria")
                return None
            
            # Get categorized symbols
            categorized_symbols = self.get_symbols_by_category()
            
            # Symbol selection with categories
            st.subheader("📈 Select Symbol")
            
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
            
            # 表示期間設定（改善版）
            st.subheader("📅 Displaying Period")
            
            # 分析基準日の範囲を取得
            try:
                # 🚀 パフォーマンス最適化: 必要最小限のデータ取得
                all_analyses = self.db.get_recent_analyses(symbol=selected_symbol, limit=100)
                if not all_analyses.empty:
                    # 分析基準日の取得（優先順位: analysis_basis_date > data_period_end）
                    basis_dates = []
                    for _, row in all_analyses.iterrows():
                        if pd.notna(row.get('analysis_basis_date')):
                            basis_dates.append(pd.to_datetime(row['analysis_basis_date']))
                        elif pd.notna(row.get('data_period_end')):
                            basis_dates.append(pd.to_datetime(row['data_period_end']))
                    
                    if basis_dates:
                        basis_dates = sorted(basis_dates)
                        min_date = basis_dates[0].date()
                        max_date = basis_dates[-1].date()
                        
                        # デフォルト値の計算
                        default_end = max_date
                        default_start = max(min_date, max_date - timedelta(days=120))  # 4ヶ月前
                        
                        # 期間選択UI（改善版）
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            start_date = st.date_input(
                                "From",
                                value=default_start,
                                min_value=min_date,
                                max_value=max_date,
                                help="Start date for analysis period (oldest fitting basis date to include)"
                            )
                            st.caption("*Start of analysis basis date range*")
                        
                        with col2:
                            end_date = st.date_input(
                                "To",
                                value=default_end,
                                min_value=min_date,
                                max_value=max_date,
                                help="End date for analysis period (newest fitting basis date to include)"
                            )
                            st.caption("*End of analysis basis date range*")
                        
                        # 日付範囲の妥当性チェック
                        if start_date > end_date:
                            st.error("Start date must be earlier than end date")
                            start_date, end_date = default_start, default_end
                        
                        period_selection = {
                            'start_date': start_date,
                            'end_date': end_date
                        }
                    else:
                        st.warning("No valid basis dates found")
                        period_selection = None
                else:
                    st.warning("No analysis data for period selection")
                    period_selection = None
            except Exception as e:
                st.error(f"Error loading period data: {str(e)}")
                period_selection = None
            
            # フィルター設定をまとめて返却（Legacy Priority Filter削除）
            filter_settings = {
                'preset': preset_config,
                'preset_name': selected_preset if selected_preset != "User Defined" else None,
                'custom': custom_filters if selected_preset == "User Defined" else {},
                'legacy_priority': None  # 廃止済み
            }
            
            return selected_symbol, period_selection, filter_settings
    
    def get_symbol_price_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Get symbol price data with caching for API efficiency"""
        try:
            # 🔧 API効率化: キャッシュキーを生成
            cache_key = f"{symbol}_{start_date}_{end_date}"
            
            # キャッシュから取得を試行
            if cache_key in st.session_state.price_data_cache:
                cached_data = st.session_state.price_data_cache[cache_key]
                cache_info = st.session_state.cache_metadata.get(cache_key, {})
                print(f"🔄 キャッシュからデータ取得: {symbol} ({cache_info.get('source', 'unknown')}) - {len(cached_data)}日分")
                return cached_data
            
            # データベースから最新の分析結果を取得してデータソースを特定
            latest_analysis = self.db.get_recent_analyses(symbol=symbol, limit=1)
            preferred_source = None
            if not latest_analysis.empty:
                data_source = latest_analysis.iloc[0].get('data_source')
                if data_source:
                    # 安定版v1.0: FRED優先 → Twelve Data補完
                    preferred_source = 'fred' if data_source == 'fred' else 'twelvedata'
            
            # 統合データクライアントからフォールバック付きでデータ取得
            data, source_used = self.data_client.get_data_with_fallback(
                symbol, start_date, end_date, preferred_source=preferred_source
            )
            
            if data is not None and len(data) > 0:
                # 🔧 API効率化: データをキャッシュに保存
                st.session_state.price_data_cache[cache_key] = data
                st.session_state.cache_metadata[cache_key] = {
                    'source': source_used,
                    'cached_at': pd.Timestamp.now(),
                    'size': len(data)
                }
                print(f"✅ API取得成功・キャッシュ保存: {symbol} ({source_used}) - {len(data)}日分")
                return data
            else:
                print(f"❌ データ取得失敗: {symbol}")
                return None
            
        except Exception as e:
            st.error(f"データ取得エラー: {str(e)}")
            return None
    
    def compute_extended_lppl_fit(self, prices: pd.Series, params: Dict, basis_date: pd.Timestamp, 
                                  target_date: pd.Timestamp) -> Dict:
        """Generate extended LPPL fit for Future Period display"""
        try:
            # 元データの期間
            data_start = prices.index[0]
            data_end = prices.index[-1]
            
            # Future Period用の日付範囲を生成
            future_dates = pd.date_range(start=basis_date, end=target_date, freq='D')
            future_dates = future_dates[future_dates > basis_date]  # 基準日は除外
            
            if len(future_dates) == 0:
                return None
            
            # 正規化された時間軸を計算
            total_days = (data_end - data_start).days
            future_days = [(date - data_start).days for date in future_dates]
            t_future = np.array(future_days) / total_days
            
            # LPPLパラメータ
            tc = params['tc']
            beta = params['beta']
            omega = params['omega']
            phi = params['phi']
            A = params['A']
            B = params['B']
            C = params['C']
            
            # Future Period用のLPPL計算
            tau_future = tc - t_future
            tau_power_beta = np.power(np.abs(tau_future), beta)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                log_term = np.log(np.abs(tau_future))
                oscillation = np.cos(omega * log_term + phi)
            
            fitted_log_prices = A + B * tau_power_beta + C * tau_power_beta * oscillation
            fitted_prices = np.exp(fitted_log_prices)
            
            # 正規化（元の価格範囲ベース）
            price_min, price_max = prices.min(), prices.max()
            normalized_fitted = (fitted_prices - price_min) / (price_max - price_min)
            
            return {
                'future_dates': future_dates,
                'fitted_prices': fitted_prices,
                'normalized_fitted': normalized_fitted
            }
            
        except Exception as e:
            print(f"⚠️ Extended LPPL calculation error: {str(e)}")
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
        """Tab 3: LPPL Fitting Plot - Visual analysis of LPPL model fitting results"""
        
        st.header(f"📈 {symbol} - LPPL Fitting Plot")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        # Analysis Data Period - Enhanced version matching clustering tab
        st.subheader("📅 Analysis Data Period")
        st.caption("解析データの対象とする期間")
        
        # データ範囲の計算（From/Toの下に表示用）
        original_data = self.get_symbol_analysis_data(symbol, limit=1000)  # フィルタ前の全データ
        if not original_data.empty:
            original_data['analysis_basis_date'] = pd.to_datetime(original_data['analysis_basis_date'])
            full_min_date = original_data['analysis_basis_date'].min()
            full_max_date = original_data['analysis_basis_date'].max()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'lppl_from_date' not in st.session_state:
                st.session_state.lppl_from_date = analysis_data['analysis_basis_date'].min().date()
            from_date = st.date_input("From", st.session_state.lppl_from_date, key='lppl_from_date_input')
            st.session_state.lppl_from_date = from_date
            # Oldest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Oldest Analysis: {full_min_date.strftime('%Y-%m-%d')}")
            
        with col2:
            if 'lppl_to_date' not in st.session_state:
                st.session_state.lppl_to_date = analysis_data['analysis_basis_date'].max().date()
            to_date = st.date_input("To", st.session_state.lppl_to_date, key='lppl_to_date_input')
            st.session_state.lppl_to_date = to_date
            # Latest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Latest Analysis: {full_max_date.strftime('%Y-%m-%d')}")
        
        # 📊 選択期間の情報表示
        if not original_data.empty:
            selected_min = pd.to_datetime(from_date)
            selected_max = pd.to_datetime(to_date)
            
            # 期間の割合計算
            total_days = (full_max_date - full_min_date).days
            selected_duration = (selected_max - selected_min).days
            start_offset = (selected_min - full_min_date).days if total_days > 0 else 0
            selected_ratio = selected_duration / total_days if total_days > 0 else 1.0
            
            # テキスト形式で期間情報を表示
            st.info(f"📅 **Analysis Period Summary**: {selected_duration} days selected ({selected_ratio*100:.1f}% of available data) | Position: Day {start_offset+1}-{start_offset+selected_duration} of {total_days} total days")
        
        st.markdown("---")
        
        # Display Period フィルタリング
        analysis_data['analysis_basis_date'] = pd.to_datetime(analysis_data['analysis_basis_date'])
        from_datetime = pd.to_datetime(from_date)
        to_datetime = pd.to_datetime(to_date)
        
        date_mask = (analysis_data['analysis_basis_date'] >= from_datetime) & (analysis_data['analysis_basis_date'] <= to_datetime)
        analysis_data = analysis_data[date_mask].copy()
        
        if len(analysis_data) == 0:
            st.warning(f"No data available for selected period: {from_date} to {to_date}")
            return
        
        st.markdown("---")
        st.info(f"**LPPL Analysis Settings**: Period: {from_date} to {to_date} ({len(analysis_data)} analyses)")
        st.markdown("---")
        
        # デバッグ用のプロット分割オプション
        debug_mode = st.checkbox("🔍 Debug Mode: Split Integrated Plot into Two Separate Views", 
                                 value=False, 
                                 help="分析プロット：最新データの詳細確認、統合プロット：期間範囲の複数予測表示")
        
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
            # 🔧 FRED API修正: Timestamp オブジェクトを文字列に安全変換
            data_start = self._ensure_date_string(latest['data_period_start'])
            data_end = self._ensure_date_string(latest['data_period_end'])
            
            # 表示数を事前に定義
            display_count = len(analysis_data)
            
            # 🔧 API効率化改善: 全ての分析期間をカバーする完全な期間を計算
            # Individual Analysis で必要な全期間を事前に把握
            min_data_start = data_start
            max_pred_date = data_end
            
            for _, row in analysis_data.head(display_count).iterrows():
                # 各分析の開始日を含める
                row_start = self._ensure_date_string(row.get('data_period_start'))
                if row_start and row_start < min_data_start:
                    min_data_start = row_start
                    
                # 各分析の予測日を含める
                if pd.notna(row.get('tc')):
                    # 🔧 FRED API修正: 日付変換関数適用
                    row_start = self._ensure_date_string(row.get('data_period_start', data_start))
                    row_end = self._ensure_date_string(row.get('data_period_end', data_end))
                    if row_start and row_end:
                        pred_date = self.convert_tc_to_real_date(row.get('tc'), row_start, row_end)
                        if pred_date > pd.to_datetime(max_pred_date):
                            max_pred_date = pred_date.strftime('%Y-%m-%d')
            
            # 最小開始日を使用（全期間をカバー）
            data_start = min_data_start
            print(f"🔧 全期間カバー範囲: {data_start} to {max_pred_date} (全{display_count}件対応)")
            
            # Future Period表示のためにさらに期間を拡張（予測日+60日）
            # 🔧 レート制限対応: 極端に遠い予測日を制限
            max_pred_dt = pd.to_datetime(max_pred_date)
            max_allowed_dt = datetime.now() + timedelta(days=365)  # 最大1年先まで制限
            
            if max_pred_dt > max_allowed_dt:
                print(f"⚠️ 予測日制限: {max_pred_dt.date()} → {max_allowed_dt.date()} (レート制限対応)")
                max_pred_dt = max_allowed_dt
            
            extended_end = (max_pred_dt + timedelta(days=60)).strftime('%Y-%m-%d')
            print(f"🔍 Getting extended price data for {symbol}: {data_start} to {extended_end}")
            
            # 実際の価格データを取得（拡張期間）
            price_data = self.get_symbol_price_data(symbol, data_start, extended_end)
            
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
                    
                    # 最新のフィッティング基準日を取得
                    latest_fitting_basis = latest.get('analysis_basis_date', data_end)
                    latest_fitting_basis_dt = pd.to_datetime(latest_fitting_basis)
                    
                    # LPPLフィット（基準日まで）- 最新プロットのみに適用
                    basis_mask = price_data.index <= latest_fitting_basis_dt
                    fig.add_trace(go.Scatter(
                        x=price_data.index[basis_mask],
                        y=lppl_results['normalized_fitted'][basis_mask],
                        mode='lines',
                        name='LPPL Fit (Basis Period)',
                        line=dict(color='red', width=2.5)
                    ))
                    
                    # LPPLフィット（基準日以降）- Future Period表示
                    # Individual Analysisと同じ方式で実装
                    if pd.notna(latest.get('tc')):
                        # Individual Analysisと同じ方式でtc変換
                        integrated_pred_date = self.convert_tc_to_real_date(
                            latest['tc'], data_start, data_end)
                        
                        # Individual Analysisと同じ方式でextended LPPL計算
                        extended_lppl = self.compute_extended_lppl_fit(
                            price_data['Close'], lppl_params, 
                            latest_fitting_basis_dt, integrated_pred_date + timedelta(days=30))
                        
                        if extended_lppl and len(extended_lppl['future_dates']) > 0:
                            fig.add_trace(go.Scatter(
                                x=extended_lppl['future_dates'],
                                y=extended_lppl['normalized_fitted'],
                                mode='lines',
                                name='LPPL Fit (Future Period)',
                                line=dict(color='orange', width=2.5, dash='dot'),
                                opacity=0.8
                            ))
                        else:
                            # フォールバック：基準日以降の既存データのみ
                            future_mask = price_data.index > latest_fitting_basis_dt
                            if future_mask.any():
                                fig.add_trace(go.Scatter(
                                    x=price_data.index[future_mask],
                                    y=lppl_results['normalized_fitted'][future_mask],
                                    mode='lines',
                                    name='LPPL Fit (Future Period)',
                                    line=dict(color='orange', width=2.5, dash='dot')
                                ))
                    
                    # Number of Results で指定された数の予測線を縦線で表示
                    # Analysis Period Selectionに基づいてフィルタされたanalysis_dataの件数を使用
                    display_count = len(analysis_data)  # 期間フィルタ済みのデータ全件表示
                    
                    # フィッティング基準日の取得とソート（グラデーション用）
                    basis_dates = []
                    for _, pred in analysis_data.head(display_count).iterrows():
                        if pd.notna(pred.get('analysis_basis_date')):
                            basis_dates.append(pd.to_datetime(pred['analysis_basis_date']))
                        elif pd.notna(pred.get('data_period_end')):
                            basis_dates.append(pd.to_datetime(pred['data_period_end']))
                        else:
                            basis_dates.append(pd.to_datetime('1900-01-01'))  # フォールバック
                    
                    # 基準日の範囲を計算（グラデーション用）
                    if len([d for d in basis_dates if d.year > 1900]) > 1:
                        valid_dates = [d for d in basis_dates if d.year > 1900]
                        min_date = min(valid_dates)
                        max_date = max(valid_dates)
                        date_range = (max_date - min_date).days
                    else:
                        date_range = 0
                    
                    for i, (_, pred) in enumerate(analysis_data.head(display_count).iterrows()):
                        if pd.notna(pred.get('tc')):
                            pred_tc = pred['tc']
                            pred_start = pred.get('data_period_start', data_start)
                            pred_end = pred.get('data_period_end', data_end)
                            
                            if pred_start and pred_end:
                                pred_date = self.convert_tc_to_real_date(pred_tc, pred_start, pred_end)
                                
                                # フィッティング基準日を取得
                                fitting_basis_date = basis_dates[i] if i < len(basis_dates) else pd.to_datetime('1900-01-01')
                                
                                # グラデーション色の計算（基準日ベース）
                                if date_range > 0 and fitting_basis_date.year > 1900:
                                    days_from_oldest = (fitting_basis_date - min_date).days
                                    gradient_ratio = days_from_oldest / date_range
                                    # 古い予測：青系、新しい予測：赤系
                                    red = int(50 + gradient_ratio * 200)  # 50-250
                                    green = int(50 + (1-gradient_ratio) * 100)  # 50-150
                                    blue = int(250 - gradient_ratio * 200)  # 50-250
                                    alpha = 0.8
                                else:
                                    # フォールバック色
                                    red, green, blue = 255, 150, 150
                                    alpha = 0.7
                                
                                # 予測線を縦線で表示
                                fig.add_shape(
                                    type="line",
                                    x0=pred_date,
                                    x1=pred_date,
                                    y0=0,
                                    y1=1,
                                    line=dict(
                                        color=f'rgba({red}, {green}, {blue}, {alpha})', 
                                        width=2, 
                                        dash="dash"
                                    )
                                )
                                
                                # 予測線のラベル（月日のみ表示）
                                label_text = pred_date.strftime('%m/%d')
                                fig.add_annotation(
                                    x=pred_date,
                                    y=0.95 - i * 0.05,
                                    text=label_text,
                                    showarrow=False,
                                    font=dict(size=10, color='white'),
                                    bgcolor=f"rgba(0, 0, 0, 0.7)",  # 黒系背景
                                    bordercolor=f'rgba({red}, {green}, {blue}, 0.8)',
                                    borderwidth=1
                                )
                    
                    # グラデーション凡例を追加（散布図として表示）
                    if date_range > 0 and len([d for d in basis_dates if d.year > 1900]) > 1:
                        # グラデーション用のダミーデータ
                        legend_dates = pd.date_range(min_date, max_date, periods=5)
                        legend_y = [0.85, 0.82, 0.79, 0.76, 0.73]  # Y座標
                        legend_colors = []
                        
                        for j, legend_date in enumerate(legend_dates):
                            days_from_oldest = (legend_date - min_date).days
                            gradient_ratio = days_from_oldest / date_range
                            red = int(50 + gradient_ratio * 200)
                            green = int(50 + (1-gradient_ratio) * 100)
                            blue = int(250 - gradient_ratio * 200)
                            legend_colors.append(f'rgb({red}, {green}, {blue})')
                        
                        # 凡例用の散布図を追加
                        fig.add_trace(go.Scatter(
                            x=[price_data.index.min()] * len(legend_dates),
                            y=legend_y,
                            mode='markers+text',
                            marker=dict(size=15, color=legend_colors),
                            text=[f"{date.strftime('%Y-%m')}: {(date-min_date).days}d" for date in legend_dates],
                            textposition='middle right',
                            textfont=dict(color='white', size=9),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                    
                    # グラフのレイアウト設定
                    fig.update_layout(
                        title=f"{symbol} - Normalized Price Data with LPPL Predictions",
                        xaxis_title="Date",
                        yaxis_title="Normalized Price",
                        height=600,
                        hovermode='x unified',
                        showlegend=True,
                        # 背景色を黒系に変更
                        plot_bgcolor='rgba(20, 20, 30, 0.95)',
                        paper_bgcolor='rgba(15, 15, 25, 0.95)',
                        font=dict(color='white'),
                        # x軸の範囲を予測線まで拡張
                        xaxis=dict(
                            range=[
                                price_data.index.min(),
                                max(price_data.index.max(), 
                                    max([self.convert_tc_to_real_date(row.get('tc', 1.0), 
                                                                     row.get('data_period_start', data_start),
                                                                     row.get('data_period_end', data_end)) 
                                         for _, row in analysis_data.head(display_count).iterrows() 
                                         if pd.notna(row.get('tc'))], default=price_data.index.max()))
                            ],
                            gridcolor='rgba(100, 100, 100, 0.2)',
                            showgrid=True,
                            gridwidth=1
                        ),
                        yaxis=dict(
                            gridcolor='rgba(100, 100, 100, 0.2)',
                            showgrid=True,
                            gridwidth=1
                        )
                    )
                    
                    # 通常モード：2つのプロットを縦並びで表示
                    st.markdown("---")
                    st.subheader("📊 Analysis Views: Latest & Integrated Predictions")
                    
                    # Latest Analysis Details（上部）- 常に最新のデータを表示
                    st.markdown("**🔍 Latest Analysis Details**")
                    st.caption("Display Period範囲内での最新フィッティング結果の詳細表示")
                    
                    # 🔧 Display Period連携修正: フィルタ済みanalysis_data範囲内で最新データ取得（2025-08-11）
                    # Display Periodでフィルタされたanalysis_data内の最新データを使用
                    if not analysis_data.empty:
                        absolute_latest = analysis_data.iloc[0]  # analysis_dataは既にフィルタ済み
                    else:
                        absolute_latest = latest  # フォールバック
                    
                    # 最新分析プロット作成（absolute_latestを使用）
                    latest_fig = go.Figure()
                    
                    # 絶対最新データ用のパラメータと予測日を計算
                    # 🔧 FRED API修正: Timestamp オブジェクトを文字列に安全変換
                    absolute_latest_data_start = self._ensure_date_string(absolute_latest.get('data_period_start'))
                    absolute_latest_data_end = self._ensure_date_string(absolute_latest.get('data_period_end'))
                    absolute_latest_fitting_basis = absolute_latest.get('analysis_basis_date', absolute_latest_data_end)
                    absolute_latest_fitting_basis_dt = pd.to_datetime(absolute_latest_fitting_basis)
                    
                    # 絶対最新の予測日計算
                    if pd.notna(absolute_latest.get('tc')):
                        absolute_latest_pred_date = self.convert_tc_to_real_date(
                            absolute_latest['tc'], absolute_latest_data_start, absolute_latest_data_end)
                    else:
                        absolute_latest_pred_date = None
                    
                    # 絶対最新用のLPPLパラメータ
                    absolute_latest_lppl_params = {
                        'tc': absolute_latest.get('tc', 1.0),
                        'beta': absolute_latest.get('beta', 0.33),
                        'omega': absolute_latest.get('omega', 6.0),
                        'phi': absolute_latest.get('phi', 0.0),
                        'A': absolute_latest.get('A', 0.0),
                        'B': absolute_latest.get('B', 0.0),
                        'C': absolute_latest.get('C', 0.0)
                    }
                    
                    # 絶対最新データに基づくprice_dataとLPPL結果を取得
                    absolute_latest_price_data = self.get_symbol_price_data(symbol, absolute_latest_data_start, absolute_latest_data_end)
                    absolute_latest_lppl_results = None
                    latest_extended_lppl = None
                    
                    if absolute_latest_price_data is not None:
                        absolute_latest_lppl_results = self.compute_lppl_fit(absolute_latest_price_data['Close'], absolute_latest_lppl_params)
                        
                        if absolute_latest_lppl_results:
                            # 絶対最新の生データ
                            latest_fig.add_trace(go.Scatter(
                                x=absolute_latest_price_data.index,
                                y=absolute_latest_lppl_results['normalized_prices'],
                                mode='lines',
                                name='Market Data',
                                line=dict(color='lightblue', width=2)
                            ))
                            
                            # 絶対最新のLPPLフィッティング（基準日まで）
                            basis_mask = absolute_latest_price_data.index <= absolute_latest_fitting_basis_dt
                            latest_fig.add_trace(go.Scatter(
                                x=absolute_latest_price_data.index[basis_mask],
                                y=absolute_latest_lppl_results['normalized_fitted'][basis_mask],
                                mode='lines',
                                name='LPPL Fit (Basis Period)',
                                line=dict(color='red', width=2.5)
                            ))
                            
                            # 絶対最新のLPPL Future Period
                            if absolute_latest_pred_date is not None:
                                latest_extended_lppl = self.compute_extended_lppl_fit(
                                    absolute_latest_price_data['Close'], absolute_latest_lppl_params, 
                                    absolute_latest_fitting_basis_dt, absolute_latest_pred_date + timedelta(days=30))
                    
                            # Future Period表示
                            if latest_extended_lppl and len(latest_extended_lppl['future_dates']) > 0:
                                latest_fig.add_trace(go.Scatter(
                                    x=latest_extended_lppl['future_dates'],
                                    y=latest_extended_lppl['normalized_fitted'],
                                    mode='lines',
                                    name='LPPL Fit (Future Period)',
                                    line=dict(color='orange', width=2.5, dash='dot'),
                                    opacity=0.8
                                ))
                            
                            # 絶対最新の予測日縦線（最後に描画してFuture Periodより上に表示）
                            if absolute_latest_pred_date is not None:
                                # Y軸の実際の範囲を計算
                                y_min = absolute_latest_lppl_results['normalized_prices'].min()
                                y_max = absolute_latest_lppl_results['normalized_prices'].max()
                                
                                # LPPLフィットの範囲も考慮
                                y_min = min(y_min, absolute_latest_lppl_results['normalized_fitted'].min())
                                y_max = max(y_max, absolute_latest_lppl_results['normalized_fitted'].max())
                                
                                # Future Periodがある場合はその範囲も考慮
                                if latest_extended_lppl and len(latest_extended_lppl['future_dates']) > 0:
                                    y_max = max(y_max, max(latest_extended_lppl['normalized_fitted']))
                                    y_min = min(y_min, min(latest_extended_lppl['normalized_fitted']))
                                
                                # 少し余裕を持たせる
                                y_range = y_max - y_min
                                y_min_extended = y_min - y_range * 0.02
                                y_max_extended = y_max + y_range * 0.02
                                
                                latest_fig.add_shape(
                                    type="line",
                                    x0=absolute_latest_pred_date, x1=absolute_latest_pred_date,
                                    y0=y_min_extended, y1=y_max_extended,
                                    line=dict(color='red', width=3, dash="dash"),  # 赤系に変更
                                    layer='above'  # 他の要素より上に描画
                                )
                                latest_fig.add_annotation(
                                    x=absolute_latest_pred_date, 
                                    y=y_max_extended * 0.95,  # 実際の範囲の上部に配置
                                    text=f"Latest Prediction\n{absolute_latest_pred_date.strftime('%m/%d')}",
                                    showarrow=False, font=dict(color='red', size=11),
                                    bgcolor="rgba(255, 200, 200, 0.3)"  # 赤系の背景
                                )
                            
                            # X軸範囲を絶対最新の予測日+30日まで拡張
                            x_range_end = absolute_latest_pred_date + timedelta(days=30) if absolute_latest_pred_date else absolute_latest_price_data.index.max()
                            latest_fig.update_layout(
                                title="Latest Analysis (Most Recent - Absolute)",
                                height=400,
                                plot_bgcolor='rgba(20, 30, 40, 0.95)',
                                paper_bgcolor='rgba(15, 25, 35, 0.95)',
                                font=dict(color='white', size=10),
                                xaxis=dict(
                                    gridcolor='rgba(100, 100, 100, 0.2)',
                                    showgrid=True,
                                    gridwidth=1,
                                    range=[absolute_latest_price_data.index.min(), x_range_end]
                                ),
                                yaxis=dict(
                                    gridcolor='rgba(100, 100, 100, 0.2)',
                                    showgrid=True,
                                    gridwidth=1
                                )
                            )
                    
                    # フォールバック用のレイアウト（データが取得できない場合）
                    if len(latest_fig.data) == 0:
                        latest_fig.update_layout(
                            title="Latest Analysis - Data Not Available",
                            height=400,
                            plot_bgcolor='rgba(20, 30, 40, 0.95)',
                            paper_bgcolor='rgba(15, 25, 35, 0.95)',
                            font=dict(color='white', size=10)
                        )
                    
                    # Latest Analysis プロットを表示
                    st.plotly_chart(latest_fig, use_container_width=True)
                    
                    # Integrated Predictions（統合予測表示）
                    st.markdown("**📈 Integrated Predictions**")
                    st.caption("統合予測表示 - Display Period範囲内の全分析結果による予測統合")
                    
                    # Latest Analysis基準での新しいIntegrated Predictions
                    if absolute_latest_price_data is not None:
                        integrated_fig = go.Figure()
                        
                        # Latest Analysis基準での市場データ
                        integrated_fig.add_trace(go.Scatter(
                            x=absolute_latest_price_data.index,
                            y=absolute_latest_lppl_results['normalized_prices'],
                            mode='lines',
                            name='Market Data (Latest Basis)',
                            line=dict(color='lightblue', width=2)
                        ))
                        
                        # 期間内の複数予測日を収集（後で描画）
                        prediction_colors = ['red', 'orange', 'green', 'purple', 'brown', 'cyan', 'magenta', 'yellow', 'lime', 'pink']
                        prediction_count = 0
                        prediction_lines = []  # 後で描画するための縦線情報を保存
                        
                        for i, (_, analysis) in enumerate(analysis_data.iterrows()):
                            if pd.notna(analysis.get('tc')):
                                # 各分析の予測日を計算
                                analysis_data_start = analysis.get('data_period_start', absolute_latest_data_start)
                                analysis_data_end = analysis.get('data_period_end', absolute_latest_data_end)
                                analysis_pred_date = self.convert_tc_to_real_date(
                                    analysis['tc'], analysis_data_start, analysis_data_end)
                                
                                color = prediction_colors[prediction_count % len(prediction_colors)]
                                # 縦線情報を保存（後で描画）
                                prediction_lines.append({
                                    'date': analysis_pred_date,
                                    'color': color,
                                    'index': prediction_count
                                })
                                
                                prediction_count += 1
                        
                        # Latest Analysis基準でのLPPLフィッティング
                        if absolute_latest_lppl_results:
                            # Basis Period
                            basis_mask = absolute_latest_price_data.index <= absolute_latest_fitting_basis_dt
                            integrated_fig.add_trace(go.Scatter(
                                x=absolute_latest_price_data.index[basis_mask],
                                y=absolute_latest_lppl_results['normalized_fitted'][basis_mask],
                                mode='lines',
                                name='LPPL Fit (Latest Basis)',
                                line=dict(color='red', width=2.5)
                            ))
                            
                            # Future Period
                            if latest_extended_lppl and len(latest_extended_lppl['future_dates']) > 0:
                                integrated_fig.add_trace(go.Scatter(
                                    x=latest_extended_lppl['future_dates'],
                                    y=latest_extended_lppl['normalized_fitted'],
                                    mode='lines',
                                    name='LPPL Fit (Future Period)',
                                    line=dict(color='orange', width=2.5, dash='dot'),
                                    opacity=0.8
                                ))
                        
                        # 縦線を最後に描画（Future Periodより上に表示）
                        if absolute_latest_lppl_results:
                            # Y軸の実際の範囲を計算
                            y_min = absolute_latest_lppl_results['normalized_prices'].min()
                            y_max = absolute_latest_lppl_results['normalized_prices'].max()
                            y_min = min(y_min, absolute_latest_lppl_results['normalized_fitted'].min())
                            y_max = max(y_max, absolute_latest_lppl_results['normalized_fitted'].max())
                            
                            if latest_extended_lppl and len(latest_extended_lppl['future_dates']) > 0:
                                y_max = max(y_max, max(latest_extended_lppl['normalized_fitted']))
                                y_min = min(y_min, min(latest_extended_lppl['normalized_fitted']))
                            
                            y_range = y_max - y_min
                            y_min_extended = y_min - y_range * 0.02
                            y_max_extended = y_max + y_range * 0.02
                            
                            # 保存した縦線情報を描画
                            for pred_info in prediction_lines:
                                integrated_fig.add_shape(
                                    type="line",
                                    x0=pred_info['date'], x1=pred_info['date'],
                                    y0=y_min_extended, y1=y_max_extended,
                                    line=dict(color=pred_info['color'], width=2, dash="dash"),
                                    layer='above'  # 他の要素より上に描画
                                )
                                
                                # ラベルも追加
                                y_pos = y_max_extended * (0.95 - (pred_info['index'] % 10) * 0.03)
                                integrated_fig.add_annotation(
                                    x=pred_info['date'], 
                                    y=y_pos,
                                    text=f"{pred_info['date'].strftime('%m/%d')}",
                                    showarrow=False, 
                                    font=dict(color='white', size=9),
                                    bgcolor="rgba(0, 0, 0, 0.8)"
                                )
                        
                        # レイアウト設定
                        x_range_end = absolute_latest_pred_date + timedelta(days=60) if absolute_latest_pred_date else absolute_latest_price_data.index.max() + timedelta(days=30)
                        integrated_fig.update_layout(
                            title="Integrated Predictions (Latest Analysis Basis)",
                            height=400,
                            plot_bgcolor='rgba(20, 30, 40, 0.95)',
                            paper_bgcolor='rgba(15, 25, 35, 0.95)',
                            font=dict(color='white', size=10),
                            xaxis=dict(
                                gridcolor='rgba(100, 100, 100, 0.2)',
                                showgrid=True,
                                gridwidth=1,
                                range=[absolute_latest_price_data.index.min(), x_range_end]
                            ),
                            yaxis=dict(
                                gridcolor='rgba(100, 100, 100, 0.2)',
                                showgrid=True,
                                gridwidth=1
                            )
                        )
                        
                        st.plotly_chart(integrated_fig, use_container_width=True)
                        
                        # 説明
                        st.info(f"📊 Showing latest analysis basis with {prediction_count} integrated predictions from selected period")
                    
                    # デバッグモード：詳細分析プロット表示
                    if debug_mode:
                        st.markdown("---")
                        st.subheader("🔍 Debug Mode: Additional Detailed Analysis Plots")
                        
                        # Plot 1: 最新データの詳細分析プロット
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**📊 Debug Plot 1: Alternative Latest View**")
                            st.caption("デバッグ用：最新マーケット生データ + 最新LPPL + 最新予測日（別実装確認）")
                            
                            latest_fig = go.Figure()
                            
                            # 最新の生データ
                            latest_fig.add_trace(go.Scatter(
                                x=price_data.index,
                                y=lppl_results['normalized_prices'],
                                mode='lines',
                                name='Latest Market Data',
                                line=dict(color='cyan', width=2)
                            ))
                            
                            # 最新のLPPLフィッティング（全期間）
                            latest_fig.add_trace(go.Scatter(
                                x=price_data.index,
                                y=lppl_results['normalized_fitted'],
                                mode='lines',
                                name='Latest LPPL Fit (Full)',
                                line=dict(color='magenta', width=2.5)
                            ))
                            
                            # 最新の予測日
                            if pd.notna(latest.get('tc')):
                                latest_pred_date = self.convert_tc_to_real_date(
                                    latest['tc'], data_start, data_end)
                                latest_fig.add_shape(
                                    type="line",
                                    x0=latest_pred_date, x1=latest_pred_date,
                                    y0=0, y1=1,
                                    line=dict(color='yellow', width=3, dash="solid")
                                )
                                latest_fig.add_annotation(
                                    x=latest_pred_date, y=0.9,
                                    text=f"Latest Prediction\n{latest_pred_date.strftime('%m/%d')}",
                                    showarrow=False, font=dict(color='yellow', size=12),
                                    bgcolor="rgba(255, 255, 0, 0.3)"
                                )
                            
                            latest_fig.update_layout(
                                title="Latest Analysis (Most Recent Fitting)",
                                height=400,
                                plot_bgcolor='rgba(20, 30, 20, 0.95)',
                                font=dict(color='white', size=10)
                            )
                            
                            st.plotly_chart(latest_fig, use_container_width=True)
                        
                        with col2:
                            st.markdown("**📊 Debug Plot 2: Alternative Integration View**")
                            st.caption("デバッグ用：期間範囲データ + 最近LPPL + 複数予測日（別実装確認）")
                            
                            integration_fig = go.Figure()
                            
                            # 期間範囲の生データ
                            integration_fig.add_trace(go.Scatter(
                                x=price_data.index,
                                y=lppl_results['normalized_prices'],
                                mode='lines',
                                name='Period Market Data',
                                line=dict(color='lightblue', width=2)
                            ))
                            
                            # サイドバー期間内の最も最近のフィッティング
                            recent_analysis = analysis_data.iloc[0]  # 最も最近のもの
                            if pd.notna(recent_analysis.get('tc')):
                                recent_params = {
                                    'tc': recent_analysis.get('tc', 1.0),
                                    'beta': recent_analysis.get('beta', 0.33),
                                    'omega': recent_analysis.get('omega', 6.0),
                                    'phi': recent_analysis.get('phi', 0.0),
                                    'A': recent_analysis.get('A', 0.0),
                                    'B': recent_analysis.get('B', 0.0),
                                    'C': recent_analysis.get('C', 0.0)
                                }
                                recent_lppl = self.compute_lppl_fit(price_data['Close'], recent_params)
                                
                                if recent_lppl:
                                    integration_fig.add_trace(go.Scatter(
                                        x=price_data.index,
                                        y=recent_lppl['normalized_fitted'],
                                        mode='lines',
                                        name='Recent Period LPPL Fit',
                                        line=dict(color='orange', width=2.5)
                                    ))
                            
                            # 期間内の複数予測線
                            display_count = min(len(analysis_data), 5)
                            for i, (_, pred) in enumerate(analysis_data.head(display_count).iterrows()):
                                if pd.notna(pred.get('tc')):
                                    pred_date = self.convert_tc_to_real_date(
                                        pred['tc'], pred.get('data_period_start', data_start), 
                                        pred.get('data_period_end', data_end))
                                    
                                    color_alpha = 0.8 - i * 0.15
                                    integration_fig.add_shape(
                                        type="line",
                                        x0=pred_date, x1=pred_date,
                                        y0=0, y1=1,
                                        line=dict(color=f'rgba(255, 100, 100, {color_alpha})', 
                                                 width=2, dash="dash")
                                    )
                            
                            integration_fig.update_layout(
                                title="Integration Analysis (Period Range)",
                                height=400,
                                plot_bgcolor='rgba(30, 20, 20, 0.95)',
                                font=dict(color='white', size=10)
                            )
                            
                            st.plotly_chart(integration_fig, use_container_width=True)
                        
                        # デバッグ情報表示
                        with st.expander("🔍 Debug Information"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Latest Analysis Info:**")
                                st.write(f"- Analysis Basis Date: {latest.get('analysis_basis_date', 'N/A')}")
                                st.write(f"- Data Period: {data_start} to {data_end}")
                                st.write(f"- TC Value: {latest.get('tc', 'N/A')}")
                                st.write(f"- Extended End: {extended_end}")
                                
                            with col2:
                                st.write("**Price Data Info:**")
                                st.write(f"- Price Data Range: {price_data.index.min()} to {price_data.index.max()}")
                                st.write(f"- Data Points: {len(price_data)}")
                                st.write(f"- Max Prediction Date: {max_pred_date}")
                    
                    # 予測サマリーを表形式で表示
                    st.subheader("🔮 Prediction Summary")
                    
                    # 表形式のデータを準備
                    summary_data = []
                    valid_predictions = analysis_data.head(display_count)
                    
                    for i, (_, pred) in enumerate(valid_predictions.iterrows()):
                        if pd.notna(pred.get('tc')):
                            pred_tc = pred['tc']
                            pred_start = pred.get('data_period_start', data_start)
                            pred_end = pred.get('data_period_end', data_end)
                            
                            if pred_start and pred_end:
                                pred_date = self.convert_tc_to_real_date(pred_tc, pred_start, pred_end)
                                # 安全な日付比較（pred_dateがすでにdatetime型のため修正不要だが念のため確認）
                                if isinstance(pred_date, str):
                                    pred_date = pd.to_datetime(pred_date)
                                days_from_today = (pred_date - datetime.now()).days
                                
                                # フィッティング基準日を表示
                                fitting_basis = pred.get('analysis_basis_date', pred.get('data_period_end', 'N/A'))
                                if fitting_basis != 'N/A':
                                    fitting_basis_dt = pd.to_datetime(fitting_basis)
                                    fitting_basis_str = fitting_basis_dt.strftime('%Y-%m-%d')
                                    days_from_basis = (pred_date - fitting_basis_dt).days
                                else:
                                    fitting_basis_str = 'N/A'
                                    days_from_basis = None
                                
                                # 2つの日数指標を準備
                                days_from_today_str = f"{days_from_today:+d}"
                                if days_from_basis is not None:
                                    days_from_basis_str = f"{days_from_basis:+d}"
                                else:
                                    days_from_basis_str = "N/A"
                                
                                summary_data.append({
                                    'Fitting Basis Date': fitting_basis_str,
                                    'Predicted Crash Date': pred_date.strftime('%Y-%m-%d'),
                                    'Days from Today': days_from_today_str,
                                    'Days from Basis': days_from_basis_str,
                                    'tc Value': f"{pred_tc:.4f}",
                                    'β (Beta)': f"{pred.get('beta', 0):.4f}",
                                    'ω (Omega)': f"{pred.get('omega', 0):.2f}",
                                    'R² Score': f"{pred.get('r_squared', 0):.4f}",
                                    'Quality': pred.get('quality', 'N/A')
                                })
                    
                    if summary_data:
                        # DataFrameに変換して表示
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(
                            summary_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Fitting Basis Date": st.column_config.TextColumn("Fitting Basis Date", help="Date when the fitting was performed"),
                                "Predicted Crash Date": st.column_config.TextColumn("Predicted Crash Date", help="Date when crash is predicted"),
                                "Days from Today": st.column_config.TextColumn("Days from Today", help="Days from current date to predicted crash"),
                                "Days from Basis": st.column_config.TextColumn("Days from Basis", help="Days from fitting basis date to predicted crash (prediction horizon)"),
                                "tc Value": st.column_config.TextColumn("tc Value", help="Critical time parameter"),
                                "β (Beta)": st.column_config.TextColumn("β (Beta)", help="Critical exponent (typically ~0.33)"),
                                "ω (Omega)": st.column_config.TextColumn("ω (Omega)", help="Angular frequency of oscillations"),
                                "R² Score": st.column_config.TextColumn("R² Score", help="Goodness of fit (higher is better)"),
                                "Quality": st.column_config.TextColumn("Quality", help="Overall analysis quality assessment")
                            }
                        )
                        st.caption(f"📊 Showing {len(summary_data)} prediction results from the selected analysis period")
                    else:
                        st.warning("No valid predictions found in the selected period")
                    
                    # 個別フィッティング結果表示機能を追加
                    st.subheader("📊 Individual Fitting Results")
                    
                    # 表示数を統合プロットと一致させる（Analysis Period Selectionと連動）
                    individual_display_count = len(analysis_data)  # 期間フィルタ済みのデータ全件表示
                    
                    # パフォーマンス考慮で上限設定（大量データ時）
                    is_limited = individual_display_count > 20
                    if is_limited:
                        individual_display_count = 20
                        st.markdown(f"*Displaying latest {individual_display_count} results out of {len(analysis_data)} total analyses (performance optimization)*")
                        # 上部に警告表示
                        st.warning(f"⚠️ **Performance Note**: Showing the most recent {individual_display_count} individual analyses from the selected period for optimal performance. To view older analyses, please adjust the period selection in the sidebar.")
                    else:
                        st.markdown(f"*Displaying all {individual_display_count} individual analyses from the selected period*")
                    
                    st.caption("Each plot shows an individual analysis with its own fitting period and prediction")
                    
                    for i, (_, individual) in enumerate(analysis_data.head(individual_display_count).iterrows()):
                        if pd.notna(individual.get('tc')):
                            ind_tc = individual['tc']
                            # 🔧 FRED API修正: Timestamp オブジェクトを文字列に安全変換
                            ind_start = self._ensure_date_string(individual.get('data_period_start'))
                            ind_end = self._ensure_date_string(individual.get('data_period_end'))
                            
                            if ind_start and ind_end:
                                # フィッティング基準日を取得
                                fitting_basis_date = individual.get('analysis_basis_date', ind_end)
                                fitting_basis_dt = pd.to_datetime(fitting_basis_date)
                                
                                st.markdown(f"---")
                                st.markdown(f"**Analysis #{i+1} - Fitting Basis: {fitting_basis_dt.strftime('%Y-%m-%d')}**")
                                
                                # 🔧 API効率化: 既に取得済みの拡張データから必要期間を抽出
                                if price_data is not None and not price_data.empty:
                                    # 拡張データから該当期間を抽出
                                    ind_start_dt = pd.to_datetime(ind_start)
                                    ind_end_dt = pd.to_datetime(ind_end)
                                    
                                    # 既存データの範囲内であることを確認（多少の余裕を持って判定）
                                    data_start_dt = price_data.index.min()
                                    data_end_dt = price_data.index.max()
                                    
                                    # 🔧 API効率化改善: 少しでも重複があれば既存データを使用
                                    available_data_in_range = price_data.loc[
                                        (price_data.index >= ind_start_dt) & (price_data.index <= ind_end_dt)
                                    ]
                                    
                                    if len(available_data_in_range) >= 30:  # 最低30日のデータがあれば使用
                                        # 既存データから期間抽出（API呼び出し不要）
                                        individual_data = available_data_in_range.copy()
                                        print(f"🔄 既存データから期間抽出: {symbol} {ind_start} to {ind_end} - {len(individual_data)}日分")
                                    else:
                                        # データが不足している場合のみAPI呼び出し
                                        individual_data = self.get_symbol_price_data(symbol, ind_start, ind_end)
                                        print(f"⚠️ データ不足のためAPI呼び出し: {symbol} (既存:{len(available_data_in_range)}日 < 30日)")
                                else:
                                    # フォールバック: 拡張データ取得失敗時のみAPI呼び出し
                                    individual_data = self.get_symbol_price_data(symbol, ind_start, ind_end)
                                
                                if individual_data is not None and not individual_data.empty and 'Close' in individual_data.columns:
                                    # LPPLパラメータを抽出
                                    individual_params = {
                                        'tc': individual.get('tc', 1.0),
                                        'beta': individual.get('beta', 0.33),
                                        'omega': individual.get('omega', 6.0),
                                        'phi': individual.get('phi', 0.0),
                                        'A': individual.get('A', 0.0),
                                        'B': individual.get('B', 0.0),
                                        'C': individual.get('C', 0.0)
                                    }
                                    
                                    # LPPLフィッティングを計算
                                    individual_lppl = self.compute_lppl_fit(individual_data['Close'], individual_params)
                                    
                                    if individual_lppl:
                                        # 個別フィッティンググラフを作成
                                        individual_fig = go.Figure()
                                        
                                        # 実データ
                                        individual_fig.add_trace(go.Scatter(
                                            x=individual_data.index,
                                            y=individual_lppl['normalized_prices'],
                                            mode='lines',
                                            name='Market Data',
                                            line=dict(color='lightblue', width=2)
                                        ))
                                        
                                        # LPPLフィット（基準日まで）
                                        basis_mask = individual_data.index <= fitting_basis_dt
                                        individual_fig.add_trace(go.Scatter(
                                            x=individual_data.index[basis_mask],
                                            y=individual_lppl['normalized_fitted'][basis_mask],
                                            mode='lines',
                                            name='LPPL Fit (Basis Period)',
                                            line=dict(color='red', width=2.5)
                                        ))
                                        
                                        # LPPLフィット（基準日以降）- 拡張版Future Period
                                        future_mask = individual_data.index > fitting_basis_dt
                                        
                                        # 拡張Future Period計算
                                        individual_pred_date = self.convert_tc_to_real_date(ind_tc, ind_start, ind_end)
                                        extended_individual_lppl = self.compute_extended_lppl_fit(
                                            individual_data['Close'], individual_params, 
                                            fitting_basis_dt, individual_pred_date + timedelta(days=30))
                                        
                                        if extended_individual_lppl and len(extended_individual_lppl['future_dates']) > 0:
                                            # 拡張Future Period表示
                                            individual_fig.add_trace(go.Scatter(
                                                x=extended_individual_lppl['future_dates'],
                                                y=extended_individual_lppl['normalized_fitted'],
                                                mode='lines',
                                                name='LPPL Fit (Future Period)',
                                                line=dict(color='orange', width=2.5, dash='dot'),
                                                opacity=0.8
                                            ))
                                        elif future_mask.any():
                                            # フォールバック：元のFuture Period
                                            individual_fig.add_trace(go.Scatter(
                                                x=individual_data.index[future_mask],
                                                y=individual_lppl['normalized_fitted'][future_mask],
                                                mode='lines',
                                                name='LPPL Fit (Future Period)',
                                                line=dict(color='orange', width=2.5, dash='dot')
                                            ))
                                        
                                        # 予測クラッシュ日の縦線（データ範囲全体に表示）
                                        # Y軸の範囲を実際のデータに合わせる
                                        y_min = min(individual_lppl['normalized_prices'].min(), 
                                                   individual_lppl['normalized_fitted'].min())
                                        y_max = max(individual_lppl['normalized_prices'].max(), 
                                                   individual_lppl['normalized_fitted'].max())
                                        
                                        # Future Periodのデータも考慮
                                        if extended_individual_lppl and len(extended_individual_lppl['future_dates']) > 0:
                                            y_max = max(y_max, max(extended_individual_lppl['normalized_fitted']))
                                        
                                        # 縦線を最後に描画（他のプロットより上に表示）
                                        individual_fig.add_shape(
                                            type="line",
                                            x0=individual_pred_date,
                                            x1=individual_pred_date,
                                            y0=y_min * 0.98,  # 少し下から
                                            y1=y_max * 1.02,  # 少し上まで
                                            line=dict(color='rgba(255, 100, 100, 0.8)', width=3, dash="dash"),
                                            layer='above'  # 他の要素より上に描画
                                        )
                                        
                                        individual_fig.add_annotation(
                                            x=individual_pred_date,
                                            y=0.9,
                                            text=individual_pred_date.strftime('%m/%d'),
                                            showarrow=False,
                                            font=dict(size=10, color='white'),
                                            bgcolor="rgba(0, 0, 0, 0.7)"
                                        )
                                        
                                        # レイアウト（X軸範囲を予測日+30日まで拡張）
                                        x_range_end = max(individual_data.index.max(), 
                                                        individual_pred_date + timedelta(days=30))
                                        individual_fig.update_layout(
                                            title=f"Individual Analysis - Fitted on {fitting_basis_dt.strftime('%Y-%m-%d')}",
                                            height=400,
                                            plot_bgcolor='rgba(20, 20, 30, 0.95)',
                                            paper_bgcolor='rgba(15, 15, 25, 0.95)',
                                            font=dict(color='white'),
                                            xaxis=dict(
                                                gridcolor='rgba(100, 100, 100, 0.2)',
                                                showgrid=True,
                                                gridwidth=1,
                                                range=[individual_data.index.min(), x_range_end]
                                            ),
                                            yaxis=dict(
                                                gridcolor='rgba(100, 100, 100, 0.2)',
                                                showgrid=True,
                                                gridwidth=1
                                            )
                                        )
                                        
                                        st.plotly_chart(individual_fig, use_container_width=True, key=f"individual_pred_{symbol}_{i}")
                                        
                                        # 個別結果の統計
                                        col1, col2, col3, col4 = st.columns(4)
                                        with col1:
                                            st.metric("Predicted Crash", individual_pred_date.strftime('%Y-%m-%d'))
                                        with col2:
                                            st.metric("R² Score", f"{individual.get('r_squared', 0):.4f}")
                                        with col3:
                                            st.metric("Quality", individual.get('quality', 'N/A'))
                                        with col4:
                                            st.metric("tc Value", f"{ind_tc:.4f}")
                                    else:
                                        st.error(f"LPPL calculation failed for analysis #{i+1}")
                                else:
                                    st.warning(f"Unable to retrieve data for analysis #{i+1}")
                    
                    # 下部にも警告表示（20件制限がある場合）
                    if is_limited:
                        st.markdown("---")
                        st.warning(f"⚠️ **Performance Note**: You have reached the display limit of {individual_display_count} analyses. There are {len(analysis_data) - individual_display_count} additional older analyses available. To view these, please adjust the period selection in the sidebar to focus on a different time range.")
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
    
    def render_prediction_data_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 1: Crash Prediction Data Visualization"""
        
        st.header(f"📊 {symbol} - Crash Prediction Data")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        valid_data = analysis_data.dropna(subset=['predicted_crash_date'])
        
        if valid_data.empty:
            st.warning("No valid prediction data available")
            return
        
        # Add fitting_basis_date column to valid_data for multi-period analysis
        fitting_basis_dates_valid = []
        for _, row in valid_data.iterrows():
            # 優先順位: analysis_basis_date > data_period_end > analysis_date
            for col in ['analysis_basis_date', 'data_period_end', 'data_end', 'end_date', 'analysis_date']:
                if col in valid_data.columns and pd.notna(row.get(col)):
                    fitting_basis_dates_valid.append(pd.to_datetime(row[col]))
                    break
            else:
                fitting_basis_dates_valid.append(pd.to_datetime(row.get('analysis_date', datetime.now())))
        
        valid_data = valid_data.copy()  # Make a copy to avoid modifying the original
        valid_data['fitting_basis_date'] = fitting_basis_dates_valid
        
        # Analysis Data Period functionality
        st.subheader("📅 Analysis Data Period")
        st.caption("解析データの対象とする期間")
        
        # データ範囲の計算（From/Toの下に表示用）
        original_data = self.get_symbol_analysis_data(symbol, limit=1000)  # フィルタ前の全データ
        if not original_data.empty:
            original_data['analysis_basis_date'] = pd.to_datetime(original_data['analysis_basis_date'])
            full_min_date = original_data['analysis_basis_date'].min()
            full_max_date = original_data['analysis_basis_date'].max()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'prediction_data_from_date' not in st.session_state:
                st.session_state.prediction_data_from_date = valid_data['fitting_basis_date'].min().date()
            from_date = st.date_input("From", st.session_state.prediction_data_from_date, key='prediction_data_from_date_input')
            st.session_state.prediction_data_from_date = from_date
            # Oldest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Oldest Analysis: {full_min_date.strftime('%Y-%m-%d')}")
            
        with col2:
            if 'prediction_data_to_date' not in st.session_state:
                st.session_state.prediction_data_to_date = valid_data['fitting_basis_date'].max().date()
            to_date = st.date_input("To", st.session_state.prediction_data_to_date, key='prediction_data_to_date_input')
            st.session_state.prediction_data_to_date = to_date
            # Latest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Latest Analysis: {full_max_date.strftime('%Y-%m-%d')}")
        
        # 📊 選択期間の視覚表示（プログレスバーのみ・より幅広く）
        if not original_data.empty:
            selected_min = pd.to_datetime(from_date)
            selected_max = pd.to_datetime(to_date)
            
            # 期間の割合計算
            total_days = (full_max_date - full_min_date).days
            selected_duration = (selected_max - selected_min).days
            
            # 選択期間の開始位置と長さを計算
            start_offset = (selected_min - full_min_date).days if total_days > 0 else 0
            selected_ratio = selected_duration / total_days if total_days > 0 else 1.0
        
        st.markdown("---")
        
        # Period フィルタリング
        valid_data['fitting_basis_date'] = pd.to_datetime(valid_data['fitting_basis_date'])
        from_datetime = pd.to_datetime(from_date)
        to_datetime = pd.to_datetime(to_date)
        
        date_mask = (valid_data['fitting_basis_date'] >= from_datetime) & (valid_data['fitting_basis_date'] <= to_datetime)
        valid_data = valid_data[date_mask].copy()
        
        if len(valid_data) == 0:
            st.warning(f"No data available for selected period: {from_date} to {to_date}")
            return
        
        # Main scatter plot: Analysis date vs Predicted crash date
        st.subheader("📊 Crash Prediction Data")
        
        fig = go.Figure()
        
        # Prepare data for plotting
        plot_data = valid_data.copy()
        
        # Get fitting basis dates (フィッティング基準日を優先的に取得)
        fitting_basis_dates = []
        for _, row in plot_data.iterrows():
            # 優先順位: analysis_basis_date > data_period_end > analysis_date
            for col in ['analysis_basis_date', 'data_period_end', 'data_end', 'end_date', 'analysis_date']:
                if col in plot_data.columns and pd.notna(row.get(col)):
                    fitting_basis_dates.append(pd.to_datetime(row[col]))
                    break
            else:
                fitting_basis_dates.append(pd.to_datetime(row.get('analysis_date', datetime.now())))
        
        plot_data['fitting_basis_date'] = fitting_basis_dates
        
        # Convert predicted crash dates（安全な変換・エラーハンドリング追加）
        crash_dates = []
        for date in plot_data['predicted_crash_date']:
            try:
                if pd.isna(date) or date is None:
                    crash_dates.append(None)
                elif hasattr(date, 'to_pydatetime'):
                    crash_dates.append(date.to_pydatetime())
                else:
                    # 文字列や他の形式を安全にTimestampに変換
                    converted_date = pd.to_datetime(date)
                    if hasattr(converted_date, 'to_pydatetime'):
                        crash_dates.append(converted_date.to_pydatetime())
                    else:
                        crash_dates.append(converted_date)
            except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime):
                # 変換できない場合はNoneを設定
                crash_dates.append(None)
        
        plot_data['crash_date_converted'] = crash_dates
        
        # フィッティング基準日から予測クラッシュ日までの日数を計算（安全な処理）
        hover_texts = []
        for _, row in plot_data.iterrows():
            fitting_basis_date = row['fitting_basis_date']
            crash_date = row['crash_date_converted']
            
            try:
                # 基準日からクラッシュ予想日までの日数を計算（安全な処理）
                if crash_date is None or pd.isna(crash_date):
                    days_to_crash = "N/A"
                else:
                    # 両方の日付を確実にTimestamp/datetimeオブジェクトに変換
                    if isinstance(fitting_basis_date, str):
                        fitting_basis_date = pd.to_datetime(fitting_basis_date)
                    if isinstance(crash_date, str):
                        crash_date = pd.to_datetime(crash_date)
                    
                    days_to_crash = (crash_date - fitting_basis_date).days
            except (ValueError, TypeError, AttributeError) as e:
                st.warning(f"日数計算エラー (行{_}): {str(e)}")
                days_to_crash = "Error"
            
            # hover_text作成（days_to_crashのタイプに応じて適切に表示）
            if isinstance(days_to_crash, (int, float)):
                days_text = f"Days to Crash: {days_to_crash} days<br>"
            else:
                days_text = f"Days to Crash: {days_to_crash}<br>"
            
            hover_text = (days_text +
                         f"R²: {row['r_squared']:.3f}<br>" +
                         f"Quality: {row['quality']}")
            hover_texts.append(hover_text)
        
        # Color by R² score
        fig.add_trace(go.Scatter(
            x=plot_data['fitting_basis_date'],
            y=plot_data['crash_date_converted'],
            mode='markers',
            marker=dict(
                size=10,
                color=plot_data['r_squared'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="R² Score",
                    x=1.02,  # Move colorbar further right to avoid overlap
                    len=0.7,  # Make colorbar shorter
                    y=0.5     # Center vertically
                )
            ),
            text=hover_texts,
            hovertemplate='Fitting Basis Date: %{x}<br>Predicted Crash: %{y}<br>%{text}<extra></extra>',
            name='Predictions'
        ))
        
        # Add y=x reference line (predictions that match fitting date)
        x_range = [plot_data['fitting_basis_date'].min(), plot_data['fitting_basis_date'].max()]
        y_range = [plot_data['crash_date_converted'].min(), plot_data['crash_date_converted'].max()]
        
        # Limit the line to scatter plot x-range to avoid excessive white space
        line_start = min(x_range[0], y_range[0])
        line_end = x_range[1]  # Use latest fitting basis date as end point
        
        # Always add the y=x reference line (without annotations to avoid overlap)
        fig.add_trace(go.Scatter(
            x=[line_start, line_end],
            y=[line_start, line_end],
            mode='lines',
            line=dict(color='lightblue', width=1, dash='solid'),  # 青系、細線、実線
            name='Reference Line',
            showlegend=False,  # Remove from legend to avoid clutter
            hoverinfo='skip'   # Remove hover info to avoid annotation overlap
        ))
        
        fig.update_layout(
            title=f"{symbol} - Prediction Data Visualization",
            xaxis_title="Fitting Basis Date",
            yaxis_title="Predicted Crash Date",
            height=600,
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Reference line explanation
        st.info("""
        📏 **Reference Line (Light Blue)**: The diagonal line represents the theoretical case where the predicted crash date equals the fitting basis date. If points are on the line, predictions suggest crashes on the same day as fitting (immediate risk).
        """)
        
        
    
    def render_crash_clustering_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """
        新タブ: Crash Prediction Clustering (I052実装) - デバッグ簡素版
        """
        
        st.header(f"🎯 {symbol} - Prediction Clustering")
        
        if analysis_data.empty:
            st.warning("No analysis data available for clustering")
            return
        
        
        # Clustering Analysis Settings
        st.subheader("⚙️ Clustering Analysis Settings")
        
        # 期間設定セクション
        st.markdown("### 📅 Analysis Data Period")
        st.caption("解析データの対象とする期間")
        
        # データ範囲の計算（From/Toの下に表示用）
        original_data = self.get_symbol_analysis_data(symbol, limit=1000)  # フィルタ前の全データ
        if not original_data.empty:
            original_data['analysis_basis_date'] = pd.to_datetime(original_data['analysis_basis_date'])
            full_min_date = original_data['analysis_basis_date'].min()
            full_max_date = original_data['analysis_basis_date'].max()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'clustering_from_date' not in st.session_state:
                st.session_state.clustering_from_date = analysis_data['analysis_basis_date'].min().date()
            from_date = st.date_input("From", st.session_state.clustering_from_date, key='clustering_from_date_input')
            st.session_state.clustering_from_date = from_date
            # Oldest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Oldest Analysis: {full_min_date.strftime('%Y-%m-%d')}")
            
        with col2:
            if 'clustering_to_date' not in st.session_state:
                st.session_state.clustering_to_date = analysis_data['analysis_basis_date'].max().date()
            to_date = st.date_input("To", st.session_state.clustering_to_date, key='clustering_to_date_input')
            st.session_state.clustering_to_date = to_date
            # Latest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Latest Analysis: {full_max_date.strftime('%Y-%m-%d')}")
        
        # 📊 選択期間の視覚表示（プログレスバーのみ・より幅広く）
        if not original_data.empty:
            selected_min = pd.to_datetime(from_date)
            selected_max = pd.to_datetime(to_date)
            
            # 期間の割合計算
            total_days = (full_max_date - full_min_date).days
            selected_duration = (selected_max - selected_min).days
            
            # 選択期間の開始位置と長さを計算
            start_offset = (selected_min - full_min_date).days if total_days > 0 else 0
            selected_ratio = selected_duration / total_days if total_days > 0 else 1.0
        
        st.markdown("---")
        
        # Display Period フィルタリング
        analysis_data['analysis_basis_date'] = pd.to_datetime(analysis_data['analysis_basis_date'])
        from_datetime = pd.to_datetime(from_date)
        to_datetime = pd.to_datetime(to_date)
        
        date_mask = (analysis_data['analysis_basis_date'] >= from_datetime) & (analysis_data['analysis_basis_date'] <= to_datetime)
        analysis_data = analysis_data[date_mask].copy()
        
        if len(analysis_data) == 0:
            st.warning(f"No data available for selected period: {from_date} to {to_date}")
            return
        
        
        # データ準備 - 日付フィルタリング適用済みのanalysis_dataを使用
        valid_data = analysis_data.dropna(subset=['predicted_crash_date', 'analysis_basis_date']).copy()
        
        if len(valid_data) < 5:
            st.warning(f"Insufficient data for clustering analysis (need at least 5 points, have {len(valid_data)})")
            return
        
        # 日付変換
        valid_data['basis_date'] = pd.to_datetime(valid_data['analysis_basis_date'])
        valid_data['crash_date'] = pd.to_datetime(valid_data['predicted_crash_date'])
        
        # 数値化（分析用）
        base_date = valid_data['basis_date'].min()  # 共通基準日
        valid_data['basis_days'] = (valid_data['basis_date'] - base_date).dt.days
        valid_data['crash_days'] = (valid_data['crash_date'] - base_date).dt.days
        
        # クラスタリングパラメータ設定
        st.markdown("### 🎯 Clustering Parameters")
        
        # ヘルプ情報をexpanderに追加
        with st.expander("ℹ️ Understanding Clustering Parameters & Methods", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **📊 R²-Weighted Average Method:**
                - Uses R² scores to weight each prediction's influence
                - Higher R² predictions have more impact on the cluster center
                - No time-series assumptions - purely quality-based weighting
                - Center line shows the weighted average prediction date
                
                **📏 Clustering Parameters:**
                - **Distance (days)**: Maximum time gap between predictions to group them
                - **Min Cluster Size**: Minimum predictions needed to form a valid cluster
                - **Min R²**: Quality threshold for including data in clustering
                - **Min Days to Crash**: Minimum time between fitting date and predicted crash date
                """)
                
            with col2:
                st.markdown("""
                **🎯 Confidence Levels:**
                - **High**: Avg R² > 0.7 and cluster size ≥ 5
                - **Medium**: Avg R² > 0.5 and cluster size ≥ 3  
                - **Low**: Below medium criteria
                
                **📈 Reference Line Interpretation:**
                - Blue dotted diagonal line where Fitting Date = Crash Date
                - **Above line**: Predicted crash is in the future
                - **On line**: Predicted crash is imminent (same day as fitting)
                - **Below line**: Predicted crash is in the past (expired prediction)
                """)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # プレビュー用の一時変数（Applyまで反映されない）
            if 'clustering_eps_days_preview' not in st.session_state:
                st.session_state.clustering_eps_days_preview = st.session_state.get('clustering_eps_days', 30)
            eps_days_preview = st.slider("Distance", 10, 90, 
                                       st.session_state.clustering_eps_days_preview, 
                                       key='eps_days_slider', help="Max days between predictions to be in same cluster")
            st.caption("days")
            
        with col2:
            if 'clustering_min_samples_preview' not in st.session_state:
                st.session_state.clustering_min_samples_preview = st.session_state.get('clustering_min_samples', 3)
            min_samples_preview = st.slider("Min Cluster", 2, 20, 
                                          st.session_state.clustering_min_samples_preview,
                                          key='min_samples_slider', help="Minimum predictions to form a cluster. Default: 3 for better cluster formation")
            st.caption("size")
            
        with col3:
            if 'clustering_r2_threshold_preview' not in st.session_state:
                st.session_state.clustering_r2_threshold_preview = st.session_state.get('clustering_r2_threshold', 0.8)
            r2_threshold_preview = st.slider("Min R²", 0.0, 1.0, 
                                           st.session_state.clustering_r2_threshold_preview, 0.05,
                                           key='r2_threshold_slider', help="Minimum R² value to include in clustering. Only data points with R² above this threshold will be used for clustering analysis (Data Quality Filter)")
            
        with col4:
            if 'clustering_min_horizon_days_preview' not in st.session_state:
                st.session_state.clustering_min_horizon_days_preview = st.session_state.get('clustering_min_horizon_days', 21)
            min_horizon_days_preview = st.slider(
                "Min Days to Crash", 
                min_value=0, max_value=90, 
                value=st.session_state.clustering_min_horizon_days_preview,
                key='min_horizon_days_slider',
                help="Minimum days between fitting date and predicted crash date (excludes near-crash predictions with low accuracy)"
            )
            st.caption("days")
        
        # Min Days to Crash Details Button
        if st.button("❓ Min Days to Crash - Sornette Research Details", help="Click for scientific background and filter rationale"):
            st.session_state.show_horizon_details = not st.session_state.get('show_horizon_details', False)
            
        # 詳細説明の表示制御
        if st.session_state.get('show_horizon_details', False):
            with st.expander("📚 Sornette Research: Prediction Horizon Theory", expanded=True):
                st.markdown(f"""
                **🎯 Current Filter Setting**: Excluding predictions within **{min_horizon_days_preview} days** of fitting date.
                
                **📖 Sornette Research Evidence**:
                - **Optimal Prediction Window**: 1-6 months ahead
                - **Minimum Practical Horizon**: ~30 days
                - **Near-Crash Problem**: Fittings too close to critical time suffer from:
                  - Increased noise sensitivity
                  - LPPL singularity effects
                  - Degraded predictive accuracy
                
                **⚙️ Implementation**:
                - **0 days**: No filtering (include all predictions)
                - **10-30 days**: Conservative filtering (recommended)
                - **30+ days**: Strict filtering (Sornette theoretical minimum)
                
                **✅ Scientific Basis**: Based on LPPL model behavior near critical time points.
                """)
                
                if st.button("✖️ Close Details"):
                    st.session_state.show_horizon_details = False
        
        # Applyボタン（すべての設定を一度に適用）
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            apply_settings = st.button("🔄 Apply Analysis Settings", type="primary", key='clustering_apply_settings',
                                      help="Apply all settings above: Analysis Period + Clustering Parameters", 
                                      use_container_width=True)
        
        # Applyボタンが押された場合、プレビュー値を実際の値にコピー
        if apply_settings:
            st.session_state.clustering_period_applied = True
            st.session_state.clustering_eps_days = eps_days_preview
            st.session_state.clustering_min_samples = min_samples_preview
            st.session_state.clustering_r2_threshold = r2_threshold_preview
            st.session_state.clustering_min_horizon_days = min_horizon_days_preview
            
        # 初回表示時の処理
        if 'clustering_period_applied' not in st.session_state:
            st.info("💡 **Getting Started**: Configure your settings above and click 'Apply' to start clustering analysis.")
            return
        
        # 実際に使用する値（Apply後の値）
        eps_days = st.session_state.get('clustering_eps_days', 30)
        min_samples = st.session_state.get('clustering_min_samples', 3)
        r2_threshold = st.session_state.get('clustering_r2_threshold', 0.8)
        min_horizon_days = st.session_state.get('clustering_min_horizon_days', 21)
            
        # データ準備 - 日付フィルタリング適用済みのanalysis_dataを使用
        valid_data = analysis_data.dropna(subset=['predicted_crash_date', 'analysis_basis_date']).copy()
        
        if len(valid_data) < 5:
            st.warning(f"Insufficient data for clustering analysis (need at least 5 points, have {len(valid_data)})")
            return
        
        # 日付変換
        valid_data['basis_date'] = pd.to_datetime(valid_data['analysis_basis_date'])
        valid_data['crash_date'] = pd.to_datetime(valid_data['predicted_crash_date'])
        
        # 予測期間計算（最小予測期間フィルター用）
        valid_data['prediction_horizon'] = (valid_data['crash_date'] - valid_data['basis_date']).dt.days
        
        # 最小予測期間フィルター適用
        horizon_filtered_data = valid_data[valid_data['prediction_horizon'] >= min_horizon_days].copy()
        
        if len(horizon_filtered_data) < 5:
            st.warning(f"""
            **Insufficient Data After Horizon Filtering**
            
            After applying the {min_horizon_days}-day minimum prediction horizon, only {len(horizon_filtered_data)} data points remain.
            
            **💡 Solutions:**
            1. **Reduce Min Horizon**: Try {max(0, min_horizon_days-5)}-{min_horizon_days-1} days
            2. **Expand Analysis Period**: Select a longer time range
            3. **Review Filter Settings**: Consider if {min_horizon_days}-day horizon is too restrictive
            """)
            return
        
        # 数値化（分析用）
        base_date = horizon_filtered_data['basis_date'].min()  # 共通基準日
        horizon_filtered_data['basis_days'] = (horizon_filtered_data['basis_date'] - base_date).dt.days
        horizon_filtered_data['crash_days'] = (horizon_filtered_data['crash_date'] - base_date).dt.days
        
        # R²フィルタリングによるデータ分離（予測期間フィルター後に適用）
        high_quality_mask = horizon_filtered_data['r_squared'] >= r2_threshold
        clustering_data = horizon_filtered_data[high_quality_mask].copy()
        low_quality_data = horizon_filtered_data[~high_quality_mask].copy()
        
        if len(clustering_data) < 5:
            st.warning(f"""
            **Insufficient Data for Clustering Analysis**
            
            - Current high-quality data: {len(clustering_data)} points (R² ≥ {r2_threshold:.2f})
            - Required minimum: 5 points
            
            **💡 Solutions:**
            1. **Expand Analysis Period**: Select a longer time range (From/To dates)
            2. **Lower R² Threshold**: Reduce Min R² to {max(0.5, r2_threshold-0.1):.1f} or lower
            3. **Check Data Availability**: Ensure sufficient historical analysis data exists
            
            Current period: {from_date} to {to_date} ({len(valid_data)} total points)
            """)
            return
        
        # Step 2: 高品質データのみで1次元クラスタリング（予測クラッシュ日のみ）
        from sklearn.cluster import DBSCAN
        clustering_input = clustering_data['crash_days'].values.reshape(-1, 1)
        clusterer = DBSCAN(eps=eps_days, min_samples=min_samples)
        clusters = clusterer.fit_predict(clustering_input)
        clustering_data['cluster'] = clusters
        
        # クラスター統計（高品質データのみ）
        unique_clusters = [c for c in np.unique(clusters) if c != -1]
        n_clusters = len(unique_clusters)
        n_noise = np.sum(clusters == -1)
        
        # 統計表示（Data Quality Filter + Horizon Filter結果を含む）
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Raw Data", len(valid_data), help="All data points in selected period")
        with col2:
            removal_rate = (len(valid_data) - len(horizon_filtered_data)) / len(valid_data) * 100 if len(valid_data) > 0 else 0
            st.metric("Horizon Filtered", len(horizon_filtered_data), 
                     delta=f"-{removal_rate:.1f}%",
                     help=f"After excluding predictions within {min_horizon_days} days (Sornette filter)")
        with col3:
            st.metric("High Quality", len(clustering_data), 
                     delta=f"R²≥{r2_threshold:.2f}", 
                     help=f"Points with R² ≥ {r2_threshold:.2f} (used for clustering)")
        with col4:
            st.metric("Clusters Found", n_clusters, help="Number of distinct clusters identified")
        with col5:
            st.metric("Isolated Points", n_noise, help="High-quality predictions that don't form clusters (insufficient density for min cluster size)")
        
        if n_clusters == 0:
            st.warning(f"""
            **No Clusters Found**
            
            All {len(clustering_data)} high-quality data points remain isolated (unclustered) with current parameters.
            
            **💡 Solutions:**
            1. **Increase Clustering Distance**: Try {eps_days + 10}-{eps_days + 30} days (currently {eps_days})
            2. **Decrease Min Cluster Size**: Try {max(2, min_samples - 2)}-{max(2, min_samples - 1)} (currently {min_samples})
            3. **Lower R² Threshold**: Include more data by reducing to {max(0.5, r2_threshold - 0.1):.1f}
            
            **Current Settings**: Distance={eps_days}d, MinSize={min_samples}, R²≥{r2_threshold:.2f}
            """)
            return
        
        # Step 3: 各クラスターでR²重み付き統計サマリー（I054改善実装）
        cluster_predictions = {}
        
        for cluster_id in unique_clusters:
            cluster_subset = clustering_data[clustering_data['cluster'] == cluster_id]
            
            if len(cluster_subset) >= 1:  # 単一点でも統計計算可能
                # R²重み付きによる重み計算
                r2_weights = cluster_subset['r_squared'].values
                # 重みを0.1-1.0の範囲に正規化（低R²でも最小重みは保持）
                normalized_weights = 0.1 + 0.9 * (r2_weights - r2_weights.min()) / (r2_weights.max() - r2_weights.min() + 1e-10)
                
                # R²重み付き平均値計算（改善手法）
                crash_days = cluster_subset['crash_days'].values
                weighted_mean = np.average(crash_days, weights=normalized_weights)
                
                # ばらつき指標計算
                weighted_std = np.sqrt(np.average((crash_days - weighted_mean)**2, weights=normalized_weights))
                simple_std = np.std(crash_days, ddof=1 if len(crash_days) > 1 else 0)
                
                # 四分位範囲計算
                q25 = np.percentile(crash_days, 25)
                q75 = np.percentile(crash_days, 75)
                iqr = q75 - q25
                
                # 信頼度評価（簡素化：平均R²とデータ数ベース）
                avg_r2 = r2_weights.mean()
                confidence = 'High' if avg_r2 > 0.7 and len(cluster_subset) >= 5 else \
                           'Medium' if avg_r2 > 0.5 and len(cluster_subset) >= 3 else 'Low'
                
                # 将来予測：重み付き平均をそのまま使用（プロットと同じbase_date基準）
                future_crash_days = weighted_mean
                future_crash_date = base_date + timedelta(days=int(weighted_mean))
                
                cluster_predictions[cluster_id] = {
                    'weighted_mean': weighted_mean,
                    'weighted_std': weighted_std,
                    'simple_std': simple_std,
                    'q25': q25,
                    'q75': q75,
                    'iqr': iqr,
                    'size': len(cluster_subset),
                    'avg_r2': avg_r2,
                    'weight_range': f"{normalized_weights.min():.2f}-{normalized_weights.max():.2f}",
                    'future_crash_days': future_crash_days,
                    'future_crash_date': future_crash_date,
                    'confidence': confidence,
                    'mean_crash_date': cluster_subset['crash_date'].mean(),
                    'data_range': f"{crash_days.min():.0f}-{crash_days.max():.0f} days"
                }
        
        # 可視化: 2次元散布図 + クラスター
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=("Crash Prediction Clustering",)
        )
        
        # カラーマップ（シンプルな色）
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA726', '#AB47BC', '#66BB6A', '#EF5350', '#26C6DA']
        
        # プロット1: 高品質データのクラスター
        for i, cluster_id in enumerate(unique_clusters):
            cluster_subset = clustering_data[clustering_data['cluster'] == cluster_id]
            color = colors[i % len(colors)]
            
            # Center線の情報を取得して統合された名前を作成
            if cluster_id in cluster_predictions:
                pred = cluster_predictions[cluster_id]
                base_date = clustering_data['basis_date'].min()
                weighted_mean_date = base_date + timedelta(days=int(pred['weighted_mean']))
                
                # 統合された表示名：日付、STD、サイズを全て含む
                cluster_name = f'C{cluster_id+1}: {weighted_mean_date.strftime("%Y-%m-%d")}, ±{pred["weighted_std"]:.1f}d, n={len(cluster_subset)}'
            else:
                cluster_name = f'C{cluster_id+1}: n={len(cluster_subset)}'
            
            # 散布図（シンプルな小さい点） - 統合された名前を使用
            fig.add_trace(go.Scatter(
                x=cluster_subset['basis_date'],
                y=cluster_subset['crash_date'],
                mode='markers',
                name=cluster_name,
                marker=dict(size=6, color=color, opacity=0.7),
                text=[f"LPPL R²={row['r_squared']:.3f}<br>Weight={0.1 + 0.9 * (row['r_squared'] - cluster_subset['r_squared'].min()) / (cluster_subset['r_squared'].max() - cluster_subset['r_squared'].min() + 1e-10):.2f}"
                      for _, row in cluster_subset.iterrows()],
                hovertemplate='<b>Cluster %{fullData.name}</b><br>%{text}<br>Basis: %{x}<br>Predicted: %{y}<extra></extra>'
            ), row=1, col=1)
            
            # R²重み付き平均値の水平線（Legendは非表示）
            if cluster_id in cluster_predictions:
                pred = cluster_predictions[cluster_id]
                
                # X軸範囲（全データ範囲に拡張）
                all_basis_min = clustering_data['basis_days'].min()
                all_basis_max = clustering_data['basis_days'].max()
                x_range = [base_date + timedelta(days=int(all_basis_min)), 
                          base_date + timedelta(days=int(all_basis_max))]
                
                # 中心線（水平・細いライン） - Legendは非表示
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=[weighted_mean_date, weighted_mean_date],
                    mode='lines',
                    name='',  # 名前を空に
                    line=dict(color=color, width=1, dash='solid'),
                    showlegend=False,  # Legend表示を無効化
                    hovertemplate=f'C{cluster_id+1}<br>R²-Weighted Mean: {weighted_mean_date.strftime("%Y-%m-%d")}<br>Weighted STD: ±{pred["weighted_std"]:.1f} days<extra></extra>'
                ), row=1, col=1)
        
        # ノイズポイント（高品質データ内のノイズ）
        noise_data = clustering_data[clustering_data['cluster'] == -1]
        if len(noise_data) > 0:
            fig.add_trace(go.Scatter(
                x=noise_data['basis_date'],
                y=noise_data['crash_date'],
                mode='markers',
                name=f'Isolated (High Quality, n={len(noise_data)})',
                marker=dict(size=4, color='lightgray', symbol='x', opacity=0.5),
                hovertemplate='Isolated Prediction<br>LPPL R²=%{customdata:.3f}<br>Basis: %{x}<br>Predicted: %{y}<extra></extra>',
                customdata=noise_data['r_squared']
            ), row=1, col=1)
            
        # 低品質データ（別カテゴリで表示）
        if len(low_quality_data) > 0:
            fig.add_trace(go.Scatter(
                x=low_quality_data['basis_date'],
                y=low_quality_data['crash_date'],
                mode='markers',
                name=f'Low Quality (R²<{r2_threshold:.2f}, n={len(low_quality_data)})',
                marker=dict(size=4, color='red', symbol='triangle-up', opacity=0.3),
                hovertemplate='Low Quality Data<br>LPPL R²=%{customdata:.3f}<br>Basis: %{x}<br>Predicted: %{y}<extra></extra>',
                customdata=low_quality_data['r_squared']
            ), row=1, col=1)
            
        # 基準日=クラッシュ日の直線（y=x線） - Center線と同じX軸範囲を使用
        if len(clustering_data) > 0:
            # Center線と同じX軸範囲を計算
            all_basis_min = clustering_data['basis_days'].min()
            all_basis_max = clustering_data['basis_days'].max()
            x_range = [base_date + timedelta(days=int(all_basis_min)), 
                      base_date + timedelta(days=int(all_basis_max))]
            
            fig.add_trace(go.Scatter(
                x=x_range,
                y=x_range,
                mode='lines',
                name='Reference: Fitting Date = Crash Date',
                line=dict(color='lightblue', width=2, dash='dot'),
                hovertemplate='Reference Line<br>Fitting Date = Predicted Crash Date<extra></extra>',
                showlegend=True
            ), row=1, col=1)
        
        # 現在時刻ライン（タイムスタンプ形式の問題のため一時的に無効化）
        # today = datetime.datetime.now()
        # fig.add_hline(y=today, line_dash="dot", line_color="gray", 
        #              annotation_text="Today", row=1, col=1)
        
        # レイアウト設定
        fig.update_xaxes(title_text="Fitting Basis Date", row=1, col=1)
        fig.update_yaxes(title_text="Predicted Crash Date", row=1, col=1)
        
        fig.update_layout(
            height=600,  # 棒グラフ削除により高さを減少
            showlegend=True,
            hovermode='closest',
            title_text=f"{symbol} - Crash Prediction Clustering Analysis"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        
        # クラスター詳細テーブル
        if cluster_predictions:
            st.subheader("📊 Cluster Analysis Results")
            
            # 今日からの日数を計算
            today = datetime.now().date()
            
            cluster_df = pd.DataFrame([
                {
                    'Cluster': f"C{cid+1}",
                    'Weight Mean Date': pred['future_crash_date'].strftime('%Y-%m-%d'),
                    'Days to Crash': f"{pred['future_crash_days']:.0f}",
                    'Days from Today': f"{(pred['future_crash_date'].date() - today).days}",
                    'Weighted STD': f"{pred['weighted_std']:.1f}",
                    'STD': f"{pred['simple_std']:.1f}",
                    'Size': pred['size'],
                    'Avg R²': f"{pred['avg_r2']:.3f}",
                    'Confidence': pred['confidence']
                }
                for cid, pred in sorted(cluster_predictions.items())  # クラスターID順にソート
            ])
            
            # DataFrameはクラスターID順で既にソート済み（上記のsorted()により）
            
            st.dataframe(cluster_df, use_container_width=True)
            
            # 単位情報を別行で表示
            st.caption("**Units**: Days to Crash (days from analysis basis date) | Days from Today (days from current date) | Weighted STD & STD (±days) | Size (number of predictions)")
            st.caption("*Center predictions are calculated using R²-weighted averaging, giving higher influence to predictions with better model fit*")
            
            # 最も信頼性の高いクラスター（平均R²×サイズで判定）
            best_cluster = max(cluster_predictions.items(), 
                             key=lambda x: (x[1]['avg_r2'] * x[1]['size']))
            best_id, best_pred = best_cluster
            
            st.success(f"""
            **🎯 Most Reliable R²-Weighted Prediction:**
            - **C{best_id+1}** with {best_pred['size']} data points
            - **Average R²**: {best_pred['avg_r2']:.3f} (weight range: {best_pred['weight_range']})
            - **Predicted crash**: {best_pred['future_crash_date'].strftime('%Y-%m-%d')}
            - **Confidence**: {best_pred['confidence']}
            - **Days to predicted crash**: {best_pred['future_crash_days']:.0f}
            - **Data range**: {best_pred['data_range']}
            """)
    
    def render_parameters_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 4: Parameters Only"""
        
        st.header(f"📋 {symbol} - LPPL Parameters")
        
        if analysis_data.empty:
            st.warning("No analysis data available for this symbol")
            return
        
        # Analysis Data Period functionality
        st.subheader("📅 Analysis Data Period")
        st.caption("解析データの対象とする期間")
        
        # データ範囲の計算（From/Toの下に表示用）
        original_data = self.get_symbol_analysis_data(symbol, limit=1000)  # フィルタ前の全データ
        if not original_data.empty:
            original_data['analysis_basis_date'] = pd.to_datetime(original_data['analysis_basis_date'])
            full_min_date = original_data['analysis_basis_date'].min()
            full_max_date = original_data['analysis_basis_date'].max()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'parameters_from_date' not in st.session_state:
                st.session_state.parameters_from_date = analysis_data['analysis_basis_date'].min().date()
            from_date = st.date_input("From", st.session_state.parameters_from_date, key='parameters_from_date_input')
            st.session_state.parameters_from_date = from_date
            # Oldest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Oldest Analysis: {full_min_date.strftime('%Y-%m-%d')}")
            
        with col2:
            if 'parameters_to_date' not in st.session_state:
                st.session_state.parameters_to_date = analysis_data['analysis_basis_date'].max().date()
            to_date = st.date_input("To", st.session_state.parameters_to_date, key='parameters_to_date_input')
            st.session_state.parameters_to_date = to_date
            # Latest Analysis情報を直下に表示
            if not original_data.empty:
                st.caption(f"📍 Latest Analysis: {full_max_date.strftime('%Y-%m-%d')}")
        
        # 📊 選択期間の視覚表示（プログレスバーのみ・より幅広く）
        if not original_data.empty:
            selected_min = pd.to_datetime(from_date)
            selected_max = pd.to_datetime(to_date)
            
            # 期間の割合計算
            total_days = (full_max_date - full_min_date).days
            selected_duration = (selected_max - selected_min).days
            
            # 選択期間の開始位置と長さを計算
            start_offset = (selected_min - full_min_date).days if total_days > 0 else 0
            selected_ratio = selected_duration / total_days if total_days > 0 else 1.0
        
        st.markdown("---")
        
        # Period フィルタリング
        analysis_data['analysis_basis_date'] = pd.to_datetime(analysis_data['analysis_basis_date'])
        from_datetime = pd.to_datetime(from_date)
        to_datetime = pd.to_datetime(to_date)
        
        date_mask = (analysis_data['analysis_basis_date'] >= from_datetime) & (analysis_data['analysis_basis_date'] <= to_datetime)
        analysis_data = analysis_data[date_mask].copy()
        
        if len(analysis_data) == 0:
            st.warning(f"No data available for selected period: {from_date} to {to_date}")
            return
        
        # Prepare detailed parameter table
        display_df = analysis_data.copy()
        
        # Add formatted predicted crash date（安全な日付変換）
        if 'predicted_crash_date' in display_df.columns:
            def safe_format_date(x):
                if pd.isna(x) or x is None:
                    return 'N/A'
                try:
                    # 文字列の場合はTimestampに変換
                    if isinstance(x, str):
                        x = pd.to_datetime(x)
                    # strftimeメソッドが使える形式に変換
                    if hasattr(x, 'strftime'):
                        return x.strftime('%Y-%m-%d %H:%M')
                    else:
                        # それでも使えない場合は文字列で返す
                        return str(x)
                except (ValueError, TypeError, AttributeError):
                    return str(x) if x is not None else 'N/A'
            
            display_df['predicted_crash_date_formatted'] = display_df['predicted_crash_date'].apply(safe_format_date)
        else:
            display_df['predicted_crash_date_formatted'] = 'N/A'
        
        # Add fitting basis date (フィッティング基準日) - most important date（安全な変換）
        def safe_format_date_simple(x):
            if pd.isna(x) or x is None:
                return 'N/A'
            try:
                if isinstance(x, str):
                    x = pd.to_datetime(x)
                if hasattr(x, 'strftime'):
                    return x.strftime('%Y-%m-%d')
                else:
                    return str(x)
            except (ValueError, TypeError, AttributeError):
                return str(x) if x is not None else 'N/A'
        
        if 'analysis_basis_date' in display_df.columns:
            display_df['fitting_basis_date_formatted'] = display_df['analysis_basis_date'].apply(safe_format_date_simple)
        elif 'data_period_end' in display_df.columns:
            # Fallback to data period end
            display_df['fitting_basis_date_formatted'] = display_df['data_period_end'].apply(safe_format_date_simple)
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
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            highest_r2 = analysis_data['r_squared'].max()
            st.metric("Highest R²", f"{highest_r2:.3f}" if pd.notna(highest_r2) else "N/A")
        
        with col2:
            avg_r2 = analysis_data['r_squared'].mean()
            st.metric("Average R²", f"{avg_r2:.3f}" if pd.notna(avg_r2) else "N/A")
        
        with col3:
            high_quality_count = len(analysis_data[analysis_data['quality'] == 'high_quality'])
            st.metric("High Quality", f"{high_quality_count}/{len(analysis_data)}")
        
        with col4:
            valid_predictions = len(analysis_data.dropna(subset=['predicted_crash_date']))
            st.metric("Valid Predictions", f"{valid_predictions}/{len(analysis_data)}")
        
        with col5:
            if 'predicted_crash_date' in analysis_data.columns:
                # 安全な日付比較（文字列→Timestamp変換）
                try:
                    now = datetime.now()
                    # 文字列日付をTimestampに変換してから比較
                    crash_dates_converted = pd.to_datetime(analysis_data['predicted_crash_date'], errors='coerce')
                    future_predictions = len(crash_dates_converted[crash_dates_converted > now])
                    st.metric("Future Predictions", future_predictions)
                except Exception as e:
                    st.metric("Future Predictions", "Error")
                    st.caption(f"⚠️ Date comparison error: {str(e)}")
            else:
                st.metric("Future Predictions", "N/A")
        
        # Download functionality
        csv = final_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Parameter Data",
            data=csv,
            file_name=f"{symbol}_parameters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    def render_references_tab(self, symbol: str, analysis_data: pd.DataFrame):
        """Tab 5: References and Benchmarks"""
        
        st.header("📚 References & Benchmarks")
        
        # Reference information from Sornette paper reproduction
        st.subheader("📚 Reference: Sornette Paper Reproduction")
        
        # Multiple historical crash references
        crash_tabs = st.tabs([
            "🎯 1987 Black Monday", 
            "💻 2000 Dot-com Bubble",
            "📊 General Benchmarks"
        ])
        
        with crash_tabs[0]:
            st.markdown("""
            **1987 Black Monday LPPL Analysis** (100/100 score reproduction):
            
            📊 **Validated Parameters**:
            - **Paper Reproduction Score**: 100/100 ✅
            - **R² Range**: Typically 0.85-0.95 for high-quality fits
            - **β (Beta) Parameter**: ~0.33 (critical exponent from theory)
            - **ω (Omega) Parameter**: ~6-8 (log-periodic oscillation frequency)
            - **Data Period**: 706 days pre-crash analysis
            - **Total Return**: +65.2% (bubble formation criteria met)
            - **Peak Return**: +85.1% (accelerating growth confirmed)
            - **Crash Magnitude**: -28.2% (major crash threshold exceeded)
            """)
            
        with crash_tabs[1]:
            st.markdown("""
            **2000 Dot-com Bubble LPPL Analysis** (Qualitative validation):
            
            📊 **Reference Parameters**:
            - **Bubble Formation**: +417% total return (2000 peak)
            - **β (Beta) Parameter**: 0.1-0.5 range (theory-consistent)
            - **ω (Omega) Parameter**: 4-12 range (log-periodic patterns)
            - **R² Performance**: 0.6-0.9 depending on fitting window
            - **Data Period**: Multi-year bubble formation analysis
            - **Crash Magnitude**: -78% from peak (major crash confirmed)
            
            📋 **Key Insights**:
            - Longer bubble formation periods show different parameter ranges
            - Technology sector bubbles exhibit distinct ω patterns
            - Higher volatility affects R² consistency
            """)
            
        with crash_tabs[2]:
            st.markdown("""
            **General LPPL Parameter Benchmarks**:
            
            📖 **Interpretation Guidelines**:
            - **R² > 0.8**: Excellent fit quality (paper-level accuracy)
            - **R² 0.6-0.8**: Good fit quality (acceptable for analysis)
            - **R² < 0.6**: Lower confidence (use with caution)
            - **β ≈ 0.33**: Theoretical expectation from critical phenomena
            - **β = 0.1-0.5**: Acceptable range for most market conditions
            - **ω = 6-8**: Optimal log-periodic frequency (Black Monday)
            - **ω = 4-12**: Extended acceptable range for various bubbles
            
            🔬 **Scientific Validation Standards**:
            - Our implementation achieves **identical results** to published papers
            - All parameters fall within theoretical bounds from literature
            - Multiple crash validations confirm prediction accuracy
            
            📋 **Quality Classification**:
            - **High Quality**: R² > 0.8, β = 0.2-0.5, ω = 4-12
            - **Research Grade**: Matches or exceeds paper reproduction metrics
            - **Trading Grade**: High quality + recent data validation
            """)
    
    def run(self):
        """Main dashboard execution"""
        
        st.title("📊 LPPL Market Analysis Dashboard")
        st.markdown("*Symbol-based analysis with trading position prioritization*")
        
        # Render new sidebar (v2) - Symbol選択のみ
        selected_symbol = self.render_sidebar_v2()
        
        if selected_symbol is None:
            # 初期画面でユーザーガイドを表示
            st.info("""
            ### 📋 Getting Started
            
            Please use the sidebar to:
            1. **🎛️ Symbol Filters**: Set filters to find symbols of interest
            2. **📈 Select Symbol**: Choose a symbol and click "Select Symbol"
            
            After selecting a symbol, each tab will have its own Display Period settings.
            """)
            return
        
        # 🆕 選択銘柄の全データ取得（各タブで個別にフィルタリング）
        with st.spinner(f"Loading all analysis data for {selected_symbol}..."):
            # 全データ取得（フィルタリングは各タブで実施）
            analysis_data = self.get_symbol_analysis_data(selected_symbol, limit=None, period_selection=None)
        
        if analysis_data.empty:
            st.warning(f"No analysis data found for {selected_symbol}")
            return
        
        # 🎯 フィルタリング完了 - 新システムで全て処理済み
        
        # Main content tabs - 新しいタブ順序（2025-08-13）
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Crash Prediction Data",     # 1. データ確認・可視化
            "🎯 Prediction Clustering",     # 2. クラスタリング分析  
            "📈 LPPL Fitting Plot",         # 3. フィッティング結果
            "📋 Parameters",                # 4. パラメータ詳細
            "📚 References"                 # 5. 参照情報
        ])
        
        with tab1:
            self.render_prediction_data_tab(selected_symbol, analysis_data)
        
        with tab2:
            self.render_crash_clustering_tab(selected_symbol, analysis_data)
        
        with tab3:
            self.render_price_predictions_tab(selected_symbol, analysis_data)
        
        with tab4:
            self.render_parameters_tab(selected_symbol, analysis_data)
        
        with tab5:
            self.render_references_tab(selected_symbol, analysis_data)

def main():
    """Main execution function"""
    app = SymbolAnalysisDashboard()
    app.run()

if __name__ == "__main__":
    main()