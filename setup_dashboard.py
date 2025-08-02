#!/usr/bin/env python3
"""
ダッシュボードセットアップスクリプト
必要な依存関係をインストールし、ダッシュボードを起動
"""

import subprocess
import sys
import os
from pathlib import Path

def check_and_install_requirements():
    """必要なパッケージのチェックとインストール"""
    print("📦 依存関係のチェック...")
    
    required_packages = [
        'streamlit',
        'plotly',
        'sqlite3'  # Python標準ライブラリなのでスキップ
    ]
    
    missing_packages = []
    
    for package in required_packages:
        if package == 'sqlite3':
            continue  # 標準ライブラリ
            
        try:
            __import__(package)
            print(f"✅ {package}: インストール済み")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}: 未インストール")
    
    if missing_packages:
        print(f"\n📥 不足パッケージをインストール中: {', '.join(missing_packages)}")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package}: インストール完了")
            except subprocess.CalledProcessError:
                print(f"❌ {package}: インストール失敗")
                return False
    
    return True

def create_sample_data():
    """サンプルデータの作成"""
    print("\n📊 サンプルデータ作成中...")
    
    try:
        # デモ分析を実行してサンプルデータを作成
        from demo_database_integration import demo_headless_analysis
        
        analysis_id, chart_path = demo_headless_analysis()
        print(f"✅ サンプルデータ作成完了: 分析ID={analysis_id}")
        return True
        
    except Exception as e:
        print(f"❌ サンプルデータ作成失敗: {str(e)}")
        
        # 最小限のダミーデータを作成
        try:
            from src.database.results_database import ResultsDatabase
            
            db = ResultsDatabase("results/demo_analysis.db")
            
            sample_data = {
                'symbol': 'DEMO_NASDAQ',
                'data_source': 'demo',
                'data_period_start': '2024-01-01',
                'data_period_end': '2024-12-31',
                'data_points': 250,
                'tc': 1.15,
                'beta': 0.33,
                'omega': 7.4,
                'r_squared': 0.95,
                'quality': 'high_quality',
                'confidence': 0.92,
                'is_usable': True
            }
            
            db.save_analysis_result(sample_data)
            print("✅ 最小限のサンプルデータ作成完了")
            return True
            
        except Exception as e2:
            print(f"❌ 最小限データ作成も失敗: {str(e2)}")
            return False

def launch_dashboard():
    """ダッシュボードの起動"""
    print("\n🚀 ダッシュボード起動中...")
    
    dashboard_script = "src/web_interface/analysis_dashboard.py"
    
    if not os.path.exists(dashboard_script):
        print(f"❌ ダッシュボードスクリプトが見つかりません: {dashboard_script}")
        return False
    
    try:
        print("🌐 ブラウザでダッシュボードを開いています...")
        print("📝 注意: 終了する場合は Ctrl+C を押してください")
        print("🔗 URL: http://localhost:8501")
        print("-" * 50)
        
        # Streamlitでダッシュボードを起動
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 
            dashboard_script,
            '--server.port=8501',
            '--server.address=localhost'
        ])
        
        return True
        
    except KeyboardInterrupt:
        print("\n👋 ダッシュボードを終了しました")
        return True
    except Exception as e:
        print(f"❌ ダッシュボード起動失敗: {str(e)}")
        return False

def show_manual_instructions():
    """手動起動の手順を表示"""
    print("\n📋 手動でダッシュボードを起動する方法:")
    print("=" * 50)
    print("1. ターミナルで以下のコマンドを実行:")
    print("   streamlit run src/web_interface/analysis_dashboard.py")
    print()
    print("2. ブラウザで以下のURLを開く:")
    print("   http://localhost:8501")
    print()
    print("3. 終了する場合:")
    print("   ターミナルで Ctrl+C を押す")

def main():
    """メイン実行関数"""
    print("🎯 LPPL分析ダッシュボード セットアップ")
    print("=" * 60)
    print("このスクリプトは以下を実行します:")
    print("1. 必要な依存関係のインストール")
    print("2. サンプルデータの作成")
    print("3. ブラウザダッシュボードの起動")
    print()
    
    # ユーザー確認
    response = input("続行しますか？ (y/N): ").lower().strip()
    if response not in ['y', 'yes']:
        print("👋 セットアップをキャンセルしました")
        return
    
    print("\n" + "="*60)
    
    # 1. 依存関係チェック
    if not check_and_install_requirements():
        print("❌ 依存関係のインストールに失敗しました")
        return
    
    # 2. サンプルデータ作成
    if not create_sample_data():
        print("⚠️ サンプルデータの作成に失敗しましたが、続行します")
    
    # 3. ダッシュボード起動
    print("\n" + "="*60)
    print("🚀 ダッシュボードを起動します...")
    
    if not launch_dashboard():
        print("\n⚠️ 自動起動に失敗しました")
        show_manual_instructions()
    
    print("\n✅ セットアップ完了！")

if __name__ == "__main__":
    main()