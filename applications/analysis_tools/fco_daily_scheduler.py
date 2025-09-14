#!/usr/bin/env python3
"""
FCO Daily Analysis Scheduler
日次でFCO分析を実行するシンプルなスケジューラー

設計方針:
- シンプルさを最優先（複雑な設定管理を避ける）
- 日次実行に特化
- FCOエンジンとの疎結合
- エラー時の継続性（一部失敗でも他の銘柄は処理）
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import time

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.fitting.fco_engine import FCOEngine
from infrastructure.database.fco_results_database import FCOResultsDatabase
from infrastructure.data_sources.unified_data_client import UnifiedDataClient

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FCODailyScheduler:
    """FCO日次分析スケジューラー"""
    
    def __init__(self, 
                 db_path: str = "results/fco_analysis_results.db",
                 state_file: str = "results/fco_scheduler_state.json"):
        """
        初期化
        
        Args:
            db_path: FCOデータベースパス
            state_file: スケジューラー状態ファイル
        """
        self.db = FCOResultsDatabase(db_path)
        self.state_file = state_file
        self.data_client = UnifiedDataClient()
        self.engine = FCOEngine(use_parallel=True, max_workers=4)
        
        # カタログから銘柄リスト取得
        self.symbols = self._load_symbols_from_catalog()
        
        # 状態管理
        self.state = self._load_state()
    
    def _load_symbols_from_catalog(self) -> List[str]:
        """カタログから銘柄リストを読み込み"""
        try:
            catalog_path = Path(__file__).parent.parent.parent / "infrastructure" / "data_sources" / "market_data_catalog.json"
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            # symbols辞書からキーを取得
            symbols = list(catalog.get('symbols', {}).keys())
            logger.info(f"📊 カタログから{len(symbols)}銘柄を読み込み")
            return symbols
        except Exception as e:
            logger.error(f"❌ カタログ読み込みエラー: {e}")
            return []
    
    def _load_state(self) -> Dict:
        """スケジューラー状態を読み込み"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # デフォルト状態
        return {
            'last_run_date': None,
            'last_success_count': 0,
            'last_failure_count': 0,
            'failed_symbols': []
        }
    
    def _save_state(self):
        """スケジューラー状態を保存"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def run_daily_analysis(self) -> Dict:
        """
        日次FCO分析を実行
        
        Returns:
            実行結果の辞書
        """
        start_time = datetime.now()
        today = start_time.strftime('%Y-%m-%d')
        
        logger.info("=" * 60)
        logger.info(f"🚀 FCO日次分析開始: {today}")
        logger.info(f"📊 対象銘柄数: {len(self.symbols)}")
        logger.info("=" * 60)
        
        # 結果格納
        results = {
            'date': today,
            'start_time': start_time,
            'successful': [],
            'failed': [],
            'skipped': [],
            'details': {}
        }
        
        # 前回実行日チェック
        if self.state.get('last_run_date') == today:
            logger.warning(f"⚠️ 本日({today})は既に実行済みです")
            results['skipped'] = self.symbols
            return results
        
        # 各銘柄を分析
        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"\n[{i}/{len(self.symbols)}] 📈 {symbol} を分析中...")
            
            try:
                # データ取得（2年分）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)
                
                df, source = self.data_client.get_data_with_fallback(
                    symbol,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if df is not None and not df.empty:
                    # FREDは'Close'、他は'close'の可能性
                    if 'Close' in df.columns:
                        prices = df['Close'].values
                    elif 'close' in df.columns:
                        prices = df['close'].values
                    else:
                        raise ValueError(f"価格カラムが見つかりません: {df.columns.tolist()}")
                    
                    # FCO分析実行
                    fco_result = self.engine.compute_ds_lppls_confidence(prices)
                    
                    # データベース保存
                    db_data = {
                        'symbol': symbol,
                        'analysis_basis_date': end_date.strftime('%Y-%m-%d'),
                        'data_source': source,
                        'data_period_start': start_date.strftime('%Y-%m-%d'),
                        'data_period_end': end_date.strftime('%Y-%m-%d'),
                        'data_points': len(prices),
                        'ds_lppls_confidence': fco_result.ds_lppls_confidence,
                        'ds_lppls_confidence_neg': fco_result.ds_lppls_confidence_neg,
                        'bubble_type': fco_result.bubble_type,
                        'predicted_tc': fco_result.predicted_tc,
                        'tc_std': fco_result.tc_std,
                        'scenario_probability': fco_result.scenario_probability,
                        'num_windows': fco_result.metadata.get('num_windows', 0),
                        'num_qualified_fits': fco_result.metadata.get('qualified_fits', 0),
                        'window_results': fco_result.window_results,
                        'metadata': fco_result.metadata
                    }
                    
                    analysis_id = self.db.save_fco_analysis(db_data)
                    
                    # Confidence履歴も保存
                    self.db.save_confidence_history(
                        symbol=symbol,
                        timestamp=end_date,
                        price=prices[-1],
                        confidence=fco_result.ds_lppls_confidence,
                        confidence_neg=fco_result.ds_lppls_confidence_neg,
                        bubble_status=fco_result.bubble_type
                    )
                    
                    results['successful'].append(symbol)
                    results['details'][symbol] = {
                        'confidence': fco_result.ds_lppls_confidence,
                        'bubble_type': fco_result.bubble_type,
                        'analysis_id': analysis_id
                    }
                    
                    logger.info(f"  ✅ 成功: Confidence={fco_result.ds_lppls_confidence:.1%}, Type={fco_result.bubble_type}")
                    
                else:
                    results['failed'].append(symbol)
                    logger.warning(f"  ❌ データ取得失敗: データが空またはNone")
                
            except Exception as e:
                results['failed'].append(symbol)
                logger.error(f"  ❌ 分析エラー: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            # API制限対策（少し待機）
            if i < len(self.symbols):
                time.sleep(0.5)
        
        # 結果集計
        end_time = datetime.now()
        results['end_time'] = end_time
        results['duration'] = str(end_time - start_time)
        results['total_success'] = len(results['successful'])
        results['total_failed'] = len(results['failed'])
        results['total_skipped'] = len(results['skipped'])
        
        # 状態更新
        self.state['last_run_date'] = today
        self.state['last_success_count'] = results['total_success']
        self.state['last_failure_count'] = results['total_failed']
        self.state['failed_symbols'] = results['failed']
        self._save_state()
        
        # サマリー表示
        logger.info("\n" + "=" * 60)
        logger.info("📊 FCO日次分析完了")
        logger.info(f"  期間: {results['duration']}")
        logger.info(f"  成功: {results['total_success']} 銘柄")
        logger.info(f"  失敗: {results['total_failed']} 銘柄")
        if results['total_failed'] > 0:
            logger.info(f"  失敗銘柄: {', '.join(results['failed'][:10])}")
        logger.info("=" * 60)
        
        return results
    
    def retry_failed_symbols(self) -> Dict:
        """
        前回失敗した銘柄のみ再実行
        
        Returns:
            実行結果の辞書
        """
        if not self.state.get('failed_symbols'):
            logger.info("📊 再実行対象の失敗銘柄がありません")
            return {'message': 'No failed symbols to retry'}
        
        # 失敗銘柄のみで再実行
        original_symbols = self.symbols
        self.symbols = self.state['failed_symbols']
        
        logger.info(f"🔄 {len(self.symbols)}銘柄を再実行します")
        results = self.run_daily_analysis()
        
        # 元のリストに戻す
        self.symbols = original_symbols
        
        return results
    
    def get_status(self) -> Dict:
        """
        スケジューラーの状態を取得
        
        Returns:
            状態情報の辞書
        """
        status = {
            'configured_symbols': len(self.symbols),
            'last_run': self.state.get('last_run_date'),
            'last_success': self.state.get('last_success_count', 0),
            'last_failure': self.state.get('last_failure_count', 0),
            'failed_symbols': self.state.get('failed_symbols', [])
        }
        
        # 最新のバブル検出状況
        high_confidence = self.db.get_high_confidence_bubbles(confidence_threshold=0.3, limit=10)
        if not high_confidence.empty:
            status['high_confidence_bubbles'] = high_confidence[['symbol', 'ds_lppls_confidence', 'bubble_type']].to_dict('records')
        
        return status


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FCO Daily Analysis Scheduler')
    parser.add_argument('action', choices=['run', 'retry', 'status', 'test'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    scheduler = FCODailyScheduler()
    
    if args.action == 'run':
        scheduler.run_daily_analysis()
    elif args.action == 'retry':
        scheduler.retry_failed_symbols()
    elif args.action == 'status':
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, default=str))
    elif args.action == 'test':
        # テスト実行（3銘柄のみ）
        original_symbols = scheduler.symbols
        scheduler.symbols = ['SP500', 'NASDAQCOM', 'DJIA']
        logger.info(f"🧪 テストモード: {len(scheduler.symbols)}銘柄で実行")
        scheduler.run_daily_analysis()
        scheduler.symbols = original_symbols


if __name__ == "__main__":
    main()