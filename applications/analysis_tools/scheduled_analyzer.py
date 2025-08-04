#!/usr/bin/env python3
"""
定期分析システム
スケジュールに基づいた自動LPPL分析の実行・管理
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from infrastructure.database.schedule_manager import ScheduleManager, ScheduleConfig
from applications.analysis_tools.crash_alert_system import CrashAlertSystem
from infrastructure.database.integration_helpers import AnalysisResultSaver
from infrastructure.data_sources.unified_data_client import UnifiedDataClient
from core.fitting.multi_criteria_selection import MultiCriteriaSelector
from infrastructure.visualization.lppl_visualizer import LPPLVisualizer
from infrastructure.config.matplotlib_config import configure_matplotlib_for_automation
from infrastructure.error_handling.analysis_error_handler import AnalysisErrorHandler, ErrorCategory, ErrorSeverity

# matplotlib GUI無効化
configure_matplotlib_for_automation()

class ScheduledAnalyzer:
    """定期分析システムメインクラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db_path = db_path
        self.schedule_manager = ScheduleManager(db_path)
        
        # 分析コンポーネント
        self.data_client = UnifiedDataClient()
        self.selector = MultiCriteriaSelector()
        self.db_saver = AnalysisResultSaver(db_path)
        self.visualizer = LPPLVisualizer(db_path)
        
        # エラーハンドリング
        self.error_handler = AnalysisErrorHandler(db_path)
        
        # 自動補完制限
        self.AUTO_BACKFILL_LIMIT = 30  # 最大30日分
    
    def run_scheduled_analysis(self, schedule_name: str = 'fred_weekly') -> Dict:
        """
        定期分析の実行（自動データ補完付き）
        
        Args:
            schedule_name: スケジュール名
            
        Returns:
            Dict: 実行結果サマリー
        """
        print(f"🕐 定期分析開始: {schedule_name}")
        print("=" * 60)
        
        # 1. スケジュール設定読み込み
        config = self.schedule_manager.get_schedule_config(schedule_name)
        if not config:
            raise ValueError(f"スケジュール設定が見つかりません: {schedule_name}")
        
        if not config.enabled:
            print(f"⚠️ スケジュール無効: {schedule_name}")
            return {'status': 'disabled'}
        
        # 2. 分析基準日の算出
        basis_date = self._calculate_analysis_basis_date(config)
        print(f"📅 分析基準日: {basis_date}")
        
        # 3. 不足データの検出
        missing_periods = self._detect_missing_periods(config, basis_date)
        
        # 4. 自動データ補完の判定・実行
        results = {
            'schedule_name': schedule_name,
            'basis_date': basis_date,
            'missing_periods': len(missing_periods),
            'auto_backfill_executed': False,
            'analyzed_symbols': [],
            'failed_symbols': [],
            'start_time': datetime.now()
        }
        
        if missing_periods:
            if len(missing_periods) <= self.AUTO_BACKFILL_LIMIT:
                print(f"🔄 自動データ補完開始: {len(missing_periods)}期間")
                backfill_results = self._run_backfill_periods(missing_periods, config)
                results['auto_backfill_executed'] = True
                results['backfill_results'] = backfill_results
            else:
                print(f"⚠️ 不足データが多すぎます: {len(missing_periods)}期間 > {self.AUTO_BACKFILL_LIMIT}")
                print(f"💡 手動バックフィル推奨:")
                print(f"   python entry_points/main.py scheduled-analysis backfill --start {missing_periods[0]}")
                # 今回分のみ実行
        
        # 5. 今回分の定期分析実行
        print(f"\\n📊 定期分析実行: {basis_date}")
        current_results = self._run_analysis_for_period(basis_date, config.symbols, schedule_name)
        
        results['analyzed_symbols'].extend(current_results['successful'])
        results['failed_symbols'].extend(current_results['failed'])
        
        # 6. スケジュール状態更新
        self.schedule_manager.update_last_run(schedule_name, datetime.now())
        
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        results['total_success'] = len(results['analyzed_symbols'])
        results['total_failed'] = len(results['failed_symbols'])
        
        return results
    
    def _calculate_analysis_basis_date(self, config: ScheduleConfig) -> str:
        """
        分析基準日の算出
        
        Args:
            config: スケジュール設定
            
        Returns:
            str: 分析基準日 (YYYY-MM-DD)
        """
        now = datetime.now()
        
        if config.frequency == 'weekly':
            # 前回の指定曜日を基準日とする
            days_since_target = (now.weekday() - config.day_of_week) % 7
            if days_since_target == 0 and now.hour < config.hour:
                # 今日が指定曜日だが、まだ実行時刻前の場合は前週
                days_since_target = 7
            
            basis_date = now - timedelta(days=days_since_target)
        elif config.frequency == 'daily':
            # 昨日を基準日とする  
            basis_date = now - timedelta(days=1)
        else:
            # 月次など他の頻度はとりあえず昨日
            basis_date = now - timedelta(days=1)
        
        return basis_date.strftime('%Y-%m-%d')
    
    def _detect_missing_periods(self, config: ScheduleConfig, current_basis_date: str) -> List[str]:
        """
        不足データ期間の検出
        
        Args:
            config: スケジュール設定  
            current_basis_date: 今回の分析基準日
            
        Returns:
            List[str]: 不足期間のリスト
        """
        if not config.last_run:
            # 初回実行の場合は不足なし（今回分のみ）
            return []
        
        missing_periods = []
        
        if config.frequency == 'weekly':
            # 前回実行から今回まで、週次で不足期間をチェック
            last_basis = config.last_run.date()
            current_basis = datetime.strptime(current_basis_date, '%Y-%m-%d').date()
            
            check_date = last_basis + timedelta(days=7)
            while check_date < current_basis:
                missing_periods.append(check_date.strftime('%Y-%m-%d'))
                check_date += timedelta(days=7)
        
        return missing_periods
    
    def _run_backfill_periods(self, periods: List[str], config: ScheduleConfig) -> Dict:
        """
        指定期間のバックフィル実行
        
        Args:
            periods: バックフィル対象期間
            config: スケジュール設定
            
        Returns:
            Dict: バックフィル結果
        """
        batch_id = f"auto_backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            'batch_id': batch_id,
            'periods': len(periods),
            'successful': [],
            'failed': []
        }
        
        for i, period in enumerate(periods, 1):
            print(f"  📊 バックフィル進捗: {i}/{len(periods)} - {period}")
            
            period_results = self._run_analysis_for_period(
                period, config.symbols, config.schedule_name, backfill_batch_id=batch_id
            )
            
            results['successful'].extend(period_results['successful'])
            results['failed'].extend(period_results['failed'])
            
            # API制限対応
            if i < len(periods):
                print("  ⏳ API制限管理: 2秒待機...")
                time.sleep(2)
        
        return results
    
    def _run_analysis_for_period(self, basis_date: str, symbols: List[str], 
                                schedule_name: str, backfill_batch_id: Optional[str] = None) -> Dict:
        """
        指定期間・銘柄の分析実行
        
        Args:
            basis_date: 分析基準日
            symbols: 対象銘柄リスト
            schedule_name: スケジュール名
            backfill_batch_id: バックフィルバッチID
            
        Returns:
            Dict: 分析結果
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        for i, symbol in enumerate(symbols, 1):
            print(f"  📊 分析進捗: {i}/{len(symbols)} - {symbol}")
            
            success = self._analyze_single_symbol(
                symbol, basis_date, schedule_name, backfill_batch_id
            )
            
            if success:
                results['successful'].append(symbol)
                print(f"    ✅ {symbol} 完了")
            else:
                results['failed'].append(symbol)
                print(f"    ❌ {symbol} 失敗")
            
            # API制限対応
            if i < len(symbols):
                time.sleep(1)  # 短い間隔
        
        return results
    
    def _analyze_single_symbol(self, symbol: str, basis_date: str, 
                              schedule_name: str, backfill_batch_id: Optional[str] = None,
                              period_days: int = 365) -> bool:
        """
        単一銘柄の分析実行
        
        Args:
            symbol: 分析対象銘柄
            basis_date: 分析基準日
            schedule_name: スケジュール名
            backfill_batch_id: バックフィルバッチID
            period_days: 分析期間（日数）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            # 1. データ取得期間の計算
            end_date = datetime.strptime(basis_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=period_days - 1)
            
            # 2. データ取得
            data, source = self.data_client.get_data_with_fallback(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if data is None or data.empty:
                return False
            
            # 3. LPPL分析実行
            result = self.selector.perform_comprehensive_fitting(data)
            if result is None:
                return False
            
            # 4. 分析結果の拡張（スケジュール情報追加）
            selected_result = result.get_selected_result()
            
            # 5. データベース保存（スケジュール情報付き）
            analysis_id = self._save_scheduled_analysis(
                symbol, data, result, source, schedule_name, 
                basis_date, backfill_batch_id
            )
            
            # 6. 可視化生成
            self.visualizer.create_comprehensive_visualization(analysis_id)
            
            return True
            
        except Exception as e:
            print(f"    ❌ {symbol} 分析エラー: {e}")
            return False
    
    def _save_scheduled_analysis(self, symbol: str, data, result, source: str,
                               schedule_name: str, basis_date: str, 
                               backfill_batch_id: Optional[str] = None) -> int:
        """
        スケジュール分析結果の保存
        
        Args:
            symbol: 銘柄
            data: 価格データ
            result: 分析結果
            source: データソース
            schedule_name: スケジュール名
            basis_date: 分析基準日
            backfill_batch_id: バックフィルバッチID
            
        Returns:
            int: 分析ID
        """
        # 通常の保存処理
        analysis_id = self.db_saver.save_lppl_analysis(symbol, data, result, source)
        
        # スケジュール情報の追加更新（曜日メタデータ含む）
        import sqlite3
        from datetime import datetime
        
        # 分析基準日の曜日とスケジュール頻度を計算
        basis_datetime = datetime.strptime(basis_date, '%Y-%m-%d')
        basis_day_of_week = basis_datetime.weekday()  # 0=月曜, 6=日曜
        
        # スケジュール名から頻度を抽出
        if '_weekly' in schedule_name:
            analysis_frequency = 'weekly'
        elif '_daily' in schedule_name:
            analysis_frequency = 'daily'
        elif '_monthly' in schedule_name:
            analysis_frequency = 'monthly'
        else:
            analysis_frequency = 'unknown'
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE analysis_results 
                SET schedule_name = ?, 
                    analysis_basis_date = ?, 
                    is_scheduled = 1,
                    backfill_batch_id = ?,
                    basis_day_of_week = ?,
                    analysis_frequency = ?
                WHERE id = ?
            ''', (schedule_name, basis_date, backfill_batch_id, 
                  basis_day_of_week, analysis_frequency, analysis_id))
            conn.commit()
        
        return analysis_id
    
    def get_schedule_status(self) -> Dict:
        """スケジュール状態の取得"""
        return self.schedule_manager.get_schedule_status()
    
    def run_backfill_analysis(self, start_date: str, end_date: Optional[str] = None, 
                             schedule_name: str = 'fred_weekly') -> Dict:
        """
        バックフィル分析の実行
        
        Args:
            start_date: バックフィル開始日 (YYYY-MM-DD)
            end_date: バックフィル終了日 (YYYY-MM-DD、省略時は昨日)
            schedule_name: スケジュール名
            
        Returns:
            Dict: バックフィル結果
        """
        print(f"🔄 バックフィル分析開始: {start_date} から")
        print("=" * 60)
        
        # 1. スケジュール設定読み込み
        config = self.schedule_manager.get_schedule_config(schedule_name)
        if not config:
            raise ValueError(f"スケジュール設定が見つかりません: {schedule_name}")
        
        # 2. バックフィル期間の算出
        start = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end = datetime.now() - timedelta(days=1)  # 昨日まで
        
        # 3. バックフィル対象期間の生成（週次の場合は曜日整合性確保）
        backfill_periods = self._generate_backfill_periods(start, end, config.frequency, config)
        
        print(f"📋 バックフィル対象: {len(backfill_periods)}期間")
        for i, period in enumerate(backfill_periods[:5], 1):  # 最初の5期間を表示
            print(f"  {i:2d}. {period}")
        if len(backfill_periods) > 5:
            print(f"  ... 他{len(backfill_periods)-5}期間")
        
        # 4. 既存分析の重複チェック
        periods_to_analyze = self._filter_unanalyzed_periods(backfill_periods, config.symbols, schedule_name)
        
        if len(periods_to_analyze) < len(backfill_periods):
            skipped = len(backfill_periods) - len(periods_to_analyze)
            print(f"📊 重複スキップ: {skipped}期間（既分析済み）")
        
        print(f"🎯 実行対象: {len(periods_to_analyze)}期間")
        
        # 5. バックフィル実行
        batch_id = f"manual_backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            'batch_id': batch_id,
            'start_date': start_date,
            'end_date': end_date or end.strftime('%Y-%m-%d'),
            'total_periods': len(backfill_periods),
            'analyzed_periods': len(periods_to_analyze),
            'skipped_periods': len(backfill_periods) - len(periods_to_analyze),
            'successful_analyses': [],
            'failed_analyses': [],
            'start_time': datetime.now()
        }
        
        for i, period in enumerate(periods_to_analyze, 1):
            print(f"\\n📊 バックフィル進捗: {i}/{len(periods_to_analyze)} - {period}")
            
            period_results = self._run_analysis_for_period(
                period, config.symbols, schedule_name, backfill_batch_id=batch_id
            )
            
            results['successful_analyses'].extend([
                f"{period}:{symbol}" for symbol in period_results['successful']
            ])
            results['failed_analyses'].extend([
                f"{period}:{symbol}" for symbol in period_results['failed']
            ])
            
            # 進捗表示
            period_success = len(period_results['successful'])
            period_failed = len(period_results['failed'])
            print(f"  ✅ {period}: 成功{period_success}, 失敗{period_failed}")
            
            # API制限対応（期間間の待機）
            if i < len(periods_to_analyze):
                print("  ⏳ API制限管理: 3秒待機...")
                time.sleep(3)
        
        # 6. 結果サマリー
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        results['total_successful'] = len(results['successful_analyses'])
        results['total_failed'] = len(results['failed_analyses'])
        results['success_rate'] = (results['total_successful'] / 
                                 max(1, results['total_successful'] + results['total_failed'])) * 100
        
        print(f"\\n📊 バックフィル完了:")
        print(f"   期間: {results['start_date']} 〜 {results['end_date']}")
        print(f"   対象期間: {results['analyzed_periods']}")
        print(f"   成功分析: {results['total_successful']}")
        print(f"   失敗分析: {results['total_failed']}")
        print(f"   成功率: {results['success_rate']:.1f}%")
        print(f"   実行時間: {results['duration']}")
        
        return results
    
    def _generate_backfill_periods(self, start: datetime, end: datetime, frequency: str, 
                                  schedule_config: Optional[ScheduleConfig] = None) -> List[str]:
        """
        バックフィル対象期間の生成（週次の場合は曜日整合性を確保）
        
        Args:
            start: 開始日
            end: 終了日  
            frequency: 頻度
            schedule_config: スケジュール設定（週次の曜日調整用）
            
        Returns:
            List[str]: 対象期間リスト
        """
        periods = []
        
        if frequency == 'weekly':
            # 週次: スケジュール設定の曜日に合わせて調整
            target_weekday = schedule_config.day_of_week if schedule_config else 5  # デフォルト土曜日
            
            # 開始日を指定曜日に調整
            days_until_target = (target_weekday - start.weekday()) % 7
            if days_until_target == 0 and start.weekday() != target_weekday:
                # 既に同じ曜日で開始日より後の日を探す
                days_until_target = 7
            
            # 最初の対象曜日を見つける
            current = start + timedelta(days=days_until_target)
            
            # 開始日より前の最初の対象曜日も含める（範囲内の場合）
            if days_until_target > 0:
                prev_target = current - timedelta(days=7)
                if prev_target >= start:
                    current = prev_target
            
            # 7日間隔で期間生成
            while current <= end:
                periods.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=7)
        elif frequency == 'daily':
            # 日次: 1日間隔
            current = start
            while current <= end:
                periods.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        elif frequency == 'monthly':
            # 月次: 月初を基準
            current = start
            while current <= end:
                periods.append(current.strftime('%Y-%m-%d'))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        else:
            # 不明な頻度は日次として扱う
            current = start
            while current <= end:
                periods.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        
        return periods
    
    def _filter_unanalyzed_periods(self, periods: List[str], symbols: List[str], 
                                  schedule_name: str) -> List[str]:
        """
        未分析期間のフィルタリング
        
        Args:
            periods: 全期間リスト
            symbols: 対象銘柄リスト
            schedule_name: スケジュール名
            
        Returns:
            List[str]: 未分析期間リスト
        """
        import sqlite3
        
        unanalyzed_periods = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for period in periods:
                # 該当期間・スケジュールでの分析数をチェック
                cursor.execute('''
                    SELECT COUNT(DISTINCT symbol) 
                    FROM analysis_results 
                    WHERE analysis_basis_date = ? 
                    AND schedule_name = ?
                ''', (period, schedule_name))
                
                existing_count = cursor.fetchone()[0]
                
                # 全銘柄が分析済みでない場合は対象に含める
                if existing_count < len(symbols):
                    unanalyzed_periods.append(period)
        
        return unanalyzed_periods
    
    def _retry_data_fetch(self, symbol: str, start_date: str, end_date: str):
        """データ取得リトライ（短期間で再試行）"""
        time.sleep(5)  # 5秒待機後リトライ
        return self.data_client.get_data_with_fallback(symbol, start_date, end_date)
    
    def _retry_analysis_with_relaxed_params(self, data):
        """分析リトライ（緩和されたパラメータで）"""
        # より緩い条件で再分析を試行
        # 注: MultiCriteriaSelector内部の実装に依存
        return self.selector.perform_comprehensive_fitting(data)
    
    def _retry_database_save(self, symbol: str, data, result, source: str,
                           schedule_name: str, basis_date: str, backfill_batch_id: Optional[str] = None):
        """データベース保存リトライ"""
        time.sleep(2)  # DB接続待機
        return self._save_scheduled_analysis(
            symbol, data, result, source, schedule_name, basis_date, backfill_batch_id
        )
    
    def get_error_summary(self, days: int = 7) -> Dict:
        """エラーサマリーの取得"""
        return self.error_handler.get_error_summary(days)
    
    def cleanup_old_errors(self, days: int = 90) -> int:
        """古いエラーログの削除"""
        return self.error_handler.cleanup_old_errors(days)
    
    def configure_schedule(self, schedule_name: str, source: str, frequency: str, symbols: List[str]) -> bool:
        """
        新しいスケジュール設定（データソース別×頻度別）
        
        Args:
            schedule_name: スケジュール名 (例: fred_weekly, alpha_vantage_daily)
            source: データソース (fred, alpha_vantage)
            frequency: 実行頻度 (weekly, daily)
            symbols: 対象銘柄リスト
            
        Returns:
            bool: 設定成功したかどうか
        """
        try:
            import sqlite3
            import json
            from datetime import datetime
            
            # 頻度に応じた設定
            if frequency == 'weekly':
                day_of_week = 5  # 土曜日 (0=月曜)
                hour = 9
            elif frequency == 'daily':
                day_of_week = None  # 毎日実行
                hour = 9
            else:
                raise ValueError(f"Unsupported frequency: {frequency}")
            
            # データソース検証
            if source not in ['fred', 'alpha_vantage']:
                raise ValueError(f"Unsupported source: {source}")
            
            # 銘柄リスト検証（基本的なもの）
            if not symbols:
                raise ValueError("Symbols list cannot be empty")
            
            # データベースに設定保存/更新
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 既存設定チェック
                cursor.execute('SELECT id FROM schedule_config WHERE schedule_name = ?', (schedule_name,))
                existing = cursor.fetchone()
                
                current_time = datetime.now()
                
                if existing:
                    # 既存設定の更新
                    cursor.execute('''
                        UPDATE schedule_config 
                        SET frequency = ?, day_of_week = ?, hour = ?, 
                            symbols = ?, enabled = 1, 
                            last_run = NULL, next_run = NULL
                        WHERE schedule_name = ?
                    ''', (frequency, day_of_week, hour, json.dumps(symbols), schedule_name))
                    
                    print(f"📝 既存スケジュール設定を更新しました: {schedule_name}")
                    
                    # 頻度変更時の自動バックフィル提案
                    cursor.execute('SELECT frequency FROM schedule_config WHERE schedule_name = ?', (schedule_name,))
                    old_frequency = cursor.fetchone()
                    if old_frequency and old_frequency[0] != frequency:
                        print(f"⚠️ 頻度変更検出: {old_frequency[0]} → {frequency}")
                        print(f"💡 過去データの整合性確保のため、バックフィル実行を推奨:")
                        print(f"   python entry_points/main.py scheduled-analysis backfill --start 2024-01-01 --schedule {schedule_name}")
                else:
                    # 新規設定の作成
                    cursor.execute('''
                        INSERT INTO schedule_config (
                            schedule_name, frequency, day_of_week, hour, minute, timezone,
                            symbols, enabled, created_date, auto_backfill_limit
                        ) VALUES (?, ?, ?, ?, 0, 'UTC', ?, 1, ?, 30)
                    ''', (schedule_name, frequency, day_of_week, hour, json.dumps(symbols), current_time))
                    
                    print(f"✨ 新規スケジュール設定を作成しました: {schedule_name}")
                
                conn.commit()
            
            # 設定の動作確認
            config = self.schedule_manager.get_schedule_config(schedule_name)
            if config:
                print(f"🔍 設定確認:")
                print(f"   スケジュール名: {config.schedule_name}")
                print(f"   実行頻度: {config.frequency}")
                print(f"   対象銘柄数: {len(config.symbols)}")
                print(f"   有効状態: {'✅' if config.enabled else '❌'}")
                return True
            else:
                print("❌ 設定確認に失敗しました")
                return False
                
        except Exception as e:
            print(f"❌ スケジュール設定エラー: {e}")
            return False

def main():
    """テスト実行"""
    print("🕐 定期分析システムテスト")
    print("=" * 50)
    
    analyzer = ScheduledAnalyzer()
    
    # 状態確認
    status = analyzer.get_schedule_status()
    print(f"📊 アクティブスケジュール: {status['enabled_schedules']}")
    
    # エラーサマリー確認
    error_summary = analyzer.get_error_summary(7)
    print(f"📊 エラーサマリー（過去7日）:")
    print(f"   総エラー数: {error_summary['recovery_statistics']['total_errors']}")
    print(f"   回復成功率: {error_summary['recovery_statistics']['recovery_rate']:.1f}%")
    
    # テスト実行（少数銘柄で）
    # result = analyzer.run_scheduled_analysis('fred_weekly')
    # print(f"\\n✅ 実行完了: 成功{result['total_success']}, 失敗{result['total_failed']}")

if __name__ == "__main__":
    main()