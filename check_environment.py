#!/usr/bin/env python3
"""
実行環境チェックスクリプト

システムが正常に動作するために必要な環境・依存関係を確認
"""

import sys
import subprocess
import os
from pathlib import Path
import importlib

def main():
    print("🔍 LPPL予測システム環境チェック")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # 1. Python バージョンチェック
    total_checks += 1
    print(f"\n1. Pythonバージョンチェック:")
    python_version = sys.version_info
    print(f"   現在のバージョン: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version >= (3, 8):
        print("   ✅ OK: Python 3.8以上")
        checks_passed += 1
    else:
        print("   ❌ NG: Python 3.8以上が必要です")
    
    # 2. 必須ライブラリチェック
    total_checks += 1
    print(f"\n2. 必須ライブラリチェック:")
    
    required_packages = [
        'numpy', 'pandas', 'matplotlib', 'scipy', 'requests',
        'python-dotenv', 'streamlit', 'plotly', 'yfinance'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (未インストール)")
            missing_packages.append(package)
    
    if not missing_packages:
        print("   ✅ 全ての必須ライブラリがインストール済み")
        checks_passed += 1
    else:
        print(f"   ❌ 不足ライブラリ: {', '.join(missing_packages)}")
        print(f"   インストールコマンド: pip install {' '.join(missing_packages)}")
    
    # 3. プロジェクト構造チェック
    total_checks += 1
    print(f"\n3. プロジェクト構造チェック:")
    
    required_dirs = [
        'src', 'src/fitting', 'src/data_sources', 'src/monitoring',
        'src/data_management', 'src/ui', 'docs', 'results'
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ❌ {dir_path}/ (見つかりません)")
            missing_dirs.append(dir_path)
    
    if not missing_dirs:
        print("   ✅ プロジェクト構造が正常")
        checks_passed += 1
    else:
        print(f"   ❌ 不足ディレクトリ: {', '.join(missing_dirs)}")
    
    # 4. 重要ファイルチェック
    total_checks += 1
    print(f"\n4. 重要ファイルチェック:")
    
    important_files = [
        'src/fitting/multi_criteria_selection.py',
        'src/fitting/fitting_quality_evaluator.py',
        'src/data_sources/fred_data_client.py',
        'src/monitoring/multi_market_monitor.py',
        'comprehensive_market_analysis.py',
        'test_quality_aware_fitting.py'
    ]
    
    missing_files = []
    for file_path in important_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (見つかりません)")
            missing_files.append(file_path)
    
    if not missing_files:
        print("   ✅ 全ての重要ファイルが存在")
        checks_passed += 1
    else:
        print(f"   ❌ 不足ファイル: {', '.join(missing_files)}")
    
    # 5. 環境変数チェック
    total_checks += 1
    print(f"\n5. 環境変数チェック:")
    
    env_file_exists = os.path.exists('.env')
    if env_file_exists:
        print("   ✅ .envファイル存在")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        fred_api_key = os.getenv('FRED_API_KEY')
        if fred_api_key:
            print("   ✅ FRED_API_KEY設定済み")
        else:
            print("   ⚠️ FRED_API_KEY未設定（データ取得に影響する可能性）")
        
        checks_passed += 1
    else:
        print("   ⚠️ .envファイルなし（オプション）")
        print("   .env.exampleをコピーして.envを作成することを推奨")
        checks_passed += 1  # 必須ではないので通す
    
    # 6. インターネット接続チェック
    total_checks += 1
    print(f"\n6. インターネット接続チェック:")
    
    try:
        import urllib.request
        urllib.request.urlopen('https://api.stlouisfed.org', timeout=5)
        print("   ✅ インターネット接続OK")
        print("   ✅ FRED API接続OK")
        checks_passed += 1
    except Exception as e:
        print(f"   ❌ インターネット接続エラー: {str(e)}")
        print("   データ取得機能が制限される可能性があります")
    
    # 7. 基本機能テスト
    total_checks += 1
    print(f"\n7. 基本機能テスト:")
    
    try:
        # 品質評価システムのテスト
        from src.fitting.fitting_quality_evaluator import FittingQualityEvaluator
        evaluator = FittingQualityEvaluator()
        
        test_params = {'tc': 1.25, 'beta': 0.33, 'omega': 6.36}
        test_stats = {'r_squared': 0.9, 'rmse': 0.05}
        assessment = evaluator.evaluate_fitting(test_params, test_stats)
        
        print("   ✅ 品質評価システム動作OK")
        
        # 多基準選択システムのテスト
        from src.fitting.multi_criteria_selection import MultiCriteriaSelector
        selector = MultiCriteriaSelector()
        
        print("   ✅ 多基準選択システム動作OK")
        
        checks_passed += 1
    except Exception as e:
        print(f"   ❌ 基本機能テストエラー: {str(e)}")
        print("   システムの一部が正常に動作しない可能性があります")
    
    # 結果サマリー
    print(f"\n" + "=" * 50)
    print(f"🎯 環境チェック結果: {checks_passed}/{total_checks} 項目OK")
    
    if checks_passed == total_checks:
        print("✅ 全ての環境チェックが完了！システムは正常に動作するはずです。")
        print("\n🚀 実行可能なコマンド:")
        print("   python comprehensive_market_analysis.py")
        print("   python test_quality_aware_fitting.py")
        print("   python retrospective_nasdaq_analysis.py")
        print("   streamlit run src/ui/criteria_comparison_dashboard.py")
        
    elif checks_passed >= total_checks * 0.8:
        print("⚠️ ほぼ準備完了！軽微な問題がありますが、基本機能は動作するはずです。")
        
    else:
        print("❌ 複数の問題があります。上記の不足項目を解決してください。")
        
        print("\n🔧 推奨解決手順:")
        if missing_packages:
            print(f"1. pip install {' '.join(missing_packages)}")
        if missing_dirs:
            print("2. プロジェクト構造を確認し、不足ディレクトリを作成")
        if missing_files:
            print("3. 不足ファイルの復元またはGitからの再取得")
    
    print(f"\n📖 詳細なガイド: USER_EXECUTION_GUIDE.md を参照してください")
    
    return checks_passed == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)