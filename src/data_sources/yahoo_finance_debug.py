#!/usr/bin/env python3
"""
Yahoo Finance データ取得方法の詳細調査・改善

目的: 既存のYahoo Finance実装の問題点を特定し、
     より信頼性の高いデータ取得方法を確立する
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import warnings
import sys
import os
warnings.filterwarnings('ignore')

def test_basic_yfinance():
    """基本的なyfinanceの動作テスト"""
    print("=== Yahoo Finance 基本動作テスト ===\n")
    
    try:
        # 1. 簡単な最近のデータ取得テスト
        print("1. 最近データ取得テスト...")
        ticker = yf.Ticker("^GSPC")
        recent_data = ticker.history(period="5d")
        
        if not recent_data.empty:
            print(f"✅ 最近データ取得成功: {len(recent_data)}日分")
            print(f"   期間: {recent_data.index[0]} - {recent_data.index[-1]}")
            print(f"   最新価格: ${recent_data['Close'].iloc[-1]:.2f}")
        else:
            print("❌ 最近データ取得失敗")
            return False
            
    except Exception as e:
        print(f"❌ 基本テスト失敗: {e}")
        return False
    
    return True

def test_historical_data_methods():
    """複数の歴史データ取得方法をテスト"""
    print("\n=== 歴史データ取得方法比較テスト ===\n")
    
    # 1987年前のデータ取得を複数の方法で試行
    start_date = "1985-01-01"
    end_date = "1987-10-01"
    symbol = "^GSPC"
    
    methods = {
        "method1_direct": lambda: yf.download(symbol, start=start_date, end=end_date, progress=False),
        "method2_ticker": lambda: yf.Ticker(symbol).history(start=start_date, end=end_date),
        "method3_period": lambda: yf.Ticker(symbol).history(period="max"),
        "method4_with_retry": lambda: download_with_retry(symbol, start_date, end_date),
        "method5_session": lambda: download_with_session(symbol, start_date, end_date)
    }
    
    results = {}
    
    for method_name, method_func in methods.items():
        print(f"📊 {method_name} テスト中...")
        
        try:
            start_time = time.time()
            data = method_func()
            duration = time.time() - start_time
            
            if data is not None and not data.empty:
                # 1987年データが含まれているかチェック
                data_1987 = data[data.index.year == 1987]
                
                results[method_name] = {
                    'success': True,
                    'total_days': len(data),
                    'days_1987': len(data_1987),
                    'duration': duration,
                    'date_range': f"{data.index[0].date()} - {data.index[-1].date()}",
                    'price_range': f"${data['Close'].min():.2f} - ${data['Close'].max():.2f}",
                    'data_sample': data.head(3)
                }
                
                print(f"   ✅ 成功: {len(data)}日分, 1987年: {len(data_1987)}日分")
                print(f"   ⏱️ 所要時間: {duration:.2f}秒")
                print(f"   📅 期間: {data.index[0].date()} - {data.index[-1].date()}")
                
            else:
                results[method_name] = {
                    'success': False,
                    'error': 'Empty data returned'
                }
                print(f"   ❌ 失敗: 空のデータ")
                
        except Exception as e:
            results[method_name] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ❌ エラー: {str(e)[:100]}...")
        
        # APIレート制限を考慮した待機
        time.sleep(1)
    
    return results

def download_with_retry(symbol, start_date, end_date, max_retries=3):
    """リトライ機能付きダウンロード"""
    for attempt in range(max_retries):
        try:
            print(f"      リトライ {attempt + 1}/{max_retries}")
            data = yf.download(symbol, start=start_date, end=end_date, 
                             progress=False, timeout=30)
            if not data.empty:
                return data
        except Exception as e:
            print(f"      試行 {attempt + 1} 失敗: {str(e)[:50]}...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数バックオフ
    
    return None

def download_with_session(symbol, start_date, end_date):
    """セッション管理付きダウンロード"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        ticker = yf.Ticker(symbol, session=session)
        data = ticker.history(start=start_date, end=end_date)
        return data
    except Exception as e:
        return None
    finally:
        session.close()

def analyze_data_quality(results):
    """データ品質の詳細分析"""
    print("\n=== データ品質分析 ===\n")
    
    successful_methods = {k: v for k, v in results.items() if v.get('success', False)}
    
    if not successful_methods:
        print("❌ 成功した取得方法がありません")
        return None
    
    print(f"📊 成功した方法: {len(successful_methods)}/{len(results)}")
    
    # 最も良い方法を特定
    print(f"\n📈 各方法の詳細比較:")
    print(f"{'方法':<20} {'総日数':<8} {'1987年':<8} {'所要時間':<8} {'品質'}")
    print("-" * 60)
    
    best_method = None
    best_score = 0
    
    for method_name, result in successful_methods.items():
        total_days = result['total_days']
        days_1987 = result['days_1987']
        duration = result['duration']
        
        # 品質スコア計算（1987年データの多さを重視）
        quality_score = days_1987 * 2 + total_days * 0.001 - duration * 0.1
        
        quality_rating = "優秀" if days_1987 > 200 else "良好" if days_1987 > 100 else "普通"
        
        print(f"{method_name:<20} {total_days:<8} {days_1987:<8} {duration:<8.2f} {quality_rating}")
        
        if quality_score > best_score:
            best_score = quality_score
            best_method = method_name
    
    print(f"\n🏆 推奨方法: {best_method}")
    
    if best_method:
        best_result = successful_methods[best_method]
        print(f"   📅 データ期間: {best_result['date_range']}")
        print(f"   💰 価格範囲: {best_result['price_range']}")
        print(f"   📊 1987年データ: {best_result['days_1987']}日分")
        
        # サンプルデータの表示
        print(f"\n📋 データサンプル:")
        sample_data = best_result['data_sample']
        for idx, row in sample_data.iterrows():
            print(f"   {idx.date()}: ${row['Close']:.2f}")
    
    return best_method, successful_methods

def implement_improved_downloader():
    """改善されたダウンローダーの実装"""
    print("\n=== 改善版ダウンローダー実装 ===\n")
    
    def robust_yahoo_download(symbol, start_date, end_date, max_retries=3):
        """
        堅牢なYahoo Financeデータダウンローダー
        
        Features:
        - 複数の取得方法を順次試行
        - リトライ機能
        - セッション管理
        - データ品質チェック
        """
        
        print(f"📊 堅牢ダウンロード開始: {symbol} ({start_date} - {end_date})")
        
        # 試行する方法のリスト（成功率順）
        download_strategies = [
            ("session_based", lambda: download_with_session(symbol, start_date, end_date)),
            ("retry_based", lambda: download_with_retry(symbol, start_date, end_date, max_retries)),
            ("ticker_history", lambda: yf.Ticker(symbol).history(start=start_date, end=end_date)),
            ("direct_download", lambda: yf.download(symbol, start=start_date, end=end_date, progress=False))
        ]
        
        for strategy_name, strategy_func in download_strategies:
            print(f"   🔄 {strategy_name} 試行中...")
            
            try:
                data = strategy_func()
                
                if data is not None and not data.empty:
                    # データ品質チェック
                    if len(data) > 100:  # 最低100日のデータが必要
                        print(f"   ✅ {strategy_name} 成功: {len(data)}日分")
                        return data, strategy_name
                    else:
                        print(f"   ⚠️ {strategy_name}: データ不足 ({len(data)}日)")
                else:
                    print(f"   ❌ {strategy_name}: 空のデータ")
                    
            except Exception as e:
                print(f"   ❌ {strategy_name} エラー: {str(e)[:50]}...")
            
            time.sleep(1)  # 次の方法を試す前に少し待機
        
        print("   ❌ 全ての方法が失敗しました")
        return None, None
    
    return robust_yahoo_download

def test_improved_downloader():
    """改善版ダウンローダーのテスト"""
    print("\n=== 改善版ダウンローダーテスト ===\n")
    
    # 改善版ダウンローダーを取得
    robust_downloader = implement_improved_downloader()
    
    # 1987年データでテスト
    start_date = "1985-01-01"
    end_date = "1987-10-01"
    symbol = "^GSPC"
    
    data, method_used = robust_downloader(symbol, start_date, end_date)
    
    if data is not None:
        print(f"🎉 改善版ダウンローダーテスト成功!")
        print(f"   使用方法: {method_used}")
        print(f"   データ期間: {data.index[0].date()} - {data.index[-1].date()}")
        print(f"   総日数: {len(data)}")
        
        # 1987年データの確認
        data_1987 = data[data.index.year == 1987]
        print(f"   1987年データ: {len(data_1987)}日分")
        
        if len(data_1987) > 0:
            print(f"   1987年価格範囲: ${data_1987['Close'].min():.2f} - ${data_1987['Close'].max():.2f}")
            
        return data, method_used
    else:
        print("❌ 改善版ダウンローダーもデータ取得に失敗")
        return None, None

def save_improved_implementation():
    """改善された実装をファイルに保存"""
    print("\n=== 改善実装の保存 ===\n")
    
    improved_code = '''#!/usr/bin/env python3
"""
改善されたYahoo Finance データ取得クラス

Features:
- 複数の取得戦略による堅牢性
- 自動リトライとエラーハンドリング
- データ品質チェック
- レート制限対応
"""

import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime
from typing import Optional, Tuple

class RobustYahooFinance:
    """堅牢なYahoo Financeデータ取得クラス"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def download(self, symbol: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        堅牢なデータダウンロード
        
        Args:
            symbol: 銘柄シンボル (例: "^GSPC")
            start_date: 開始日 (例: "1985-01-01")
            end_date: 終了日 (例: "1987-10-01")
            
        Returns:
            (data, method_used): データフレームと使用された方法名
        """
        
        strategies = [
            ("session_based", self._download_with_session),
            ("retry_based", self._download_with_retry),
            ("ticker_history", self._download_ticker_history),
            ("direct_download", self._download_direct)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                data = strategy_func(symbol, start_date, end_date)
                
                if self._validate_data(data):
                    return data, strategy_name
                    
            except Exception as e:
                print(f"Strategy {strategy_name} failed: {str(e)[:50]}...")
                
            time.sleep(self.retry_delay)
        
        return None, None
    
    def _download_with_session(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """セッション管理付きダウンロード"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        try:
            ticker = yf.Ticker(symbol, session=session)
            return ticker.history(start=start_date, end=end_date)
        finally:
            session.close()
    
    def _download_with_retry(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """リトライ機能付きダウンロード"""
        for attempt in range(self.max_retries):
            try:
                data = yf.download(symbol, start=start_date, end=end_date, 
                                 progress=False, timeout=30)
                if not data.empty:
                    return data
            except Exception:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数バックオフ
        
        raise Exception("All retry attempts failed")
    
    def _download_ticker_history(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Ticker.history()メソッド"""
        ticker = yf.Ticker(symbol)
        return ticker.history(start=start_date, end=end_date)
    
    def _download_direct(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """直接ダウンロード"""
        return yf.download(symbol, start=start_date, end=end_date, progress=False)
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        """データ品質検証"""
        if data is None or data.empty:
            return False
        
        # 最低限のデータ数チェック
        if len(data) < 50:
            return False
            
        # 必要なカラムの存在チェック
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            return False
            
        # NaN値のチェック
        if data['Close'].isna().sum() > len(data) * 0.1:  # 10%以上のNaNは不合格
            return False
            
        return True

# 使用例
if __name__ == "__main__":
    downloader = RobustYahooFinance()
    data, method = downloader.download("^GSPC", "1985-01-01", "1987-10-01")
    
    if data is not None:
        print(f"Success with method: {method}")
        print(f"Data shape: {data.shape}")
    else:
        print("All methods failed")
'''
    
    os.makedirs('src/data_sources/', exist_ok=True)
    
    with open('src/data_sources/robust_yahoo_finance.py', 'w', encoding='utf-8') as f:
        f.write(improved_code)
    
    print("📁 改善実装保存: src/data_sources/robust_yahoo_finance.py")

def main():
    """メイン実行関数"""
    print("🔍 Yahoo Finance データ取得方法の詳細調査開始\n")
    
    # 1. 基本動作テスト
    if not test_basic_yfinance():
        print("❌ 基本動作に問題があります")
        return
    
    # 2. 複数の取得方法テスト
    results = test_historical_data_methods()
    
    # 3. 結果分析
    best_method, successful_methods = analyze_data_quality(results)
    
    # 4. 改善版ダウンローダーのテスト
    data, method_used = test_improved_downloader()
    
    # 5. 改善実装の保存
    save_improved_implementation()
    
    # 6. 結論とNext Steps
    print(f"\n🎯 結論:")
    if data is not None:
        print("✅ Yahoo Financeからのデータ取得は可能")
        print("✅ 改善された取得方法で1987年データ取得成功")
        print("✅ 実市場データでの検証を継続可能")
        
        print(f"\n📋 Next Steps:")
        print("1. 改善されたダウンローダーで1987年実市場検証実行")
        print("2. 複数データソースとの品質比較")
        print("3. 実用システムでの運用テスト")
        
    else:
        print("❌ Yahoo Financeでの1987年データ取得に問題")
        print("❌ 代替APIの利用を強く推奨")

if __name__ == "__main__":
    main()