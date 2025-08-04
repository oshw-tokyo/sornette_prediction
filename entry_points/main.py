#!/usr/bin/env python3
"""
Sornette Prediction System - Central Command Interface

🧠 Unified entry point for all system operations

Usage:
    python entry_points/main.py dashboard [--type main|symbol]
    python entry_points/main.py analyze [symbol] [--period 1y]
    python entry_points/main.py validate [--crash 1987|2000|all]
    python entry_points/main.py schedule [symbol]
    python entry_points/main.py dev [--check-env|--debug-viz]
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 🔧 自動.env読み込み機能
def load_environment_variables():
    """プロジェクトの.envファイルを自動読み込み"""
    try:
        from dotenv import load_dotenv
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ .env ファイル読み込み完了")
            
            # APIキー設定確認
            fred_key = os.getenv('FRED_API_KEY')
            alpha_key = os.getenv('ALPHA_VANTAGE_KEY')
            
            if fred_key:
                print(f"✅ FRED API Key: {fred_key[:10]}...")
            else:
                print("⚠️  FRED API Key が設定されていません")
            
            if alpha_key:
                print(f"✅ Alpha Vantage Key: {alpha_key[:10]}...")
            else:
                print("⚠️  Alpha Vantage Key が設定されていません")
        else:
            print("⚠️  .env ファイルが見つかりません")
            
    except ImportError:
        print("⚠️  python-dotenv が未インストール: pip install python-dotenv")
    except Exception as e:
        print(f"⚠️  環境変数読み込みエラー: {e}")

# システム起動時に環境変数を自動読み込み
load_environment_variables()

def launch_dashboard(dashboard_type='main'):
    """Launch web dashboard"""
    print(f"🚀 Launching {dashboard_type} dashboard...")
    
    if dashboard_type == 'symbol':
        import subprocess
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 
            'applications/dashboards/symbol_dashboard.py'
        ])
    else:
        import subprocess
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run',
            'applications/dashboards/main_dashboard.py' 
        ])

def run_analysis(symbol, period='1y'):
    """Run LPPL analysis on specified symbol"""
    print(f"📊 Running LPPL analysis: {symbol} ({period})")
    
    if symbol.upper() == 'ALL':
        # 全銘柄包括解析（カタログベース）
        try:
            from applications.analysis_tools.crash_alert_system import main as run_crash_alert
            print("🌍 カタログベース包括解析を実行...")
            run_crash_alert()
            return True
        except Exception as e:
            print(f"❌ Crash alert analysis error: {e}")
            return False
    elif symbol.upper() == 'MARKET':
        # 市場リスク分析
        try:
            from applications.analysis_tools.market_analyzer import main as run_market_analysis
            print("📈 市場リスク分析を実行...")
            run_market_analysis()
            return True
        except Exception as e:
            print(f"❌ Market analysis error: {e}")
            return False
    else:
        # 個別銘柄解析
        try:
            from applications.examples.simple_symbol_analysis import analyze_symbol
            print(f"🎯 個別銘柄解析: {symbol}")
            result = analyze_symbol(symbol, period)
            if result:
                print(f"✅ {symbol} analysis completed")
            return True
        except Exception as e:
            print(f"❌ Symbol analysis error: {e}")
            return False

def run_validation(crash_type='all'):
    """Run historical crash validation"""
    print(f"🎯 Running validation: {crash_type}")
    
    if crash_type in ['1987', 'all']:
        try:
            from core.validation.crash_validators.black_monday_1987_validator import main as validate_1987
            result = validate_1987()
            if result:
                print("✅ 1987 Black Monday validation: PASSED")
            else:
                print("❌ 1987 Black Monday validation: FAILED")
        except Exception as e:
            print(f"❌ 1987 validation error: {e}")
    
    if crash_type in ['2000', 'all']:
        try:
            from core.validation.crash_validators.dotcom_bubble_2000_validator import main as validate_2000
            result = validate_2000()
            if result:
                print("✅ 2000 Dotcom Bubble validation: PASSED")
            else:
                print("❌ 2000 Dotcom Bubble validation: FAILED")
        except Exception as e:
            print(f"❌ 2000 validation error: {e}")

def run_scheduler(symbol):
    """Run analysis scheduler for symbol (DEPRECATED)"""
    print(f"⚠️ スケジューラー機能は廃止されました")
    print(f"📊 代わりに以下のコマンドを使用してください:")
    print(f"   python applications/analysis_tools/crash_alert_system.py")
    print(f"   python applications/analysis_tools/market_analyzer.py")
    return False

def run_dev_tools(check_env=False, debug_viz=False):
    """Run development tools"""
    if check_env:
        print("🔧 Checking environment...")
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 'dev_workspace/debugging/environment_check.py'
            ])
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Environment check error: {e}")
            return False
    
    if debug_viz:
        print("🔧 Running visualization debug...")
        try:
            import subprocess  
            result = subprocess.run([
                sys.executable, 'dev_workspace/debugging/lppl_viz_debug.py'
            ])
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Visualization debug error: {e}")
            return False
    
    print("🔧 Development tools menu:")
    print("  --check-env: Check system environment")
    print("  --debug-viz: Debug visualization system")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sornette Prediction System - Central Command Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python entry_points/main.py dashboard --type main
  python entry_points/main.py analyze ALL              # カタログ全銘柄解析
  python entry_points/main.py analyze MARKET           # 市場リスク分析
  python entry_points/main.py analyze NASDAQCOM --period 2y  # 個別銘柄解析
  python entry_points/main.py validate --crash 1987
  python entry_points/main.py dev --check-env
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Dashboard commands
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch dashboards')
    dashboard_parser.add_argument('--type', choices=['main', 'symbol'], default='main',
                                help='Dashboard type to launch')
    
    # Analysis commands  
    analysis_parser = subparsers.add_parser('analyze', help='Run LPPL analysis')
    analysis_parser.add_argument('symbol', help='Symbol to analyze (ALL for all symbols, MARKET for market analysis, or specific symbol)')
    analysis_parser.add_argument('--period', default='1y', help='Analysis period (1y, 2y, 3y, 5y)')
    
    # Validation commands
    validate_parser = subparsers.add_parser('validate', help='Run validation tests')
    validate_parser.add_argument('--crash', choices=['1987', '2000', 'all'], default='all',
                                help='Crash validation to run')
    
    # Scheduler commands
    schedule_parser = subparsers.add_parser('schedule', help='Run scheduled analysis')
    schedule_parser.add_argument('symbol', help='Symbol to schedule')
    
    # Development commands
    dev_parser = subparsers.add_parser('dev', help='Development utilities')
    dev_parser.add_argument('--check-env', action='store_true', help='Check environment')
    dev_parser.add_argument('--debug-viz', action='store_true', help='Debug visualization')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    if args.command == 'dashboard':
        launch_dashboard(args.type)
    elif args.command == 'analyze':
        run_analysis(args.symbol, args.period)
    elif args.command == 'validate':
        run_validation(args.crash)
    elif args.command == 'schedule':
        run_scheduler(args.symbol)
    elif args.command == 'dev':
        run_dev_tools(args.check_env, args.debug_viz)

if __name__ == "__main__":
    main()