#!/usr/bin/env python3
"""
予測データベース管理システム

継続的な予測データの蓄積・管理・検索・分析機能を提供
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import os
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class QueryType(Enum):
    """クエリタイプ"""
    CURRENT_RISKS = "current_risks"
    HISTORICAL_ACCURACY = "historical_accuracy"
    TREND_ANALYSIS = "trend_analysis"
    MARKET_COMPARISON = "market_comparison"
    PREDICTION_TRACKING = "prediction_tracking"

@dataclass
class PredictionRecord:
    """予測レコード"""
    id: Optional[int] = None
    timestamp: datetime = None
    market: str = ""
    window_days: int = 0
    start_date: datetime = None
    end_date: datetime = None
    tc: float = 0.0
    beta: float = 0.0
    omega: float = 0.0
    r_squared: float = 0.0
    rmse: float = 0.0
    predicted_date: datetime = None
    tc_interpretation: str = ""
    confidence_score: float = 0.0
    actual_outcome: Optional[str] = None  # 実際の結果（後で更新）
    outcome_accuracy: Optional[float] = None  # 予測精度（後で更新）
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class PredictionDatabase:
    """予測データベース管理クラス"""
    
    def __init__(self, db_path: str = "predictions.db"):
        """
        Args:
            db_path: SQLiteデータベースファイルパス
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースの初期化"""
        
        with sqlite3.connect(self.db_path) as conn:
            # 予測テーブル（メイン結果 - 後方互換性維持）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    market TEXT NOT NULL,
                    window_days INTEGER NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    tc REAL NOT NULL,
                    beta REAL NOT NULL,
                    omega REAL NOT NULL,
                    r_squared REAL NOT NULL,
                    rmse REAL NOT NULL,
                    predicted_date TEXT NOT NULL,
                    tc_interpretation TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    actual_outcome TEXT,
                    outcome_accuracy REAL,
                    selection_criteria TEXT DEFAULT 'r_squared_max',
                    UNIQUE(timestamp, market, window_days)
                )
            """)
            
            # 複数選択結果テーブル（新規追加）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_group_id TEXT NOT NULL,  -- 同一フィッティングセッションのグループID
                    timestamp TEXT NOT NULL,
                    market TEXT NOT NULL,
                    window_days INTEGER NOT NULL,
                    selection_criteria TEXT NOT NULL,   -- 'r_squared_max', 'multi_criteria', 'theoretical_best' etc.
                    is_selected BOOLEAN DEFAULT FALSE,  -- この基準で選択されたかどうか
                    tc REAL NOT NULL,
                    beta REAL NOT NULL,
                    omega REAL NOT NULL,
                    phi REAL NOT NULL,
                    A REAL NOT NULL,
                    B REAL NOT NULL,
                    C REAL NOT NULL,
                    r_squared REAL NOT NULL,
                    rmse REAL NOT NULL,
                    predicted_date TEXT NOT NULL,
                    tc_interpretation TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    initial_params TEXT,               -- JSON形式の初期パラメータ
                    selection_scores TEXT,             -- JSON形式の選択スコア詳細
                    convergence_success BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL
                )
            """)
            
            # フィッティングセッション管理テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fitting_sessions (
                    id TEXT PRIMARY KEY,               -- UUID
                    timestamp TEXT NOT NULL,
                    market TEXT NOT NULL,
                    window_days INTEGER NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_candidates INTEGER NOT NULL,
                    successful_candidates INTEGER NOT NULL,
                    default_selection_criteria TEXT NOT NULL,
                    session_metadata TEXT,             -- JSON形式のメタデータ
                    created_at TEXT NOT NULL,
                    UNIQUE(timestamp, market, window_days)
                )
            """)
            
            # 市場イベントテーブル（実際の結果記録用）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    event_type TEXT NOT NULL,  -- 'crash', 'peak', 'correction'
                    magnitude REAL,  -- 変動率
                    description TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(market, event_date, event_type)
                )
            """)
            
            # アラート履歴テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,  -- 'HIGH_RISK', 'MEDIUM_RISK', 'TREND_CHANGE'
                    market TEXT NOT NULL,
                    tc_value REAL NOT NULL,
                    predicted_date TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_date TEXT,
                    resolution_outcome TEXT
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_market_date ON predictions(market, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_tc ON predictions(tc, confidence_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_market_date ON market_events(market, event_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alert_history(timestamp, resolved)")
            
            # 新テーブル用インデックス
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_group_id ON prediction_candidates(prediction_group_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_criteria ON prediction_candidates(selection_criteria, is_selected)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_market_date ON prediction_candidates(market, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_market_date ON fitting_sessions(market, timestamp)")
    
    def save_prediction(self, record: PredictionRecord) -> int:
        """予測結果の保存"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 重複チェック・更新
            cursor.execute("""
                INSERT OR REPLACE INTO predictions 
                (timestamp, market, window_days, start_date, end_date, tc, beta, omega,
                 r_squared, rmse, predicted_date, tc_interpretation, confidence_score,
                 actual_outcome, outcome_accuracy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp.isoformat(),
                record.market,
                record.window_days,
                record.start_date.isoformat(),
                record.end_date.isoformat(),
                record.tc,
                record.beta,
                record.omega,
                record.r_squared,
                record.rmse,
                record.predicted_date.isoformat(),
                record.tc_interpretation,
                record.confidence_score,
                record.actual_outcome,
                record.outcome_accuracy
            ))
            
            return cursor.lastrowid
    
    def save_multi_criteria_results(self, selection_result, market: str, window_days: int, 
                                   start_date: datetime, end_date: datetime) -> str:
        """多基準選択結果の保存"""
        from src.fitting.multi_criteria_selection import SelectionResult
        
        if not isinstance(selection_result, SelectionResult):
            raise ValueError("selection_result must be SelectionResult instance")
        
        session_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # フィッティングセッション記録
            cursor.execute("""
                INSERT OR REPLACE INTO fitting_sessions 
                (id, timestamp, market, window_days, start_date, end_date, 
                 total_candidates, successful_candidates, default_selection_criteria, 
                 session_metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                timestamp.isoformat(),
                market,
                window_days,
                start_date.isoformat(),
                end_date.isoformat(),
                len(selection_result.all_candidates),
                len([c for c in selection_result.all_candidates if c.convergence_success]),
                selection_result.default_selection.value,
                json.dumps(selection_result.get_comparison_data()),
                timestamp.isoformat()
            ))
            
            # 各選択基準での結果を保存
            for criteria, candidate in selection_result.selections.items():
                if candidate:
                    # tc解釈の計算
                    tc_interpretation = self._interpret_tc_value(candidate.tc)
                    
                    # 予測日の計算
                    observation_days = (end_date - start_date).days
                    days_to_critical = (candidate.tc - 1.0) * observation_days
                    predicted_date = end_date + timedelta(days=days_to_critical)
                    
                    # 信頼度スコアの計算
                    confidence_score = self._calculate_confidence_score(candidate, criteria)
                    
                    # 候補結果の保存
                    cursor.execute("""
                        INSERT INTO prediction_candidates 
                        (prediction_group_id, timestamp, market, window_days, selection_criteria, 
                         is_selected, tc, beta, omega, phi, A, B, C, r_squared, rmse, 
                         predicted_date, tc_interpretation, confidence_score, initial_params, 
                         selection_scores, convergence_success, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        timestamp.isoformat(),
                        market,
                        window_days,
                        criteria.value,
                        True,  # この基準で選択された
                        candidate.tc,
                        candidate.beta,
                        candidate.omega,
                        candidate.phi,
                        candidate.A,
                        candidate.B,
                        candidate.C,
                        candidate.r_squared,
                        candidate.rmse,
                        predicted_date.isoformat(),
                        tc_interpretation,
                        confidence_score,
                        json.dumps(candidate.initial_params),
                        json.dumps(selection_result.selection_scores.get(criteria, {})),
                        candidate.convergence_success,
                        timestamp.isoformat()
                    ))
            
            # デフォルト選択結果をメインテーブルにも保存（後方互換性）
            default_candidate = selection_result.get_selected_result()
            if default_candidate:
                tc_interpretation = self._interpret_tc_value(default_candidate.tc)
                observation_days = (end_date - start_date).days
                days_to_critical = (default_candidate.tc - 1.0) * observation_days
                predicted_date = end_date + timedelta(days=days_to_critical)
                confidence_score = self._calculate_confidence_score(default_candidate, selection_result.default_selection)
                
                # メインテーブル（predictions）への保存
                cursor.execute("""
                    INSERT OR REPLACE INTO predictions 
                    (timestamp, market, window_days, start_date, end_date, tc, beta, omega,
                     r_squared, rmse, predicted_date, tc_interpretation, confidence_score,
                     selection_criteria)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp.isoformat(),
                    market,
                    window_days,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    default_candidate.tc,
                    default_candidate.beta,
                    default_candidate.omega,
                    default_candidate.r_squared,
                    default_candidate.rmse,
                    predicted_date.isoformat(),
                    tc_interpretation,
                    confidence_score,
                    selection_result.default_selection.value
                ))
        
        return session_id
    
    def _interpret_tc_value(self, tc: float) -> str:
        """tc値の解釈"""
        if tc <= 1.1:
            return "imminent"
        elif tc <= 1.3:
            return "actionable"
        elif tc <= 1.5:
            return "monitoring_required"
        elif tc <= 2.0:
            return "extended_horizon"
        elif tc <= 3.0:
            return "long_term_trend"
        else:
            return "informational_only"
    
    def _calculate_confidence_score(self, candidate, selection_criteria) -> float:
        """信頼度スコアの計算"""
        base_score = candidate.r_squared
        
        # tc値による調整
        if candidate.tc <= 1.2:
            tc_multiplier = 1.0
        elif candidate.tc <= 1.5:
            tc_multiplier = 0.8
        elif candidate.tc <= 2.0:
            tc_multiplier = 0.6
        else:
            tc_multiplier = 0.3
        
        # 理論値との適合性
        beta_score = 1.0 - min(1.0, abs(candidate.beta - 0.33) / 0.33)
        omega_score = 1.0 - min(1.0, abs(candidate.omega - 6.36) / 6.36)
        theory_score = (beta_score + omega_score) / 2
        
        # 総合スコア
        confidence = base_score * tc_multiplier * (0.7 + 0.3 * theory_score)
        
        return min(1.0, confidence)
    
    def get_multi_criteria_results(self, market: str = None, window_days: int = None, 
                                  days_back: int = 30, criteria: str = None) -> Dict[str, Any]:
        """多基準選択結果の取得"""
        
        conditions = ["1=1"]
        params = []
        
        if market:
            conditions.append("pc.market = ?")
            params.append(market)
        
        if window_days:
            conditions.append("pc.window_days = ?")
            params.append(window_days)
        
        if criteria:
            conditions.append("pc.selection_criteria = ?")
            params.append(criteria)
        
        conditions.append("date(pc.timestamp) >= date('now', '-{} days')".format(days_back))
        
        where_clause = " AND ".join(conditions)
        
        with sqlite3.connect(self.db_path) as conn:
            # 候補結果の取得
            query = f"""
                SELECT pc.*, fs.total_candidates, fs.successful_candidates
                FROM prediction_candidates pc
                JOIN fitting_sessions fs ON pc.prediction_group_id = fs.id
                WHERE {where_clause}
                ORDER BY pc.timestamp DESC, pc.selection_criteria
            """
            
            candidates_df = pd.read_sql_query(query, conn, params=params)
            
            if candidates_df.empty:
                return {'status': 'no_data'}
            
            # セッション別にグループ化
            sessions = {}
            for _, row in candidates_df.iterrows():
                session_id = row['prediction_group_id']
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_info': {
                            'market': row['market'],
                            'window_days': row['window_days'],
                            'timestamp': row['timestamp'],
                            'total_candidates': row['total_candidates'],
                            'successful_candidates': row['successful_candidates']
                        },
                        'selections': {}
                    }
                
                sessions[session_id]['selections'][row['selection_criteria']] = {
                    'tc': row['tc'],
                    'beta': row['beta'],
                    'omega': row['omega'],
                    'r_squared': row['r_squared'],
                    'rmse': row['rmse'],
                    'predicted_date': row['predicted_date'],
                    'tc_interpretation': row['tc_interpretation'],
                    'confidence_score': row['confidence_score'],
                    'selection_scores': json.loads(row['selection_scores']) if row['selection_scores'] else {}
                }
            
            return {
                'status': 'success',
                'sessions_count': len(sessions),
                'sessions': sessions
            }
    
    def get_criteria_comparison(self, market: str, window_days: int, days_back: int = 90) -> Dict[str, Any]:
        """選択基準別の比較分析"""
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT selection_criteria, 
                       COUNT(*) as selection_count,
                       AVG(tc) as avg_tc,
                       AVG(r_squared) as avg_r_squared,
                       AVG(confidence_score) as avg_confidence,
                       MIN(tc) as min_tc,
                       MAX(tc) as max_tc
                FROM prediction_candidates 
                WHERE market = ? AND window_days = ?
                AND date(timestamp) >= date('now', '-{} days')
                AND is_selected = TRUE
                GROUP BY selection_criteria
                ORDER BY avg_confidence DESC
            """.format(days_back)
            
            df = pd.read_sql_query(query, conn, params=(market, window_days))
            
            if df.empty:
                return {'status': 'no_data'}
            
            # tc値の時系列トレンド
            trend_query = """
                SELECT timestamp, selection_criteria, tc, r_squared
                FROM prediction_candidates 
                WHERE market = ? AND window_days = ?
                AND date(timestamp) >= date('now', '-{} days')
                AND is_selected = TRUE
                ORDER BY timestamp ASC
            """.format(days_back)
            
            trend_df = pd.read_sql_query(trend_query, conn, params=(market, window_days))
            
            return {
                'status': 'success',
                'criteria_stats': df.to_dict('records'),
                'trend_data': trend_df.to_dict('records'),
                'analysis_period': f'Past {days_back} days'
            }
    
    def save_market_event(self, market: str, event_date: datetime, 
                         event_type: str, magnitude: float = None, 
                         description: str = ""):
        """実際の市場イベントの記録"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO market_events 
                (market, event_date, event_type, magnitude, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                market,
                event_date.isoformat(),
                event_type,
                magnitude,
                description,
                datetime.now().isoformat()
            ))
    
    def save_alert(self, alert_type: str, market: str, tc_value: float,
                  predicted_date: datetime, confidence_score: float,
                  message: str = ""):
        """アラートの記録"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alert_history 
                (timestamp, alert_type, market, tc_value, predicted_date, 
                 confidence_score, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                alert_type,
                market,
                tc_value,
                predicted_date.isoformat(),
                confidence_score,
                message
            ))
    
    def get_current_risks(self, tc_threshold: float = 1.5, 
                         confidence_threshold: float = 0.6) -> List[Dict]:
        """現在の高リスク予測の取得"""
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM predictions 
                WHERE tc <= ? AND confidence_score >= ?
                AND date(predicted_date) >= date('now')
                ORDER BY tc ASC, confidence_score DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(tc_threshold, confidence_threshold))
            
            if df.empty:
                return []
            
            return df.to_dict('records')
    
    def get_market_trend(self, market: str, window_days: int, 
                        days_back: int = 90) -> Dict[str, Any]:
        """特定市場のトレンド分析"""
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, tc, confidence_score, predicted_date
                FROM predictions 
                WHERE market = ? AND window_days = ?
                AND date(timestamp) >= date('now', '-{} days')
                ORDER BY timestamp ASC
            """.format(days_back)
            
            df = pd.read_sql_query(query, conn, params=(market, window_days))
            
            if df.empty:
                return {'status': 'no_data'}
            
            # 時系列変換
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['predicted_date'] = pd.to_datetime(df['predicted_date'])
            
            # tc値のトレンド分析
            tc_values = df['tc'].values
            if len(tc_values) > 1:
                tc_trend = np.polyfit(range(len(tc_values)), tc_values, 1)[0]
                tc_velocity = np.gradient(tc_values)[-1]  # 最新の変化率
            else:
                tc_trend = 0
                tc_velocity = 0
            
            # 解釈
            if tc_trend < -0.05:
                trend_interpretation = "approaching_critical"
            elif tc_trend > 0.05:
                trend_interpretation = "moving_away"
            else:
                trend_interpretation = "stable"
            
            return {
                'market': market,
                'window_days': window_days,
                'data_points': len(df),
                'latest_tc': tc_values[-1],
                'tc_trend': tc_trend,
                'tc_velocity': tc_velocity,
                'interpretation': trend_interpretation,
                'history': df.to_dict('records')
            }
    
    def update_prediction_outcome(self, prediction_id: int, 
                                actual_outcome: str, accuracy: float):
        """予測結果の実際の結果による更新"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE predictions 
                SET actual_outcome = ?, outcome_accuracy = ?
                WHERE id = ?
            """, (actual_outcome, accuracy, prediction_id))
    
    def get_prediction_accuracy_stats(self, days_back: int = 365) -> Dict[str, Any]:
        """予測精度統計の取得"""
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT market, tc_interpretation, 
                       COUNT(*) as total_predictions,
                       AVG(outcome_accuracy) as avg_accuracy,
                       COUNT(CASE WHEN outcome_accuracy > 0.8 THEN 1 END) as high_accuracy_count
                FROM predictions 
                WHERE actual_outcome IS NOT NULL
                AND date(timestamp) >= date('now', '-{} days')
                GROUP BY market, tc_interpretation
                ORDER BY avg_accuracy DESC
            """.format(days_back)
            
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return {'status': 'no_validation_data'}
            
            return {
                'overall_stats': {
                    'total_validated_predictions': df['total_predictions'].sum(),
                    'average_accuracy': df['avg_accuracy'].mean(),
                    'high_accuracy_rate': df['high_accuracy_count'].sum() / df['total_predictions'].sum()
                },
                'by_market': df.to_dict('records'),
                'by_interpretation': df.groupby('tc_interpretation').agg({
                    'total_predictions': 'sum',
                    'avg_accuracy': 'mean'
                }).to_dict('index')
            }
    
    def search_predictions(self, query_params: Dict[str, Any]) -> List[Dict]:
        """柔軟な検索機能"""
        
        conditions = []
        params = []
        
        # 検索条件の構築
        if 'market' in query_params:
            conditions.append("market = ?")
            params.append(query_params['market'])
        
        if 'tc_min' in query_params:
            conditions.append("tc >= ?")
            params.append(query_params['tc_min'])
        
        if 'tc_max' in query_params:
            conditions.append("tc <= ?")
            params.append(query_params['tc_max'])
        
        if 'confidence_min' in query_params:
            conditions.append("confidence_score >= ?")
            params.append(query_params['confidence_min'])
        
        if 'date_from' in query_params:
            conditions.append("date(timestamp) >= date(?)")
            params.append(query_params['date_from'])
        
        if 'date_to' in query_params:
            conditions.append("date(timestamp) <= date(?)")
            params.append(query_params['date_to'])
        
        if 'tc_interpretation' in query_params:
            conditions.append("tc_interpretation = ?")
            params.append(query_params['tc_interpretation'])
        
        # クエリ実行
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM predictions WHERE {where_clause} ORDER BY timestamp DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return []
            
            return df.to_dict('records')
    
    def get_alert_dashboard(self) -> Dict[str, Any]:
        """アラートダッシュボードのデータ取得"""
        
        with sqlite3.connect(self.db_path) as conn:
            # アクティブアラート
            active_alerts = pd.read_sql_query("""
                SELECT * FROM alert_history 
                WHERE resolved = FALSE 
                ORDER BY confidence_score DESC, timestamp DESC
            """, conn)
            
            # 最近のアラート統計
            recent_stats = pd.read_sql_query("""
                SELECT alert_type, COUNT(*) as count
                FROM alert_history 
                WHERE date(timestamp) >= date('now', '-7 days')
                GROUP BY alert_type
            """, conn)
            
            # 解決済みアラートの精度
            resolved_accuracy = pd.read_sql_query("""
                SELECT alert_type, 
                       COUNT(*) as total_resolved,
                       AVG(CASE WHEN resolution_outcome = 'accurate' THEN 1.0 ELSE 0.0 END) as accuracy_rate
                FROM alert_history 
                WHERE resolved = TRUE AND resolution_outcome IS NOT NULL
                GROUP BY alert_type
            """, conn)
            
            return {
                'active_alerts': active_alerts.to_dict('records') if not active_alerts.empty else [],
                'recent_stats': recent_stats.to_dict('records') if not recent_stats.empty else [],
                'alert_accuracy': resolved_accuracy.to_dict('records') if not resolved_accuracy.empty else []
            }
    
    def export_data(self, query_type: QueryType, 
                   output_format: str = 'json', **kwargs) -> str:
        """データのエクスポート"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if query_type == QueryType.CURRENT_RISKS:
            data = self.get_current_risks(**kwargs)
            filename = f"current_risks_{timestamp}"
            
        elif query_type == QueryType.HISTORICAL_ACCURACY:
            data = self.get_prediction_accuracy_stats(**kwargs)
            filename = f"accuracy_stats_{timestamp}"
            
        elif query_type == QueryType.TREND_ANALYSIS:
            market = kwargs.get('market', 'NASDAQ')
            window = kwargs.get('window_days', 730)
            data = self.get_market_trend(market, window, **kwargs)
            filename = f"trend_{market}_{window}d_{timestamp}"
            
        else:
            data = self.search_predictions(kwargs)
            filename = f"search_results_{timestamp}"
        
        # 出力ディレクトリ作成
        os.makedirs('exports/prediction_data', exist_ok=True)
        
        if output_format == 'json':
            filepath = f"exports/prediction_data/{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        elif output_format == 'csv':
            filepath = f"exports/prediction_data/{filename}.csv"
            if isinstance(data, list):
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False)
            else:
                # 辞書形式の場合は flatten
                df = pd.json_normalize(data)
                df.to_csv(filepath, index=False)
        
        return filepath
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """古いデータのクリーンアップ"""
        
        with sqlite3.connect(self.db_path) as conn:
            # 古い予測データの削除
            conn.execute("""
                DELETE FROM predictions 
                WHERE date(timestamp) < date('now', '-{} days')
                AND actual_outcome IS NULL
            """.format(days_to_keep))
            
            # 古いアラート履歴の削除（解決済みのみ）
            conn.execute("""
                DELETE FROM alert_history 
                WHERE date(timestamp) < date('now', '-{} days')
                AND resolved = TRUE
            """.format(days_to_keep // 2))  # アラートはより短期間で削除
            
            # データベース最適化
            conn.execute("VACUUM")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """データベース統計情報"""
        
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # テーブル別レコード数
            for table in ['predictions', 'market_events', 'alert_history']:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[f'{table}_count'] = count
            
            # 最新・最古データ
            latest = conn.execute("SELECT MAX(timestamp) FROM predictions").fetchone()[0]
            oldest = conn.execute("SELECT MIN(timestamp) FROM predictions").fetchone()[0]
            
            stats['data_range'] = {
                'latest': latest,
                'oldest': oldest
            }
            
            # 市場別統計
            market_stats = pd.read_sql_query("""
                SELECT market, COUNT(*) as prediction_count
                FROM predictions 
                GROUP BY market 
                ORDER BY prediction_count DESC
            """, conn)
            
            stats['by_market'] = market_stats.to_dict('records')
            
            # データベースサイズ
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            stats['database_size_mb'] = round(db_size, 2)
            
            return stats

# 使用例・テスト関数
def example_usage():
    """使用例の実演"""
    
    print("🗄️ 予測データベース管理システム デモンストレーション")
    print("=" * 60)
    
    # データベース初期化
    db = PredictionDatabase("demo_predictions.db")
    
    # サンプル予測データの追加
    sample_records = [
        PredictionRecord(
            timestamp=datetime.now() - timedelta(days=7),
            market="NASDAQ",
            window_days=730,
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2024, 1, 1),
            tc=1.25,
            beta=0.35,
            omega=6.2,
            r_squared=0.92,
            rmse=0.05,
            predicted_date=datetime(2025, 3, 15),
            tc_interpretation="actionable",
            confidence_score=0.88
        ),
        PredictionRecord(
            timestamp=datetime.now() - timedelta(days=3),
            market="SP500",
            window_days=365,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            tc=1.08,
            beta=0.33,
            omega=7.1,
            r_squared=0.89,
            rmse=0.07,
            predicted_date=datetime(2025, 2, 10),
            tc_interpretation="imminent",
            confidence_score=0.95
        )
    ]
    
    print("📊 サンプルデータ追加中...")
    for record in sample_records:
        record_id = db.save_prediction(record)
        print(f"   レコードID {record_id}: {record.market} tc={record.tc:.3f}")
    
    # 現在のリスク取得
    print(f"\n⚠️ 現在の高リスク予測:")
    current_risks = db.get_current_risks()
    for risk in current_risks:
        print(f"   {risk['market']}: tc={risk['tc']:.3f}, 予測日={risk['predicted_date'][:10]}")
    
    # 検索機能テスト
    print(f"\n🔍 検索テスト（tc < 1.3）:")
    search_results = db.search_predictions({'tc_max': 1.3})
    for result in search_results:
        print(f"   {result['market']}: tc={result['tc']:.3f}, 信頼度={result['confidence_score']:.2f}")
    
    # アラート追加
    print(f"\n🚨 アラート追加テスト:")
    db.save_alert(
        "HIGH_RISK", "SP500", 1.08, 
        datetime(2025, 2, 10), 0.95,
        "差し迫ったクラッシュリスク検出"
    )
    
    # データベース統計
    print(f"\n📊 データベース統計:")
    stats = db.get_database_stats()
    print(f"   予測レコード数: {stats['predictions_count']}")
    print(f"   アラート数: {stats['alert_history_count']}")
    print(f"   データベースサイズ: {stats['database_size_mb']} MB")
    
    # クリーンアップ
    os.remove("demo_predictions.db")
    print(f"\n✅ デモンストレーション完了")

if __name__ == "__main__":
    example_usage()