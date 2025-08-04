#!/usr/bin/env python3
"""
LPPL可視化の統一システム
スケール問題とデータベース統合を解決
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, Tuple, Optional
import os

from ..database.results_database import ResultsDatabase
from ..fitting.fitter import LogarithmPeriodicFitter
from ..fitting.utils import logarithm_periodic_func
from ..config.matplotlib_config import save_and_close_figure

class LPPLVisualizer:
    """LPPL分析結果の可視化クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db = ResultsDatabase(db_path)
        self.fitter = LogarithmPeriodicFitter()
    
    def create_comprehensive_visualization(self, analysis_id: int, 
                                         original_data: Optional[pd.DataFrame] = None) -> str:
        """
        包括的なLPPL可視化を作成
        
        Args:
            analysis_id: 分析結果ID
            original_data: 元データ（Noneの場合は模擬データ使用）
            
        Returns:
            str: 保存された画像ファイルパス
        """
        print(f"🎨 LPPL包括可視化作成: ID={analysis_id}")
        
        # データベースから分析結果取得
        details = self.db.get_analysis_details(analysis_id)
        if not details:
            raise ValueError(f"分析ID {analysis_id} が見つかりません")
        
        # パラメータ抽出
        params = self._extract_parameters(details)
        print(f"📊 パラメータ: tc={params['tc']:.4f}, β={params['beta']:.4f}, ω={params['omega']:.4f}")
        
        # データ準備
        if original_data is None:
            # 模擬データ生成（実際のFREDデータに近い特性）
            data = self._generate_realistic_data(details)
        else:
            data = original_data.copy()
        
        prices = data['Close'].values
        print(f"📊 データ範囲: {prices.min():.0f} - {prices.max():.0f}")
        
        # 正規化とフィッティング
        normalized_results = self._compute_normalized_fitting(prices, params)
        
        # 可視化作成
        fig_path = self._create_visualization_plots(
            data, prices, params, normalized_results, details
        )
        
        print(f"✅ 可視化保存: {fig_path}")
        return fig_path
    
    def _extract_parameters(self, details: Dict) -> Dict:
        """データベースから全パラメータを抽出"""
        return {
            'tc': details['tc'],
            'beta': details['beta'],
            'omega': details['omega'],
            'phi': details['phi'],
            'A': details['A'],
            'B': details['B'],
            'C': details['C'],
            'r_squared': details['r_squared'],
            'quality': details['quality']
        }
    
    def _generate_realistic_data(self, details: Dict) -> pd.DataFrame:
        """実際のFREDデータに近い模擬データ生成"""
        n_points = details.get('data_points', 124)
        start_date = details.get('data_period_start', '2025-02-04')
        
        dates = pd.date_range(start=start_date, periods=n_points, freq='D')
        
        # 実際のNASDAQ価格帯での模擬データ
        np.random.seed(42)  # 再現性のため
        
        # ベース価格とトレンド
        base_price = 17000
        trend = np.linspace(0, 2500, n_points)
        
        # 市場の自然な変動パターン
        t = np.arange(n_points)
        weekly_cycle = 300 * np.sin(2 * np.pi * t / 7)
        monthly_cycle = 500 * np.sin(2 * np.pi * t / 30)
        
        # ランダムウォーク成分
        random_walk = np.cumsum(np.random.normal(0, 50, n_points))
        
        # ノイズ
        noise = np.random.normal(0, 100, n_points)
        
        # 合成
        prices = base_price + trend + weekly_cycle + monthly_cycle + random_walk + noise
        
        # 価格が負にならないよう調整
        prices = np.maximum(prices, base_price * 0.5)
        
        return pd.DataFrame({'Close': prices}, index=dates)
    
    def _compute_normalized_fitting(self, prices: np.ndarray, params: Dict) -> Dict:
        """正規化空間でのフィッティング計算"""
        # 1. データ正規化（フィッティング時と同じ方法）
        t_norm, y_norm = self.fitter.prepare_data(prices)
        
        if t_norm is None or y_norm is None:
            raise ValueError("データ正規化に失敗")
        
        # 2. 正規化空間でLPPL計算
        fitted_norm = logarithm_periodic_func(
            t_norm, params['tc'], params['beta'], params['omega'],
            params['phi'], params['A'], params['B'], params['C']
        )
        
        # 3. 元のスケールに戻す
        # 正規化は log(price) - log(price[0]) で行われているため
        # 元のスケールは: exp(正規化結果) * price[0]
        fitted_original = np.exp(fitted_norm) * prices[0]
        
        # 4. 成分分析（正規化空間）
        components = self._compute_lppl_components(t_norm, params)
        
        return {
            't_norm': t_norm,
            'y_norm': y_norm,
            'fitted_norm': fitted_norm,
            'fitted_original': fitted_original,
            'components': components,
            'scale_factor': prices[0]  # スケール変換用
        }
    
    def _compute_lppl_components(self, t_norm: np.ndarray, params: Dict) -> Dict:
        """LPPL成分分析"""
        tc, beta, omega, phi, A, B, C = [
            params[k] for k in ['tc', 'beta', 'omega', 'phi', 'A', 'B', 'C']
        ]
        
        dt = tc - t_norm
        mask = dt > 0
        
        trend_component = np.zeros_like(t_norm)
        oscillation_component = np.zeros_like(t_norm)
        full_model = np.zeros_like(t_norm)
        
        if np.any(mask):
            power_term = np.power(dt[mask], beta)
            log_term = np.log(dt[mask])
            cos_term = np.cos(omega * log_term + phi)
            
            trend_component[mask] = A + B * power_term
            oscillation_component[mask] = C * power_term * cos_term
            full_model[mask] = trend_component[mask] + oscillation_component[mask]
        
        return {
            'trend': trend_component,
            'oscillation': oscillation_component,
            'full_model': full_model
        }
    
    def _create_visualization_plots(self, data: pd.DataFrame, prices: np.ndarray, 
                                  params: Dict, norm_results: Dict, details: Dict) -> str:
        """包括的な可視化プロット作成"""
        fig = plt.figure(figsize=(16, 12))
        
        # プロット1: メインフィッティング（元スケール）
        ax1 = plt.subplot(2, 2, 1)
        ax1.plot(data.index, prices, 'b-', label='Market Data', alpha=0.8, linewidth=1.5)
        ax1.plot(data.index, norm_results['fitted_original'], 'r-', 
                label='LPPL Model', linewidth=2.5)
        ax1.set_title(f'LPPL Fitting (R² = {params["r_squared"]:.4f})', fontsize=14)
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # 価格範囲情報
        price_info = f'Data: ${prices.min():.0f} - ${prices.max():.0f}\n'
        price_info += f'Fit: ${norm_results["fitted_original"].min():.0f} - ${norm_results["fitted_original"].max():.0f}'
        ax1.text(0.02, 0.98, price_info, transform=ax1.transAxes, 
                verticalalignment='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # プロット2: 正規化空間での比較
        ax2 = plt.subplot(2, 2, 2)
        ax2.plot(data.index, norm_results['y_norm'], 'b-', 
                label='Normalized Data', alpha=0.8, linewidth=1.5)
        ax2.plot(data.index, norm_results['fitted_norm'], 'r-', 
                label='LPPL Fit (Normalized)', linewidth=2.5)
        ax2.set_title('Normalized Space Comparison', fontsize=14)
        ax2.set_ylabel('Log-Normalized Price', fontsize=12)
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # プロット3: 残差分析
        ax3 = plt.subplot(2, 2, 3)
        residuals = prices - norm_results['fitted_original']
        ax3.plot(data.index, residuals, 'g-', alpha=0.7, linewidth=1)
        ax3.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        rmse = np.sqrt(np.mean(residuals**2))
        ax3.set_title(f'Residuals (RMSE: ${rmse:.0f})', fontsize=14)
        ax3.set_ylabel('Residual ($)', fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # 残差統計
        residual_stats = f'Mean: ${residuals.mean():.0f}\nStd: ${residuals.std():.0f}'
        ax3.text(0.02, 0.98, residual_stats, transform=ax3.transAxes,
                verticalalignment='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        # プロット4: パラメータとメタ情報
        ax4 = plt.subplot(2, 2, 4)
        
        # パラメータ情報
        param_text = f"""LPPL Parameters:
tc = {params['tc']:.4f}
β = {params['beta']:.4f}
ω = {params['omega']:.4f}
φ = {params['phi']:.4f}
A = {params['A']:.4f}
B = {params['B']:.4f}
C = {params['C']:.4f}

Quality Metrics:
R² = {params['r_squared']:.4f}
Quality = {params['quality']}
Usable = {'Yes' if details.get('is_usable', False) else 'No'}

Scale Information:
Original: ${prices.min():.0f} - ${prices.max():.0f}
Normalized: {norm_results['y_norm'].min():.3f} - {norm_results['y_norm'].max():.3f}
Scale Factor: {norm_results['scale_factor']:.0f}

Critical Time Analysis:
tc = {params['tc']:.3f} (normalized)
Predicted beyond data: {(params['tc'] - 1.0) * 365:.0f} days"""
        
        ax4.text(0.05, 0.95, param_text, transform=ax4.transAxes, fontsize=9,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8))
        ax4.set_title('Analysis Summary', fontsize=14)
        ax4.axis('off')
        
        plt.tight_layout()
        
        # 保存
        os.makedirs('results/comprehensive_viz', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fig_path = f'results/comprehensive_viz/lppl_comprehensive_id{details["id"]}_{timestamp}.png'
        save_and_close_figure(fig, fig_path)
        
        return fig_path
    
    def update_database_visualization(self, analysis_id: int, fig_path: str) -> int:
        """新しい可視化をデータベースに追加"""
        viz_id = self.db.save_visualization(
            analysis_id,
            'lppl_comprehensive',
            fig_path,
            'LPPL Comprehensive Analysis',
            'Complete LPPL analysis with proper scaling and component breakdown'
        )
        print(f"📊 データベース更新: 可視化ID={viz_id}")
        return viz_id

def create_database_integrated_visualization(analysis_id: int, 
                                           db_path: str = "results/demo_analysis.db") -> str:
    """データベース統合LPPL可視化の作成"""
    visualizer = LPPLVisualizer(db_path)
    
    # 可視化作成
    fig_path = visualizer.create_comprehensive_visualization(analysis_id)
    
    # データベース更新
    viz_id = visualizer.update_database_visualization(analysis_id, fig_path)
    
    print(f"✅ 統合可視化完了: ID={analysis_id} → 可視化ID={viz_id}")
    return fig_path

if __name__ == "__main__":
    # 最新の分析結果で可視化テスト
    create_database_integrated_visualization(4)