#!/usr/bin/env python3
"""
FCO Analysis Dashboard Components

独立したFCO専用コンポーネント。
既存ダッシュボードへの影響を最小限にするため、
完全に独立したモジュールとして実装。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

from infrastructure.database.fco_results_database import FCOResultsDatabase


class FCODashboardComponents:
    """FCO分析結果表示用コンポーネント"""
    
    def __init__(self):
        self.fco_db = FCOResultsDatabase()
    
    def render_fco_overview(self, symbol: str) -> None:
        """
        FCO分析概要の表示（最小限の実装）
        
        Args:
            symbol: 銘柄コード
        """
        # 最新のFCO分析結果を取得
        latest_result = self.fco_db.get_latest_fco_analysis(symbol)
        
        if not latest_result:
            st.info(f"🔍 {symbol}のFCO分析結果が見つかりません")
            st.write("FCO分析を実行するには:")
            st.code(f"python entry_points/main.py analyze {symbol} --fco")
            return
        
        # 基本情報の表示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "DS-LPPLS Confidence (正)",
                f"{latest_result.get('ds_lppls_confidence', 0):.1%}"
            )
        
        with col2:
            st.metric(
                "DS-LPPLS Confidence (負)",
                f"{latest_result.get('ds_lppls_confidence_neg', 0):.1%}"
            )
        
        with col3:
            bubble_type = latest_result.get('bubble_type', 'none')
            bubble_emoji = {
                'positive_bubble': '🔴',
                'negative_bubble': '🔵',
                'weak_positive': '🟡',
                'no_bubble': '⚪'
            }.get(bubble_type, '⚪')
            st.metric("バブル判定", f"{bubble_emoji} {bubble_type}")
        
        # 詳細情報
        with st.expander("📊 FCO分析詳細"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**分析情報**")
                st.write(f"- 分析基準日: {latest_result.get('analysis_basis_date', 'N/A')}")
                st.write(f"- データソース: {latest_result.get('data_source', 'N/A')}")
                st.write(f"- データ期間: {latest_result.get('data_period_start', 'N/A')} ~ {latest_result.get('data_period_end', 'N/A')}")
                st.write(f"- データポイント数: {latest_result.get('data_points', 0)}")
            
            with col2:
                st.write("**窓分析結果**")
                st.write(f"- 分析窓数: {latest_result.get('num_windows', 0)}")
                st.write(f"- 適合窓数: {latest_result.get('num_qualified_fits', 0)}")
                if latest_result.get('predicted_tc'):
                    st.write(f"- 予測tc（中央値）: {latest_result['predicted_tc']:.1f}日")
                    st.write(f"- 標準偏差: {latest_result.get('tc_std', 0):.1f}日")
    
    def render_fco_window_distribution(self, symbol: str) -> None:
        """
        FCO窓分布の可視化（シンプル版）
        
        Args:
            symbol: 銘柄コード
        """
        latest_result = self.fco_db.get_latest_fco_analysis(symbol)
        
        if not latest_result or not latest_result.get('id'):
            return
        
        # 窓フィッティング結果を取得
        window_fits = self.fco_db.get_window_fits(latest_result['id'])
        
        if window_fits.empty:
            st.info("窓フィッティング詳細データがありません")
            return
        
        # tc分布のヒストグラム
        fig = go.Figure()
        
        # 適合窓のみフィルタ
        qualified_fits = window_fits[window_fits['is_qualified'] == 1] if 'is_qualified' in window_fits.columns else window_fits
        
        if not qualified_fits.empty and 'tc' in qualified_fits.columns:
            fig.add_trace(go.Histogram(
                x=qualified_fits['tc'],
                nbinsx=20,
                name='tc分布',
                marker_color='blue',
                opacity=0.7
            ))
            
            # 中央値を表示
            median_tc = qualified_fits['tc'].median()
            fig.add_vline(
                x=median_tc,
                line_dash="dash",
                line_color="red",
                annotation_text=f"中央値: {median_tc:.1f}"
            )
        
        fig.update_layout(
            title="予測tc値の分布（適合窓のみ）",
            xaxis_title="予測tc（日）",
            yaxis_title="窓数",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_fco_confidence_history(self, symbol: str) -> None:
        """
        DS-LPPLS Confidence履歴の表示
        
        Args:
            symbol: 銘柄コード
        """
        # Confidence履歴を取得
        confidence_history = self.fco_db.get_confidence_history(symbol)
        
        if confidence_history.empty:
            st.info("DS-LPPLS Confidence履歴データがまだありません")
            return
        
        # 時系列グラフ
        fig = go.Figure()
        
        if 'timestamp' in confidence_history.columns and 'ds_lppls_confidence' in confidence_history.columns:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(confidence_history['timestamp']),
                y=confidence_history['ds_lppls_confidence'],
                mode='lines+markers',
                name='Positive Bubble Confidence',
                line=dict(color='red', width=2)
            ))
        
        if 'ds_lppls_confidence_neg' in confidence_history.columns:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(confidence_history['timestamp']),
                y=confidence_history['ds_lppls_confidence_neg'],
                mode='lines+markers',
                name='Negative Bubble Confidence',
                line=dict(color='blue', width=2)
            ))
        
        # 閾値ライン
        fig.add_hline(y=0.3, line_dash="dash", line_color="gray", annotation_text="FCO閾値 (30%)")
        
        fig.update_layout(
            title="DS-LPPLS Confidence推移",
            xaxis_title="日付",
            yaxis_title="Confidence",
            yaxis=dict(tickformat='.0%'),
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_fco_comparison_table(self, symbol: str) -> None:
        """
        FCO vs LPPL比較テーブル
        
        Args:
            symbol: 銘柄コード
        """
        st.subheader("📊 FCO vs LPPL比較")
        
        comparison_data = {
            "指標": ["分析手法", "時間窓数", "主要指標", "信頼性評価", "予測方式"],
            "LPPL (従来)": ["単一窓", "1", "R²", "フィッティング品質", "点推定"],
            "FCO (新方式)": ["多重時間窓", "126", "DS-LPPLS", "統計的信頼度", "分布推定"]
        }
        
        df = pd.DataFrame(comparison_data)
        st.table(df)
    
    def render_full_fco_tab(self, symbol: Optional[str]) -> None:
        """
        完全なFCOタブの表示（日次分析対応）
        
        Args:
            symbol: 選択された銘柄コード
        """
        st.header("🆕 FCO Multi-Window Analysis (Daily Updates)")
        
        # 日次分析の説明
        st.caption("*FCO analysis is updated daily for more frequent monitoring*")
        
        if not symbol:
            st.info("👈 左のサイドバーから銘柄を選択してください")
            return
        
        # FCO概要
        self.render_fco_overview(symbol)
        
        # 窓分布
        st.subheader("📊 予測値分布")
        self.render_fco_window_distribution(symbol)
        
        # Confidence履歴（データがある場合）
        st.subheader("📈 Confidence履歴")
        self.render_fco_confidence_history(symbol)
        
        # 比較テーブル
        self.render_fco_comparison_table(symbol)
        
        # 実行方法の案内
        with st.expander("🔧 FCO分析の実行方法"):
            st.write("FCO分析を実行するには、以下のコマンドを使用してください:")
            st.code(f"python entry_points/main.py analyze {symbol} --fco")
            st.write("または、全銘柄のFCO分析:")
            st.code("python entry_points/main.py analyze ALL --fco")
    
    def render_overview_screening_tab(self, symbol: Optional[str]) -> None:
        """
        Overview & Screening タブ実装
        LPPLのCrash Prediction DataをFCO版に変換
        
        Args:
            symbol: 選択された銘柄コード
        """
        st.header("📊 Overview & Screening - FCO Analysis")
        
        if not symbol:
            st.info("👈 左のサイドバーから銘柄を選択してください")
            return
        
        # 最新分析結果のメトリック表示
        latest_result = self.fco_db.get_latest_fco_analysis(symbol)
        
        if not latest_result:
            st.warning(f"⚠️ {symbol}のFCO分析結果がありません")
            st.info("FCO分析を実行するには:")
            st.code(f"python entry_points/main.py fco-daily run --symbols {symbol}")
            return
        
        # メトリック表示
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            confidence_pos = latest_result.get('ds_lppls_confidence', 0)
            st.metric(
                "DS-LPPLS Confidence (Pos)",
                f"{confidence_pos:.1%}",
                help="Positive bubble confidence (>30% indicates bubble)"
            )
        
        with col2:
            confidence_neg = latest_result.get('ds_lppls_confidence_neg', 0)
            st.metric(
                "DS-LPPLS Confidence (Neg)",
                f"{confidence_neg:.1%}",
                help="Negative bubble confidence"
            )
        
        with col3:
            trust = latest_result.get('ds_lppls_trust', 0)
            st.metric(
                "DS-LPPLS Trust",
                f"{trust:.1%}" if trust else "N/A",
                help="Bootstrap-based reliability measure"
            )
        
        with col4:
            bubble_type = latest_result.get('bubble_type', 'none')
            bubble_emoji = {
                'positive_bubble': '🔴',
                'negative_bubble': '🔵',
                'weak_positive': '🟡',
                'no_bubble': '⚪'
            }.get(bubble_type, '⚪')
            st.metric(
                "Bubble Status",
                f"{bubble_emoji} {bubble_type.replace('_', ' ').title()}"
            )
        
        st.markdown("---")
        
        # 期間選択機能
        st.subheader("📅 Analysis Data Period")
        
        # 分析履歴を取得
        history = self.fco_db.get_analysis_history(symbol, limit=100)
        
        if history.empty:
            st.info("分析履歴データがありません")
            return
        
        # 日付列を変換
        history['analysis_basis_date'] = pd.to_datetime(history['analysis_basis_date'])
        
        # 期間選択
        col1, col2 = st.columns(2)
        
        with col1:
            min_date = history['analysis_basis_date'].min()
            max_date = history['analysis_basis_date'].max()
            # デフォルトを3年前からに設定（LPPLと同じ）
            three_years_ago = max_date - pd.DateOffset(years=3)
            # データが3年分以上ある場合は3年前から、それ未満の場合は最古のデータから
            if min_date <= three_years_ago:
                default_from = three_years_ago.date()
            else:
                default_from = min_date.date()
            from_date = st.date_input(
                "From",
                value=default_from,
                min_value=min_date.date(),
                max_value=history['analysis_basis_date'].max().date(),
                key='fco_from_date'
            )
            st.caption(f"📍 Oldest Analysis: {min_date.strftime('%Y-%m-%d')}")
        
        with col2:
            # max_dateは既に上で定義済み
            default_to = max_date.date()
            to_date = st.date_input(
                "To",
                value=default_to,
                min_value=min_date.date(),
                max_value=max_date.date(),
                key='fco_to_date'
            )
            st.caption(f"📍 Latest Analysis: {max_date.strftime('%Y-%m-%d')}")
        
        # 期間フィルタリング
        from_datetime = pd.to_datetime(from_date)
        to_datetime = pd.to_datetime(to_date)
        
        filtered_data = history[
            (history['analysis_basis_date'] >= from_datetime) &
            (history['analysis_basis_date'] <= to_datetime)
        ].copy()
        
        if filtered_data.empty:
            st.warning(f"選択期間にデータがありません: {from_date} ~ {to_date}")
            return
        
        st.markdown("---")
        
        # Crash Prediction Data プロット
        st.subheader("📊 Crash Prediction Data (FCO)")
        
        # predicted_crash_dateの処理（既存のものを使用、または必要に応じてtcから計算）
        if 'predicted_crash_date' not in filtered_data.columns and 'predicted_tc' in filtered_data.columns:
            # predicted_crash_dateがない場合のみ、tcから計算
            filtered_data['predicted_crash_date'] = filtered_data.apply(
                lambda row: pd.to_datetime(row['analysis_basis_date']) + pd.Timedelta(days=float(row['predicted_tc']))
                if pd.notna(row['predicted_tc']) else None,
                axis=1
            )
        else:
            # 既存のpredicted_crash_dateを日付型に変換
            filtered_data['predicted_crash_date'] = pd.to_datetime(filtered_data['predicted_crash_date'])
        
        # プロット作成
        fig = go.Figure()
        
        # DS-LPPLS Confidenceで色分け（predicted_crash_dateがあるデータのみ）
        valid_predictions = filtered_data.dropna(subset=['predicted_crash_date'])
        
        
        # プロットデータの処理
        if not valid_predictions.empty:
            # データを直接使用（.valuesでnumpy配列として取得）
            x_dates = valid_predictions['analysis_basis_date'].values
            y_dates = valid_predictions['predicted_crash_date'].values
            confidence_values = (valid_predictions['ds_lppls_confidence'] * 100).values
            
            # 散布図追加
            fig.add_trace(go.Scatter(
                x=x_dates,
                y=y_dates,
                mode='markers',
                marker=dict(
                    size=12,
                    color=confidence_values,
                    colorscale='Viridis',  # LPPLと同じカラースケール（視認性向上）
                    showscale=True,
                    colorbar=dict(title="DS-LPPLS<br>Confidence (%)", x=1.02),
                    cmin=0,
                    cmax=100
                ),
                name='FCO Predictions',
                text=[f"Confidence: {c:.1f}%" for c in confidence_values],
                hovertemplate='Analysis: %{x}<br>Predicted: %{y}<br>%{text}<extra></extra>'
            ))
            
            # 参照線（基準日＝予測日）
            min_date = valid_predictions['analysis_basis_date'].min()
            max_date = valid_predictions['analysis_basis_date'].max()
            
            fig.add_trace(go.Scatter(
                x=[min_date, max_date],
                y=[min_date, max_date],
                mode='lines',
                line=dict(color='gray', width=1, dash='dash'),
                name='Reference (Immediate)',
                hoverinfo='skip'
            ))
        
        # レイアウト設定
        fig.update_layout(
            title="FCO Crash Prediction Analysis",
            xaxis_title="Analysis Basis Date (Fitting Period End)",
            yaxis_title="Predicted Crash Date",
            height=600,
            hovermode='closest',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=0.01
            )
        )
        
        # X軸とY軸の範囲設定（削除して自動設定に任せる）
        # 注：範囲を統一すると、データポイントが見えなくなる可能性がある
        # fig.update_xaxes(range=date_range)
        # fig.update_yaxes(range=date_range)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 統計サマリー
        with st.expander("📊 Statistical Summary"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Analysis Statistics:**")
                st.write(f"- Total Analyses: {len(filtered_data)}")
                st.write(f"- Valid Predictions: {len(valid_predictions)}")
                high_conf_count = len(filtered_data[filtered_data['ds_lppls_confidence'] > 0.3])
                st.write(f"- High Confidence (>30%): {high_conf_count}")
                avg_confidence = filtered_data['ds_lppls_confidence'].mean()
                st.write(f"- Average Confidence: {avg_confidence:.1%}")
            
            with col2:
                st.write("**Bubble Detection:**")
                bubble_counts = filtered_data['bubble_type'].value_counts()
                for bubble_type, count in bubble_counts.items():
                    emoji = {
                        'positive_bubble': '🔴',
                        'negative_bubble': '🔵',
                        'weak_positive': '🟡',
                        'no_bubble': '⚪'
                    }.get(bubble_type, '⚪')
                    st.write(f"- {emoji} {bubble_type.replace('_', ' ').title()}: {count}")
        
        # データテーブル（オプション）
        with st.expander("📋 Detailed Data Table"):
            # カラム順序を修正：analysis_basis_date, predicted_crash_date, predicted_tc, その他
            display_cols = [
                'analysis_basis_date',
                'predicted_crash_date',  # 追加
                'predicted_tc',
                'ds_lppls_confidence',
                'ds_lppls_confidence_neg',
                'ds_lppls_trust',
                'bubble_type',
                'num_qualified_fits'
            ]
            
            # 存在する列のみ表示
            available_cols = [col for col in display_cols if col in filtered_data.columns]
            
            display_df = filtered_data[available_cols].copy()
            
            # 日付フォーマット
            if 'analysis_basis_date' in display_df.columns:
                display_df['analysis_basis_date'] = display_df['analysis_basis_date'].dt.strftime('%Y-%m-%d')
            
            if 'predicted_crash_date' in display_df.columns:
                display_df['predicted_crash_date'] = pd.to_datetime(display_df['predicted_crash_date']).dt.strftime('%Y-%m-%d')
            
            # 数値フォーマット設定
            format_dict = {
                'predicted_tc': '{:.1f} days',
                'ds_lppls_confidence': '{:.1%}',
                'ds_lppls_confidence_neg': '{:.1%}',
                'ds_lppls_trust': '{:.1%}'
            }
            
            for col, fmt in format_dict.items():
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: fmt.format(float(x)) if pd.notna(x) else 'N/A')
            
            # カラム名を日本語でも分かりやすく
            rename_dict = {
                'analysis_basis_date': 'Analysis Date',
                'predicted_crash_date': 'Predicted Crash',
                'predicted_tc': 'Days to Crash',
                'ds_lppls_confidence': 'Confidence (Pos)',
                'ds_lppls_confidence_neg': 'Confidence (Neg)',
                'ds_lppls_trust': 'Trust',
                'bubble_type': 'Bubble Type',
                'num_qualified_fits': 'Qualified Windows'
            }
            
            display_df = display_df.rename(columns={k: v for k, v in rename_dict.items() if k in display_df.columns})
            
            st.dataframe(display_df, use_container_width=True)