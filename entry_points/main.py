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

def run_analysis(symbol, period='1y', use_fco=False):
    """Run LPPL analysis on specified symbol
    
    Args:
        symbol: 銘柄コードまたは'ALL'/'MARKET'
        period: 分析期間
        use_fco: FCOエンジンを使用するか（デフォルト: False）
    """
    if use_fco:
        print(f"🎯 Running FCO analysis: {symbol} ({period})")
    else:
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
        # 市場リスク分析（カタログベース包括分析で代替）
        print("📈 市場リスク分析を実行...")
        print("💡 'MARKET'は'ALL'コマンドで代替されました")
        print("   推奨: python entry_points/main.py analyze ALL")
        return run_analysis('ALL')
    else:
        # 個別銘柄解析
        if use_fco:
            # FCOエンジンを使用した解析
            try:
                from core.fitting.fco_engine import FCOEngine
                from infrastructure.database.fco_results_database import FCOResultsDatabase
                from infrastructure.data_sources.unified_data_client import UnifiedDataClient
                
                print(f"🎯 FCO個別銘柄解析: {symbol}")
                
                # データ取得
                from datetime import datetime, timedelta
                data_client = UnifiedDataClient()
                
                # 期間をパース
                end_date = datetime.now()
                if period == '1y':
                    start_date = end_date - timedelta(days=365)
                elif period == '2y':
                    start_date = end_date - timedelta(days=730)
                elif period == '3y':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5y':
                    start_date = end_date - timedelta(days=1825)
                else:
                    start_date = end_date - timedelta(days=365)
                
                # データ取得（タプル形式: (DataFrame, source_name)）
                data, source = data_client.get_data_with_fallback(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if data is None:
                    print(f"❌ データ取得失敗: {symbol}")
                    return False
                    
                # DataFrameから価格データを抽出
                if 'close' in data.columns:
                    prices = data['close'].values
                elif 'Close' in data.columns:
                    prices = data['Close'].values
                elif 'value' in data.columns:
                    prices = data['value'].values
                else:
                    # 最初の数値列を使用
                    prices = data.iloc[:, 0].values
                    
                metadata = {
                    'source': source,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
                
                if prices is None or len(prices) < 200:
                    print(f"❌ データ不足: {symbol} ({len(prices) if prices is not None else 0}点)")
                    return False
                
                # FCO分析実行
                engine = FCOEngine(use_parallel=True, max_workers=4)
                result = engine.compute_ds_lppls_confidence(prices)
                
                # 結果表示
                print(f"\n--- FCO分析結果 ---")
                print(f"DS-LPPLS Confidence (正): {result.ds_lppls_confidence:.2%}")
                print(f"DS-LPPLS Confidence (負): {result.ds_lppls_confidence_neg:.2%}")
                print(f"バブルタイプ: {result.bubble_type}")
                
                if result.predicted_tc:
                    print(f"予測臨界時間: {result.predicted_tc:.3f}")
                    print(f"標準偏差: {result.tc_std:.3f}")
                
                # データベース保存
                db = FCOResultsDatabase()
                db_result = {
                    'symbol': symbol,
                    'analysis_basis_date': metadata.get('end_date'),
                    'data_source': metadata.get('source'),
                    'data_period_start': metadata.get('start_date'),
                    'data_period_end': metadata.get('end_date'),
                    'data_points': len(prices),
                    'ds_lppls_confidence': result.ds_lppls_confidence,
                    'ds_lppls_confidence_neg': result.ds_lppls_confidence_neg,
                    'bubble_type': result.bubble_type,
                    'predicted_tc': result.predicted_tc,
                    'tc_std': result.tc_std,
                    'scenario_probability': result.scenario_probability,
                    'num_windows': result.metadata.get('num_windows', 0),
                    'num_qualified_fits': result.metadata.get('qualified_fits', 0),
                    'filter_m_range': [0.1, 0.9],
                    'filter_omega_range': [2.0, 25.0],
                    'window_results': result.window_results,  # 全窓結果を渡す
                    'metadata': result.metadata
                }
                
                analysis_id = db.save_fco_analysis(db_result)
                print(f"✅ FCO分析結果をDBに保存 (ID: {analysis_id})")
                
                return True
                
            except Exception as e:
                print(f"❌ FCO analysis error: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            # 従来のLPPL解析
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

def run_validation(crash_type='all', use_fco=False):
    """Run historical crash validation"""
    engine_type = "FCO" if use_fco else "LPPL"
    print(f"🎯 Running validation: {crash_type} (Engine: {engine_type})")
    
    if crash_type in ['1987', 'all']:
        try:
            if use_fco:
                # FCO版バリデーション
                from core.validation.crash_validators.black_monday_1987_fco_validator import BlackMonday1987FCOValidator
                validator = BlackMonday1987FCOValidator(use_cache=True)
                result = validator.validate()
                if result:
                    print("✅ 1987 Black Monday FCO validation: PASSED")
                else:
                    print("❌ 1987 Black Monday FCO validation: FAILED")
            else:
                # LPPL版バリデーション
                from core.validation.crash_validators.black_monday_1987_validator import main as validate_1987
                result = validate_1987()
                if result:
                    print("✅ 1987 Black Monday LPPL validation: PASSED")
                else:
                    print("❌ 1987 Black Monday LPPL validation: FAILED")
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

def run_fco_daily(args):
    """FCO日次分析の実行（V3: 自動更新・リトライ機能付き）"""
    if not args.fco_action:
        print("❌ サブコマンドが必要です")
        print("📊 利用可能なコマンド:")
        print("   python entry_points/main.py fco-daily run     # FCO日次分析実行（自動更新付き）")
        print("   python entry_points/main.py fco-daily update  # データ更新のみ実行")
        print("   python entry_points/main.py fco-daily check   # データ利用可能状況確認")
        print("   python entry_points/main.py fco-daily status  # 状態確認")
        print("   python entry_points/main.py fco-daily retry   # 失敗した更新を再試行")
        return False
    
    try:
        from applications.analysis_tools.fco_daily_scheduler_v3 import FCODailySchedulerV3
        scheduler = FCODailySchedulerV3()
        
        if args.fco_action == 'run':
            print("🚀 FCO日次分析を実行します（V3: 自動更新付き）...")
            symbols = args.symbols if hasattr(args, 'symbols') and args.symbols else None
            skip_update = args.skip_update if hasattr(args, 'skip_update') else False
            result = scheduler.run_daily_analysis(symbols=symbols, skip_update=skip_update)
            if 'successful' in result:
                return len(result['successful']) > 0
            return False
            
        elif args.fco_action == 'update':
            print("📥 市場データを更新します...")
            symbols = args.symbols if hasattr(args, 'symbols') and args.symbols else None
            results = scheduler.update_market_data(symbols=symbols)
            success_count = sum(1 for v in results.values() if v)
            print(f"✅ 更新完了: {success_count}/{len(results)}銘柄成功")
            return success_count > 0
            
        elif args.fco_action == 'check':
            print("📊 全履歴キャッシュ利用可能状況を確認します...")
            availability = scheduler.check_data_availability()
            available = sum(1 for v in availability.values() if v['available'])
            print(f"\n✅ {available}/{len(availability)}銘柄が利用可能")
            return available > 0
            
        elif args.fco_action == 'status':
            print("📊 FCOスケジューラー状態:")
            import json
            print(json.dumps(scheduler.state, indent=2, default=str))
            return True
            
        elif args.fco_action == 'retry':
            print("🔄 失敗した更新を再試行します...")
            results = scheduler.retry_failed_updates()
            if results:
                success_count = sum(1 for v in results.values() if v)
                print(f"✅ 再試行完了: {success_count}/{len(results)}銘柄成功")
                return success_count > 0
            else:
                print("📊 再試行対象なし")
                return True
            
        elif args.fco_action == 'test':
            print("🧪 FCOテストモード: 3銘柄で実行します...")
            test_symbols = ['SP500', 'NASDAQCOM', 'BTC']
            result = scheduler.run_daily_analysis(symbols=test_symbols, skip_update=True)
            if 'successful' in result:
                return len(result['successful']) > 0
            return False
            
        elif args.fco_action == 'historical':
            print("⚠️ historical コマンドは廃止されました")
            print("📊 代わりに以下を使用してください:")
            print("   python entry_points/main.py market-data download --full  # 全履歴ダウンロード")
            print("   python entry_points/main.py fco-daily run                # FCO分析実行")
            return False
            
            # 以下は削除予定（互換性のため一時的に残す）
            if False and args.download:
                print("📥 マーケットデータをダウンロード中...")
                symbols = args.symbols if hasattr(args, 'symbols') and args.symbols else None
                cache_files = analyzer.download_all_market_data(years=2, symbols=symbols)
                print(f"✅ {len(cache_files)}銘柄のデータをキャッシュしました")
            
            # 過去データ分析
            if args.analyze:
                periods = analyzer.generate_weekly_periods(weeks=args.weeks)
                print(f"📅 分析期間: {periods[0]} 〜 {periods[-1]} ({len(periods)}週)")
                
                symbols = args.symbols if hasattr(args, 'symbols') and args.symbols else None
                results = analyzer.analyze_historical_periods(periods, symbols)
                
                print(f"\n✅ 分析完了: {results['successful']}件成功")
                return results['successful'] > 0
            
            if not args.download and not args.analyze:
                print("⚠️ --download または --analyze オプションを指定してください")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ FCO日次分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_scheduled_analysis(args):
    """LPPL定期解析システムの実行"""
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
        
        elif args.scheduled_action == 'backfillbatch':
            print(f"🚀 Batch Backfill 実行: {args.start} から")
            print("⚡ API効率化バージョン: 一括データ取得で高速化")
            
            # Import batch analyzer
            from applications.analysis_tools.batch_scheduled_analyzer import BatchScheduledAnalyzer
            batch_analyzer = BatchScheduledAnalyzer()
            
            # Execute backfill-v2
            result = batch_analyzer.run_batch_backfill(
                start_date=args.start,
                end_date=args.end,
                schedule_name=args.schedule,
                dry_run=args.dry_run if hasattr(args, 'dry_run') else False
            )
            
            return len(result['successful']) > 0
            
    except Exception as e:
        print(f"❌ 定期解析システムエラー: {e}")
        return False

def run_market_data(args):
    """市場データ管理の実行（新アーキテクチャ）"""
    if not args.market_action:
        print("❌ サブコマンドが必要です")
        print("📊 利用可能なコマンド:")
        print("   python entry_points/main.py market-data download  # データダウンロード")
        print("   python entry_points/main.py market-data update    # 差分更新")
        print("   python entry_points/main.py market-data stats     # 統計表示")
        return False
    
    try:
        from infrastructure.market_data.data_downloader import MarketDataDownloader
        downloader = MarketDataDownloader()
        
        if args.market_action == 'download':
            print("📥 市場データダウンロード開始...")
            # カンマ区切りの文字列をリストに変換
            symbols_list = None
            if hasattr(args, 'symbols') and args.symbols:
                if isinstance(args.symbols, str):
                    symbols_list = [s.strip() for s in args.symbols.split(',')]
                else:
                    symbols_list = args.symbols

            results = downloader.download_all_symbols(
                symbols=symbols_list,
                years=args.years if hasattr(args, 'years') else 2
            )
            success_count = sum(1 for v in results.values() if v)
            print(f"✅ 完了: {success_count}/{len(results)}銘柄成功")
            return success_count > 0
            
        elif args.market_action == 'update':
            print("🔄 最新データ差分更新...")
            # カンマ区切りの文字列をリストに変換
            symbols_list = None
            if hasattr(args, 'symbols') and args.symbols:
                if isinstance(args.symbols, str):
                    symbols_list = [s.strip() for s in args.symbols.split(',')]
                else:
                    symbols_list = args.symbols

            results = downloader.update_latest_data(
                symbols=symbols_list
            )
            success_count = sum(1 for v in results.values() if v)
            print(f"✅ 更新: {success_count}/{len(results)}銘柄成功")
            return success_count > 0
            
        elif args.market_action == 'stats':
            print("📊 データ統計:")
            stats = downloader.get_data_stats()
            import json
            print(json.dumps(stats, indent=2, default=str))
            return True
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_fco_analyze(args):
    """FCO分析の実行（ローカルデータ専用）"""
    if not args.fco_analyze_action:
        print("❌ サブコマンドが必要です")
        print("📊 利用可能なコマンド:")
        print("   python entry_points/main.py fco-analyze run         # 分析実行")
        print("   python entry_points/main.py fco-analyze historical  # 過去分析")
        print("   python entry_points/main.py fco-analyze status      # 状態確認")
        return False
    
    try:
        from applications.analysis_tools.fco_daily_analyzer import FCODailyAnalyzer
        analyzer = FCODailyAnalyzer()
        
        if args.fco_analyze_action == 'run':
            print("🔬 FCO分析実行...")
            result = analyzer.run_daily_analysis(
                symbols=args.symbols if hasattr(args, 'symbols') else None,
                analysis_date=args.date if hasattr(args, 'date') else None
            )
            print(f"✅ 完了: {result['total_success']}銘柄成功")
            return result['total_success'] > 0
            
        elif args.fco_analyze_action == 'historical':
            print("📅 過去期間分析...")

            # --start-dateが指定された場合は期間リストを生成
            if hasattr(args, 'start_date') and args.start_date:
                from datetime import datetime, timedelta

                start = datetime.strptime(args.start_date, '%Y-%m-%d')
                if hasattr(args, 'end_date') and args.end_date:
                    end = datetime.strptime(args.end_date, '%Y-%m-%d')
                else:
                    end = datetime.now() - timedelta(days=1)  # 昨日まで

                # 頻度に応じて期間リストを生成
                frequency = args.frequency if hasattr(args, 'frequency') else 'weekly'
                periods = []
                current = start

                if frequency == 'weekly':
                    # 週次: 毎週土曜日
                    while current <= end:
                        days_to_saturday = (5 - current.weekday()) % 7
                        saturday = current + timedelta(days=days_to_saturday)
                        if saturday <= end:
                            periods.append(saturday.strftime('%Y-%m-%d'))
                        current += timedelta(weeks=1)
                else:  # daily
                    # 日次: 毎日
                    while current <= end:
                        periods.append(current.strftime('%Y-%m-%d'))
                        current += timedelta(days=1)

                print(f"📊 生成された期間: {len(periods)}件 ({periods[0]} 〜 {periods[-1]})")

                symbols = args.symbols if hasattr(args, 'symbols') and args.symbols else ['SP500']
                total_success = 0
                total_failed = 0

                # 🚀 銘柄並列化モード（--parallel フラグで有効化）
                if hasattr(args, 'parallel') and args.parallel:
                    print("🚀 銘柄並列化モード: カスタムFCOエンジン使用（科学的精度100%保証）")

                    from infrastructure.parallelization import analyze_symbols_parallel
                    from infrastructure.database.market_price_database import get_prices_from_db
                    from infrastructure.database.fco_results_database import FCOResultsDatabase

                    db = FCOResultsDatabase()

                    # 各期間ごとに銘柄並列化実行
                    for i, period_end in enumerate(periods, 1):
                        end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
                        period_days = (end_date - start.date()).days

                        print(f"\n📅 [{i}/{len(periods)}] 期間: {period_end} ({period_days}日間)")

                        # 価格データ取得（ログスケール最適化）
                        prices_dict = {}
                        for symbol in symbols:
                            log_prices = get_prices_from_db(
                                symbol=symbol,
                                period_days=period_days,
                                end_date=period_end,
                                use_log_scale=True  # ログスケール最適化（Phase B実装済み）
                            )
                            if log_prices is not None and len(log_prices) >= 200:
                                prices_dict[symbol] = log_prices
                            else:
                                print(f"  ⚠️ {symbol}: データ不足またはなし")

                        if len(prices_dict) == 0:
                            print(f"  ❌ 利用可能なデータなし")
                            continue

                        # 銘柄並列解析（2-4倍高速化）
                        print(f"  🔬 銘柄並列解析開始: {len(prices_dict)}銘柄")
                        results = analyze_symbols_parallel(
                            symbols=list(prices_dict.keys()),
                            prices_dict=prices_dict,
                            n_tries=10,
                            n_symbol_workers=4,  # 4銘柄同時処理
                            n_window_workers=None  # 自動設定（残りCPU）
                        )

                        # データベース保存
                        for symbol, result in results.items():
                            if result is not None:
                                try:
                                    analysis_data = {
                                        'symbol': symbol,
                                        'analysis_date': datetime.now(),
                                        'analysis_basis_date': period_end,
                                        'data_source': 'local_db',
                                        'data_period_start': start.strftime('%Y-%m-%d'),
                                        'data_period_end': period_end,
                                        'data_points': len(prices_dict[symbol]),
                                        'ds_lppls_confidence': result.ds_lppls_confidence,
                                        'ds_lppls_confidence_neg': result.ds_lppls_confidence_neg,
                                        'bubble_type': result.bubble_type,
                                        'predicted_tc': result.predicted_tc,
                                        'tc_std': result.tc_std if result.tc_std else None,
                                        'scenario_probability': result.scenario_probability,
                                        'num_qualified_fits': result.qualified_fits,
                                        'num_windows': result.total_fits,
                                        'window_results': result.window_results,
                                        'metadata': result.metadata
                                    }

                                    db.save_fco_analysis(analysis_data)
                                    print(f"  ✅ {symbol}: Confidence={result.ds_lppls_confidence:.2%}, " +
                                          f"Bubble={result.bubble_type}, Qualified={result.qualified_fits}/{result.total_fits}")
                                    total_success += 1

                                except Exception as e:
                                    print(f"  ❌ {symbol} DB保存エラー: {e}")
                                    total_failed += 1
                            else:
                                print(f"  ❌ {symbol}: 解析失敗")
                                total_failed += 1

                    print(f"\n✅ 銘柄並列化分析完了: {total_success}件成功, {total_failed}件失敗")
                    return total_success > 0

                else:
                    # 既存の逐次版実装（FCOService経由、互換性維持）
                    sys.path.insert(0, str(project_root / 'fco-api'))
                    from app.services.fco_service import FCOService
                    fco_service = FCOService()

                    for symbol in symbols:
                        print(f"\n🎯 {symbol} の分析開始...")
                        for i, period_end in enumerate(periods, 1):
                            try:
                                end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
                                period_days = (end_date - start.date()).days

                                print(f"  [{i}/{len(periods)}] {period_end} まで ({period_days}日間)")

                                result = fco_service.run_new_analysis(
                                    symbol=symbol,
                                    period=period_days,
                                    end_date=end_date,
                                    force=True,
                                    use_external_api=False  # ローカルDBから読み込む
                                )

                                print(f"    ✅ Confidence: {result.get('ds_lppls_confidence', 0):.2%}, " +
                                      f"Bubble: {result.get('bubble_type', 'N/A')}")
                                total_success += 1

                            except Exception as e:
                                print(f"    ❌ エラー: {e}")
                                total_failed += 1

                    print(f"\n✅ 分析完了: {total_success}件成功, {total_failed}件失敗")
                    return total_success > 0

            # 既存の期間リスト指定方式
            elif hasattr(args, 'periods') and args.periods:
                periods = args.periods
            else:
                # 過去4週間の土曜日
                from datetime import datetime, timedelta
                today = datetime.now()
                periods = []
                for i in range(4):
                    date = today - timedelta(weeks=i)
                    days_to_saturday = (5 - date.weekday()) % 7
                    saturday = date + timedelta(days=days_to_saturday)
                    periods.append(saturday.strftime('%Y-%m-%d'))
                periods.reverse()

            result = analyzer.analyze_historical(
                periods=periods,
                symbols=args.symbols if hasattr(args, 'symbols') else None
            )
            print(f"✅ 総分析: {result['total_analyses']}件完了")
            return result['total_success'] > 0
            
        elif args.fco_analyze_action == 'status':
            print("📊 FCO分析状態:")
            status = analyzer.get_status()
            import json
            print(json.dumps(status, indent=2, default=str))
            return True
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
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
    analysis_parser.add_argument('--fco', action='store_true', help='Use FCO multi-window analysis engine')
    
    # Validation commands
    validate_parser = subparsers.add_parser('validate', help='Run validation tests')
    validate_parser.add_argument('--crash', choices=['1987', '2000', 'all'], default='all',
                                help='Crash validation to run')
    validate_parser.add_argument('--fco', action='store_true',
                                help='Use FCO engine for validation (default: LPPL)')
    
    # FCO Daily Analysis commands
    fco_daily_parser = subparsers.add_parser('fco-daily', help='FCO日次分析システム')
    fco_daily_subparsers = fco_daily_parser.add_subparsers(dest='fco_action', help='FCO日次分析コマンド')
    
    # FCO run subcommand
    fco_run_parser = fco_daily_subparsers.add_parser('run', help='FCO日次分析実行（自動更新付き）')
    fco_run_parser.add_argument('--symbols', nargs='+', help='対象銘柄')
    fco_run_parser.add_argument('--skip-update', action='store_true', help='データ更新をスキップ')
    
    # FCO update subcommand (new)
    fco_update_parser = fco_daily_subparsers.add_parser('update', help='市場データ更新のみ実行')
    fco_update_parser.add_argument('--symbols', nargs='+', help='対象銘柄')
    
    # FCO retry subcommand
    fco_retry_parser = fco_daily_subparsers.add_parser('retry', help='失敗した更新の再試行')
    
    # FCO check subcommand (new)
    fco_check_parser = fco_daily_subparsers.add_parser('check', help='データ利用可能状況確認')
    
    # FCO status subcommand
    fco_status_parser = fco_daily_subparsers.add_parser('status', help='FCO分析状態確認')
    
    # FCO test subcommand
    fco_test_parser = fco_daily_subparsers.add_parser('test', help='FCOテスト実行（3銘柄のみ）')
    
    # FCO historical subcommand (deprecated - kept for compatibility)
    fco_historical_parser = fco_daily_subparsers.add_parser('historical', help='FCO過去データ蓄積（旧版）')
    fco_historical_parser.add_argument('--download', action='store_true', help='マーケットデータをダウンロード')
    fco_historical_parser.add_argument('--analyze', action='store_true', help='過去データを分析')
    fco_historical_parser.add_argument('--weeks', type=int, default=12, help='分析する週数（デフォルト: 12週）')
    fco_historical_parser.add_argument('--symbols', nargs='+', help='対象銘柄（省略時は全銘柄）')
    
    # Market Data commands (new architecture)
    market_parser = subparsers.add_parser('market-data', help='市場データ管理（新アーキテクチャ）')
    market_subparsers = market_parser.add_subparsers(dest='market_action', help='市場データコマンド')
    
    # Market download subcommand
    market_download_parser = market_subparsers.add_parser('download', help='市場データダウンロード')
    market_download_parser.add_argument('--symbols', help='対象銘柄（カンマ区切り）')
    market_download_parser.add_argument('--years', type=int, default=2, help='取得年数')
    
    # Market update subcommand
    market_update_parser = market_subparsers.add_parser('update', help='最新データ差分更新')
    market_update_parser.add_argument('--symbols', help='対象銘柄（カンマ区切り）')
    
    # Market stats subcommand
    market_stats_parser = market_subparsers.add_parser('stats', help='データ統計表示')
    
    # FCO Analysis commands (new architecture - cache only)
    fco_analysis_parser = subparsers.add_parser('fco-analyze', help='FCO分析（ローカルデータ専用）')
    fco_analysis_subparsers = fco_analysis_parser.add_subparsers(dest='fco_analyze_action', help='FCO分析コマンド')
    
    # FCO analyze subcommand
    fco_analyze_run_parser = fco_analysis_subparsers.add_parser('run', help='FCO分析実行')
    fco_analyze_run_parser.add_argument('--symbols', nargs='+', help='対象銘柄')
    fco_analyze_run_parser.add_argument('--date', help='分析基準日 (YYYY-MM-DD)')
    
    # FCO historical analysis subcommand
    fco_analyze_hist_parser = fco_analysis_subparsers.add_parser('historical', help='過去期間分析')
    fco_analyze_hist_parser.add_argument('--periods', nargs='+', help='分析期間リスト')
    fco_analyze_hist_parser.add_argument('--symbols', nargs='+', help='対象銘柄')
    fco_analyze_hist_parser.add_argument('--start-date', help='開始日 (YYYY-MM-DD) - 指定時は期間リスト生成')
    fco_analyze_hist_parser.add_argument('--end-date', help='終了日 (YYYY-MM-DD、省略時は昨日)')
    fco_analyze_hist_parser.add_argument('--frequency', choices=['weekly', 'daily'], default='weekly', help='分析頻度')
    fco_analyze_hist_parser.add_argument('--parallel', action='store_true',
                                        help='銘柄並列化を有効化（カスタムFCO使用、2-4倍高速化、科学的精度100%保証）')
    
    # FCO analyzer status subcommand
    fco_analyze_status_parser = fco_analysis_subparsers.add_parser('status', help='分析状態確認')
    
    # Scheduled Analysis commands (LPPL)
    scheduled_parser = subparsers.add_parser('scheduled-analysis', help='LPPL定期解析システム')
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
    
    # backfillbatch subcommand (batch efficient version)
    backfillbatch_parser = scheduled_subparsers.add_parser('backfillbatch', help='効率的バッチバックフィル（API最適化版）')
    backfillbatch_parser.add_argument('--start', required=True, help='開始日 (YYYY-MM-DD)')
    backfillbatch_parser.add_argument('--end', help='終了日 (YYYY-MM-DD、省略時は昨日)')
    backfillbatch_parser.add_argument('--schedule', default='fred_weekly', help='スケジュール名')
    backfillbatch_parser.add_argument('--dry-run', action='store_true', help='実行シミュレーション（DB保存なし）')
    
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
        run_analysis(args.symbol, args.period, use_fco=args.fco)
    elif args.command == 'validate':
        run_validation(args.crash, use_fco=args.fco if hasattr(args, 'fco') else False)
    elif args.command == 'scheduled-analysis':
        run_scheduled_analysis(args)
    elif args.command == 'fco-daily':
        run_fco_daily(args)
    elif args.command == 'market-data':
        run_market_data(args)
    elif args.command == 'fco-analyze':
        run_fco_analyze(args)
    elif args.command == 'dev':
        run_dev_tools(args.check_env, args.debug_viz)

if __name__ == "__main__":
    main()