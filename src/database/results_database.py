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
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON analysis_results (symbol, analysis_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality ON analysis_results (quality, is_usable)')
            
            conn.commit()
            print(f"📊 データベース初期化完了: {self.db_path}")
    
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
            
            # データ挿入
            cursor.execute('''
                INSERT INTO analysis_results (
                    symbol, data_source, data_period_start, data_period_end, data_points,
                    tc, beta, omega, phi, A, B, C,
                    r_squared, rmse, quality, confidence, is_usable,
                    predicted_crash_date, days_to_crash,
                    fitting_method, window_days, total_candidates, successful_candidates,
                    quality_metadata, selection_criteria
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(result_data.get('selection_criteria', {}))
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
                    window_days, total_candidates, successful_candidates
                FROM analysis_results
            '''
            
            params = []
            if symbol:
                query += ' WHERE symbol = ?'
                params.append(symbol)
            
            query += ' ORDER BY analysis_date DESC LIMIT ?'
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
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