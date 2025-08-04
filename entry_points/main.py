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
    
    # Import and run basic analysis
    try:
        from applications.examples.basic_analysis import main as run_basic_analysis
        run_basic_analysis()
    except ImportError:
        print("❌ Analysis module not available")
        return False
    
    return True

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
    """Run analysis scheduler for symbol"""
    print(f"⏰ Running scheduler for: {symbol}")
    
    if symbol.upper() == 'NASDAQCOM':
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 'applications/schedulers/nasdaq_scheduler.py'
            ])
            return result.returncode == 0
        except Exception as e:
            print(f"❌ NASDAQ scheduler error: {e}")
            return False
    elif symbol.upper() == 'AAPL':
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 'applications/schedulers/aapl_scheduler.py'
            ])
            return result.returncode == 0
        except Exception as e:
            print(f"❌ AAPL scheduler error: {e}")
            return False
    else:
        print(f"❌ Scheduler not available for symbol: {symbol}")
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
  python entry_points/main.py dashboard --type symbol
  python entry_points/main.py analyze NASDAQCOM --period 2y
  python entry_points/main.py validate --crash 1987
  python entry_points/main.py schedule AAPL
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
    analysis_parser.add_argument('symbol', help='Symbol to analyze')
    analysis_parser.add_argument('--period', default='1y', help='Analysis period')
    
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