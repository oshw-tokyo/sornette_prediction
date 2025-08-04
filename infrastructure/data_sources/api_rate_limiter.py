#!/usr/bin/env python3
"""
APIレート制限管理システム

複数のAPIプロバイダのレート制限を統一的に管理し、
適切な待機時間と進捗表示を提供
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from collections import deque
from pathlib import Path
import threading
from enum import Enum

class RateLimitPeriod(Enum):
    """レート制限の期間種別"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"

class APIRateLimiter:
    """統一APIレート制限管理システム"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            cache_dir: レート制限状態のキャッシュディレクトリ
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".sornette_cache" / "rate_limits"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # プロバイダごとのレート制限設定
        self.rate_limits = self._load_rate_limit_config()
        
        # リクエスト履歴（プロバイダごと）
        self.request_history: Dict[str, Dict[str, deque]] = {}
        
        # ロック（スレッドセーフ）
        self.lock = threading.Lock()
        
        # 進捗表示コールバック
        self.progress_callback = None
        
        # 状態の復元
        self._restore_state()
    
    def _load_rate_limit_config(self) -> Dict:
        """レート制限設定の読み込み"""
        # カタログファイルから読み込み
        catalog_path = Path(__file__).parent / "market_data_catalog.json"
        
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
                
            api_configs = catalog.get('api_configurations', {})
            
            rate_limits = {}
            for provider, config in api_configs.items():
                limits = config.get('rate_limits', {})
                
                # 各期間の制限を構造化
                provider_limits = {}
                
                if 'requests_per_minute' in limits:
                    provider_limits[RateLimitPeriod.MINUTE] = {
                        'limit': limits['requests_per_minute'],
                        'period_seconds': 60
                    }
                
                if 'requests_per_hour' in limits:
                    provider_limits[RateLimitPeriod.HOUR] = {
                        'limit': limits['requests_per_hour'],
                        'period_seconds': 3600
                    }
                
                if 'requests_per_day' in limits:
                    provider_limits[RateLimitPeriod.DAY] = {
                        'limit': limits['requests_per_day'],
                        'period_seconds': 86400
                    }
                
                rate_limits[provider] = provider_limits
            
            return rate_limits
        
        # デフォルト設定
        return {
            'fred': {
                RateLimitPeriod.MINUTE: {'limit': 120, 'period_seconds': 60},
                RateLimitPeriod.DAY: {'limit': 10000, 'period_seconds': 86400}
            },
            'alpha_vantage': {
                RateLimitPeriod.MINUTE: {'limit': 5, 'period_seconds': 60},
                RateLimitPeriod.DAY: {'limit': 500, 'period_seconds': 86400}
            }
        }
    
    def set_progress_callback(self, callback):
        """進捗表示コールバックの設定"""
        self.progress_callback = callback
    
    def check_and_wait(self, provider: str, request_count: int = 1) -> float:
        """
        レート制限チェックと必要な待機
        
        Args:
            provider: APIプロバイダ名
            request_count: 実行予定のリクエスト数
            
        Returns:
            float: 待機した時間（秒）
        """
        with self.lock:
            if provider not in self.rate_limits:
                # 未知のプロバイダは制限なし
                return 0.0
            
            # プロバイダの履歴初期化
            if provider not in self.request_history:
                self.request_history[provider] = {}
                for period in RateLimitPeriod:
                    self.request_history[provider][period] = deque()
            
            # 最も厳しい待機時間を計算
            max_wait_time = 0.0
            wait_reasons = []
            
            for period, config in self.rate_limits[provider].items():
                limit = config['limit']
                period_seconds = config['period_seconds']
                
                # 古いリクエストを削除
                cutoff_time = datetime.now() - timedelta(seconds=period_seconds)
                history = self.request_history[provider][period]
                
                while history and history[0] < cutoff_time:
                    history.popleft()
                
                # 現在のリクエスト数
                current_count = len(history)
                
                # 制限チェック
                if current_count + request_count > limit:
                    # 最も古いリクエストからの経過時間
                    if history:
                        oldest_request = history[0]
                        time_since_oldest = (datetime.now() - oldest_request).total_seconds()
                        wait_time = period_seconds - time_since_oldest + 1  # 1秒余裕
                        
                        if wait_time > max_wait_time:
                            max_wait_time = wait_time
                            wait_reasons.append({
                                'period': period.value,
                                'current': current_count,
                                'limit': limit,
                                'wait_time': wait_time
                            })
            
            # 待機が必要な場合
            if max_wait_time > 0:
                self._show_wait_progress(provider, max_wait_time, wait_reasons)
                time.sleep(max_wait_time)
            
            # リクエストを記録
            now = datetime.now()
            for _ in range(request_count):
                for period in RateLimitPeriod:
                    self.request_history[provider][period].append(now)
            
            # 状態を保存
            self._save_state()
            
            return max_wait_time
    
    def _show_wait_progress(self, provider: str, wait_time: float, reasons: List[Dict]):
        """待機進捗の表示"""
        if wait_time <= 0:
            return
        
        print(f"\n⏳ APIレート制限により待機中 ({provider}):")
        
        for reason in reasons:
            print(f"   {reason['period']}: {reason['current']}/{reason['limit']} リクエスト使用済み")
        
        print(f"   待機時間: {wait_time:.1f}秒")
        
        # プログレスバー表示
        if wait_time > 2:  # 2秒以上の場合のみ
            import sys
            
            start_time = time.time()
            bar_length = 40
            
            while True:
                elapsed = time.time() - start_time
                if elapsed >= wait_time:
                    break
                
                progress = elapsed / wait_time
                filled_length = int(bar_length * progress)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                remaining = wait_time - elapsed
                
                sys.stdout.write(f'\r   進捗: [{bar}] {progress*100:.1f}% | 残り: {remaining:.1f}秒 ')
                sys.stdout.flush()
                
                time.sleep(0.1)
            
            sys.stdout.write('\r   進捗: [' + '█' * bar_length + '] 100.0% | 完了!          \n')
            sys.stdout.flush()
        else:
            time.sleep(wait_time)
        
        print("✅ 待機完了、処理を再開します\n")
    
    def get_remaining_quota(self, provider: str) -> Dict[str, Dict]:
        """
        残りリクエスト数の取得
        
        Returns:
            Dict: 期間ごとの残りリクエスト数
        """
        with self.lock:
            if provider not in self.rate_limits:
                return {}
            
            result = {}
            
            for period, config in self.rate_limits[provider].items():
                limit = config['limit']
                period_seconds = config['period_seconds']
                
                # 履歴の確認
                if provider in self.request_history and period in self.request_history[provider]:
                    # 古いリクエストを削除
                    cutoff_time = datetime.now() - timedelta(seconds=period_seconds)
                    history = self.request_history[provider][period]
                    
                    while history and history[0] < cutoff_time:
                        history.popleft()
                    
                    used = len(history)
                else:
                    used = 0
                
                result[period.value] = {
                    'used': used,
                    'limit': limit,
                    'remaining': limit - used,
                    'reset_in': period_seconds
                }
            
            return result
    
    def estimate_completion_time(self, provider: str, total_requests: int) -> Dict:
        """
        複数リクエストの完了時間推定
        
        Args:
            provider: APIプロバイダ
            total_requests: 総リクエスト数
            
        Returns:
            Dict: 推定完了時間情報
        """
        if provider not in self.rate_limits:
            return {
                'can_complete': True,
                'estimated_time': 0,
                'estimated_completion': datetime.now()
            }
        
        # 最も制限の厳しい期間でのレートを計算
        min_rate_per_second = float('inf')
        limiting_period = None
        
        for period, config in self.rate_limits[provider].items():
            rate_per_second = config['limit'] / config['period_seconds']
            if rate_per_second < min_rate_per_second:
                min_rate_per_second = rate_per_second
                limiting_period = period
        
        # 推定時間
        estimated_seconds = total_requests / min_rate_per_second
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
        
        return {
            'can_complete': True,
            'estimated_time': estimated_seconds,
            'estimated_completion': estimated_completion,
            'limiting_factor': limiting_period.value if limiting_period else None,
            'effective_rate': min_rate_per_second
        }
    
    def _save_state(self):
        """状態の保存"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'request_history': {}
        }
        
        for provider, periods in self.request_history.items():
            state['request_history'][provider] = {}
            for period, history in periods.items():
                # dequeをリストに変換して保存
                state['request_history'][provider][period.value] = [
                    dt.isoformat() for dt in history
                ]
        
        state_file = self.cache_dir / "rate_limit_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _restore_state(self):
        """状態の復元"""
        state_file = self.cache_dir / "rate_limit_state.json"
        
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # タイムスタンプチェック（24時間以上古い場合は無視）
            saved_time = datetime.fromisoformat(state['timestamp'])
            if datetime.now() - saved_time > timedelta(hours=24):
                return
            
            # リクエスト履歴の復元
            for provider, periods in state['request_history'].items():
                if provider not in self.request_history:
                    self.request_history[provider] = {}
                
                for period_str, history_list in periods.items():
                    period = RateLimitPeriod(period_str)
                    self.request_history[provider][period] = deque([
                        datetime.fromisoformat(dt) for dt in history_list
                    ])
            
            print("📊 APIレート制限状態を復元しました")
            
        except Exception as e:
            print(f"⚠️ レート制限状態の復元に失敗: {e}")
    
    def reset_provider(self, provider: str):
        """特定プロバイダの履歴リセット"""
        with self.lock:
            if provider in self.request_history:
                for period in self.request_history[provider]:
                    self.request_history[provider][period].clear()
            
            self._save_state()
            print(f"🔄 {provider} のレート制限履歴をリセットしました")
    
    def get_status_report(self) -> str:
        """全プロバイダの状態レポート生成"""
        report = "📊 APIレート制限状態レポート\n"
        report += "=" * 50 + "\n\n"
        
        for provider in sorted(self.rate_limits.keys()):
            report += f"【{provider.upper()}】\n"
            
            quota = self.get_remaining_quota(provider)
            
            for period, info in sorted(quota.items()):
                percentage = (info['remaining'] / info['limit']) * 100 if info['limit'] > 0 else 100
                status_icon = "🟢" if percentage > 50 else "🟡" if percentage > 20 else "🔴"
                
                report += f"  {period}: {status_icon} {info['used']}/{info['limit']} "
                report += f"(残り: {info['remaining']}, {percentage:.1f}%)\n"
            
            report += "\n"
        
        return report

# 使用例とテスト
def example_usage():
    """使用例のデモンストレーション"""
    print("🎯 APIレート制限管理システム デモ")
    print("=" * 50)
    
    # 初期化
    limiter = APIRateLimiter()
    
    # 現在の状態確認
    print(limiter.get_status_report())
    
    # リクエスト実行シミュレーション
    providers = ['fred', 'alpha_vantage']
    
    for provider in providers:
        print(f"\n📡 {provider} へのリクエストシミュレーション")
        
        # 単一リクエスト
        wait_time = limiter.check_and_wait(provider, 1)
        if wait_time == 0:
            print(f"✅ 即座に実行可能")
        
        # 複数リクエストの推定
        total_requests = 10
        estimate = limiter.estimate_completion_time(provider, total_requests)
        
        print(f"📊 {total_requests}リクエストの推定:")
        print(f"   完了予定時間: {estimate['estimated_time']:.1f}秒")
        print(f"   制限要因: {estimate['limiting_factor']}")
        print(f"   実効レート: {estimate['effective_rate']:.2f} req/sec")
    
    # 最終状態
    print("\n" + limiter.get_status_report())

if __name__ == "__main__":
    example_usage()