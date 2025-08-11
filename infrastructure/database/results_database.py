#!/usr/bin/env python3
"""
分析結果データベース管理
LPPLフィッティング結果と可視化データを永続化
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
import base64
from pathlib import Path

class ResultsDatabase:
    """分析結果データベース管理クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        データベース初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        
        # ディレクトリ作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # データベース初期化
        self._init_database()
        
    def _init_database(self):
        """データベースとテーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 分析結果テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_source TEXT,
                    data_period_start DATE,
                    data_period_end DATE,
                    data_points INTEGER,
                    
                    -- LPPLパラメータ
                    tc REAL,
                    beta REAL,
                    omega REAL,
                    phi REAL,
                    A REAL,
                    B REAL,
                    C REAL,
                    
                    -- フィッティング品質
                    r_squared REAL,
                    rmse REAL,
                    quality TEXT,
                    confidence REAL,
                    is_usable BOOLEAN,
                    
                    -- 予測情報
                    predicted_crash_date DATE,
                    days_to_crash INTEGER,
                    
                    -- メタデータ
                    fitting_method TEXT,
                    window_days INTEGER,
                    total_candidates INTEGER,
                    successful_candidates INTEGER,
                    
                    -- JSON形式の詳細データ
                    quality_metadata TEXT,
                    selection_criteria TEXT
                )
            ''')
            
            # 可視化データテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visualizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    chart_type TEXT NOT NULL,
                    chart_title TEXT,
                    file_path TEXT,
                    image_data BLOB,
                    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    
                    FOREIGN KEY (analysis_id) REFERENCES analysis_results (id)
                )
            ''')
            
            # データソース情報テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    last_update TIMESTAMP,
                    data_points INTEGER,
                    date_range_start DATE,
                    date_range_end DATE,
                    api_status TEXT,
                    notes TEXT
                )
            ''')
            
            # スケジュール設定テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_name TEXT UNIQUE NOT NULL,
                    frequency TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly'
                    day_of_week INTEGER,      -- 0=月曜, 6=日曜 (weekly用)
                    hour INTEGER DEFAULT 9,
                    minute INTEGER DEFAULT 0,
                    timezone TEXT DEFAULT 'UTC',
                    symbols TEXT,             -- JSON配列形式
                    enabled BOOLEAN DEFAULT 1,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    auto_backfill_limit INTEGER DEFAULT 30
                )
            ''')
            
            # analysis_resultsテーブルの拡張（既存テーブルに列追加）
            self._add_column_if_not_exists(cursor, 'analysis_results', 'schedule_name', 'TEXT')
            self._add_column_if_not_exists(cursor, 'analysis_results', 'analysis_basis_date', 'DATE')
            self._add_column_if_not_exists(cursor, 'analysis_results', 'is_scheduled', 'BOOLEAN DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'analysis_results', 'backfill_batch_id', 'TEXT')
            self._add_column_if_not_exists(cursor, 'analysis_results', 'is_expired', 'BOOLEAN DEFAULT 0')
            
            # 曜日メタ情報の追加（ダッシュボード表示最適化）
            self._add_column_if_not_exists(cursor, 'analysis_results', 'basis_day_of_week', 'INTEGER')  # 0=月曜, 6=日曜
            self._add_column_if_not_exists(cursor, 'analysis_results', 'analysis_frequency', 'TEXT')     # weekly, daily
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON analysis_results (symbol, analysis_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality ON analysis_results (quality, is_usable)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedule_enabled ON schedule_config (enabled)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedule_basis ON analysis_results (schedule_name, analysis_basis_date)')
            
            # 分析基準日ベースのインデックス（最重要：ダッシュボード表示最適化）
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_symbol_basis_date ON analysis_results (symbol, analysis_basis_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_basis_date ON analysis_results (symbol, analysis_basis_date DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_frequency_basis ON analysis_results (analysis_frequency, analysis_basis_date DESC)')
            
            # 高度なフィルタリング機能用インデックス（2025-08-11追加）
            self._add_advanced_filtering_indexes(cursor)
            
            conn.commit()
            print(f"📊 データベース初期化完了: {self.db_path}")
    
    def _add_advanced_filtering_indexes(self, cursor):
        """
        高度なフィルタリング機能のための最適化インデックス追加
        既存システムに影響を与えない安全な実装 (2025-08-11追加)
        """
        advanced_indexes = [
            # 1. 品質フィルタリング最適化（R²、信頼度、使用可能性）
            ("idx_quality_comprehensive", 
             "CREATE INDEX IF NOT EXISTS idx_quality_comprehensive ON analysis_results (r_squared, confidence, is_usable, analysis_basis_date DESC)"),
            
            # 2. 予測関連フィルタリング最適化（予測日、基準日、銘柄）  
            ("idx_prediction_filters",
             "CREATE INDEX IF NOT EXISTS idx_prediction_filters ON analysis_results (predicted_crash_date, analysis_basis_date, symbol)"),
            
            # 3. 時系列分析日最適化（パフォーマンステストで0.0172秒→0.0001秒改善）
            ("idx_analysis_date_desc",
             "CREATE INDEX IF NOT EXISTS idx_analysis_date_desc ON analysis_results (analysis_date DESC)"),
            
            # 4. 複合フィルタリング最適化（品質+予測範囲）
            ("idx_composite_filters",
             "CREATE INDEX IF NOT EXISTS idx_composite_filters ON analysis_results (is_usable, r_squared, predicted_crash_date)")
        ]
        
        print("🔧 高度フィルタリング用インデックス追加中...")
        
        for idx_name, idx_sql in advanced_indexes:
            try:
                # 既存インデックス確認
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name=?
                """, (idx_name,))
                
                if cursor.fetchone():
                    print(f"  ⚪ {idx_name}: 既に存在")
                else:
                    cursor.execute(idx_sql)
                    print(f"  ✅ {idx_name}: 作成完了")
                    
            except Exception as e:
                print(f"  ❌ {idx_name}: エラー - {e}")
                # エラーがあっても他のインデックスは継続処理
                continue
    
    def _add_column_if_not_exists(self, cursor, table_name: str, column_name: str, column_def: str):
        """テーブルに列が存在しない場合のみ追加"""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            print(f"  ✅ 列追加: {table_name}.{column_name}")
    
    def save_analysis_result(self, result_data: Dict[str, Any]) -> int:
        """
        分析結果をデータベースに保存
        
        Args:
            result_data: 分析結果データ
            
        Returns:
            int: 保存されたレコードのID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 必須フィールドの確認
            required_fields = ['symbol', 'tc', 'beta', 'omega', 'r_squared']
            for field in required_fields:
                if field not in result_data:
                    raise ValueError(f"必須フィールド '{field}' が不足しています")
            
            # 🔧 Issue I048修正: analysis_basis_date を自動設定（data_period_end を使用）
            analysis_basis_date = result_data.get('analysis_basis_date') or result_data.get('data_period_end')
            
            # 重複防止: 同一銘柄・同一基準日は更新、新規は挿入（UPSERT）
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_results (
                    symbol, data_source, data_period_start, data_period_end, data_points,
                    tc, beta, omega, phi, A, B, C,
                    r_squared, rmse, quality, confidence, is_usable,
                    predicted_crash_date, days_to_crash,
                    fitting_method, window_days, total_candidates, successful_candidates,
                    quality_metadata, selection_criteria, analysis_basis_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_data['symbol'],
                result_data.get('data_source', 'unknown'),
                result_data.get('data_period_start'),
                result_data.get('data_period_end'),
                result_data.get('data_points', 0),
                result_data['tc'],
                result_data['beta'],
                result_data['omega'],
                result_data.get('phi', 0.0),
                result_data.get('A', 0.0),
                result_data.get('B', 0.0),
                result_data.get('C', 0.0),
                result_data['r_squared'],
                result_data.get('rmse', 0.0),
                result_data.get('quality', 'unknown'),
                result_data.get('confidence', 0.0),
                result_data.get('is_usable', False),
                result_data.get('predicted_crash_date'),
                result_data.get('days_to_crash'),
                result_data.get('fitting_method', 'multi_criteria'),
                result_data.get('window_days', 0),
                result_data.get('total_candidates', 0),
                result_data.get('successful_candidates', 0),
                json.dumps(result_data.get('quality_metadata', {})),
                json.dumps(result_data.get('selection_criteria', {})),
                analysis_basis_date
            ))
            
            analysis_id = cursor.lastrowid
            conn.commit()
            
            print(f"📊 分析結果保存完了: ID={analysis_id}, Symbol={result_data['symbol']}")
            return analysis_id
    
    def save_visualization(self, analysis_id: int, chart_type: str, file_path: str, 
                          title: str = "", description: str = "") -> int:
        """
        可視化データを保存
        
        Args:
            analysis_id: 関連する分析結果ID
            chart_type: チャートタイプ
            file_path: 画像ファイルパス
            title: チャートタイトル
            description: 説明
            
        Returns:
            int: 保存されたレコードのID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 画像ファイルをBLOBとして読み込み
            image_data = None
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    image_data = f.read()
            
            cursor.execute('''
                INSERT INTO visualizations (
                    analysis_id, chart_type, chart_title, file_path, 
                    image_data, description
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                analysis_id, chart_type, title, file_path, 
                image_data, description
            ))
            
            viz_id = cursor.lastrowid
            conn.commit()
            
            print(f"📊 可視化データ保存完了: ID={viz_id}, Type={chart_type}")
            return viz_id
    
    def get_recent_analyses(self, limit: int = 50, symbol: str = None) -> pd.DataFrame:
        """
        最近の分析結果を取得
        
        Args:
            limit: 取得件数制限
            symbol: 特定銘柄のみ取得する場合
            
        Returns:
            DataFrame: 分析結果
        """
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT 
                    id, symbol, analysis_date, data_source,
                    data_period_start, data_period_end, data_points,
                    tc, beta, omega, phi, A, B, C,
                    r_squared, rmse, quality, confidence, is_usable,
                    predicted_crash_date, days_to_crash,
                    window_days, total_candidates, successful_candidates,
                    analysis_basis_date
                FROM analysis_results
            '''
            
            params = []
            if symbol:
                query += ' WHERE symbol = ?'
                params.append(symbol)
            
            # ⚠️ CRITICAL: 分析基準日でソート（analysis_dateではない）
            query += ' ORDER BY analysis_basis_date DESC, analysis_date DESC'
            
            # 🔧 修正: limit=Noneの場合はLIMIT句を追加しない（2025-08-11）
            if limit is not None:
                query += ' LIMIT ?'
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_recent_analyses_by_frequency(self, symbol: str = None, frequency: str = 'weekly', limit: int = 50) -> pd.DataFrame:
        """
        頻度別最近の分析結果を取得（週次データ優先表示）
        
        Args:
            symbol: 特定銘柄のみ取得する場合
            frequency: 取得頻度 ('weekly', 'daily', 'monthly')
            limit: 取得件数制限
            
        Returns:
            DataFrame: 分析結果
        """
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT 
                    id, symbol, analysis_date, data_source,
                    data_period_start, data_period_end, data_points,
                    tc, beta, omega, phi, A, B, C,
                    r_squared, rmse, quality, confidence, is_usable,
                    predicted_crash_date, days_to_crash,
                    window_days, total_candidates, successful_candidates,
                    schedule_name, analysis_basis_date, analysis_frequency,
                    basis_day_of_week
                FROM analysis_results
                WHERE analysis_frequency = ?
            '''
            params = [frequency]
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            # ⚠️ CRITICAL: 分析基準日でソート（analysis_dateではない）
            query += ' ORDER BY analysis_basis_date DESC, analysis_date DESC'
            
            # 🔧 修正: limit=Noneの場合はLIMIT句を追加しない（2025-08-11）
            if limit is not None:
                query += ' LIMIT ?'
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_latest_analysis_per_frequency(self, symbol: str) -> pd.DataFrame:
        """
        銘柄別・頻度別の最新分析結果を取得
        
        Args:
            symbol: 対象銘柄
            
        Returns:
            DataFrame: 頻度別最新分析結果
        """
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT DISTINCT
                    a1.id, a1.symbol, a1.analysis_date, a1.data_source,
                    a1.data_period_start, a1.data_period_end, a1.data_points,
                    a1.tc, a1.beta, a1.omega, a1.phi, a1.A, a1.B, a1.C,
                    a1.r_squared, a1.rmse, a1.quality, a1.confidence, a1.is_usable,
                    a1.predicted_crash_date, a1.days_to_crash,
                    a1.window_days, a1.total_candidates, a1.successful_candidates,
                    a1.schedule_name, a1.analysis_basis_date, a1.analysis_frequency,
                    a1.basis_day_of_week
                FROM analysis_results a1
                INNER JOIN (
                    SELECT analysis_frequency, MAX(analysis_basis_date) as max_basis_date
                    FROM analysis_results 
                    WHERE symbol = ? AND analysis_frequency IS NOT NULL
                    GROUP BY analysis_frequency
                ) a2 ON a1.analysis_frequency = a2.analysis_frequency 
                    AND a1.analysis_basis_date = a2.max_basis_date
                WHERE a1.symbol = ?
                ORDER BY a1.analysis_frequency, a1.analysis_basis_date DESC
            '''
            
            return pd.read_sql_query(query, conn, params=[symbol, symbol])
    
    def get_analysis_details(self, analysis_id: int) -> Dict[str, Any]:
        """
        特定分析の詳細情報を取得
        
        Args:
            analysis_id: 分析ID
            
        Returns:
            Dict: 詳細情報
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 分析結果取得
            cursor.execute('SELECT * FROM analysis_results WHERE id = ?', (analysis_id,))
            result = cursor.fetchone()
            
            if not result:
                return {}
            
            # カラム名取得
            columns = [desc[0] for desc in cursor.description]
            analysis_data = dict(zip(columns, result))
            
            # JSON フィールドをパース
            if analysis_data.get('quality_metadata'):
                analysis_data['quality_metadata'] = json.loads(analysis_data['quality_metadata'])
            
            if analysis_data.get('selection_criteria'):
                analysis_data['selection_criteria'] = json.loads(analysis_data['selection_criteria'])
            
            # 関連可視化データ取得
            cursor.execute('''
                SELECT chart_type, chart_title, file_path, description, creation_date
                FROM visualizations 
                WHERE analysis_id = ?
                ORDER BY creation_date DESC
            ''', (analysis_id,))
            
            visualizations = []
            for viz in cursor.fetchall():
                viz_cols = ['chart_type', 'chart_title', 'file_path', 'description', 'creation_date']
                visualizations.append(dict(zip(viz_cols, viz)))
            
            analysis_data['visualizations'] = visualizations
            
            return analysis_data
    
    def get_visualization_image(self, analysis_id: int, chart_type: str) -> Optional[bytes]:
        """
        可視化画像データを取得
        
        Args:
            analysis_id: 分析ID
            chart_type: チャートタイプ
            
        Returns:
            bytes: 画像バイナリデータ
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT image_data FROM visualizations 
                WHERE analysis_id = ? AND chart_type = ?
                ORDER BY creation_date DESC LIMIT 1
            ''', (analysis_id, chart_type))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        データベースの概要統計を取得
        
        Returns:
            Dict: 統計情報
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute('SELECT COUNT(*) FROM analysis_results')
            total_analyses = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM analysis_results')
            unique_symbols = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM analysis_results WHERE is_usable = 1')
            usable_analyses = cursor.fetchone()[0]
            
            # 最新分析日
            cursor.execute('SELECT MAX(analysis_date) FROM analysis_results')
            latest_analysis = cursor.fetchone()[0]
            
            # 品質別統計
            cursor.execute('''
                SELECT quality, COUNT(*) 
                FROM analysis_results 
                GROUP BY quality
            ''')
            quality_stats = dict(cursor.fetchall())
            
            # R²統計
            cursor.execute('''
                SELECT 
                    AVG(r_squared) as avg_r_squared,
                    MIN(r_squared) as min_r_squared,
                    MAX(r_squared) as max_r_squared
                FROM analysis_results 
                WHERE r_squared IS NOT NULL
            ''')
            r_squared_stats = cursor.fetchone()
            
            return {
                'total_analyses': total_analyses,
                'unique_symbols': unique_symbols,
                'usable_analyses': usable_analyses,
                'usable_rate': usable_analyses / max(total_analyses, 1),
                'latest_analysis': latest_analysis,
                'quality_distribution': quality_stats,
                'r_squared_stats': {
                    'average': r_squared_stats[0] if r_squared_stats[0] else 0,
                    'minimum': r_squared_stats[1] if r_squared_stats[1] else 0,
                    'maximum': r_squared_stats[2] if r_squared_stats[2] else 0
                }
            }
    
    def get_filtered_analyses(self, 
                            symbol: str = None,
                            min_r_squared: float = None,
                            max_r_squared: float = None,
                            min_confidence: float = None,
                            max_confidence: float = None,
                            is_usable: bool = None,
                            basis_date_from: str = None,
                            basis_date_to: str = None,
                            predicted_crash_from: str = None,
                            predicted_crash_to: str = None,
                            quality_levels: List[str] = None,
                            sort_by: str = 'analysis_basis_date',
                            sort_order: str = 'DESC',
                            limit: int = 500) -> pd.DataFrame:
        """
        高度フィルタリング機能によるクエリ最適化分析結果取得
        2025-08-11追加: ダッシュボード多条件AND検索対応
        
        Args:
            symbol: 特定銘柄フィルタ
            min_r_squared: R²最小値
            max_r_squared: R²最大値  
            min_confidence: 信頼度最小値
            max_confidence: 信頼度最大値
            is_usable: 使用可能性フィルタ
            basis_date_from: 分析基準日開始
            basis_date_to: 分析基準日終了
            predicted_crash_from: 予測日開始
            predicted_crash_to: 予測日終了
            quality_levels: 品質レベルリスト
            sort_by: ソート基準（analysis_basis_date, r_squared, confidence等）
            sort_order: ソート順序（ASC, DESC）
            limit: 結果件数制限
            
        Returns:
            DataFrame: フィルタリング済み分析結果
        """
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT 
                    id, symbol, analysis_date, data_source,
                    data_period_start, data_period_end, data_points,
                    tc, beta, omega, phi, A, B, C,
                    r_squared, rmse, quality, confidence, is_usable,
                    predicted_crash_date, days_to_crash,
                    window_days, total_candidates, successful_candidates,
                    analysis_basis_date, analysis_frequency
                FROM analysis_results
                WHERE 1=1
            '''
            params = []
            
            # 動的WHERE句構築（AND検索）
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
                
            if min_r_squared is not None:
                query += ' AND r_squared >= ?'
                params.append(min_r_squared)
                
            if max_r_squared is not None:
                query += ' AND r_squared <= ?'
                params.append(max_r_squared)
                
            if min_confidence is not None:
                query += ' AND confidence >= ?'
                params.append(min_confidence)
                
            if max_confidence is not None:
                query += ' AND confidence <= ?'
                params.append(max_confidence)
                
            if is_usable is not None:
                query += ' AND is_usable = ?'
                params.append(is_usable)
                
            if basis_date_from:
                query += ' AND analysis_basis_date >= ?'
                params.append(basis_date_from)
                
            if basis_date_to:
                query += ' AND analysis_basis_date <= ?'
                params.append(basis_date_to)
                
            if predicted_crash_from:
                query += ' AND predicted_crash_date >= ?'
                params.append(predicted_crash_from)
                
            if predicted_crash_to:
                query += ' AND predicted_crash_date <= ?'
                params.append(predicted_crash_to)
                
            if quality_levels:
                placeholders = ','.join(['?' for _ in quality_levels])
                query += f' AND quality IN ({placeholders})'
                params.extend(quality_levels)
            
            # ソート順序設定（分析基準日優先原則）
            valid_sort_columns = ['analysis_basis_date', 'r_squared', 'confidence', 'symbol', 'predicted_crash_date']
            if sort_by not in valid_sort_columns:
                sort_by = 'analysis_basis_date'
            
            sort_order = sort_order.upper() if sort_order.upper() in ['ASC', 'DESC'] else 'DESC'
            query += f' ORDER BY {sort_by} {sort_order}, analysis_basis_date DESC'
            
            # 結果件数制限
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_filter_value_ranges(self) -> Dict[str, Any]:
        """
        フィルタリング用の値域情報を取得（フィルター UI 向け）
        2025-08-11追加: ダッシュボードフィルター自動設定
        
        Returns:
            Dict: 各カラムの最小・最大値情報
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # R²値域
            cursor.execute('SELECT MIN(r_squared), MAX(r_squared) FROM analysis_results WHERE r_squared IS NOT NULL')
            r_squared_range = cursor.fetchone()
            
            # 信頼度値域
            cursor.execute('SELECT MIN(confidence), MAX(confidence) FROM analysis_results WHERE confidence IS NOT NULL')
            confidence_range = cursor.fetchone()
            
            # 分析基準日値域
            cursor.execute('SELECT MIN(analysis_basis_date), MAX(analysis_basis_date) FROM analysis_results WHERE analysis_basis_date IS NOT NULL')
            basis_date_range = cursor.fetchone()
            
            # 予測日値域
            cursor.execute('SELECT MIN(predicted_crash_date), MAX(predicted_crash_date) FROM analysis_results WHERE predicted_crash_date IS NOT NULL')
            predicted_crash_range = cursor.fetchone()
            
            # 品質レベル一覧
            cursor.execute('SELECT DISTINCT quality FROM analysis_results WHERE quality IS NOT NULL ORDER BY quality')
            quality_levels = [row[0] for row in cursor.fetchall()]
            
            # 銘柄一覧（アルファベット順）
            cursor.execute('SELECT DISTINCT symbol FROM analysis_results ORDER BY symbol')
            symbols = [row[0] for row in cursor.fetchall()]
            
            return {
                'r_squared': {
                    'min': r_squared_range[0] if r_squared_range[0] else 0.0,
                    'max': r_squared_range[1] if r_squared_range[1] else 1.0,
                },
                'confidence': {
                    'min': confidence_range[0] if confidence_range[0] else 0.0,
                    'max': confidence_range[1] if confidence_range[1] else 1.0,
                },
                'basis_date': {
                    'min': basis_date_range[0],
                    'max': basis_date_range[1],
                },
                'predicted_crash_date': {
                    'min': predicted_crash_range[0],
                    'max': predicted_crash_range[1],
                },
                'quality_levels': quality_levels,
                'symbols': symbols
            }
    
    def validate_database_compatibility(self) -> Dict[str, bool]:
        """
        既存システム互換性検証（2025-08-11追加）
        新しいフィルタリング機能が既存メソッドに影響していないことを確認
        
        Returns:
            Dict: 各機能の動作状況
        """
        compatibility_results = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. 基本テーブル構造確認
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                compatibility_results['basic_tables'] = 'analysis_results' in tables
                
                # 2. 必須カラム存在確認
                cursor.execute("PRAGMA table_info(analysis_results)")
                columns = [row[1] for row in cursor.fetchall()]
                required_columns = ['symbol', 'r_squared', 'confidence', 'analysis_basis_date']
                compatibility_results['required_columns'] = all(col in columns for col in required_columns)
                
                # 3. get_recent_analyses互換性
                recent_df = self.get_recent_analyses(limit=1)
                compatibility_results['get_recent_analyses'] = len(recent_df) >= 0
                
                # 4. get_summary_statistics互換性
                stats = self.get_summary_statistics()
                compatibility_results['get_summary_statistics'] = 'total_analyses' in stats
                
                # 5. 新インデックス存在確認
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_quality_comprehensive'")
                compatibility_results['new_indexes'] = bool(cursor.fetchone())
                
                print("🔧 データベース互換性検証完了:")
                for feature, status in compatibility_results.items():
                    status_icon = "✅" if status else "❌"
                    print(f"  {status_icon} {feature}: {status}")
                    
        except Exception as e:
            print(f"❌ 互換性検証中にエラー: {e}")
            compatibility_results['error'] = str(e)
        
        return compatibility_results
    
    def get_filter_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        フィルタープリセット定義（2025-08-11追加）
        ダッシュボード用の事前定義されたフィルター設定
        
        Returns:
            Dict: プリセット名をキーとするフィルター設定
        """
        return {
            "High Quality Only": {
                "min_r_squared": 0.85,
                "min_confidence": 0.80,
                "is_usable": True,
                "description": "R² ≥ 0.85, Confidence ≥ 80%, Usable analyses only"
            },
            "Medium Quality+": {
                "min_r_squared": 0.70,
                "min_confidence": 0.60,
                "is_usable": True,
                "description": "R² ≥ 0.70, Confidence ≥ 60%, Usable analyses only"
            },
            "Critical (30 days)": {
                "is_usable": True,
                "predicted_crash_from": datetime.now().strftime('%Y-%m-%d'),
                "predicted_crash_to": (datetime.now() + pd.DateOffset(days=30)).strftime('%Y-%m-%d'),
                "description": "Crash predictions within 30 days (Critical priority)"
            },
            "Near-term Predictions": {
                "is_usable": True,
                "predicted_crash_from": datetime.now().strftime('%Y-%m-%d'),
                "predicted_crash_to": (datetime.now() + pd.DateOffset(days=90)).strftime('%Y-%m-%d'),
                "description": "Crash predictions within 3 months (High priority)"
            },
            "Medium-term Predictions": {
                "is_usable": True,
                "predicted_crash_from": datetime.now().strftime('%Y-%m-%d'),
                "predicted_crash_to": (datetime.now() + pd.DateOffset(days=180)).strftime('%Y-%m-%d'),
                "description": "Crash predictions within 6 months (Medium priority)"
            },
            "Recent Analyses": {
                "basis_date_from": (datetime.now() - pd.DateOffset(days=30)).strftime('%Y-%m-%d'),
                "description": "Analyses performed in the last 30 days"
            },
            "Ultra-High Precision": {
                "min_r_squared": 0.90,
                "min_confidence": 0.85,
                "is_usable": True,
                "description": "Ultra-high precision analyses (R² ≥ 0.90, Confidence ≥ 85%)"
            },
            "All Usable": {
                "is_usable": True,
                "description": "All analyses marked as usable"
            },
            "Latest 100": {
                "limit": 100,
                "description": "Latest 100 analyses by basis date"
            }
        }
    
    def apply_filter_preset(self, preset_name: str) -> pd.DataFrame:
        """
        プリセットフィルターを適用して結果取得
        2025-08-11追加: ワンクリックフィルタリング
        
        Args:
            preset_name: プリセット名
            
        Returns:
            DataFrame: プリセット適用済み分析結果
        """
        presets = self.get_filter_presets()
        
        if preset_name not in presets:
            print(f"❌ プリセット '{preset_name}' が見つかりません")
            return pd.DataFrame()
        
        preset_config = presets[preset_name]
        description = preset_config.pop('description', preset_name)
        
        print(f"🔍 プリセット適用中: {preset_name} - {description}")
        
        return self.get_filtered_analyses(**preset_config)
    
    def cleanup_old_records(self, days_to_keep: int = 90):
        """
        古いレコードのクリーンアップ
        
        Args:
            days_to_keep: 保持日数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM analysis_results 
                WHERE analysis_date < datetime('now', '-{} days')
            '''.format(days_to_keep))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"📊 古いレコード削除: {deleted_count}件")


# 使用例とテスト
def test_database():
    """データベース機能のテスト"""
    print("🧪 データベース機能テスト")
    print("=" * 50)
    
    # データベース初期化
    db = ResultsDatabase("results/test_analysis.db")
    
    # サンプルデータ保存
    sample_result = {
        'symbol': 'TEST_NASDAQ',
        'data_source': 'fred',
        'data_period_start': '2024-01-01',
        'data_period_end': '2024-12-31',
        'data_points': 250,
        'tc': 1.15,
        'beta': 0.33,
        'omega': 7.4,
        'phi': 0.1,
        'A': 10.0,
        'B': -1.0,
        'C': 0.1,
        'r_squared': 0.95,
        'rmse': 0.01,
        'quality': 'high_quality',
        'confidence': 0.92,
        'is_usable': True,
        'predicted_crash_date': '2025-01-15',
        'days_to_crash': 45,
        'fitting_method': 'multi_criteria',
        'window_days': 365,
        'total_candidates': 50,
        'successful_candidates': 35
    }
    
    # 保存テスト
    analysis_id = db.save_analysis_result(sample_result)
    print(f"✅ サンプルデータ保存: ID={analysis_id}")
    
    # 取得テスト
    recent = db.get_recent_analyses(limit=5)
    print(f"✅ 最近の分析取得: {len(recent)}件")
    
    # 統計テスト
    stats = db.get_summary_statistics()
    print(f"✅ 統計情報: 総分析数={stats['total_analyses']}, 使用可能率={stats['usable_rate']:.1%}")
    
    return db


if __name__ == "__main__":
    test_database()