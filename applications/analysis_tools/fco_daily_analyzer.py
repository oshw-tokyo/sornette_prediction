#!/usr/bin/env python3
"""
FCO日次分析実行モジュール（ローカルデータ専用）
データ取得とは完全に分離された分析専用システム
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json
import pandas as pd
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.fitting.fco_engine import FCOEngine
from infrastructure.database.fco_results_database import FCOResultsDatabase

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FCODailyAnalyzer:
    """FCO日次分析実行クラス（ローカルデータ専用）"""
    
    def __init__(self, 
                 data_dir: str = "data/market_data",
                 db_path: str = "results/fco_analysis_results.db",
                 state_file: str = "results/fco_analyzer_state.json"):
        """
        初期化
        
        Args:
            data_dir: マーケットデータディレクトリ
            db_path: FCOデータベースパス
            state_file: 分析状態ファイル
        """
        self.data_dir = Path(data_dir)
        self.full_cache_dir = self.data_dir / "cache" / "full"  # FCOは全履歴のみ使用
        self.db = FCOResultsDatabase(db_path)
        self.state_file = state_file
        self.engine = FCOEngine(use_parallel=True, max_workers=4)
        
        # 利用可能な銘柄リストを取得
        self.available_symbols = self._get_available_symbols()
        
        # 状態管理
        self.state = self._load_state()
        
        logger.info(f"📊 FCO分析システム初期化完了")
        logger.info(f"   利用可能銘柄: {len(self.available_symbols)}")
    
    def _get_available_symbols(self) -> List[str]:
        """全履歴キャッシュから利用可能な銘柄リストを取得"""
        symbols = []
        
        if not self.full_cache_dir.exists():
            logger.warning(f"⚠️ 全履歴キャッシュディレクトリが存在しません: {self.full_cache_dir}")
            return symbols
        
        # 全履歴キャッシュのみを使用
        for cache_file in self.full_cache_dir.glob("*_full.parquet"):
            symbol = cache_file.stem.replace("_full", "")
            symbols.append(symbol)
        
        if symbols:
            logger.info(f"  📂 全履歴キャッシュから{len(symbols)}銘柄を認識")
        else:
            logger.warning(f"⚠️ 利用可能な全履歴データがありません")
        
        return sorted(symbols)
    
    def _load_state(self) -> Dict:
        """分析状態を読み込み"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'last_analysis_date': None,
            'last_success_count': 0,
            'last_failure_count': 0,
            'failed_symbols': []
        }
    
    def _save_state(self):
        """分析状態を保存"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def analyze_symbol(self, 
                      symbol: str,
                      analysis_date: Optional[str] = None) -> bool:
        """
        個別銘柄のFCO分析実行
        
        Args:
            symbol: 銘柄コード
            analysis_date: 分析基準日（省略時は最新データの日付）
        
        Returns:
            成功フラグ
        """
        try:
            # FCOは全履歴キャッシュのみを使用
            cache_file = self.full_cache_dir / f"{symbol}_full.parquet"
            if not cache_file.exists():
                logger.warning(f"❌ {symbol}: 全履歴キャッシュファイルが存在しません")
                logger.info(f"  💡 ヒント: python entry_points/main.py market-data download --symbol {symbol} --full-history")
                return False
            
            logger.debug(f"  📂 {symbol}: 全履歴キャッシュを使用")
            
            # データ読み込み
            df = pd.read_parquet(cache_file)
            
            # 分析基準日の決定
            if analysis_date is None:
                analysis_date_obj = df.index.max()
                analysis_date = analysis_date_obj.strftime('%Y-%m-%d')
            else:
                analysis_date_obj = pd.to_datetime(analysis_date)
            
            # 既存分析チェック
            existing = self.db.get_analysis_by_date(symbol, analysis_date)
            if existing is not None:
                logger.debug(f"✓ {symbol} @ {analysis_date}: 既存分析あり（スキップ）")
                return True
            
            # 分析期間のデータ抽出（2年分）
            end_date = analysis_date_obj
            start_date = end_date - timedelta(days=730)
            
            df_period = df[(df.index >= start_date) & (df.index <= end_date)]
            
            if len(df_period) < 250:
                logger.warning(f"❌ {symbol}: データ不足 ({len(df_period)}日 < 250日)")
                return False
            
            # 価格データ抽出
            if 'Close' in df_period.columns:
                prices = df_period['Close'].values
            elif 'close' in df_period.columns:
                prices = df_period['close'].values
            else:
                logger.error(f"❌ {symbol}: 価格カラムが見つかりません")
                return False
            
            # FCO分析実行
            logger.info(f"🔬 {symbol} @ {analysis_date}: FCO分析実行中...")
            fco_result = self.engine.compute_ds_lppls_confidence(prices)
            
            # データベース保存
            db_data = {
                'symbol': symbol,
                'analysis_basis_date': analysis_date,
                'data_source': df.attrs.get('source', 'cached'),
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
                timestamp=analysis_date_obj.isoformat() if hasattr(analysis_date_obj, 'isoformat') else str(analysis_date_obj),
                price=float(prices[-1]),
                confidence=float(fco_result.ds_lppls_confidence),
                confidence_neg=float(fco_result.ds_lppls_confidence_neg),
                bubble_status=fco_result.bubble_type
            )
            
            logger.info(f"✅ {symbol}: Confidence={fco_result.ds_lppls_confidence:.1%}, Type={fco_result.bubble_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ {symbol}: 分析エラー - {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def run_daily_analysis(self, 
                          symbols: Optional[List[str]] = None,
                          analysis_date: Optional[str] = None) -> Dict:
        """
        日次FCO分析を実行
        
        Args:
            symbols: 対象銘柄（Noneなら全銘柄）
            analysis_date: 分析基準日（省略時は最新）
        
        Returns:
            実行結果
        """
        if symbols is None:
            symbols = self.available_symbols
        
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info("=" * 60)
        logger.info(f"🚀 FCO日次分析開始")
        logger.info(f"   分析基準日: {analysis_date}")
        logger.info(f"   対象銘柄数: {len(symbols)}")
        logger.info("=" * 60)
        
        results = {
            'analysis_date': analysis_date,
            'start_time': datetime.now(),
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        # 本日既に実行済みチェック
        if self.state.get('last_analysis_date') == analysis_date and not symbols:
            logger.warning(f"⚠️ {analysis_date} は既に分析済みです")
            results['skipped'] = symbols
            return results
        
        # 各銘柄を分析
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] {symbol}")
            
            success = self.analyze_symbol(symbol, analysis_date)
            
            if success:
                results['successful'].append(symbol)
            else:
                results['failed'].append(symbol)
        
        # 結果集計
        results['end_time'] = datetime.now()
        results['duration'] = str(results['end_time'] - results['start_time'])
        results['total_success'] = len(results['successful'])
        results['total_failed'] = len(results['failed'])
        
        # 状態更新
        if not symbols:  # 全銘柄実行の場合のみ
            self.state['last_analysis_date'] = analysis_date
            self.state['last_success_count'] = results['total_success']
            self.state['last_failure_count'] = results['total_failed']
            self.state['failed_symbols'] = results['failed']
            self._save_state()
        
        # サマリー表示
        logger.info("\n" + "=" * 60)
        logger.info("📊 FCO分析完了")
        logger.info(f"   期間: {results['duration']}")
        logger.info(f"   成功: {results['total_success']} 銘柄")
        logger.info(f"   失敗: {results['total_failed']} 銘柄")
        if results['total_failed'] > 0:
            logger.info(f"   失敗銘柄: {', '.join(results['failed'][:10])}")
        logger.info("=" * 60)
        
        return results
    
    def analyze_historical(self, 
                         periods: List[str],
                         symbols: Optional[List[str]] = None) -> Dict:
        """
        過去の複数期間で分析実行
        
        Args:
            periods: 分析基準日のリスト
            symbols: 対象銘柄
        
        Returns:
            実行結果
        """
        if symbols is None:
            symbols = self.available_symbols
        
        logger.info("=" * 60)
        logger.info(f"🔬 過去データFCO分析")
        logger.info(f"   期間数: {len(periods)}")
        logger.info(f"   銘柄数: {len(symbols)}")
        logger.info("=" * 60)
        
        all_results = {
            'periods': periods,
            'total_analyses': 0,
            'total_success': 0,
            'total_failed': 0,
            'period_results': {}
        }
        
        for period in periods:
            logger.info(f"\n📅 分析期間: {period}")
            
            result = self.run_daily_analysis(
                symbols=symbols,
                analysis_date=period
            )
            
            all_results['period_results'][period] = result
            all_results['total_success'] += result['total_success']
            all_results['total_failed'] += result['total_failed']
            all_results['total_analyses'] += (
                result['total_success'] + result['total_failed']
            )
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 過去データ分析完了")
        logger.info(f"   総分析数: {all_results['total_analyses']}")
        logger.info(f"   成功: {all_results['total_success']}")
        logger.info(f"   失敗: {all_results['total_failed']}")
        logger.info("=" * 60)
        
        return all_results
    
    def get_status(self) -> Dict:
        """分析システムの状態を取得"""
        status = {
            'available_symbols': len(self.available_symbols),
            'last_analysis_date': self.state.get('last_analysis_date'),
            'last_success': self.state.get('last_success_count', 0),
            'last_failure': self.state.get('last_failure_count', 0),
            'failed_symbols': self.state.get('failed_symbols', [])
        }
        
        # キャッシュ状態
        cache_stats = {}
        total_size = 0
        
        for cache_file in self.cache_dir.glob("*_2y.parquet"):
            size_mb = cache_file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            
            df = pd.read_parquet(cache_file)
            symbol = cache_file.stem.replace("_2y", "")
            
            cache_stats[symbol] = {
                'size_mb': round(size_mb, 2),
                'rows': len(df),
                'last_date': df.index.max().strftime('%Y-%m-%d')
            }
        
        status['cache_total_size_mb'] = round(total_size, 2)
        status['cache_symbols'] = len(cache_stats)
        
        # 最新のバブル検出状況
        high_confidence = self.db.get_high_confidence_bubbles(
            confidence_threshold=0.3, 
            limit=10
        )
        if not high_confidence.empty:
            status['high_confidence_bubbles'] = high_confidence[[
                'symbol', 'ds_lppls_confidence', 'bubble_type'
            ]].to_dict('records')
        
        return status


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FCO Daily Analyzer (Local Data)')
    parser.add_argument('action', 
                       choices=['analyze', 'historical', 'status'],
                       help='Action to perform')
    parser.add_argument('--symbols', nargs='+',
                       help='Target symbols')
    parser.add_argument('--date', 
                       help='Analysis date (YYYY-MM-DD)')
    parser.add_argument('--periods', nargs='+',
                       help='Historical periods for analysis')
    
    args = parser.parse_args()
    
    analyzer = FCODailyAnalyzer()
    
    if args.action == 'analyze':
        result = analyzer.run_daily_analysis(
            symbols=args.symbols,
            analysis_date=args.date
        )
        print(f"\n成功: {result['total_success']}銘柄")
        
    elif args.action == 'historical':
        if not args.periods:
            # デフォルト: 過去4週間の土曜日
            from datetime import datetime, timedelta
            today = datetime.now()
            periods = []
            for i in range(4):
                date = today - timedelta(weeks=i)
                # 土曜日に調整
                days_to_saturday = (5 - date.weekday()) % 7
                saturday = date + timedelta(days=days_to_saturday)
                periods.append(saturday.strftime('%Y-%m-%d'))
        else:
            periods = args.periods
        
        result = analyzer.analyze_historical(
            periods=periods,
            symbols=args.symbols
        )
        print(f"\n総分析数: {result['total_analyses']}")
        
    elif args.action == 'status':
        status = analyzer.get_status()
        print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    main()