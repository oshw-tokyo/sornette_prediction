#!/usr/bin/env python3
"""
Smart Market Data Updater
市場休業日を考慮した賢いデータ更新システム

特徴:
- 市場休業日の自動判定
- 既存データからの効率的な差分更新
- 時差を考慮した更新タイミング
- 無駄なAPI呼び出しの削減
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.data_sources.unified_data_client import UnifiedDataClient

# ロギング設定
logger = logging.getLogger(__name__)


class SmartDataUpdater:
    """賢いデータ更新クラス"""
    
    # 市場タイプの定義
    MARKET_TYPES = {
        # 株式市場（土日休み）
        'STOCK': ['SP500', 'NASDAQCOM', 'DJIA', 'DJTA', 'DJUA', 'NASDAQBANK', 'NASDAQTRAN'],
        # 仮想通貨（24/7）
        'CRYPTO': ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'LINK']
    }
    
    def __init__(self, cache_dir: str = "data/market_data/cache/full"):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_client = UnifiedDataClient()
        
    def get_market_type(self, symbol: str) -> str:
        """
        銘柄の市場タイプを判定
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            市場タイプ（STOCK/CRYPTO/UNKNOWN）
        """
        for market_type, symbols in self.MARKET_TYPES.items():
            if symbol in symbols:
                return market_type
        return 'UNKNOWN'
    
    def is_market_open(self, date: datetime, market_type: str) -> bool:
        """
        指定日に市場が開いているか判定
        
        Args:
            date: 判定対象日
            market_type: 市場タイプ
        
        Returns:
            市場が開いているか
        """
        if market_type == 'CRYPTO':
            # 仮想通貨は常に開いている
            return True
        elif market_type == 'STOCK':
            # 株式市場は土日休み（簡易判定）
            # 本来は祝日カレンダーも考慮すべきだが、ここでは簡略化
            return date.weekday() < 5  # 月曜=0, 日曜=6
        else:
            # 不明な場合は開いていると仮定
            return True
    
    def get_last_market_date(self, market_type: str, reference_date: Optional[datetime] = None) -> datetime:
        """
        最後の市場営業日を取得
        
        Args:
            market_type: 市場タイプ
            reference_date: 基準日（Noneなら現在）
        
        Returns:
            最後の市場営業日
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # 時差を考慮（米国市場の場合、日本時間の朝6時以前は前日のデータが最新）
        if market_type == 'STOCK':
            # 米国東部時間との時差を考慮（簡易版）
            if reference_date.hour < 6:  # 日本時間朝6時前
                reference_date = reference_date - timedelta(days=1)
        
        # 市場が開いている最後の日を探す
        current_date = reference_date
        for _ in range(7):  # 最大1週間遡る
            if self.is_market_open(current_date, market_type):
                return current_date
            current_date = current_date - timedelta(days=1)
        
        return reference_date  # フォールバック
    
    def check_update_needed(self, symbol: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        更新が必要か確認し、必要な期間を返す
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            (更新必要フラグ, 開始日, 終了日)
        """
        cache_file = self.cache_dir / f"{symbol}_full.parquet"
        
        # キャッシュファイルが存在しない場合
        if not cache_file.exists():
            logger.info(f"📊 {symbol}: 新規データ取得が必要")
            # 全履歴を取得（40年前から）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 40)
            return True, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        
        # 既存データの確認
        try:
            df = pd.read_parquet(cache_file)
            if df.empty:
                logger.warning(f"⚠️ {symbol}: キャッシュが空")
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365 * 40)
                return True, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
            
            last_cached_date = df.index.max()
            market_type = self.get_market_type(symbol)
            
            # 最新の市場営業日を取得
            last_market_date = self.get_last_market_date(market_type)
            
            # データが最新か確認
            if last_cached_date.date() >= last_market_date.date():
                logger.info(f"✅ {symbol}: 既に最新（{last_cached_date.strftime('%Y-%m-%d')}）")
                return False, None, None
            
            # 差分期間を計算
            start_date = (last_cached_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = last_market_date.strftime('%Y-%m-%d')
            
            # 市場休業日のみの期間の場合はスキップ
            if market_type == 'STOCK':
                # 期間内に営業日があるか確認
                check_date = last_cached_date + pd.Timedelta(days=1)
                has_market_day = False
                while check_date <= pd.Timestamp(last_market_date):
                    if self.is_market_open(check_date, market_type):
                        has_market_day = True
                        break
                    check_date += pd.Timedelta(days=1)
                
                if not has_market_day:
                    logger.info(f"🆗 {symbol}: 更新期間に市場営業日なし（スキップ）")
                    return False, None, None
            
            logger.info(f"📥 {symbol}: {start_date} 〜 {end_date} の差分更新が必要")
            return True, start_date, end_date
            
        except Exception as e:
            logger.error(f"❌ {symbol}: キャッシュ確認エラー - {e}")
            # エラー時は全履歴取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 40)
            return True, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def smart_update(self, symbol: str) -> bool:
        """
        賢い差分更新を実行
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            成功フラグ
        """
        # 更新が必要か確認
        needs_update, start_date, end_date = self.check_update_needed(symbol)
        
        if not needs_update:
            return True  # 既に最新なので成功扱い
        
        try:
            # データ取得
            logger.info(f"🔄 {symbol}: データ取得中...")
            df, source = self.data_client.get_data_with_fallback(
                symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                # データが空の場合でも、市場休業日なら正常
                market_type = self.get_market_type(symbol)
                if market_type == 'STOCK':
                    # 期間が全て休業日の可能性
                    logger.info(f"ℹ️ {symbol}: 新規データなし（市場休業期間の可能性）")
                    return True
                else:
                    logger.warning(f"⚠️ {symbol}: データ取得失敗")
                    return False
            
            # キャッシュ更新
            cache_file = self.cache_dir / f"{symbol}_full.parquet"
            
            if cache_file.exists():
                # 既存データとマージ
                existing_df = pd.read_parquet(cache_file)
                df = pd.concat([existing_df, df])
                df = df[~df.index.duplicated(keep='last')]
                df.sort_index(inplace=True)
                logger.info(f"📊 {symbol}: {len(df) - len(existing_df)}件の新規データを追加")
            else:
                logger.info(f"📊 {symbol}: {len(df)}件のデータを新規保存")
            
            # メタデータ追加
            df.attrs['symbol'] = symbol
            df.attrs['last_update'] = datetime.now().isoformat()
            df.attrs['data_source'] = source
            
            # 保存
            df.to_parquet(cache_file)
            
            logger.info(f"✅ {symbol}: 更新完了（{df.index.min().strftime('%Y-%m-%d')} 〜 {df.index.max().strftime('%Y-%m-%d')}）")
            return True
            
        except Exception as e:
            logger.error(f"❌ {symbol}: 更新エラー - {e}")
            return False
    
    def bulk_smart_update(self, symbols: List[str]) -> Dict[str, bool]:
        """
        複数銘柄の賢い更新
        
        Args:
            symbols: 銘柄リスト
        
        Returns:
            銘柄別の成功/失敗フラグ
        """
        results = {}
        
        # 市場タイプ別にグループ化
        market_groups = {}
        for symbol in symbols:
            market_type = self.get_market_type(symbol)
            if market_type not in market_groups:
                market_groups[market_type] = []
            market_groups[market_type].append(symbol)
        
        # 市場タイプごとに処理
        for market_type, group_symbols in market_groups.items():
            logger.info(f"\n📊 {market_type}市場の更新（{len(group_symbols)}銘柄）")
            
            # 市場が開いているか確認
            if market_type == 'STOCK':
                last_market_date = self.get_last_market_date(market_type)
                if last_market_date.date() < datetime.now().date():
                    logger.info(f"ℹ️ 最終営業日: {last_market_date.strftime('%Y-%m-%d')}")
            
            for symbol in group_symbols:
                results[symbol] = self.smart_update(symbol)
        
        return results


def main():
    """テスト実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Market Data Updater')
    parser.add_argument('--symbols', nargs='+', default=['SP500', 'BTC'],
                       help='更新対象銘柄')
    parser.add_argument('--check-only', action='store_true',
                       help='更新必要性のチェックのみ')
    
    args = parser.parse_args()
    
    updater = SmartDataUpdater()
    
    if args.check_only:
        print("\n📊 更新必要性チェック:")
        for symbol in args.symbols:
            needs_update, start_date, end_date = updater.check_update_needed(symbol)
            if needs_update:
                print(f"  {symbol}: 要更新（{start_date} 〜 {end_date}）")
            else:
                print(f"  {symbol}: 最新")
    else:
        print("\n📊 スマート更新実行:")
        results = updater.bulk_smart_update(args.symbols)
        
        success_count = sum(1 for v in results.values() if v)
        print(f"\n✅ 完了: {success_count}/{len(results)}銘柄成功")


if __name__ == "__main__":
    main()