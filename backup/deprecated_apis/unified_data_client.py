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
        
        # CoinGecko クライアント
        try:
            from coingecko_client import CoinGeckoClient
            coingecko_client = CoinGeckoClient()
            self.clients['coingecko'] = coingecko_client
            self.available_sources.append('coingecko')
            print("✅ CoinGecko クライアント初期化成功")
        except Exception as e:
            print(f"⚠️ CoinGecko 初期化失敗: {str(e)}")
        
        print(f"📊 利用可能データソース: {self.available_sources}")
        
        # 銘柄マッピング（カタログから動的読み込み）
        self.symbol_mapping = self._load_symbol_mapping_from_catalog()
        
        # 統合データログ出力
        symbol_count = len(self.symbol_mapping)
        print(f"📊 統合データクライアントから{symbol_count}銘柄を読み込み（FRED+Alpha Vantage+CoinGecko）")
    
    def _load_symbol_mapping_from_catalog(self) -> dict:
        """
        カタログからシンボルマッピングを動的読み込み
        
        Returns:
            dict: シンボルマッピング辞書
        """
        import json
        import os
        from pathlib import Path
        
        try:
            # プロジェクトルートからカタログパスを構築
            current_dir = Path(__file__).parent
            catalog_path = current_dir / "market_data_catalog.json"
            
            if not catalog_path.exists():
                print(f"⚠️ カタログファイルが見つかりません: {catalog_path}")
                return {}
            
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            mapping = {}
            
            # カタログの各シンボルからPRIMARYマッピングのみ構築
            for symbol, data in catalog.get('symbols', {}).items():
                sources = data.get('data_sources', {})
                
                # PRIMARY sourceのみを取得（fallbackは無視）
                primary = sources.get('primary', {})
                if primary and 'provider' in primary:
                    provider = primary['provider']
                    provider_symbol = primary.get('symbol', symbol)
                    
                    mapping[symbol] = {
                        'provider': provider,
                        'symbol': provider_symbol
                    }
            
            print(f"✅ カタログから{len(mapping)}銘柄のマッピング読み込み完了")
            return mapping
            
        except Exception as e:
            print(f"❌ カタログ読み込みエラー: {e}")
            print("  フォールバック: 空のマッピングを使用")
            return {}
    
    def get_data_with_fallback(self, symbol: str, start_date: str, end_date: str,
                              preferred_source: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """
        排他的データ取得（PRIMARY PROVIDER ONLY）
        
        Args:
            symbol: 銘柄シンボル
            start_date: 開始日
            end_date: 終了日
            preferred_source: 使用されません（後方互換性のため保持）
            
        Returns:
            (DataFrame, source_name): データと取得元ソース名
        """
        
        if not self.available_sources:
            print("❌ 利用可能なデータソースがありません")
            return None, "none"
        
        # カタログからPRIMARYプロバイダーを特定
        if symbol not in self.symbol_mapping:
            print(f"❌ {symbol} はカタログに登録されていません")
            return None, "not_in_catalog"
        
        symbol_config = self.symbol_mapping[symbol]
        primary_provider = symbol_config['provider']
        mapped_symbol = symbol_config['symbol']
        
        print(f"🎯 {symbol} → {primary_provider} (as {mapped_symbol}) - 排他的取得")
        
        # 指定されたプロバイダーが利用可能かチェック
        if primary_provider not in self.available_sources:
            print(f"❌ {primary_provider} クライアントが初期化されていません")
            return None, "provider_unavailable"
        
        # プロバイダーが利用不可の場合は即座に失敗
        if primary_provider not in self.clients:
            print(f"❌ {primary_provider} クライアントが存在しません")
            return None, "client_missing"
        
        try:
            print(f"   🔄 {primary_provider} で取得中...")
            
            # データ取得
            client = self.clients[primary_provider]
            
            if hasattr(client, 'get_series_data'):
                data = client.get_series_data(mapped_symbol, start_date, end_date)
            else:
                print(f"      ❌ {primary_provider} クライアントが get_series_data をサポートしていません")
                return None, "unsupported_method"
            
            if data is not None and len(data) > 0:
                print(f"   ✅ {primary_provider} でデータ取得成功: {len(data)}日分")
                return data, primary_provider
            else:
                print(f"   ❌ {primary_provider} でデータ取得失敗（空のデータ）")
                return None, "empty_data"
                
        except Exception as e:
            print(f"   ❌ {primary_provider} でエラー: {str(e)}")
            return None, "api_error"
    
    def _map_symbol(self, symbol: str, source: str) -> Optional[str]:
        """銘柄シンボルのマッピング（排他的設計用）"""
        
        # 排他的設計：指定されたsourceが銘柄のprimaryプロバイダーと一致する場合のみマッピング
        if symbol in self.symbol_mapping:
            symbol_config = self.symbol_mapping[symbol]
            if symbol_config['provider'] == source:
                return symbol_config['symbol']
        
        # 一致しない場合は None を返す（サポート外）
        return None
    
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
            
            # レート制限対策（2025-08-10 安全マージン強化）
            if source == 'alpha_vantage':
                time.sleep(12)  # Alpha Vantage: 5 calls/min → 12秒間隔
            elif source == 'fred':
                time.sleep(0.5)  # FRED: 120 calls/min → 0.5秒間隔
            elif source == 'coingecko':
                time.sleep(8)   # CoinGecko: 10 calls/min → 8秒間隔（強化）
            else:
                time.sleep(1)   # 一般的な待機
        
        # 取得サマリー
        successful = sum(1 for data, _ in results.values() if data is not None)
        print(f"\n📊 取得完了: {successful}/{len(symbols)} 銘柄成功")
        
        return results
    
    def get_supported_symbols(self, source: Optional[str] = None) -> dict:
        """
        サポートされている銘柄の一覧取得（排他的設計）
        
        Args:
            source: 特定ソースのみ取得する場合
            
        Returns:
            dict: ソース別サポート銘柄
        """
        
        if source:
            if source not in self.available_sources:
                return {}
            
            symbols = []
            for symbol, symbol_config in self.symbol_mapping.items():
                if symbol_config['provider'] == source:
                    symbols.append(symbol)
            
            return {source: symbols}
        
        # 全ソースの銘柄（排他的割り当て）
        result = {}
        for source in self.available_sources:
            symbols = []
            for symbol, symbol_config in self.symbol_mapping.items():
                if symbol_config['provider'] == source:
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