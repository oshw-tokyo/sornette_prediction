#!/usr/bin/env python3
"""
FCO分析結果データベース管理
DS-LPPLS指標と多重時間窓分析結果を永続化
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import os
from pathlib import Path

class FCOResultsDatabase:
    """FCO分析結果データベース管理クラス"""
    
    def __init__(self, db_path: str = "results/fco_analysis_results.db"):
        """
        FCOデータベース初期化
        
        Args:
            db_path: データベースファイルパス（デフォルト: results/fco_analysis_results.db）
        """
        self.db_path = db_path
        
        # ディレクトリ作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # データベース初期化
        self._init_database()
        
    def _init_database(self):
        """FCO用データベースとテーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # FCO分析結果テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fco_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analysis_basis_date DATE NOT NULL,  -- 分析基準日（データ期間最終日）
                    data_source TEXT,
                    data_period_start DATE,
                    data_period_end DATE,
                    data_points INTEGER,
                    
                    -- DS-LPPLS指標
                    ds_lppls_confidence REAL,  -- 正のバブル信頼度
                    ds_lppls_confidence_neg REAL,  -- 負のバブル信頼度
                    ds_lppls_trust REAL,  -- Trust指標（ブートストラップ信頼性）
                    bubble_type TEXT,  -- 'positive', 'negative', 'none'
                    
                    -- クラスター分析結果
                    predicted_tc REAL,  -- 予測臨界時間（中央値）
                    tc_std REAL,  -- 臨界時間の標準偏差
                    scenario_probability REAL,  -- 最大クラスターのシナリオ確率
                    cluster_method TEXT,  -- 'k-means', 'dbscan', etc.
                    
                    -- 多重時間窓情報
                    num_windows INTEGER,  -- 分析に使用した窓数
                    num_qualified_fits INTEGER,  -- フィルタリング条件を満たしたフィット数
                    window_min INTEGER,  -- 最小窓サイズ
                    window_max INTEGER,  -- 最大窓サイズ
                    window_step INTEGER,  -- 窓刻み幅
                    
                    -- FCOフィルタリング条件
                    filter_damping_min REAL,
                    filter_m_range TEXT,  -- JSON: [min, max]
                    filter_omega_range TEXT,  -- JSON: [min, max]
                    
                    -- 予測情報
                    predicted_crash_date DATE,
                    days_to_crash INTEGER,
                    confidence_interval TEXT,  -- JSON: [lower, upper]
                    
                    -- メタデータ
                    analysis_method TEXT DEFAULT 'FCO',
                    engine_version TEXT,
                    computation_time_seconds REAL,
                    
                    -- JSON形式の詳細データ
                    window_results TEXT,  -- 各窓の結果（大容量）
                    metadata TEXT,  -- その他のメタデータ
                    
                    -- 重複防止用の一意制約
                    UNIQUE(symbol, analysis_basis_date, analysis_method)
                )
            ''')
            
            # 個別窓フィッティング結果テーブル（詳細保存用）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fco_window_fits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    window_size INTEGER,
                    window_start_idx INTEGER,
                    window_end_idx INTEGER,
                    
                    -- LPPLパラメータ（Boulder形式）
                    tc REAL,
                    m REAL,  -- beta相当
                    w REAL,  -- omega相当
                    a REAL,
                    b REAL,
                    c1 REAL,  -- C*cos(phi)
                    c2 REAL,  -- C*sin(phi)
                    
                    -- フィッティング品質
                    r_squared REAL,
                    rmse REAL,
                    damping REAL,
                    is_qualified BOOLEAN,
                    
                    -- タイムスタンプ
                    fit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (analysis_id) REFERENCES fco_analysis_results (id)
                )
            ''')
            
            # DS-LPPLS時系列テーブル（Confidence/Trust履歴）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fco_confidence_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATE NOT NULL,
                    price REAL,
                    ds_lppls_confidence REAL,
                    ds_lppls_confidence_neg REAL,
                    ds_lppls_trust REAL,
                    bubble_status TEXT,
                    
                    UNIQUE(symbol, timestamp)
                )
            ''')
            
            # インデックス作成
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fco_symbol_date 
                ON fco_analysis_results (symbol, analysis_basis_date DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fco_confidence 
                ON fco_analysis_results (ds_lppls_confidence DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fco_bubble_type 
                ON fco_analysis_results (bubble_type)
            ''')
            
            conn.commit()
    
    def save_fco_analysis(self, result: Dict[str, Any]) -> int:
        """
        FCO分析結果を保存
        
        Args:
            result: FCOAnalysisResultまたは辞書形式の結果
        
        Returns:
            挿入されたレコードのID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # データクラスから辞書への変換（必要な場合）
            if hasattr(result, '__dict__'):
                data = result.__dict__
            else:
                data = result
            
            # JSON形式のフィールドを文字列化
            if isinstance(data.get('filter_m_range'), (list, tuple)):
                data['filter_m_range'] = json.dumps(data['filter_m_range'])
            if isinstance(data.get('filter_omega_range'), (list, tuple)):
                data['filter_omega_range'] = json.dumps(data['filter_omega_range'])
            if isinstance(data.get('confidence_interval'), (list, tuple)):
                data['confidence_interval'] = json.dumps(data['confidence_interval'])
            if isinstance(data.get('window_results'), list):
                # 大容量データは圧縮して保存
                data['window_results'] = json.dumps(data['window_results'][:100])  # 最初の100件のみ
            if isinstance(data.get('metadata'), dict):
                data['metadata'] = json.dumps(data['metadata'])
            
            # INSERT OR REPLACE（重複時は更新）
            cursor.execute('''
                INSERT OR REPLACE INTO fco_analysis_results (
                    symbol, analysis_basis_date, data_source,
                    data_period_start, data_period_end, data_points,
                    ds_lppls_confidence, ds_lppls_confidence_neg, ds_lppls_trust,
                    bubble_type, predicted_tc, tc_std, scenario_probability,
                    cluster_method, num_windows, num_qualified_fits,
                    window_min, window_max, window_step,
                    filter_damping_min, filter_m_range, filter_omega_range,
                    predicted_crash_date, days_to_crash, confidence_interval,
                    analysis_method, engine_version, computation_time_seconds,
                    window_results, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('symbol'),
                data.get('analysis_basis_date'),
                data.get('data_source'),
                data.get('data_period_start'),
                data.get('data_period_end'),
                data.get('data_points'),
                data.get('ds_lppls_confidence'),
                data.get('ds_lppls_confidence_neg'),
                data.get('ds_lppls_trust'),
                data.get('bubble_type'),
                data.get('predicted_tc'),
                data.get('tc_std'),
                data.get('scenario_probability'),
                data.get('cluster_method', 'median'),
                data.get('num_windows'),
                data.get('num_qualified_fits'),
                data.get('window_min', 125),
                data.get('window_max', 750),
                data.get('window_step', 5),
                data.get('filter_damping_min', 1.0),
                data.get('filter_m_range'),
                data.get('filter_omega_range'),
                data.get('predicted_crash_date'),
                data.get('days_to_crash'),
                data.get('confidence_interval'),
                data.get('analysis_method', 'FCO'),
                data.get('engine_version', '2.0'),
                data.get('computation_time_seconds'),
                data.get('window_results'),
                data.get('metadata')
            ))
            
            analysis_id = cursor.lastrowid
            conn.commit()
            
            return analysis_id
    
    def get_latest_fco_analysis(self, symbol: str) -> Optional[Dict]:
        """
        指定銘柄の最新FCO分析結果を取得
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            最新の分析結果（辞書形式）
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM fco_analysis_results 
                WHERE symbol = ? 
                ORDER BY analysis_basis_date DESC, analysis_date DESC 
                LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # JSON形式のフィールドをパース
                for field in ['filter_m_range', 'filter_omega_range', 
                             'confidence_interval', 'window_results', 'metadata']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except:
                            pass
                return result
            return None
    
    def get_high_confidence_bubbles(self, 
                                   confidence_threshold: float = 0.3,
                                   limit: int = 50) -> pd.DataFrame:
        """
        高信頼度のバブル銘柄を取得
        
        Args:
            confidence_threshold: 信頼度閾値（デフォルト: 0.3 = 30%）
            limit: 取得件数上限
        
        Returns:
            高信頼度バブル銘柄のDataFrame
        """
        query = '''
            SELECT 
                symbol,
                analysis_basis_date,
                ds_lppls_confidence,
                ds_lppls_confidence_neg,
                bubble_type,
                predicted_crash_date,
                days_to_crash,
                scenario_probability
            FROM fco_analysis_results
            WHERE 
                (ds_lppls_confidence >= ? OR ds_lppls_confidence_neg >= ?)
                AND analysis_basis_date = (
                    SELECT MAX(analysis_basis_date) 
                    FROM fco_analysis_results AS sub 
                    WHERE sub.symbol = fco_analysis_results.symbol
                )
            ORDER BY 
                CASE 
                    WHEN bubble_type = 'positive' THEN ds_lppls_confidence
                    ELSE ds_lppls_confidence_neg
                END DESC
            LIMIT ?
        '''
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, 
                                  params=(confidence_threshold, confidence_threshold, limit))
        
        return df
    
    def save_confidence_history(self, symbol: str, 
                               timestamp: Union[str, datetime],
                               price: float,
                               confidence: float,
                               confidence_neg: float,
                               trust: Optional[float] = None,
                               bubble_status: Optional[str] = None) -> None:
        """
        DS-LPPLS Confidence履歴を保存
        
        Args:
            symbol: 銘柄コード
            timestamp: タイムスタンプ
            price: 価格
            confidence: 正のバブル信頼度
            confidence_neg: 負のバブル信頼度
            trust: Trust指標
            bubble_status: バブル状態
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO fco_confidence_history (
                    symbol, timestamp, price,
                    ds_lppls_confidence, ds_lppls_confidence_neg,
                    ds_lppls_trust, bubble_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, timestamp, price, confidence, confidence_neg, trust, bubble_status))
            
            conn.commit()
    
    def get_confidence_history(self, symbol: str, 
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        DS-LPPLS Confidence履歴を取得
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            Confidence履歴のDataFrame
        """
        query = '''
            SELECT * FROM fco_confidence_history
            WHERE symbol = ?
        '''
        params = [symbol]
        
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
        
        query += ' ORDER BY timestamp'
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        return df


# 既存データベースとの互換性ヘルパー
class DatabaseMigrationHelper:
    """既存データベースからFCOデータベースへの移行ヘルパー"""
    
    @staticmethod
    def compare_databases(old_db_path: str = "results/analysis_results.db",
                          new_db_path: str = "results/fco_analysis_results.db") -> Dict:
        """
        新旧データベースの比較
        
        Args:
            old_db_path: 既存データベースパス
            new_db_path: FCOデータベースパス
        
        Returns:
            比較結果の辞書
        """
        comparison = {
            'old_db_exists': os.path.exists(old_db_path),
            'new_db_exists': os.path.exists(new_db_path),
            'old_records': 0,
            'new_records': 0,
            'common_symbols': [],
            'old_only_symbols': [],
            'new_only_symbols': []
        }
        
        if comparison['old_db_exists']:
            with sqlite3.connect(old_db_path) as conn:
                old_count = conn.execute(
                    "SELECT COUNT(*) FROM analysis_results"
                ).fetchone()[0]
                old_symbols = set(row[0] for row in conn.execute(
                    "SELECT DISTINCT symbol FROM analysis_results"
                ))
                comparison['old_records'] = old_count
        else:
            old_symbols = set()
        
        if comparison['new_db_exists']:
            with sqlite3.connect(new_db_path) as conn:
                new_count = conn.execute(
                    "SELECT COUNT(*) FROM fco_analysis_results"
                ).fetchone()[0]
                new_symbols = set(row[0] for row in conn.execute(
                    "SELECT DISTINCT symbol FROM fco_analysis_results"
                ))
                comparison['new_records'] = new_count
        else:
            new_symbols = set()
        
        comparison['common_symbols'] = list(old_symbols & new_symbols)
        comparison['old_only_symbols'] = list(old_symbols - new_symbols)
        comparison['new_only_symbols'] = list(new_symbols - old_symbols)
        
        return comparison