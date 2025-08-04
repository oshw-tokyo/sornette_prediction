#!/usr/bin/env python3
"""
スケジュール設定管理
定期分析の設定・状態管理を行う
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ScheduleConfig:
    """スケジュール設定データ"""
    id: Optional[int]
    schedule_name: str
    frequency: str
    day_of_week: Optional[int]
    hour: int
    minute: int
    timezone: str
    symbols: List[str]
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_date: datetime
    auto_backfill_limit: int

class ScheduleManager:
    """スケジュール設定管理クラス"""
    
    def __init__(self, db_path: str = "results/analysis_results.db"):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db_path = db_path
        self._ensure_default_schedule()
    
    def _ensure_default_schedule(self):
        """デフォルトスケジュール設定の作成"""
        # カタログから銘柄リストを取得
        catalog_path = Path(__file__).parent.parent / "data_sources" / "market_data_catalog.json"
        symbols = self._load_symbols_from_catalog(catalog_path)
        
        # デフォルト設定を挿入（存在しない場合のみ）
        # ⚠️ CRITICAL: 標準は週次解析
        default_config = {
            'schedule_name': 'fred_weekly',
            'frequency': 'weekly',
            'day_of_week': 5,  # 土曜日 (0=月曜)
            'hour': 9,
            'minute': 0,
            'timezone': 'UTC',
            'symbols': json.dumps(['NASDAQCOM', 'SP500', 'DJI']),  # 標準的な経済指標
            'enabled': 1,
            'auto_backfill_limit': 30
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 既存設定チェック
            cursor.execute('SELECT COUNT(*) FROM schedule_config WHERE schedule_name = ?', 
                         (default_config['schedule_name'],))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO schedule_config (
                        schedule_name, frequency, day_of_week, hour, minute, timezone,
                        symbols, enabled, auto_backfill_limit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    default_config['schedule_name'],
                    default_config['frequency'],
                    default_config['day_of_week'],
                    default_config['hour'],
                    default_config['minute'],
                    default_config['timezone'],
                    default_config['symbols'],
                    default_config['enabled'],
                    default_config['auto_backfill_limit']
                ))
                conn.commit()
                print(f"✅ デフォルトスケジュール設定を作成: {default_config['schedule_name']}")
    
    def _load_symbols_from_catalog(self, catalog_path: Path) -> List[str]:
        """カタログから銘柄リストを読み込み"""
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            symbols = list(catalog.get('symbols', {}).keys())
            print(f"📊 カタログから{len(symbols)}銘柄を読み込み")
            return symbols
        except Exception as e:
            print(f"⚠️ カタログ読み込み失敗: {e}")
            # フォールバック: 主要指数のみ
            return ['NASDAQCOM', 'SP500', 'NASDAQ100']
    
    def get_schedule_config(self, schedule_name: str) -> Optional[ScheduleConfig]:
        """スケジュール設定の取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM schedule_config WHERE schedule_name = ?
            ''', (schedule_name,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ScheduleConfig(
                id=row[0],
                schedule_name=row[1],
                frequency=row[2],
                day_of_week=row[3],
                hour=row[4],
                minute=row[5],
                timezone=row[6],
                symbols=json.loads(row[7]) if row[7] else [],
                enabled=bool(row[8]),
                last_run=datetime.fromisoformat(row[9]) if row[9] else None,
                next_run=datetime.fromisoformat(row[10]) if row[10] else None,
                created_date=datetime.fromisoformat(row[11]),
                auto_backfill_limit=row[12]
            )
    
    def get_active_schedules(self) -> List[ScheduleConfig]:
        """有効なスケジュール設定の取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT schedule_name FROM schedule_config WHERE enabled = 1')
            
            schedules = []
            for row in cursor.fetchall():
                config = self.get_schedule_config(row[0])
                if config:
                    schedules.append(config)
            
            return schedules
    
    def update_last_run(self, schedule_name: str, run_time: datetime):
        """最終実行時刻の更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE schedule_config 
                SET last_run = ? 
                WHERE schedule_name = ?
            ''', (run_time.isoformat(), schedule_name))
            conn.commit()
            print(f"📅 スケジュール実行時刻更新: {schedule_name} -> {run_time}")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """スケジュール状態の取得"""
        schedules = self.get_active_schedules()
        
        status = {
            'total_schedules': len(schedules),
            'enabled_schedules': len([s for s in schedules if s.enabled]),
            'schedules': []
        }
        
        for config in schedules:
            status['schedules'].append({
                'name': config.schedule_name,
                'frequency': config.frequency,
                'symbols_count': len(config.symbols),
                'last_run': config.last_run.isoformat() if config.last_run else None,
                'enabled': config.enabled
            })
        
        return status

def main():
    """テスト実行"""
    print("🕐 スケジュール管理システムテスト")
    print("=" * 50)
    
    manager = ScheduleManager()
    
    # 状態確認
    status = manager.get_schedule_status()
    print(f"📊 アクティブスケジュール: {status['enabled_schedules']}")
    
    for schedule in status['schedules']:
        print(f"  - {schedule['name']}: {schedule['frequency']}, {schedule['symbols_count']}銘柄")

if __name__ == "__main__":
    main()