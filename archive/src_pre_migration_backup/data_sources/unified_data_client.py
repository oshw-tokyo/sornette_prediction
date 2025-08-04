#!/usr/bin/env python3
"""
統合データクライアント

複数のデータソース（FRED、Alpha Vantage）を統合し、
自動フォールバック機能を提供する
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union
import time
import warnings
warnings.filterwarnings('ignore')

class UnifiedDataClient:
    """統合データクライアント"""
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, fred_key: Optional[str] = None):
        """
        統合クライアント初期化
        
        Args:
            alpha_vantage_key: Alpha Vantage API key
            fred_key: FRED API key
        """
        
        # クライアントの初期化
        self.clients = {}
        self.available_sources = []
        
        # Alpha Vantage クライアント
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(__file__))
            from alpha_vantage_client import AlphaVantageClient
            av_client = AlphaVantageClient(alpha_vantage_key)
            if av_client.api_key:
                self.clients['alpha_vantage'] = av_client
                self.available_sources.append('alpha_vantage')
                print("✅ Alpha Vantage クライアント初期化成功")
        except Exception as e:
            print(f"⚠️ Alpha Vantage 初期化失敗: {str(e)}")
        
        # FRED クライアント
        try:
            from fred_data_client import FREDDataClient
            fred_client = FREDDataClient(fred_key)
            if fred_client.api_key:
                self.clients['fred'] = fred_client
                self.available_sources.append('fred')
                print("✅ FRED クライアント初期化成功")
        except Exception as e:
            print(f"⚠️ FRED 初期化失敗: {str(e)}")
        
        print(f"📊 利用可能データソース: {self.available_sources}")
        
        # 銘柄マッピング
        self.symbol_mapping = {
            # 共通銘柄のマッピング（FRED + Alpha Vantage対応）
            'NASDAQ': {'fred': 'NASDAQCOM', 'alpha_vantage': '^IXIC'},
            'SP500': {'fred': 'SP500', 'alpha_vantage': 'SPY'},
            'DJIA': {'fred': 'DJIA', 'alpha_vantage': 'DJI'},
            'VIX': {'fred': 'VIXCLS', 'alpha_vantage': 'VIX'},
            
            # 個別株（Alpha Vantageのみ - FREDは個別株をサポートしない）
            'AAPL': {'alpha_vantage': 'AAPL'},
            'MSFT': {'alpha_vantage': 'MSFT'},
            'GOOGL': {'alpha_vantage': 'GOOGL'},
            'AMZN': {'alpha_vantage': 'AMZN'},
            'TSLA': {'alpha_vantage': 'TSLA'},
            'NVDA': {'alpha_vantage': 'NVDA'},
            'META': {'alpha_vantage': 'META'},
            'NFLX': {'alpha_vantage': 'NFLX'},
        }
    
    def get_data_with_fallback(self, symbol: str, start_date: str, end_date: str,
                              preferred_source: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """
        フォールバック機能付きデータ取得
        
        Args:
            symbol: 銘柄シンボル
            start_date: 開始日
            end_date: 終了日
            preferred_source: 優先データソース
            
        Returns:
            (DataFrame, source_name): データと取得元ソース名
        """
        
        if not self.available_sources:
            print("❌ 利用可能なデータソースがありません")
            return None, "none"
        
        # 試行順序の決定
        sources_to_try = []
        
        if preferred_source and preferred_source in self.available_sources:
            sources_to_try.append(preferred_source)
        else:
            # 銘柄タイプによる自動優先順位設定
            symbol_mapping = self.symbol_mapping.get(symbol, {})
            
            # 個別株の場合: Alpha Vantage を優先
            if len(symbol_mapping) == 1 and 'alpha_vantage' in symbol_mapping:
                if 'alpha_vantage' in self.available_sources:
                    sources_to_try.append('alpha_vantage')
            # 指数の場合: FRED を優先（無料で高頻度アクセス可能）
            elif 'fred' in symbol_mapping and 'fred' in self.available_sources:
                sources_to_try.append('fred')
                if 'alpha_vantage' in self.available_sources:
                    sources_to_try.append('alpha_vantage')
            # その他: Alpha Vantage優先
            elif 'alpha_vantage' in self.available_sources:
                sources_to_try.append('alpha_vantage')
        
        # 残りのソースを追加
        for source in self.available_sources:
            if source not in sources_to_try:
                sources_to_try.append(source)
        
        print(f"🔍 {symbol} データ取得試行順序: {sources_to_try}")
        
        # 各ソースで試行
        for source in sources_to_try:
            try:
                print(f"   🔄 {source} で試行中...")
                
                # 銘柄マッピング
                mapped_symbol = self._map_symbol(symbol, source)
                if not mapped_symbol:
                    print(f"      ⚠️ {source} では {symbol} をサポートしていません")
                    continue
                
                # データ取得
                client = self.clients[source]
                
                if hasattr(client, 'get_series_data'):
                    data = client.get_series_data(mapped_symbol, start_date, end_date)
                else:
                    print(f"      ❌ {source} クライアントが get_series_data をサポートしていません")
                    continue
                
                if data is not None and len(data) > 0:
                    print(f"   ✅ {source} でデータ取得成功: {len(data)}日分")
                    return data, source
                else:
                    print(f"      ❌ {source} でデータ取得失敗")
                    
            except Exception as e:
                print(f"      ❌ {source} エラー: {str(e)}")
                continue
        
        print(f"❌ 全てのソースで {symbol} データ取得に失敗")
        return None, "none"
    
    def _map_symbol(self, symbol: str, source: str) -> Optional[str]:
        """銘柄シンボルのマッピング"""
        
        # 直接マッピングがある場合
        if symbol in self.symbol_mapping:
            mapping = self.symbol_mapping[symbol]
            if source in mapping:
                return mapping[source]
        
        # マッピングがない場合、そのまま使用
        return symbol
    
    def get_multiple_symbols(self, symbols: list, start_date: str, end_date: str) -> dict:
        """
        複数銘柄の一括取得
        
        Args:
            symbols: 銘柄リスト
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            dict: {symbol: (data, source)} の辞書
        """
        
        results = {}
        
        print(f"📊 複数銘柄データ取得開始: {len(symbols)}銘柄")
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n進捗: {i}/{len(symbols)} - {symbol}")
            
            data, source = self.get_data_with_fallback(symbol, start_date, end_date)
            results[symbol] = (data, source)
            
            # レート制限対策
            if source == 'alpha_vantage':
                time.sleep(12)  # Alpha Vantage: 5 calls/min → 12秒間隔
            elif source == 'fred':
                time.sleep(0.5)  # FRED: 120 calls/min → 0.5秒間隔
            else:
                time.sleep(1)   # 一般的な待機
        
        # 取得サマリー
        successful = sum(1 for data, _ in results.values() if data is not None)
        print(f"\n📊 取得完了: {successful}/{len(symbols)} 銘柄成功")
        
        return results
    
    def get_supported_symbols(self, source: Optional[str] = None) -> dict:
        """
        サポートされている銘柄の一覧取得
        
        Args:
            source: 特定ソースのみ取得する場合
            
        Returns:
            dict: ソース別サポート銘柄
        """
        
        if source:
            if source not in self.available_sources:
                return {}
            
            symbols = []
            for symbol, mapping in self.symbol_mapping.items():
                if source in mapping:
                    symbols.append(symbol)
            
            return {source: symbols}
        
        # 全ソースの銘柄
        result = {}
        for source in self.available_sources:
            symbols = []
            for symbol, mapping in self.symbol_mapping.items():
                if source in mapping:
                    symbols.append(symbol)
            result[source] = symbols
        
        return result
    
    def test_all_sources(self) -> dict:
        """全データソースの接続テスト"""
        
        print("🧪 全データソース接続テスト")
        print("-" * 40)
        
        results = {}
        
        for source in self.available_sources:
            print(f"\n🔍 {source} テスト:")
            
            try:
                client = self.clients[source]
                
                # テスト用データ取得
                if source == 'fred':
                    test_symbol = 'NASDAQCOM'
                else:  # alpha_vantage
                    test_symbol = 'AAPL'
                
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)  # 1週間
                
                data, _ = self.get_data_with_fallback(
                    'NASDAQ' if source == 'fred' else 'AAPL',
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    preferred_source=source
                )
                
                if data is not None:
                    results[source] = {'status': 'success', 'data_points': len(data)}
                    print(f"   ✅ 成功: {len(data)}日分")
                else:
                    results[source] = {'status': 'failed', 'data_points': 0}
                    print(f"   ❌ 失敗")
                    
            except Exception as e:
                results[source] = {'status': 'error', 'error': str(e)}
                print(f"   ❌ エラー: {str(e)}")
        
        return results

# 使用例とテスト
def test_unified_client():
    """統合クライアントのテスト"""
    
    print("🧪 統合データクライアント テスト")
    print("=" * 50)
    
    # 環境変数読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    # クライアント初期化
    client = UnifiedDataClient()
    
    if not client.available_sources:
        print("❌ 利用可能なデータソースがありません")
        return
    
    # 接続テスト
    test_results = client.test_all_sources()
    
    # サポート銘柄確認
    print(f"\n📋 サポート銘柄:")
    supported = client.get_supported_symbols()
    for source, symbols in supported.items():
        print(f"   {source}: {symbols}")
    
    # 実際のデータ取得テスト
    print(f"\n📊 データ取得テスト:")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    test_symbols = ['NASDAQ', 'AAPL', 'SP500']
    
    for symbol in test_symbols:
        print(f"\n🔍 {symbol} テスト:")
        data, source = client.get_data_with_fallback(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if data is not None:
            print(f"   ✅ 成功 ({source}): {len(data)}日分, 最新価格: {data['Close'].iloc[-1]:.2f}")
        else:
            print(f"   ❌ 失敗")

if __name__ == "__main__":
    test_unified_client()