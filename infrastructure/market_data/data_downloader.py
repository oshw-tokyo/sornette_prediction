#!/usr/bin/env python3
"""
市場データダウンローダー
APIからデータを取得してローカルに保存する専用モジュール
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import time
import pandas as pd
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.data_sources.unified_data_client import UnifiedDataClient

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketDataDownloader:
    """市場データダウンロード専用クラス"""
    
    def __init__(self, base_dir: str = "data/market_data", for_fco: bool = True):
        """
        初期化
        
        Args:
            base_dir: データ保存ベースディレクトリ
            for_fco: FCO用（全履歴）かLPPL用（2年）か
        """
        self.for_fco = for_fco
        self.base_dir = Path(base_dir)
        self.daily_dir = self.base_dir / "daily"
        self.cache_dir = self.base_dir / "cache" / "prepared"  # LPPL用2年キャッシュ
        self.full_cache_dir = self.base_dir / "cache" / "full"  # FCO用全履歴
        self.metadata_dir = self.base_dir / "metadata"
        
        # ディレクトリ作成
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.full_cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_client = UnifiedDataClient()
        self._load_catalog()
    
    def _load_catalog(self):
        """市場データカタログを読み込み"""
        try:
            catalog_path = project_root / "infrastructure" / "data_sources" / "market_data_catalog.json"
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.catalog = json.load(f)
            
            self.symbols = list(self.catalog.get('symbols', {}).keys())
            logger.info(f"📊 カタログから{len(self.symbols)}銘柄を読み込み")
        except Exception as e:
            logger.error(f"❌ カタログ読み込みエラー: {e}")
            self.symbols = []
            self.catalog = {}
    
    def download_symbol_data(self, 
                           symbol: str, 
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           years: Optional[int] = None,
                           download_full: bool = True) -> bool:
        """
        個別銘柄のデータをダウンロード
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）
            years: 取得年数（Noneで全履歴）
            download_full: 全履歴をダウンロードするか
        
        Returns:
            成功フラグ
        """
        try:
            # 日付設定
            if end_date is None:
                end_dt = datetime.now()
                end_date = end_dt.strftime('%Y-%m-%d')
            else:
                end_dt = pd.to_datetime(end_date)
            
            if start_date is None:
                if download_full or self.for_fco:
                    # 全履歴を取得（40年前から、またはAPI最古データから）
                    start_dt = end_dt - timedelta(days=365 * 40)
                    start_date = start_dt.strftime('%Y-%m-%d')
                elif years:
                    # 指定年数分を取得
                    start_dt = end_dt - timedelta(days=365 * years)
                    start_date = start_dt.strftime('%Y-%m-%d')
                else:
                    # デフォルト2年
                    start_dt = end_dt - timedelta(days=365 * 2)
                    start_date = start_dt.strftime('%Y-%m-%d')
            else:
                start_dt = pd.to_datetime(start_date)
            
            logger.info(f"📥 {symbol}: {start_date} 〜 {end_date} のデータを取得中...")
            
            # データ取得
            df, source = self.data_client.get_data_with_fallback(
                symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"  ❌ {symbol}: データ取得失敗")
                return False
            
            # メタデータ付与
            df.attrs['symbol'] = symbol
            df.attrs['source'] = source
            df.attrs['download_date'] = datetime.now().isoformat()
            df.attrs['start_date'] = start_date
            df.attrs['end_date'] = end_date
            
            # 保存
            self._save_daily_data(symbol, df)
            if self.for_fco:
                self._update_full_cache(symbol, df)  # FCO用は全履歴
            else:
                self._update_cache(symbol, df)  # LPPL用は2年
            self._update_metadata(symbol, df.attrs)
            
            logger.info(f"  ✅ {symbol}: {len(df)}日分保存完了 (source: {source})")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ {symbol}: エラー - {e}")
            return False
    
    def _save_daily_data(self, symbol: str, df: pd.DataFrame):
        """日次データを階層的に保存"""
        # 年月でグループ化
        df.index = pd.to_datetime(df.index)
        for (year, month), group in df.groupby([df.index.year, df.index.month]):
            # 保存パス
            symbol_dir = self.daily_dir / symbol / str(year)
            symbol_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = symbol_dir / f"{month:02d}.parquet"
            
            # 既存データとマージ（重複排除）
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined.sort_index(inplace=True)
                group = combined
            
            # Parquet形式で保存
            group.to_parquet(file_path)
    
    def _update_cache(self, symbol: str, df: pd.DataFrame):
        """キャッシュファイルを更新（2年分の連結データ - 互換性維持用）"""
        cache_file = self.cache_dir / f"{symbol}_2y.parquet"
        
        # 既存キャッシュとマージ
        if cache_file.exists():
            existing = pd.read_parquet(cache_file)
            df = pd.concat([existing, df])
            df = df[~df.index.duplicated(keep='last')]
            df.sort_index(inplace=True)
        
        # 2年分のみ保持
        end_date = df.index.max()
        start_date = end_date - pd.Timedelta(days=365 * 2)
        df = df[df.index >= start_date]
        
        # メタデータ保持
        df.attrs['symbol'] = symbol
        df.attrs['last_update'] = datetime.now().isoformat()
        
        df.to_parquet(cache_file)
    
    def _update_full_cache(self, symbol: str, df: pd.DataFrame):
        """全履歴キャッシュファイルを更新"""
        cache_file = self.full_cache_dir / f"{symbol}_full.parquet"
        
        # 既存キャッシュとマージ（全履歴保持）
        if cache_file.exists():
            existing = pd.read_parquet(cache_file)
            df = pd.concat([existing, df])
            df = df[~df.index.duplicated(keep='last')]
            df.sort_index(inplace=True)
        
        # メタデータ保持
        df.attrs['symbol'] = symbol
        df.attrs['last_update'] = datetime.now().isoformat()
        df.attrs['start_date'] = df.index.min().strftime('%Y-%m-%d')
        df.attrs['end_date'] = df.index.max().strftime('%Y-%m-%d')
        df.attrs['total_days'] = len(df)
        
        df.to_parquet(cache_file)
        
        logger.info(f"  📊 {symbol}: 全履歴キャッシュ更新 ({len(df)}日分, {df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')})")
    
    def _update_metadata(self, symbol: str, attrs: Dict):
        """メタデータを更新"""
        metadata_file = self.metadata_dir / "data_catalog.json"
        
        # 既存メタデータ読み込み
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # 更新
        if symbol not in metadata:
            metadata[symbol] = {}
        
        metadata[symbol].update({
            'last_download': attrs.get('download_date'),
            'source': attrs.get('source'),
            'last_start_date': attrs.get('start_date'),
            'last_end_date': attrs.get('end_date')
        })
        
        # 保存
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def download_all_symbols(self, 
                            symbols: Optional[List[str]] = None,
                            years: Optional[int] = None,
                            download_full: bool = True) -> Dict[str, bool]:
        """
        複数銘柄を一括ダウンロード
        
        Args:
            symbols: 対象銘柄リスト（Noneなら全銘柄）
            years: 取得年数（Noneなら全履歴）
            download_full: 全履歴をダウンロードするか
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        if symbols is None:
            symbols = self.symbols
        
        logger.info("=" * 60)
        logger.info(f"📥 市場データ一括ダウンロード")
        logger.info(f"   対象: {len(symbols)}銘柄")
        if download_full or self.use_full_history:
            logger.info(f"   期間: 全履歴データ")
        else:
            logger.info(f"   期間: 過去{years if years else 2}年分")
        logger.info("=" * 60)
        
        results = {}
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] {symbol}")
            
            # キャッシュチェック
            if self.for_fco:
                cache_file = self.full_cache_dir / f"{symbol}_full.parquet"
            else:
                cache_file = self.cache_dir / f"{symbol}_2y.parquet"
            
            if cache_file.exists():
                # 最終更新から1日以内ならスキップ
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if (datetime.now() - mtime).days < 1:
                    logger.info(f"  ✓ 最新キャッシュ使用（{mtime.strftime('%Y-%m-%d %H:%M')}更新）")
                    results[symbol] = True
                    continue
            
            # ダウンロード実行
            success = self.download_symbol_data(symbol, years=years, download_full=download_full)
            results[symbol] = success
            
            # API制限対策
            if i < len(symbols):
                time.sleep(0.2)
        
        # サマリー
        success_count = sum(1 for v in results.values() if v)
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ ダウンロード完了: {success_count}/{len(symbols)}銘柄成功")
        if success_count < len(symbols):
            failed = [s for s, v in results.items() if not v]
            logger.info(f"❌ 失敗銘柄: {', '.join(failed[:10])}")
        logger.info("=" * 60)
        
        return results
    
    def update_latest_data(self, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        最新データのみ差分更新
        
        Args:
            symbols: 対象銘柄リスト
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        if symbols is None:
            symbols = self.symbols
        
        logger.info("📈 最新データ差分更新開始")
        results = {}
        
        for symbol in symbols:
            try:
                # 既存データの最終日を確認
                if self.for_fco:
                    cache_file = self.full_cache_dir / f"{symbol}_full.parquet"
                else:
                    cache_file = self.cache_dir / f"{symbol}_2y.parquet"
                    
                if cache_file.exists():
                    df = pd.read_parquet(cache_file)
                    last_date = df.index.max()
                    start_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    # 新規の場合
                    start_date = None
                
                # 最新データ取得
                success = self.download_symbol_data(
                    symbol,
                    start_date=start_date,
                    download_full=self.for_fco if start_date is None else False
                )
                results[symbol] = success
                
            except Exception as e:
                logger.error(f"{symbol}: 更新エラー - {e}")
                results[symbol] = False
        
        return results
    
    def get_data_stats(self) -> Dict:
        """データ統計情報を取得"""
        stats = {
            'total_symbols': len(self.symbols),
            'cached_symbols_2y': 0,
            'cached_symbols_full': 0,
            'total_size_mb_2y': 0,
            'total_size_mb_full': 0,
            'symbols': {}
        }
        
        # 2年キャッシュファイル確認
        for cache_file in self.cache_dir.glob("*_2y.parquet"):
            symbol = cache_file.stem.replace("_2y", "")
            size_mb = cache_file.stat().st_size / (1024 * 1024)
            
            df = pd.read_parquet(cache_file)
            
            stats['cached_symbols_2y'] += 1
            stats['total_size_mb_2y'] += size_mb
            
            if symbol not in stats['symbols']:
                stats['symbols'][symbol] = {}
            
            stats['symbols'][symbol]['cache_2y'] = {
                'size_mb': round(size_mb, 2),
                'rows': len(df),
                'start_date': df.index.min().strftime('%Y-%m-%d'),
                'end_date': df.index.max().strftime('%Y-%m-%d'),
                'last_update': datetime.fromtimestamp(
                    cache_file.stat().st_mtime
                ).strftime('%Y-%m-%d %H:%M')
            }
        
        # 全履歴キャッシュファイル確認
        for cache_file in self.full_cache_dir.glob("*_full.parquet"):
            symbol = cache_file.stem.replace("_full", "")
            size_mb = cache_file.stat().st_size / (1024 * 1024)
            
            df = pd.read_parquet(cache_file)
            
            stats['cached_symbols_full'] += 1
            stats['total_size_mb_full'] += size_mb
            
            if symbol not in stats['symbols']:
                stats['symbols'][symbol] = {}
            
            stats['symbols'][symbol]['cache_full'] = {
                'size_mb': round(size_mb, 2),
                'rows': len(df),
                'start_date': df.index.min().strftime('%Y-%m-%d'),
                'end_date': df.index.max().strftime('%Y-%m-%d'),
                'years': round((df.index.max() - df.index.min()).days / 365.25, 1),
                'last_update': datetime.fromtimestamp(
                    cache_file.stat().st_mtime
                ).strftime('%Y-%m-%d %H:%M')
            }
        
        stats['total_size_mb_2y'] = round(stats['total_size_mb_2y'], 2)
        stats['total_size_mb_full'] = round(stats['total_size_mb_full'], 2)
        return stats


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Data Downloader')
    parser.add_argument('action', choices=['download', 'update', 'stats'],
                       help='Action to perform')
    parser.add_argument('--symbols', nargs='+',
                       help='Target symbols')
    parser.add_argument('--years', type=int, default=2,
                       help='Years of data to download')
    
    args = parser.parse_args()
    
    downloader = MarketDataDownloader()
    
    if args.action == 'download':
        results = downloader.download_all_symbols(
            symbols=args.symbols,
            years=args.years
        )
        print(f"\n成功: {sum(1 for v in results.values() if v)}銘柄")
        
    elif args.action == 'update':
        results = downloader.update_latest_data(symbols=args.symbols)
        print(f"\n更新成功: {sum(1 for v in results.values() if v)}銘柄")
        
    elif args.action == 'stats':
        stats = downloader.get_data_stats()
        print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()