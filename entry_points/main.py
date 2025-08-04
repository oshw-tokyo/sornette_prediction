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

def run_scheduled_analysis(args):
    """定期解析システムの実行"""
    if not args.scheduled_action:
        print("❌ サブコマンドが必要です")
        print("📊 利用可能なコマンド:")
        print("   python entry_points/main.py scheduled-analysis configure  # スケジュール設定")
        print("   python entry_points/main.py scheduled-analysis run        # 定期解析実行")
        print("   python entry_points/main.py scheduled-analysis status     # システム状態確認")
        print("   python entry_points/main.py scheduled-analysis errors     # エラー解析")
        print("   python entry_points/main.py scheduled-analysis cleanup    # 古いエラーログ削除")
        print("   python entry_points/main.py scheduled-analysis backfill --start 2024-01-01  # 過去データ補完")
        return False
    
    try:
        from applications.analysis_tools.scheduled_analyzer import ScheduledAnalyzer
        analyzer = ScheduledAnalyzer()
        
        if args.scheduled_action == 'run':
            # 新しい方式でスケジュール名を特定
            if hasattr(args, 'source') and hasattr(args, 'frequency') and args.source and args.frequency:
                schedule_name = f"{args.source}_{args.frequency}"
                print(f"🕐 定期解析実行: {schedule_name} (データソース: {args.source}, 頻度: {args.frequency})")
            else:
                schedule_name = args.schedule  # 旧方式との互換性
                print(f"🕐 定期解析実行: {schedule_name}")
            
            result = analyzer.run_scheduled_analysis(schedule_name)
            
            print(f"\n📊 実行結果サマリー:")
            print(f"   スケジュール名: {result['schedule_name']}")
            print(f"   分析基準日: {result['basis_date']}")
            print(f"   不足期間数: {result['missing_periods']}")
            print(f"   自動補完実行: {'✅' if result['auto_backfill_executed'] else '❌'}")
            print(f"   成功銘柄数: {result['total_success']}")
            print(f"   失敗銘柄数: {result['total_failed']}")
            print(f"   実行時間: {result['duration']}")
            
            return result['total_success'] > 0
            
        elif args.scheduled_action == 'status':
            print("📊 定期解析システム状態")
            print("=" * 50)
            status = analyzer.get_schedule_status()
            
            print(f"アクティブスケジュール: {status['enabled_schedules']}")
            for schedule in status['schedules']:
                print(f"  - {schedule['name']}:")
                print(f"    頻度: {schedule['frequency']}")
                print(f"    銘柄数: {schedule['symbols_count']}")
                print(f"    最終実行: {schedule['last_run'] or 'なし'}")
                print(f"    有効: {'✅' if schedule['enabled'] else '❌'}")
            
            # エラーサマリーも表示
            print(f"\n🛡️ エラーサマリー（過去7日）:")
            try:
                error_summary = analyzer.get_error_summary(7)
                print(f"   総エラー数: {error_summary['recovery_statistics']['total_errors']}")
                print(f"   回復試行: {error_summary['recovery_statistics']['attempted_recoveries']}")
                print(f"   回復成功: {error_summary['recovery_statistics']['successful_recoveries']}")
                print(f"   回復成功率: {error_summary['recovery_statistics']['recovery_rate']:.1f}%")
                
                if error_summary['error_statistics']:
                    print(f"   主要エラー:")
                    for category, severity, count in error_summary['error_statistics'][:3]:
                        print(f"     - {category}({severity}): {count}件")
            except Exception as e:
                print(f"   エラーサマリー取得エラー: {e}")
            
            return True
            
        elif args.scheduled_action == 'errors':
            print("🛡️ エラー解析システム")
            print("=" * 50)
            
            # エラーサマリーの詳細表示
            try:
                days = getattr(args, 'days', 7)
                error_summary = analyzer.get_error_summary(days)
                
                print(f"📊 エラーサマリー（過去{days}日間）:")
                print(f"   総エラー数: {error_summary['recovery_statistics']['total_errors']}")
                print(f"   回復試行数: {error_summary['recovery_statistics']['attempted_recoveries']}")
                print(f"   回復成功数: {error_summary['recovery_statistics']['successful_recoveries']}")
                print(f"   回復成功率: {error_summary['recovery_statistics']['recovery_rate']:.1f}%")
                
                if error_summary['error_statistics']:
                    print(f"\n📋 エラー分類:")
                    for category, severity, count in error_summary['error_statistics']:
                        print(f"   - {category}({severity}): {count}件")
                
                # 古いエラーログクリーンアップの提案
                if error_summary['recovery_statistics']['total_errors'] > 100:
                    print(f"\n💡 提案: python entry_points/main.py scheduled-analysis cleanup")
                
            except Exception as e:
                print(f"❌ エラーサマリー取得失敗: {e}")
                return False
            
            return True
            
        elif args.scheduled_action == 'cleanup':
            print("🧹 古いエラーログクリーンアップ")
            print("=" * 50)
            
            try:
                days = getattr(args, 'days', 90)
                deleted_count = analyzer.cleanup_old_errors(days)
                print(f"✅ {deleted_count}件の古いエラーログを削除しました")
                print(f"   （{days}日以前のレコード）")
                
            except Exception as e:
                print(f"❌ クリーンアップ失敗: {e}")
                return False
            
            return True
            
        elif args.scheduled_action == 'configure':
            print("⚙️ スケジュール設定")
            print("=" * 50)
            
            try:
                # 設定パラメータの取得
                source = getattr(args, 'source', None)
                frequency = getattr(args, 'frequency', None)
                symbols = getattr(args, 'symbols', None)
                
                if not all([source, frequency]):
                    print("❌ 必須パラメータが不足しています")
                    print("📋 使用例:")
                    print("   python entry_points/main.py scheduled-analysis configure --source fred --frequency weekly --symbols NASDAQ,SP500")
                    print("   python entry_points/main.py scheduled-analysis configure --source alpha_vantage --frequency daily --symbols AAPL,MSFT")
                    print("\n📊 利用可能な値:")
                    print("   --source: fred, alpha_vantage")
                    print("   --frequency: weekly, daily")
                    print("   --symbols: カンマ区切りの銘柄リスト")
                    return False
                
                # スケジュール名生成（新方式）
                schedule_name = f"{source}_{frequency}"
                
                # 銘柄リストの処理
                if symbols:
                    symbol_list = [s.strip() for s in symbols.split(',')]
                else:
                    # デフォルトの銘柄リスト
                    symbol_list = ['NASDAQCOM', 'SP500', 'DJI'] if source == 'fred' else ['AAPL', 'MSFT', 'GOOGL']
                
                # スケジュール設定の更新/作成
                result = analyzer.configure_schedule(
                    schedule_name=schedule_name,
                    source=source,
                    frequency=frequency,
                    symbols=symbol_list
                )
                
                if result:
                    print(f"✅ スケジュール設定完了: {schedule_name}")
                    print(f"   データソース: {source}")
                    print(f"   実行頻度: {frequency}")
                    print(f"   対象銘柄: {', '.join(symbol_list)}")
                    
                    # 実行時間の表示
                    if frequency == 'weekly':
                        print(f"   実行日時: 毎週土曜日 09:00 UTC")
                    elif frequency == 'daily':
                        print(f"   実行日時: 毎日 09:00 UTC")
                else:
                    print("❌ スケジュール設定に失敗しました")
                    return False
                
            except Exception as e:
                print(f"❌ 設定エラー: {e}")
                return False
            
            return True
            
        elif args.scheduled_action == 'backfill':
            print(f"🔄 バックフィル実行: {args.start} から")
            
            # 実行前確認
            config = analyzer.schedule_manager.get_schedule_config(args.schedule)
            if not config:
                print(f"❌ スケジュール設定が見つかりません: {args.schedule}")
                return False
            
            from datetime import datetime, timedelta
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
            end_date = datetime.strptime(args.end, '%Y-%m-%d') if args.end else datetime.now() - timedelta(days=1)
            
            # 期間の妥当性チェック
            days_diff = (end_date - start_date).days
            if days_diff < 0:
                print("❌ 終了日が開始日より前です")
                return False
            
            # 大量データの警告
            if days_diff > 365:
                print(f"⚠️ 長期間のバックフィル: {days_diff}日間")
                print("📊 推定分析数:", days_diff // 7 * len(config.symbols), "件（週次の場合）")
                
                confirm = input("実行しますか？ (y/N): ")
                if confirm.lower() != 'y':
                    print("❌ バックフィル実行をキャンセルしました")
                    return False
            
            result = analyzer.run_backfill_analysis(args.start, args.end, args.schedule)
            
            print(f"\n📊 バックフィル結果:")
            print(f"   バッチID: {result['batch_id']}")
            print(f"   成功率: {result['success_rate']:.1f}%")
            print(f"   実行時間: {result['duration']}")
            
            return result['total_successful'] > 0
            
    except Exception as e:
        print(f"❌ 定期解析システムエラー: {e}")
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
    
    # Scheduled Analysis commands
    scheduled_parser = subparsers.add_parser('scheduled-analysis', help='定期解析システム')
    scheduled_subparsers = scheduled_parser.add_subparsers(dest='scheduled_action', help='定期解析コマンド')
    
    # run subcommand
    run_parser = scheduled_subparsers.add_parser('run', help='定期解析実行')
    run_parser.add_argument('--schedule', default='fred_weekly', help='スケジュール名（旧方式互換）')
    run_parser.add_argument('--source', choices=['fred', 'alpha_vantage'], help='データソース（新方式）')
    run_parser.add_argument('--frequency', choices=['weekly', 'daily'], help='実行頻度（新方式）')
    
    # status subcommand
    status_parser = scheduled_subparsers.add_parser('status', help='解析状態確認')
    
    # configure subcommand
    configure_parser = scheduled_subparsers.add_parser('configure', help='スケジュール設定')
    configure_parser.add_argument('--source', choices=['fred', 'alpha_vantage'], required=True,
                                help='データソース (fred: 経済指標, alpha_vantage: 個別株)')
    configure_parser.add_argument('--frequency', choices=['weekly', 'daily'], required=True,
                                help='実行頻度 (weekly: 週次, daily: 日次)')
    configure_parser.add_argument('--symbols', help='対象銘柄（カンマ区切り、省略時はデフォルト）')
    
    # backfill subcommand
    backfill_parser = scheduled_subparsers.add_parser('backfill', help='過去データ蓄積')
    backfill_parser.add_argument('--start', required=True, help='開始日 (YYYY-MM-DD)')
    backfill_parser.add_argument('--end', help='終了日 (YYYY-MM-DD、省略時は昨日)')
    backfill_parser.add_argument('--schedule', default='fred_weekly', help='スケジュール名')
    
    # errors subcommand
    errors_parser = scheduled_subparsers.add_parser('errors', help='エラー解析・監視')
    errors_parser.add_argument('--days', type=int, default=7, help='解析期間（日数）')
    
    # cleanup subcommand
    cleanup_parser = scheduled_subparsers.add_parser('cleanup', help='古いエラーログ削除')
    cleanup_parser.add_argument('--days', type=int, default=90, help='削除対象期間（日数）')
    
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
    elif args.command == 'scheduled-analysis':
        run_scheduled_analysis(args)
    elif args.command == 'dev':
        run_dev_tools(args.check_env, args.debug_viz)

if __name__ == "__main__":
    main()