#!/usr/bin/env python3
"""
FCO Daily Analysis Scheduler V3
自動データ更新とリトライ機能を統合した新バージョン

主要機能:
- 分析前の自動データ更新
- 更新失敗時のリトライ機能
- 全履歴キャッシュの差分更新
- エラー時の継続性保証
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import time
import traceback

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from applications.analysis_tools.fco_daily_analyzer import FCODailyAnalyzer
from infrastructure.market_data.data_downloader import MarketDataDownloader
from infrastructure.market_data.smart_data_updater import SmartDataUpdater

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FCODailySchedulerV3:
    """FCO日次分析スケジューラー V3（自動更新・リトライ機能付き）"""
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 3, 5]  # 秒単位の待機時間
    
    def __init__(self, 
                 state_file: str = "results/fco_scheduler_state.json",
                 auto_update: bool = True,
                 use_smart_update: bool = True):
        """
        初期化
        
        Args:
            state_file: スケジューラー状態ファイル
            auto_update: 分析前に自動でデータを更新するか
            use_smart_update: スマート更新を使用するか
        """
        self.state_file = state_file
        self.auto_update = auto_update
        self.use_smart_update = use_smart_update
        
        # FCO分析器（全履歴キャッシュ専用）
        self.analyzer = FCODailyAnalyzer()
        
        # データ更新システム
        if use_smart_update:
            self.smart_updater = SmartDataUpdater()
            logger.info("   📊 スマート更新モード有効（市場休業日対応）")
        else:
            self.downloader = MarketDataDownloader(for_fco=True)
        
        # 利用可能な銘柄
        self.symbols = self.analyzer.available_symbols
        
        # 状態管理
        self.state = self._load_state()
        
        logger.info(f"📊 FCOスケジューラーV3初期化完了")
        logger.info(f"   利用可能銘柄: {len(self.symbols)}（全履歴キャッシュ）")
        logger.info(f"   自動更新: {'有効' if auto_update else '無効'}")
    
    def _load_state(self) -> Dict:
        """スケジューラー状態を読み込み"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"状態ファイル読み込みエラー: {e}")
        
        # デフォルト状態
        return {
            'last_run_date': None,
            'last_update_date': None,
            'last_success_count': 0,
            'last_failure_count': 0,
            'failed_symbols': [],
            'update_failures': [],
            'architecture': 'v3_auto_update'
        }
    
    def _save_state(self):
        """スケジューラー状態を保存"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def _update_data_with_retry(self, symbols: List[str]) -> Dict[str, bool]:
        """
        データ更新（リトライ機能付き）
        
        Args:
            symbols: 更新対象銘柄
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        results = {}
        failed_symbols = []
        
        # スマート更新モードの場合
        if self.use_smart_update:
            # まず更新必要性をチェック
            update_needed = {}
            for symbol in symbols:
                needs_update, start_date, end_date = self.smart_updater.check_update_needed(symbol)
                if needs_update:
                    update_needed[symbol] = (start_date, end_date)
                else:
                    results[symbol] = True  # 既に最新
                    logger.info(f"  ✅ {symbol}: 既に最新")
            
            # 更新が必要な銘柄のみ処理
            for symbol, (start_date, end_date) in update_needed.items():
                success = False
                
                # リトライループ
                for retry in range(self.MAX_RETRIES):
                    try:
                        logger.info(f"  📥 {symbol}: {start_date} 〜 {end_date} を更新中..." + 
                                  (f" (リトライ {retry + 1}/{self.MAX_RETRIES})" if retry > 0 else ""))
                        
                        success = self.smart_updater.smart_update(symbol)
                        
                        if success:
                            break
                        else:
                            raise Exception("データ取得失敗")
                            
                    except Exception as e:
                        logger.warning(f"    ⚠️ 更新失敗: {e}")
                        
                        if retry < self.MAX_RETRIES - 1:
                            wait_time = self.RETRY_DELAYS[retry]
                            logger.info(f"    ⏳ {wait_time}秒待機後リトライ...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"    ❌ 最大リトライ回数到達: {symbol}")
                            failed_symbols.append(symbol)
                
                results[symbol] = success
        
        # 従来の更新モード
        else:
            for symbol in symbols:
                success = False
                last_error = None
                
                # リトライループ
                for retry in range(self.MAX_RETRIES):
                    try:
                        logger.info(f"  📥 {symbol}: データ更新中..." + 
                                  (f" (リトライ {retry + 1}/{self.MAX_RETRIES})" if retry > 0 else ""))
                        
                        # 差分更新を試行
                        success = self.downloader.update_latest_data([symbol])[symbol]
                        
                        if success:
                            logger.info(f"    ✅ 更新成功")
                            break
                        else:
                            raise Exception("データ取得失敗")
                            
                    except Exception as e:
                        last_error = e
                        logger.warning(f"    ⚠️ 更新失敗: {e}")
                        
                        if retry < self.MAX_RETRIES - 1:
                            wait_time = self.RETRY_DELAYS[retry]
                            logger.info(f"    ⏳ {wait_time}秒待機後リトライ...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"    ❌ 最大リトライ回数到達: {symbol}")
                            failed_symbols.append(symbol)
                
                results[symbol] = success
                
                # API制限対策（成功時も少し待機）
                if symbol != symbols[-1]:  # 最後の銘柄以外
                    time.sleep(0.5)
        
        # 失敗銘柄を記録
        if failed_symbols:
            self.state['update_failures'] = failed_symbols
            self._save_state()
        
        return results
    
    def update_market_data(self, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        市場データを更新（公開メソッド）
        
        Args:
            symbols: 更新対象銘柄（Noneなら全銘柄）
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        if symbols is None:
            symbols = self.symbols
        
        logger.info("=" * 60)
        logger.info(f"📥 市場データ更新開始（全履歴キャッシュ）")
        logger.info(f"   対象銘柄数: {len(symbols)}")
        logger.info("=" * 60)
        
        # リトライ機能付き更新
        results = self._update_data_with_retry(symbols)
        
        # 結果集計
        success_count = sum(1 for v in results.values() if v)
        failure_count = len(results) - success_count
        
        logger.info("=" * 60)
        logger.info(f"✅ データ更新完了")
        logger.info(f"   成功: {success_count}銘柄")
        if failure_count > 0:
            logger.info(f"   失敗: {failure_count}銘柄")
            failed = [s for s, v in results.items() if not v]
            logger.info(f"   失敗銘柄: {', '.join(failed)}")
        logger.info("=" * 60)
        
        # 状態更新
        self.state['last_update_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_state()
        
        return results
    
    def run_daily_analysis(self, 
                          symbols: Optional[List[str]] = None,
                          analysis_date: Optional[str] = None,
                          skip_update: bool = False) -> Dict:
        """
        日次FCO分析を実行（自動更新付き）
        
        Args:
            symbols: 分析対象銘柄（Noneなら全銘柄）
            analysis_date: 分析基準日（Noneなら最新）
            skip_update: データ更新をスキップするか
        
        Returns:
            実行結果の辞書
        """
        start_time = datetime.now()
        today = start_time.strftime('%Y-%m-%d')
        
        if symbols is None:
            symbols = self.symbols
        
        logger.info("=" * 60)
        logger.info(f"🚀 FCO日次分析開始 V3（自動更新機能付き）")
        logger.info(f"📅 実行日時: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📊 対象銘柄数: {len(symbols)}")
        logger.info(f"🗄️ データソース: 全履歴ローカルキャッシュ")
        logger.info("=" * 60)
        
        # 前回実行日チェック（同一日の再実行を許可するオプション）
        if self.state.get('last_run_date') == today and not analysis_date:
            logger.warning(f"⚠️ 本日({today})は既に実行済みです")
            logger.info("   再実行する場合は analysis_date を指定してください")
            return {'skipped': symbols, 'reason': 'already_run_today'}
        
        # データ更新フェーズ
        if self.auto_update and not skip_update:
            logger.info("\n📥 データ更新フェーズ")
            update_results = self.update_market_data(symbols)
            
            # 更新失敗した銘柄は分析から除外するか警告
            failed_updates = [s for s, v in update_results.items() if not v]
            if failed_updates:
                logger.warning(f"⚠️ {len(failed_updates)}銘柄のデータ更新に失敗しました")
                logger.warning(f"   古いデータで分析を続行します: {', '.join(failed_updates[:5])}")
        
        # 分析フェーズ
        logger.info("\n🔬 分析フェーズ")
        
        # 結果格納
        results = {
            'date': today,
            'start_time': start_time,
            'successful': [],
            'failed': [],
            'skipped': [],
            'details': {},
            'architecture': 'v3_auto_update'
        }
        
        # 各銘柄を分析
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] 📈 {symbol}")
            
            try:
                # FCO分析実行（全履歴キャッシュ使用）
                success = self.analyzer.analyze_symbol(symbol, analysis_date)
                
                if success:
                    results['successful'].append(symbol)
                    logger.info(f"  ✅ 分析成功")
                else:
                    results['failed'].append(symbol)
                    logger.warning(f"  ❌ 分析失敗")
                
            except Exception as e:
                logger.error(f"  ❌ エラー: {e}")
                results['failed'].append(symbol)
                results['details'][symbol] = {'error': str(e)}
            
            # システム負荷軽減のため短い待機
            if i < len(symbols):
                time.sleep(0.1)
        
        # 実行時間計算
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 結果サマリー
        success_count = len(results['successful'])
        failure_count = len(results['failed'])
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ FCO日次分析完了")
        logger.info(f"   成功: {success_count}銘柄")
        logger.info(f"   失敗: {failure_count}銘柄")
        logger.info(f"   実行時間: {duration:.1f}秒")
        logger.info("=" * 60)
        
        # 状態更新
        self.state['last_run_date'] = today
        self.state['last_success_count'] = success_count
        self.state['last_failure_count'] = failure_count
        self.state['failed_symbols'] = results['failed']
        self._save_state()
        
        results['end_time'] = end_time
        results['duration_seconds'] = duration
        
        return results
    
    def retry_failed_updates(self) -> Dict[str, bool]:
        """
        前回失敗したデータ更新を再試行
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        if not self.state.get('update_failures'):
            logger.info("📊 再試行対象の失敗更新がありません")
            return {}
        
        failed_symbols = self.state['update_failures']
        logger.info(f"🔄 {len(failed_symbols)}銘柄のデータ更新を再試行します")
        
        results = self._update_data_with_retry(failed_symbols)
        
        # 成功した銘柄を失敗リストから除外
        remaining_failures = [s for s, v in results.items() if not v]
        self.state['update_failures'] = remaining_failures
        self._save_state()
        
        return results
    
    def check_data_availability(self) -> Dict[str, Dict]:
        """
        全履歴キャッシュの利用可能状況と鮮度を確認
        
        Returns:
            銘柄別の利用可能状況と最終更新日
        """
        logger.info("📊 全履歴キャッシュ利用可能状況:")
        availability = {}
        
        cache_dir = Path("data/market_data/cache/full")
        if not cache_dir.exists():
            logger.error(f"❌ キャッシュディレクトリが存在しません: {cache_dir}")
            return availability
        
        import pandas as pd
        
        for symbol in self.symbols:
            cache_file = cache_dir / f"{symbol}_full.parquet"
            info = {
                'available': False,
                'size_mb': 0,
                'last_date': None,
                'days_old': None,
                'total_days': 0
            }
            
            if cache_file.exists():
                info['available'] = True
                info['size_mb'] = cache_file.stat().st_size / (1024 * 1024)
                
                try:
                    df = pd.read_parquet(cache_file)
                    if len(df) > 0:
                        last_date = df.index.max()
                        info['last_date'] = last_date.strftime('%Y-%m-%d')
                        info['days_old'] = (datetime.now() - last_date).days
                        info['total_days'] = len(df)
                        
                        # 鮮度による状態表示
                        if info['days_old'] == 0:
                            status = "✅ 最新"
                        elif info['days_old'] <= 1:
                            status = "🆗 1日前"
                        elif info['days_old'] <= 7:
                            status = f"⚠️ {info['days_old']}日前"
                        else:
                            status = f"❌ {info['days_old']}日前（要更新）"
                        
                        logger.info(f"  {symbol:12} {status} | {info['total_days']:5}日分 | {info['size_mb']:.2f} MB")
                except Exception as e:
                    logger.error(f"  {symbol:12} ❌ 読み込みエラー: {e}")
            else:
                logger.warning(f"  {symbol:12} ❌ データなし")
            
            availability[symbol] = info
        
        total = len(availability)
        available_count = sum(1 for v in availability.values() if v['available'])
        fresh_count = sum(1 for v in availability.values() 
                         if v['available'] and v.get('days_old', float('inf')) <= 1)
        
        logger.info(f"\n合計: {available_count}/{total}銘柄が利用可能")
        logger.info(f"      {fresh_count}/{total}銘柄が最新（1日以内）")
        
        return availability


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FCO Daily Scheduler V3')
    parser.add_argument('action', 
                       choices=['run', 'update', 'check', 'status', 'retry'],
                       help='Action to perform')
    parser.add_argument('--symbols', nargs='+',
                       help='Specific symbols to analyze')
    parser.add_argument('--date',
                       help='Analysis date (YYYY-MM-DD)')
    parser.add_argument('--skip-update', action='store_true',
                       help='Skip data update phase')
    parser.add_argument('--no-auto-update', action='store_true',
                       help='Disable automatic data updates')
    
    args = parser.parse_args()
    
    scheduler = FCODailySchedulerV3(auto_update=not args.no_auto_update)
    
    if args.action == 'run':
        results = scheduler.run_daily_analysis(
            symbols=args.symbols,
            analysis_date=args.date,
            skip_update=args.skip_update
        )
        if 'successful' in results:
            print(f"\n実行結果: 成功{len(results['successful'])}件、失敗{len(results['failed'])}件")
        
    elif args.action == 'update':
        results = scheduler.update_market_data(symbols=args.symbols)
        success = sum(1 for v in results.values() if v)
        print(f"\n更新結果: 成功{success}/{len(results)}件")
        
    elif args.action == 'check':
        availability = scheduler.check_data_availability()
        available = sum(1 for v in availability.values() if v['available'])
        print(f"\nデータ利用可能: {available}/{len(availability)}銘柄")
        
    elif args.action == 'status':
        print(f"\n📊 FCOスケジューラーV3状態:")
        print(f"最終実行日: {scheduler.state.get('last_run_date', 'なし')}")
        print(f"最終更新日: {scheduler.state.get('last_update_date', 'なし')}")
        print(f"最終成功数: {scheduler.state.get('last_success_count', 0)}")
        print(f"最終失敗数: {scheduler.state.get('last_failure_count', 0)}")
        if scheduler.state.get('failed_symbols'):
            print(f"失敗銘柄: {', '.join(scheduler.state['failed_symbols'])}")
        if scheduler.state.get('update_failures'):
            print(f"更新失敗銘柄: {', '.join(scheduler.state['update_failures'])}")
            
    elif args.action == 'retry':
        results = scheduler.retry_failed_updates()
        if results:
            success = sum(1 for v in results.values() if v)
            print(f"\n再試行結果: 成功{success}/{len(results)}件")
        else:
            print("\n再試行対象なし")


if __name__ == "__main__":
    main()