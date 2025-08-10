#!/usr/bin/env python3
"""
フィッティング失敗追跡システム
- データ取得成功・フィッティング失敗のケースを記録
- 重複解析防止機能
- 失敗理由の詳細追跡
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

class FittingFailureTracker:
    """フィッティング失敗追跡クラス"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースパス（未指定時は自動設定）
        """
        if db_path is None:
            # プロジェクトルートからの相対パス
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "results" / "analysis_results.db"
        
        self.db_path = str(db_path)
        self._init_failure_tables()
    
    def _init_failure_tables(self):
        """失敗追跡テーブルの初期化"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. フィッティング失敗記録テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fitting_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            analysis_basis_date DATE NOT NULL,
            analysis_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            -- データ取得情報
            data_source TEXT NOT NULL,
            data_period_start DATE,
            data_period_end DATE,
            data_points INTEGER,
            data_retrieval_success BOOLEAN NOT NULL DEFAULT TRUE,
            
            -- フィッティング失敗情報
            failure_stage TEXT NOT NULL,  -- 'data_retrieval', 'data_processing', 'fitting_execution', 'quality_check'
            failure_category TEXT NOT NULL,  -- 'api_failure', 'rate_limit', 'insufficient_data', 'optimization_failed', 'quality_rejected'
            failure_reason TEXT NOT NULL,
            failure_details TEXT,  -- JSON形式の詳細情報
            failure_metadata TEXT,  -- JSON形式の失敗種別メタデータ
            
            -- メタデータ
            schedule_name TEXT,
            backfill_batch_id TEXT,
            retry_count INTEGER DEFAULT 0,
            last_retry_date TIMESTAMP,
            
            -- 制約
            UNIQUE(symbol, analysis_basis_date, schedule_name)
        )""")
        
        # 2. 解析状態追跡テーブル（重複防止用）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            analysis_basis_date DATE NOT NULL,
            schedule_name TEXT,
            
            -- 状態情報
            status TEXT NOT NULL,  -- 'pending', 'in_progress', 'success', 'failed', 'skipped'
            data_available BOOLEAN DEFAULT FALSE,
            fitting_attempted BOOLEAN DEFAULT FALSE,
            fitting_successful BOOLEAN DEFAULT FALSE,
            
            -- 時間記録
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 結果参照
            analysis_result_id INTEGER,  -- analysis_resultsテーブルのID
            failure_record_id INTEGER,   -- fitting_failuresテーブルのID
            
            -- 制約
            UNIQUE(symbol, analysis_basis_date, schedule_name),
            
            -- 外部キー
            FOREIGN KEY(analysis_result_id) REFERENCES analysis_results(id),
            FOREIGN KEY(failure_record_id) REFERENCES fitting_failures(id)
        )""")
        
        # 3. インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fitting_failures_symbol_date ON fitting_failures(symbol, analysis_basis_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fitting_failures_schedule ON fitting_failures(schedule_name, analysis_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_status_symbol_date ON analysis_status(symbol, analysis_basis_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_status_schedule ON analysis_status(schedule_name)")
        
        conn.commit()
        conn.close()
        
        print("✅ フィッティング失敗追跡テーブル初期化完了")
    
    def check_analysis_needed(self, symbol: str, analysis_basis_date: str, 
                            schedule_name: str = None) -> Dict[str, Any]:
        """
        解析が必要かチェック（重複防止）
        
        Args:
            symbol: 銘柄シンボル
            analysis_basis_date: 分析基準日
            schedule_name: スケジュール名
            
        Returns:
            dict: 解析必要性と理由
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 既存の解析状態確認
            query = """
            SELECT status, data_available, fitting_attempted, fitting_successful,
                   analysis_result_id, failure_record_id, completed_at
            FROM analysis_status
            WHERE symbol = ? AND analysis_basis_date = ? 
            AND (schedule_name = ? OR schedule_name IS NULL)
            ORDER BY updated_at DESC LIMIT 1
            """
            
            cursor.execute(query, (symbol, analysis_basis_date, schedule_name))
            result = cursor.fetchone()
            
            if not result:
                # 未解析
                return {
                    'needed': True,
                    'reason': 'no_previous_analysis',
                    'action': 'full_analysis',
                    'status': None
                }
            
            status, data_available, fitting_attempted, fitting_successful, result_id, failure_id, completed_at = result
            
            # 成功済みの場合
            if status == 'success' and fitting_successful and result_id:
                return {
                    'needed': False,
                    'reason': 'already_successful',
                    'action': 'skip',
                    'status': status,
                    'result_id': result_id
                }
            
            # データ取得済み・フィッティング失敗の場合
            if status == 'failed' and data_available and failure_id:
                # 失敗詳細確認
                cursor.execute("SELECT failure_category, retry_count FROM fitting_failures WHERE id = ?", 
                             (failure_id,))
                failure_info = cursor.fetchone()
                
                if failure_info:
                    failure_category, retry_count = failure_info
                    
                    # リトライ可能かチェック
                    if retry_count < 3 and failure_category not in ['insufficient_data', 'invalid_symbol']:
                        return {
                            'needed': True,
                            'reason': 'retry_fitting',
                            'action': 'retry_fitting_only',
                            'status': status,
                            'retry_count': retry_count
                        }
                    else:
                        return {
                            'needed': False,
                            'reason': 'permanent_failure',
                            'action': 'skip',
                            'status': status,
                            'failure_category': failure_category
                        }
            
            # 進行中の場合
            if status == 'in_progress':
                # 24時間以上経過していれば再実行
                if completed_at:
                    last_update = datetime.fromisoformat(completed_at)
                    if datetime.now() - last_update > timedelta(hours=24):
                        return {
                            'needed': True,
                            'reason': 'stale_in_progress',
                            'action': 'full_analysis',
                            'status': status
                        }
                
                return {
                    'needed': False,
                    'reason': 'currently_in_progress',
                    'action': 'skip',
                    'status': status
                }
            
            # その他の場合は再解析
            return {
                'needed': True,
                'reason': 'incomplete_previous_analysis',
                'action': 'full_analysis',
                'status': status
            }
            
        finally:
            conn.close()
    
    def start_analysis(self, symbol: str, analysis_basis_date: str, 
                      schedule_name: str = None) -> int:
        """
        解析開始を記録
        
        Args:
            symbol: 銘柄シンボル
            analysis_basis_date: 分析基準日
            schedule_name: スケジュール名
            
        Returns:
            int: analysis_status レコードID
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 既存レコードの更新または新規作成
            cursor.execute("""
            INSERT OR REPLACE INTO analysis_status 
            (symbol, analysis_basis_date, schedule_name, status, started_at, updated_at)
            VALUES (?, ?, ?, 'in_progress', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (symbol, analysis_basis_date, schedule_name))
            
            status_id = cursor.lastrowid
            conn.commit()
            
            print(f"🔄 解析開始記録: {symbol} ({analysis_basis_date}) - ID: {status_id}")
            return status_id
            
        finally:
            conn.close()
    
    def record_data_retrieval(self, status_id: int, data_source: str, 
                            data_points: int, period_start: str, period_end: str):
        """
        データ取得成功を記録
        
        Args:
            status_id: analysis_status レコードID
            data_source: データソース
            data_points: データポイント数
            period_start: データ期間開始日
            period_end: データ期間終了日
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE analysis_status 
            SET data_available = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (status_id,))
            
            conn.commit()
            print(f"📊 データ取得成功記録: ID {status_id} - {data_points}日分")
            
        finally:
            conn.close()
    
    def record_success(self, status_id: int, analysis_result_id: int):
        """
        フィッティング成功を記録
        
        Args:
            status_id: analysis_status レコードID
            analysis_result_id: analysis_results テーブルのID
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE analysis_status 
            SET status = 'success', 
                fitting_attempted = TRUE,
                fitting_successful = TRUE,
                analysis_result_id = ?,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (analysis_result_id, status_id))
            
            conn.commit()
            print(f"✅ フィッティング成功記録: ID {status_id} → 結果ID {analysis_result_id}")
            
        finally:
            conn.close()
    
    def record_failure(self, status_id: int, symbol: str, analysis_basis_date: str,
                      data_source: str, failure_stage: str, failure_category: str,
                      failure_reason: str, failure_details: Dict[str, Any] = None,
                      failure_metadata: Dict[str, Any] = None,
                      data_info: Dict[str, Any] = None, schedule_name: str = None,
                      backfill_batch_id: str = None) -> int:
        """
        フィッティング失敗を記録
        
        Args:
            status_id: analysis_status レコードID
            symbol: 銘柄シンボル
            analysis_basis_date: 分析基準日
            data_source: データソース
            failure_stage: 失敗段階 ('data_retrieval', 'data_processing', 'fitting_execution', 'quality_check')
            failure_category: 失敗カテゴリ ('api_failure', 'rate_limit', 'insufficient_data', 'optimization_failed', 'quality_rejected')
            failure_reason: 失敗理由
            failure_details: 失敗詳細
            failure_metadata: 失敗種別メタデータ
            data_info: データ情報
            schedule_name: スケジュール名
            backfill_batch_id: バックフィルバッチID
            
        Returns:
            int: fitting_failures レコードID
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # データ情報のデフォルト設定
            if data_info is None:
                data_info = {}
            
            data_points = data_info.get('data_points', 0)
            period_start = data_info.get('period_start')
            period_end = data_info.get('period_end')
            data_retrieval_success = data_info.get('retrieval_success', True)
            
            # 失敗詳細をJSON化
            details_json = json.dumps(failure_details, ensure_ascii=False) if failure_details else None
            metadata_json = json.dumps(failure_metadata, ensure_ascii=False) if failure_metadata else None
            
            # 既存の失敗レコード確認（重複挿入防止）
            cursor.execute("""
            SELECT id, retry_count FROM fitting_failures 
            WHERE symbol = ? AND analysis_basis_date = ? AND schedule_name = ?
            """, (symbol, analysis_basis_date, schedule_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # 既存レコードの更新（リトライカウント増加）
                existing_id, retry_count = existing
                cursor.execute("""
                UPDATE fitting_failures 
                SET failure_stage = ?, failure_category = ?, failure_reason = ?,
                    failure_details = ?, failure_metadata = ?, retry_count = ?, 
                    last_retry_date = CURRENT_TIMESTAMP,
                    analysis_date = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (failure_stage, failure_category, failure_reason, 
                     details_json, metadata_json, retry_count + 1, existing_id))
                
                failure_id = existing_id
                print(f"🔄 失敗レコード更新: {symbol} - リトライ{retry_count + 1}回目")
            else:
                # 新規失敗レコード作成
                cursor.execute("""
                INSERT INTO fitting_failures 
                (symbol, analysis_basis_date, data_source, data_period_start, data_period_end,
                 data_points, data_retrieval_success, failure_stage, failure_category,
                 failure_reason, failure_details, failure_metadata, schedule_name, backfill_batch_id, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (symbol, analysis_basis_date, data_source, period_start, period_end,
                     data_points, data_retrieval_success, failure_stage, failure_category,
                     failure_reason, details_json, metadata_json, schedule_name, backfill_batch_id))
                
                failure_id = cursor.lastrowid
                print(f"❌ 失敗レコード新規作成: {symbol} ({failure_category})")
            
            # analysis_status テーブル更新
            cursor.execute("""
            UPDATE analysis_status 
            SET status = 'failed',
                fitting_attempted = TRUE,
                fitting_successful = FALSE,
                failure_record_id = ?,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (failure_id, status_id))
            
            conn.commit()
            return failure_id
            
        finally:
            conn.close()
    
    def get_failure_statistics(self, schedule_name: str = None) -> Dict[str, Any]:
        """
        失敗統計の取得
        
        Args:
            schedule_name: 特定スケジュールの統計（未指定時は全体）
            
        Returns:
            dict: 失敗統計情報
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 基本統計
            where_clause = "WHERE schedule_name = ?" if schedule_name else ""
            params = [schedule_name] if schedule_name else []
            
            # 失敗カテゴリ別統計
            cursor.execute(f"""
            SELECT failure_category, COUNT(*) as count
            FROM fitting_failures {where_clause}
            GROUP BY failure_category
            ORDER BY count DESC
            """, params)
            
            category_stats = dict(cursor.fetchall())
            
            # 失敗段階別統計
            cursor.execute(f"""
            SELECT failure_stage, COUNT(*) as count
            FROM fitting_failures {where_clause}
            GROUP BY failure_stage
            ORDER BY count DESC
            """, params)
            
            stage_stats = dict(cursor.fetchall())
            
            # 最近の失敗（7日以内）
            cursor.execute(f"""
            SELECT COUNT(*) FROM fitting_failures 
            {where_clause} {"AND" if where_clause else "WHERE"} 
            analysis_date >= date('now', '-7 days')
            """, params)
            
            recent_failures = cursor.fetchone()[0]
            
            # 成功・失敗・進行中の統計
            cursor.execute(f"""
            SELECT status, COUNT(*) as count
            FROM analysis_status {where_clause}
            GROUP BY status
            ORDER BY count DESC
            """, params)
            
            status_stats = dict(cursor.fetchall())
            
            return {
                'failure_by_category': category_stats,
                'failure_by_stage': stage_stats,
                'recent_failures_7days': recent_failures,
                'analysis_status': status_stats,
                'total_failures': sum(category_stats.values()),
                'total_analyses': sum(status_stats.values())
            }
            
        finally:
            conn.close()
    
    def get_retry_candidates(self, max_retry_count: int = 2) -> List[Dict[str, Any]]:
        """
        リトライ候補の取得
        
        Args:
            max_retry_count: 最大リトライ回数
            
        Returns:
            list: リトライ候補リスト
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT f.symbol, f.analysis_basis_date, f.schedule_name,
                   f.failure_category, f.retry_count, f.failure_reason,
                   f.data_points, f.last_retry_date
            FROM fitting_failures f
            JOIN analysis_status s ON (
                s.symbol = f.symbol AND 
                s.analysis_basis_date = f.analysis_basis_date AND
                s.schedule_name = f.schedule_name
            )
            WHERE f.retry_count < ? 
            AND f.failure_category NOT IN ('insufficient_data', 'invalid_symbol')
            AND s.status = 'failed'
            AND (f.last_retry_date IS NULL OR f.last_retry_date < date('now', '-1 day'))
            ORDER BY f.analysis_basis_date DESC, f.retry_count ASC
            """
            
            cursor.execute(query, (max_retry_count,))
            results = cursor.fetchall()
            
            candidates = []
            for row in results:
                candidates.append({
                    'symbol': row[0],
                    'analysis_basis_date': row[1],
                    'schedule_name': row[2],
                    'failure_category': row[3],
                    'retry_count': row[4],
                    'failure_reason': row[5],
                    'data_points': row[6],
                    'last_retry_date': row[7]
                })
            
            return candidates
            
        finally:
            conn.close()

# 使用例とテスト
def test_failure_tracker():
    """失敗追跡システムのテスト"""
    
    print("🧪 フィッティング失敗追跡システムテスト")
    print("=" * 50)
    
    tracker = FittingFailureTracker()
    
    # テスト用データ
    test_symbol = "TEST_BTC"
    test_date = "2025-08-10"
    test_schedule = "test_schedule"
    
    print(f"📋 テスト対象: {test_symbol} ({test_date})")
    
    # 1. 解析必要性チェック
    check_result = tracker.check_analysis_needed(test_symbol, test_date, test_schedule)
    print(f"🔍 解析必要性: {check_result}")
    
    # 2. 解析開始
    if check_result['needed']:
        status_id = tracker.start_analysis(test_symbol, test_date, test_schedule)
        
        # 3. データ取得成功記録
        tracker.record_data_retrieval(status_id, "coingecko", 365, "2024-08-10", "2025-08-10")
        
        # 4. 失敗記録
        failure_details = {
            "error": "Optimization failed to converge",
            "attempted_methods": ["SLSQP", "L-BFGS-B"],
            "parameter_bounds": {"tc": [1.0, 3.0], "beta": [0.1, 1.0]}
        }
        
        failure_id = tracker.record_failure(
            status_id, test_symbol, test_date, "coingecko",
            "fitting_execution", "optimization_failed",
            "scipy optimization did not converge after 100 iterations",
            failure_details,
            {"data_points": 365, "period_start": "2024-08-10", "period_end": "2025-08-10"},
            test_schedule
        )
        
        print(f"📊 失敗記録ID: {failure_id}")
        
        # 5. 再度解析必要性チェック
        recheck_result = tracker.check_analysis_needed(test_symbol, test_date, test_schedule)
        print(f"🔍 再チェック結果: {recheck_result}")
    
    # 6. 統計取得
    stats = tracker.get_failure_statistics(test_schedule)
    print(f"📊 失敗統計: {stats}")
    
    # 7. リトライ候補取得
    retry_candidates = tracker.get_retry_candidates()
    print(f"🔄 リトライ候補数: {len(retry_candidates)}")

if __name__ == "__main__":
    test_failure_tracker()