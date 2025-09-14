#!/usr/bin/env python3
"""
FCO Daily Analysis Scheduler V2
全履歴ローカルキャッシュを使用する新アーキテクチャ版

設計方針:
- 全履歴キャッシュ専用
- API呼び出しなし（完全ローカル）
- FCODailyAnalyzerを使用
- エラー時の継続性
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json
import time

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from applications.analysis_tools.fco_daily_analyzer import FCODailyAnalyzer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FCODailySchedulerV2:
    """FCO日次分析スケジューラー V2（全履歴キャッシュ版）"""
    
    def __init__(self, 
                 state_file: str = "results/fco_scheduler_state.json"):
        """
        初期化
        
        Args:
            state_file: スケジューラー状態ファイル
        """
        self.state_file = state_file
        
        # FCO分析器（全履歴キャッシュ専用）
        self.analyzer = FCODailyAnalyzer()
        
        # 利用可能な銘柄（全履歴キャッシュから取得）
        self.symbols = self.analyzer.available_symbols
        
        # 状態管理
        self.state = self._load_state()
        
        logger.info(f"📊 FCOスケジューラーV2初期化完了")
        logger.info(f"   利用可能銘柄: {len(self.symbols)}（全履歴キャッシュ）")
    
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
            'last_success_count': 0,
            'last_failure_count': 0,
            'failed_symbols': [],
            'architecture': 'v2_full_history'
        }
    
    def _save_state(self):
        """スケジューラー状態を保存"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def run_daily_analysis(self, 
                          symbols: Optional[List[str]] = None,
                          analysis_date: Optional[str] = None) -> Dict:
        """
        日次FCO分析を実行
        
        Args:
            symbols: 分析対象銘柄（Noneなら全銘柄）
            analysis_date: 分析基準日（Noneなら最新）
        
        Returns:
            実行結果の辞書
        """
        start_time = datetime.now()
        today = start_time.strftime('%Y-%m-%d')
        
        if symbols is None:
            symbols = self.symbols
        
        logger.info("=" * 60)
        logger.info(f"🚀 FCO日次分析開始 V2（全履歴キャッシュ版）")
        logger.info(f"📅 実行日時: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📊 対象銘柄数: {len(symbols)}")
        logger.info(f"🗄️ データソース: 全履歴ローカルキャッシュ")
        logger.info("=" * 60)
        
        # 結果格納
        results = {
            'date': today,
            'start_time': start_time,
            'successful': [],
            'failed': [],
            'skipped': [],
            'details': {},
            'architecture': 'v2_full_history'
        }
        
        # 前回実行日チェック（同一日の再実行を許可するオプション）
        if self.state.get('last_run_date') == today and not analysis_date:
            logger.warning(f"⚠️ 本日({today})は既に実行済みです")
            logger.info("   再実行する場合は analysis_date を指定してください")
            results['skipped'] = symbols
            return results
        
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
            
            # API制限はないが、システム負荷軽減のため短い待機
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
    
    def check_data_availability(self) -> Dict[str, bool]:
        """
        全履歴キャッシュの利用可能状況を確認
        
        Returns:
            銘柄別の利用可能状況
        """
        logger.info("📊 全履歴キャッシュ利用可能状況:")
        availability = {}
        
        cache_dir = Path("data/market_data/cache/full")
        if not cache_dir.exists():
            logger.error(f"❌ キャッシュディレクトリが存在しません: {cache_dir}")
            return availability
        
        for symbol in self.symbols:
            cache_file = cache_dir / f"{symbol}_full.parquet"
            available = cache_file.exists()
            availability[symbol] = available
            
            if available:
                size_mb = cache_file.stat().st_size / (1024 * 1024)
                logger.info(f"  ✅ {symbol}: {size_mb:.2f} MB")
            else:
                logger.warning(f"  ❌ {symbol}: データなし")
        
        total = len(availability)
        available_count = sum(1 for v in availability.values() if v)
        logger.info(f"\n合計: {available_count}/{total}銘柄が利用可能")
        
        return availability


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FCO Daily Scheduler V2')
    parser.add_argument('action', choices=['run', 'check', 'status'],
                       help='Action to perform')
    parser.add_argument('--symbols', nargs='+',
                       help='Specific symbols to analyze')
    parser.add_argument('--date',
                       help='Analysis date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    scheduler = FCODailySchedulerV2()
    
    if args.action == 'run':
        results = scheduler.run_daily_analysis(
            symbols=args.symbols,
            analysis_date=args.date
        )
        print(f"\n実行結果: 成功{len(results['successful'])}件、失敗{len(results['failed'])}件")
        
    elif args.action == 'check':
        availability = scheduler.check_data_availability()
        available = sum(1 for v in availability.values() if v)
        print(f"\nデータ利用可能: {available}/{len(availability)}銘柄")
        
    elif args.action == 'status':
        print(f"\n最終実行日: {scheduler.state.get('last_run_date', 'なし')}")
        print(f"最終成功数: {scheduler.state.get('last_success_count', 0)}")
        print(f"最終失敗数: {scheduler.state.get('last_failure_count', 0)}")
        if scheduler.state.get('failed_symbols'):
            print(f"失敗銘柄: {', '.join(scheduler.state['failed_symbols'])}")


if __name__ == "__main__":
    main()