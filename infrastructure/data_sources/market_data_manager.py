#!/usr/bin/env python3
"""
マーケットデータ管理システム

JSONカタログベースの構造化されたデータソース管理を提供
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from pathlib import Path

class MarketDataManager:
    """マーケットデータカタログ管理システム"""
    
    def __init__(self, catalog_path: Optional[str] = None):
        """
        初期化
        
        Args:
            catalog_path: カタログJSONファイルのパス
        """
        if catalog_path is None:
            catalog_path = os.path.join(os.path.dirname(__file__), 'market_data_catalog.json')
        
        self.catalog_path = catalog_path
        self.catalog_data = self._load_catalog()
        
        # データクライアントの初期化（遅延読み込み）
        self._clients = {}
        self._initialize_clients()
    
    def _load_catalog(self) -> Dict:
        """カタログデータの読み込み"""
        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            print(f"📊 マーケットデータカタログ読み込み成功")
            print(f"   バージョン: {catalog['catalog_metadata']['version']}")
            print(f"   更新日: {catalog['catalog_metadata']['last_updated']}")
            print(f"   対応銘柄数: {len(catalog['symbols'])}")
            
            return catalog
            
        except FileNotFoundError:
            print(f"❌ カタログファイルが見つかりません: {self.catalog_path}")
            return self._get_default_catalog()
        except json.JSONDecodeError as e:
            print(f"❌ カタログファイルの形式エラー: {e}")
            return self._get_default_catalog()
    
    def _get_default_catalog(self) -> Dict:
        """デフォルトカタログの生成"""
        return {
            "catalog_metadata": {
                "version": "0.0.1",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "description": "デフォルトカタログ（最小限）",
                "maintainer": "System Default"
            },
            "symbols": {
                "NASDAQCOM": {
                    "display_name": "NASDAQ Composite",
                    "data_sources": {
                        "primary": {"provider": "fred", "symbol": "NASDAQCOM"}
                    }
                }
            },
            "api_configurations": {},
            "data_categories": {}
        }
    
    def _initialize_clients(self):
        """データクライアントの初期化"""
        api_configs = self.catalog_data.get('api_configurations', {})
        
        # FRED クライアント
        if 'fred' in api_configs:
            try:
                from fred_data_client import FREDDataClient
                self._clients['fred'] = FREDDataClient()
                print("✅ FRED クライアント初期化")
            except Exception as e:
                print(f"⚠️ FRED クライアント初期化失敗: {e}")
        
        # Alpha Vantage クライアント  
        if 'alpha_vantage' in api_configs:
            try:
                from alpha_vantage_client import AlphaVantageClient
                self._clients['alpha_vantage'] = AlphaVantageClient()
                print("✅ Alpha Vantage クライアント初期化")
            except Exception as e:
                print(f"⚠️ Alpha Vantage クライアント初期化失敗: {e}")
    
    def get_available_symbols(self, category: Optional[str] = None) -> List[str]:
        """
        利用可能銘柄リストの取得
        
        Args:
            category: カテゴリフィルタ（us_indices, individual_stocks等）
            
        Returns:
            List[str]: 銘柄シンボルのリスト
        """
        symbols = list(self.catalog_data.get('symbols', {}).keys())
        
        if category:
            filtered_symbols = []
            for symbol in symbols:
                symbol_info = self.catalog_data['symbols'][symbol]
                if symbol_info.get('category') == category:
                    filtered_symbols.append(symbol)
            return filtered_symbols
        
        return symbols
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        銘柄詳細情報の取得
        
        Args:
            symbol: 銘柄シンボル
            
        Returns:
            Dict: 銘柄詳細情報
        """
        return self.catalog_data.get('symbols', {}).get(symbol, {})
    
    def get_recommended_analysis_symbols(self) -> List[str]:
        """バブル分析推奨銘柄の取得"""
        return self.catalog_data.get('analysis_recommendations', {}).get('bubble_detection_priority', [])
    
    def get_data_with_fallback(self, symbol: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str, Dict]:
        """
        フォールバック機能付きデータ取得
        
        Args:
            symbol: 銘柄シンボル
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            
        Returns:
            Tuple[DataFrame, source_name, metadata]: データ、ソース名、メタデータ
        """
        symbol_info = self.get_symbol_info(symbol)
        
        if not symbol_info:
            print(f"❌ 未対応銘柄: {symbol}")
            return None, "unknown", {}
        
        data_sources = symbol_info.get('data_sources', {})
        
        # プライマリソースを試行
        if 'primary' in data_sources:
            primary = data_sources['primary']
            provider = primary['provider']
            provider_symbol = primary['symbol']
            
            if provider in self._clients:
                print(f"📊 プライマリソース試行: {provider} ({provider_symbol})")
                data = self._get_data_from_provider(provider, provider_symbol, start_date, end_date)
                
                if data is not None:
                    metadata = {
                        'source': provider,
                        'provider_symbol': provider_symbol,
                        'reliability': primary.get('reliability', 'unknown'),
                        'symbol_info': symbol_info
                    }
                    return data, provider, metadata
        
        # フォールバックソースを試行
        if 'fallback' in data_sources:
            fallback = data_sources['fallback']
            provider = fallback['provider']
            provider_symbol = fallback['symbol']
            
            if provider in self._clients:
                print(f"📊 フォールバック試行: {provider} ({provider_symbol})")
                data = self._get_data_from_provider(provider, provider_symbol, start_date, end_date)
                
                if data is not None:
                    metadata = {
                        'source': provider,
                        'provider_symbol': provider_symbol,
                        'reliability': fallback.get('reliability', 'unknown'),
                        'symbol_info': symbol_info,
                        'fallback_used': True
                    }
                    return data, provider, metadata
        
        print(f"❌ 全データソースでの取得に失敗: {symbol}")
        return None, "failed", {'symbol_info': symbol_info}
    
    def _get_data_from_provider(self, provider: str, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """指定プロバイダからのデータ取得"""
        client = self._clients.get(provider)
        
        if not client:
            return None
        
        try:
            if provider == 'fred':
                return client.get_series_data(symbol, start_date, end_date)
            elif provider == 'alpha_vantage':
                # Alpha Vantage 클라이언트는 get_series_data 메서드 사용
                return client.get_series_data(symbol, start_date, end_date)
            else:
                print(f"❌ 未対応プロバイダ: {provider}")
                return None
                
        except Exception as e:
            print(f"❌ {provider}でのデータ取得エラー: {e}")
            return None
    
    def get_lppl_analysis_config(self, symbol: str) -> Dict:
        """LPPL分析設定の取得"""
        symbol_info = self.get_symbol_info(symbol)
        return symbol_info.get('lppl_analysis', {})
    
    def is_suitable_for_bubble_analysis(self, symbol: str) -> bool:
        """バブル分析適合性の判定"""
        symbol_info = self.get_symbol_info(symbol)
        suitability = symbol_info.get('bubble_analysis_suitability', 'unknown')
        return suitability in ['excellent', 'good']
    
    def get_analysis_report(self) -> Dict:
        """分析レポートの生成"""
        symbols = self.get_available_symbols()
        categories = {}
        
        for symbol in symbols:
            info = self.get_symbol_info(symbol)
            category = info.get('category', 'uncategorized')
            
            if category not in categories:
                categories[category] = []
            categories[category].append({
                'symbol': symbol,
                'display_name': info.get('display_name', symbol),
                'bubble_suitability': info.get('bubble_analysis_suitability', 'unknown'),
                'primary_provider': info.get('data_sources', {}).get('primary', {}).get('provider', 'unknown')
            })
        
        return {
            'total_symbols': len(symbols),
            'categories': categories,
            'available_providers': list(self._clients.keys()),
            'catalog_version': self.catalog_data.get('catalog_metadata', {}).get('version', 'unknown')
        }
    
    def update_catalog(self, updates: Dict) -> bool:
        """カタログの更新"""
        try:
            # バックアップ作成
            backup_path = f"{self.catalog_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(self.catalog_path, 'r') as original:
                with open(backup_path, 'w') as backup:
                    backup.write(original.read())
            
            # 更新適用
            self.catalog_data.update(updates)
            
            # バージョン更新
            if 'catalog_metadata' not in self.catalog_data:
                self.catalog_data['catalog_metadata'] = {}
            self.catalog_data['catalog_metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            
            # 保存
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ カタログ更新完了: {self.catalog_path}")
            print(f"📁 バックアップ作成: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ カタログ更新エラー: {e}")
            return False

def main():
    """デモンストレーション"""
    print("🎯 マーケットデータ管理システム デモ")
    print("=" * 50)
    
    # 初期化
    manager = MarketDataManager()
    
    # 利用可能銘柄の表示
    print(f"\n📊 利用可能銘柄:")
    symbols = manager.get_available_symbols()
    for symbol in symbols[:5]:  # 最初の5つを表示
        info = manager.get_symbol_info(symbol)
        print(f"   {symbol}: {info.get('display_name', symbol)}")
    
    # カテゴリ別表示
    print(f"\n📈 米国指数:")
    us_indices = manager.get_available_symbols('us_indices')
    for symbol in us_indices:
        info = manager.get_symbol_info(symbol)
        print(f"   {symbol}: {info.get('display_name', symbol)}")
    
    # 推奨銘柄
    print(f"\n💡 バブル分析推奨銘柄:")
    recommended = manager.get_recommended_analysis_symbols()
    for symbol in recommended:
        print(f"   {symbol}")
    
    # 分析レポート
    print(f"\n📊 システムレポート:")
    report = manager.get_analysis_report()
    print(f"   総銘柄数: {report['total_symbols']}")
    print(f"   カテゴリ数: {len(report['categories'])}")
    print(f"   利用可能プロバイダ: {report['available_providers']}")

if __name__ == "__main__":
    main()