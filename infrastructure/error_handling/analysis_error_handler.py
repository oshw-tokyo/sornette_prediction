#!/usr/bin/env python3
"""
分析エラーハンドリングシステム
定期分析における各種エラーの検出・回復・ログ記録を管理
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import traceback
import json
from pathlib import Path

class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"           # 一時的なエラー、自動回復可能
    MEDIUM = "medium"     # 手動確認推奨
    HIGH = "high"         # 即座の対応必要
    CRITICAL = "critical" # システム停止レベル

class ErrorCategory(Enum):
    """エラーカテゴリ"""
    API_ERROR = "api_error"           # API接続・制限エラー
    DATA_ERROR = "data_error"         # データ品質・欠損エラー
    ANALYSIS_ERROR = "analysis_error" # LPPL分析計算エラー
    DATABASE_ERROR = "database_error" # DB接続・保存エラー
    SYSTEM_ERROR = "system_error"     # システム・環境エラー

@dataclass
class AnalysisError:
    """分析エラー情報"""
    id: Optional[int]
    timestamp: datetime
    symbol: str
    schedule_name: str
    basis_date: str
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    error_message: str
    error_details: str
    stack_trace: Optional[str]
    recovery_attempted: bool
    recovery_successful: bool
    retry_count: int

class AnalysisErrorHandler:
    """分析エラーハンドリングシステム"""
    
    def __init__(self, db_path: str = "results/analysis_results.db", 
                 log_path: str = "results/analysis_errors.log"):
        """
        初期化
        
        Args:
            db_path: データベースパス
            log_path: ログファイルパス
        """
        self.db_path = db_path
        self.log_path = log_path
        
        # ログ設定
        self._setup_logging()
        
        # エラーテーブル作成
        self._init_error_table()
        
        # リトライ設定
        self.max_retries = {
            ErrorCategory.API_ERROR: 3,
            ErrorCategory.DATA_ERROR: 1,
            ErrorCategory.ANALYSIS_ERROR: 2,
            ErrorCategory.DATABASE_ERROR: 2,
            ErrorCategory.SYSTEM_ERROR: 1
        }
        
        # リトライ待機時間（秒）
        self.retry_delays = {
            ErrorCategory.API_ERROR: [10, 30, 60],
            ErrorCategory.DATA_ERROR: [5],
            ErrorCategory.ANALYSIS_ERROR: [5, 15],
            ErrorCategory.DATABASE_ERROR: [5, 10],
            ErrorCategory.SYSTEM_ERROR: [10]
        }
    
    def _setup_logging(self):
        """ログ設定の初期化"""
        # ログディレクトリ作成
        log_dir = Path(self.log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ログフォーマット設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _init_error_table(self):
        """エラーテーブルの作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    schedule_name TEXT,
                    basis_date DATE,
                    error_category TEXT NOT NULL,
                    error_severity TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    error_details TEXT,
                    stack_trace TEXT,
                    recovery_attempted BOOLEAN DEFAULT 0,
                    recovery_successful BOOLEAN DEFAULT 0,
                    retry_count INTEGER DEFAULT 0
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_timestamp ON analysis_errors (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_symbol ON analysis_errors (symbol, basis_date)')
            
            conn.commit()
    
    def log_error(self, symbol: str, error: Exception, 
                  schedule_name: str = None, basis_date: str = None,
                  category: ErrorCategory = None, severity: ErrorSeverity = None) -> int:
        """
        エラーのログ記録
        
        Args:
            symbol: 銘柄
            error: エラーオブジェクト
            schedule_name: スケジュール名
            basis_date: 分析基準日
            category: エラーカテゴリ（自動推定可能）
            severity: エラー重要度（自動推定可能）
            
        Returns:
            int: エラーレコードID
        """
        # エラーカテゴリの自動推定
        if not category:
            category = self._categorize_error(error)
        
        # エラー重要度の自動推定
        if not severity:
            severity = self._assess_severity(error, category)
        
        # エラー詳細の取得
        error_details = self._extract_error_details(error)
        stack_trace = traceback.format_exc()
        
        # データベース保存
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analysis_errors (
                    symbol, schedule_name, basis_date, error_category, error_severity,
                    error_message, error_details, stack_trace
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, schedule_name, basis_date, category.value, severity.value,
                str(error), error_details, stack_trace
            ))
            
            error_id = cursor.lastrowid
            conn.commit()
        
        # ログ出力
        self.logger.error(f"[{category.value.upper()}] {symbol}: {error}")
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.critical(f"HIGH/CRITICAL ERROR: {symbol} - {error}")
        
        return error_id
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """エラーの自動分類"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # API関連エラー
        if any(keyword in error_str for keyword in ['api', 'request', 'timeout', 'connection', 'rate limit']):
            return ErrorCategory.API_ERROR
        
        # データベース関連エラー
        if any(keyword in error_str for keyword in ['database', 'sqlite', 'sql', 'table']):
            return ErrorCategory.DATABASE_ERROR
        
        # データ関連エラー  
        if any(keyword in error_str for keyword in ['data', 'empty', 'nan', 'missing', 'invalid']):
            return ErrorCategory.DATA_ERROR
        
        # 分析関連エラー
        if any(keyword in error_str for keyword in ['fitting', 'convergence', 'optimization', 'lppl']):
            return ErrorCategory.ANALYSIS_ERROR
        
        # その他はシステムエラー
        return ErrorCategory.SYSTEM_ERROR
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """エラー重要度の自動評価"""
        error_str = str(error).lower()
        
        # CRITICAL: システム停止レベル
        if any(keyword in error_str for keyword in ['critical', 'fatal', 'permission denied', 'disk full']):
            return ErrorSeverity.CRITICAL
        
        # HIGH: 即座の対応必要
        if category == ErrorCategory.DATABASE_ERROR:
            return ErrorSeverity.HIGH
        
        if any(keyword in error_str for keyword in ['authentication', 'unauthorized', 'forbidden']):
            return ErrorSeverity.HIGH
        
        # MEDIUM: 手動確認推奨
        if category == ErrorCategory.API_ERROR:
            return ErrorSeverity.MEDIUM
        
        # LOW: 一時的・回復可能
        return ErrorSeverity.LOW
    
    def _extract_error_details(self, error: Exception) -> str:
        """エラー詳細情報の抽出"""
        details = {
            'error_type': type(error).__name__,
            'error_args': str(error.args) if error.args else None,
        }
        
        # 特定のエラータイプの詳細情報
        if hasattr(error, 'response'):
            details['http_status'] = getattr(error.response, 'status_code', None)
            details['response_text'] = getattr(error.response, 'text', None)[:500]  # 最初の500文字
        
        return json.dumps(details, ensure_ascii=False)
    
    def attempt_recovery(self, symbol: str, error_id: int, 
                        recovery_function, *args, **kwargs) -> Tuple[bool, Any]:
        """
        エラー回復の試行
        
        Args:
            symbol: 銘柄
            error_id: エラーレコードID
            recovery_function: 回復処理関数
            *args, **kwargs: 回復処理関数の引数
            
        Returns:
            Tuple[bool, Any]: (回復成功, 回復結果)
        """
        try:
            # 回復処理実行
            result = recovery_function(*args, **kwargs)
            
            # 成功時の記録更新
            self._update_recovery_status(error_id, attempted=True, successful=True)
            self.logger.info(f"Recovery successful for {symbol} (error_id: {error_id})")
            
            return True, result
            
        except Exception as recovery_error:
            # 失敗時の記録更新
            self._update_recovery_status(error_id, attempted=True, successful=False)
            self.logger.error(f"Recovery failed for {symbol} (error_id: {error_id}): {recovery_error}")
            
            return False, None
    
    def _update_recovery_status(self, error_id: int, attempted: bool, successful: bool = False):
        """回復試行状況の更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE analysis_errors 
                SET recovery_attempted = ?, recovery_successful = ?
                WHERE id = ?
            ''', (attempted, successful, error_id))
            conn.commit()
    
    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """エラーサマリーの取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 期間内のエラー統計
            cursor.execute('''
                SELECT error_category, error_severity, COUNT(*) as count
                FROM analysis_errors 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY error_category, error_severity
                ORDER BY count DESC
            '''.format(days))
            
            error_stats = cursor.fetchall()
            
            # 回復率統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_errors,
                    SUM(recovery_attempted) as attempted_recoveries,
                    SUM(recovery_successful) as successful_recoveries
                FROM analysis_errors 
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days))
            
            recovery_stats = cursor.fetchone()
        
        return {
            'period_days': days,
            'error_statistics': error_stats,
            'recovery_statistics': {
                'total_errors': recovery_stats[0] or 0,
                'attempted_recoveries': recovery_stats[1] or 0,
                'successful_recoveries': recovery_stats[2] or 0,
                'recovery_rate': ((recovery_stats[2] or 0) / max(1, recovery_stats[1] or 1)) * 100
            }
        }
    
    def cleanup_old_errors(self, days: int = 90):
        """古いエラーレコードの削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM analysis_errors 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        self.logger.info(f"Cleaned up {deleted_count} old error records (older than {days} days)")
        return deleted_count

def main():
    """テスト実行"""
    print("🛡️ エラーハンドリングシステムテスト")
    print("=" * 50)
    
    handler = AnalysisErrorHandler()
    
    # テストエラーの記録
    try:
        raise ValueError("テストエラー: データが見つかりません")
    except Exception as e:
        error_id = handler.log_error("TEST_SYMBOL", e, "test_schedule", "2025-01-01")
        print(f"✅ エラー記録完了: ID={error_id}")
    
    # エラーサマリーの表示
    summary = handler.get_error_summary(7)
    print(f"📊 エラーサマリー（過去7日）:")
    print(f"   総エラー数: {summary['recovery_statistics']['total_errors']}")
    print(f"   回復試行: {summary['recovery_statistics']['attempted_recoveries']}")
    print(f"   回復成功: {summary['recovery_statistics']['successful_recoveries']}")

if __name__ == "__main__":
    main()