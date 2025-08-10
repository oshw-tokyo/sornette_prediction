#!/usr/bin/env python3
"""
解析重複防止システム
- 同一銘柄・同一基準日での重複解析防止
- 失敗追跡システムとの統合
- backfillbatch実行時の効率化
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

# プロジェクトルートのパスを追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.fitting_failure_tracker import FittingFailureTracker

class AnalysisDeduplicationSystem:
    """解析重複防止システム"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.failure_tracker = FittingFailureTracker(db_path)
        self.db_path = self.failure_tracker.db_path
    
    def filter_analysis_candidates(self, symbol_date_pairs: List[Tuple[str, str]], 
                                 schedule_name: str = None,
                                 force_retry: bool = False,
                                 max_retry_count: int = 2) -> Dict[str, List[Tuple[str, str]]]:
        """
        解析候補のフィルタリング（重複排除）
        
        Args:
            symbol_date_pairs: [(symbol, analysis_basis_date), ...] のリスト
            schedule_name: スケジュール名
            force_retry: 失敗したケースも強制再実行
            max_retry_count: 最大リトライ回数
            
        Returns:
            dict: フィルタリング結果
                - 'to_analyze': 解析が必要な銘柄・日付ペア
                - 'to_skip': スキップする銘柄・日付ペア
                - 'to_retry': リトライする銘柄・日付ペア
                - 'already_successful': 既に成功済みの銘柄・日付ペア
        """
        
        print("🔍 解析候補フィルタリング開始")
        print("=" * 50)
        
        results = {
            'to_analyze': [],      # 新規解析が必要
            'to_skip': [],         # スキップ（成功済み・永続的失敗）
            'to_retry': [],        # リトライ可能な失敗
            'already_successful': [] # 既に成功済み
        }
        
        print(f"📋 入力候補数: {len(symbol_date_pairs)}")
        print(f"📋 スケジュール: {schedule_name or '未指定'}")
        print(f"📋 強制リトライ: {'有効' if force_retry else '無効'}")
        
        for i, (symbol, analysis_date) in enumerate(symbol_date_pairs, 1):
            print(f"\\n{i:3d}. {symbol:10} ({analysis_date})", end=" ")
            
            # 解析必要性チェック
            check_result = self.failure_tracker.check_analysis_needed(
                symbol, analysis_date, schedule_name
            )
            
            action = check_result['action']
            reason = check_result['reason']
            status = check_result.get('status')
            
            if action == 'full_analysis':
                results['to_analyze'].append((symbol, analysis_date))
                print(f"→ 🆕 解析必要 ({reason})")
                
            elif action == 'retry_fitting_only':
                if force_retry or check_result.get('retry_count', 0) < max_retry_count:
                    results['to_retry'].append((symbol, analysis_date))
                    retry_count = check_result.get('retry_count', 0)
                    print(f"→ 🔄 リトライ ({retry_count}回目)")
                else:
                    results['to_skip'].append((symbol, analysis_date))
                    print(f"→ ⏭️ スキップ (リトライ上限)")
                    
            elif action == 'skip':
                if reason == 'already_successful':
                    results['already_successful'].append((symbol, analysis_date))
                    print(f"→ ✅ 成功済み")
                else:
                    results['to_skip'].append((symbol, analysis_date))
                    print(f"→ ⏭️ スキップ ({reason})")
        
        # サマリー表示
        print(f"\\n" + "=" * 50)
        print("🔍 フィルタリング結果サマリー")
        print("=" * 50)
        
        print(f"🆕 新規解析: {len(results['to_analyze'])}件")
        print(f"🔄 リトライ: {len(results['to_retry'])}件")
        print(f"✅ 成功済み: {len(results['already_successful'])}件")
        print(f"⏭️ スキップ: {len(results['to_skip'])}件")
        
        total_work = len(results['to_analyze']) + len(results['to_retry'])
        total_input = len(symbol_date_pairs)
        efficiency = (total_input - total_work) / total_input * 100 if total_input > 0 else 0
        
        print(f"\\n📊 効率化:")
        print(f"  実行必要: {total_work}/{total_input} ({total_work/total_input*100:.1f}%)")
        print(f"  重複排除: {efficiency:.1f}%")
        
        return results
    
    def generate_backfill_execution_plan(self, symbols: List[str], 
                                       start_date: str = "2024-01-01",
                                       schedule_name: str = None,
                                       force_retry: bool = False) -> Dict[str, Any]:
        """
        backfillbatch実行計画の生成
        
        Args:
            symbols: 対象銘柄リスト
            start_date: 開始日
            schedule_name: スケジュール名
            force_retry: 強制リトライ
            
        Returns:
            dict: 実行計画
        """
        
        print("🚀 Backfillbatch実行計画生成")
        print("=" * 50)
        
        # 週次基準日の生成（金曜日基準）
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.now()
        
        # 最初の金曜日を見つける
        days_to_friday = (4 - start_dt.weekday()) % 7  # 4 = Friday (0=Monday)
        first_friday = start_dt + timedelta(days=days_to_friday)
        
        # 週次基準日リストの生成
        basis_dates = []
        current_friday = first_friday
        while current_friday <= end_dt:
            basis_dates.append(current_friday.strftime('%Y-%m-%d'))
            current_friday += timedelta(weeks=1)
        
        print(f"📅 期間: {start_date} ～ {end_dt.strftime('%Y-%m-%d')}")
        print(f"📅 週次基準日: {len(basis_dates)}週分")
        print(f"📋 対象銘柄: {len(symbols)}銘柄")
        
        # 銘柄×基準日のすべての組み合わせ
        all_combinations = []
        for symbol in symbols:
            for basis_date in basis_dates:
                all_combinations.append((symbol, basis_date))
        
        print(f"📋 総組み合わせ数: {len(all_combinations)}件")
        
        # 重複排除フィルタリング
        filtered_results = self.filter_analysis_candidates(
            all_combinations, schedule_name, force_retry
        )
        
        # 実行計画の構築
        execution_plan = {
            'metadata': {
                'plan_generated_at': datetime.now().isoformat(),
                'target_symbols': symbols,
                'start_date': start_date,
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'total_weeks': len(basis_dates),
                'schedule_name': schedule_name,
                'force_retry': force_retry
            },
            'statistics': {
                'total_combinations': len(all_combinations),
                'new_analyses': len(filtered_results['to_analyze']),
                'retries': len(filtered_results['to_retry']),
                'already_successful': len(filtered_results['already_successful']),
                'skipped': len(filtered_results['to_skip']),
                'efficiency_percent': (len(all_combinations) - len(filtered_results['to_analyze']) - len(filtered_results['to_retry'])) / len(all_combinations) * 100 if all_combinations else 0
            },
            'execution_batches': {
                'new_analyses': filtered_results['to_analyze'],
                'retries': filtered_results['to_retry']
            },
            'skip_details': {
                'already_successful': filtered_results['already_successful'],
                'permanent_skips': filtered_results['to_skip']
            }
        }
        
        # 実行優先度付け（主要銘柄優先、最新データ優先）
        major_symbols = {'BTC', 'ETH', 'SP500', 'NASDAQ', 'USDT', 'USDC'}
        
        def prioritize_analyses(analyses):
            """解析リストの優先度付け"""
            priority_scores = []
            
            for symbol, date in analyses:
                score = 0
                
                # 主要銘柄ボーナス
                if symbol in major_symbols:
                    score += 100
                
                # 新しいデータほど高スコア
                date_dt = datetime.strptime(date, '%Y-%m-%d')
                days_old = (datetime.now() - date_dt).days
                score += max(0, 365 - days_old) / 365 * 50
                
                priority_scores.append((score, symbol, date))
            
            # スコア順でソート
            priority_scores.sort(reverse=True)
            return [(symbol, date) for _, symbol, date in priority_scores]
        
        execution_plan['execution_batches']['new_analyses'] = prioritize_analyses(
            filtered_results['to_analyze']
        )
        execution_plan['execution_batches']['retries'] = prioritize_analyses(
            filtered_results['to_retry']
        )
        
        return execution_plan
    
    def save_execution_plan(self, plan: Dict[str, Any], filename: str = None) -> str:
        """
        実行計画の保存
        
        Args:
            plan: 実行計画
            filename: ファイル名（未指定時は自動生成）
            
        Returns:
            str: 保存されたファイルパス
        """
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            schedule_name = plan['metadata'].get('schedule_name', 'unknown')
            filename = f"backfill_plan_{schedule_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        print(f"💾 実行計画保存: {filename}")
        return filename
    
    def generate_execution_commands(self, plan: Dict[str, Any]) -> List[str]:
        """
        実行計画からコマンドライン生成
        
        Args:
            plan: 実行計画
            
        Returns:
            list: 実行コマンドリスト
        """
        
        commands = []
        
        # 新規解析コマンド
        new_analyses = plan['execution_batches']['new_analyses']
        if new_analyses:
            # 銘柄ごとにグループ化
            symbol_groups = {}
            for symbol, date in new_analyses:
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(date)
            
            schedule_name = plan['metadata'].get('schedule_name', 'manual_backfill')
            
            for symbol, dates in symbol_groups.items():
                if len(dates) > 10:  # 多数の場合は範囲指定
                    start_date = min(dates)
                    end_date = max(dates)
                    cmd = f"python entry_points/main.py scheduled-analysis backfill --symbols {symbol} --start {start_date} --end {end_date} --schedule-name {schedule_name}"
                else:  # 少数の場合は個別指定
                    dates_str = ','.join(dates)
                    cmd = f"python entry_points/main.py scheduled-analysis backfill --symbols {symbol} --dates {dates_str} --schedule-name {schedule_name}"
                
                commands.append(cmd)
        
        # リトライコマンド
        retries = plan['execution_batches']['retries']
        if retries:
            retry_symbols = list(set([symbol for symbol, _ in retries]))
            symbols_str = ','.join(retry_symbols)
            cmd = f"python entry_points/main.py scheduled-analysis retry --symbols {symbols_str} --max-retries 3"
            commands.append(cmd)
        
        return commands

def test_deduplication_system():
    """重複排除システムのテスト"""
    
    print("🧪 解析重複防止システムテスト")
    print("=" * 60)
    
    # システム初期化
    dedup = AnalysisDeduplicationSystem()
    
    # テスト用銘柄（不足しているCoinGecko銘柄を含む）
    test_symbols = ['BTC', 'ETH', 'USDT', 'USDC', 'MATIC']
    
    print(f"📋 テスト対象銘柄: {test_symbols}")
    
    # 実行計画生成
    plan = dedup.generate_backfill_execution_plan(
        symbols=test_symbols,
        start_date="2025-07-01",
        schedule_name="missing_coingecko_test",
        force_retry=False
    )
    
    # 結果表示
    print(f"\\n📊 実行計画統計:")
    stats = plan['statistics']
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 実行コマンド生成
    commands = dedup.generate_execution_commands(plan)
    print(f"\\n🚀 生成された実行コマンド:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {cmd}")
    
    # 計画保存
    plan_file = dedup.save_execution_plan(plan)
    
    return plan, plan_file

if __name__ == "__main__":
    test_deduplication_system()