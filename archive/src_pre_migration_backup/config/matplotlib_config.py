#!/usr/bin/env python3
"""
matplotlib 設定管理
GUIスタック問題を防ぐための設定
"""

import matplotlib
import matplotlib.pyplot as plt
import warnings

def configure_matplotlib_for_automation():
    """
    自動化・テスト環境向けのmatplotlib設定
    GUIを無効化してスタック問題を防ぐ
    """
    # バックエンドをAggに設定（GUIなし）
    matplotlib.use('Agg')
    
    # 警告を抑制
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    
    # デフォルトのスタイル設定
    plt.style.use('default')
    
    # 日本語フォント問題を回避
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    print("📊 matplotlib設定完了: 非GUIモード、自動保存専用")

def save_and_close_figure(fig, filepath, dpi=300):
    """
    図を保存して確実にクローズ
    
    Args:
        fig: matplotlib Figure オブジェクト
        filepath: 保存先パス
        dpi: 解像度
    """
    try:
        fig.savefig(filepath, dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"📊 図を保存: {filepath}")
    except Exception as e:
        print(f"❌ 図の保存に失敗: {str(e)}")
    finally:
        plt.close(fig)  # 確実にリソースを解放

def create_headless_plot():
    """
    ヘッドレス環境での安全なプロット作成
    
    Returns:
        fig, ax: matplotlib オブジェクト
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    return fig, ax

# モジュールインポート時に自動設定
configure_matplotlib_for_automation()