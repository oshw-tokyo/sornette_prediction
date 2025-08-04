#!/usr/bin/env python3
"""
差し迫ったクラッシュ警告システム

LPPL分析結果から投資判断に必要な高確度・緊急性の高いクラッシュ予測を抽出し、
優先度付きリストとして表示する
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
from pathlib import Path

class RiskLevel(Enum):
    """リスクレベル"""
    CRITICAL = "critical"    # tc < 1.1, R² > 0.85
    HIGH = "high"           # tc < 1.2, R² > 0.75
    MEDIUM = "medium"       # tc < 1.5, R² > 0.65
    LOW = "low"            # その他

class UrgencyLevel(Enum):
    """緊急度レベル"""
    IMMEDIATE = "immediate"  # tc < 1.05 (数日以内)
    NEAR_TERM = "near_term"  # tc < 1.1 (数週間以内)
    SHORT_TERM = "short_term" # tc < 1.2 (数ヶ月以内)
    LONG_TERM = "long_term"   # tc >= 1.2

@dataclass
class CrashAlert:
    """クラッシュ警告情報"""
    symbol: str
    display_name: str
    asset_class: str
    instrument_type: str
    
    # LPPL分析結果
    tc: float
    beta: float
    omega: float
    r_squared: float
    rmse: float
    
    # 警告レベル
    risk_level: RiskLevel
    urgency_level: UrgencyLevel
    confidence_score: float  # 0-100
    
    # 時間予測
    estimated_crash_date: Optional[datetime] = None
    days_until_crash: Optional[int] = None
    
    # メタデータ
    analysis_date: datetime = field(default_factory=datetime.now)
    data_period_days: Optional[int] = None
    last_price: Optional[float] = None
    
    # 投資アクション推奨
    recommended_action: Optional[str] = None
    position_sizing: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'symbol': self.symbol,
            'display_name': self.display_name,
            'asset_class': self.asset_class,
            'instrument_type': self.instrument_type,
            'tc': self.tc,
            'beta': self.beta,
            'omega': self.omega,
            'r_squared': self.r_squared,
            'rmse': self.rmse,
            'risk_level': self.risk_level.value,
            'urgency_level': self.urgency_level.value,
            'confidence_score': self.confidence_score,
            'estimated_crash_date': self.estimated_crash_date.isoformat() if self.estimated_crash_date else None,
            'days_until_crash': self.days_until_crash,
            'analysis_date': self.analysis_date.isoformat(),
            'data_period_days': self.data_period_days,
            'last_price': self.last_price,
            'recommended_action': self.recommended_action,
            'position_sizing': self.position_sizing
        }

class CrashAlertSystem:
    """クラッシュ警告システム"""
    
    def __init__(self, database_path: Optional[str] = None, catalog_path: Optional[str] = None):
        """
        初期化
        
        Args:
            database_path: 分析結果データベースのパス
            catalog_path: マーケットデータカタログのパス
        """
        self.database_path = database_path or "results/analysis_results.db"
        
        # カタログデータの読み込み
        if catalog_path is None:
            catalog_path = Path(__file__).parent.parent.parent / "infrastructure" / "data_sources" / "market_data_catalog.json"
        
        self.catalog_data = self._load_catalog(catalog_path)
        
        # 警告判定基準
        self.alert_thresholds = {
            RiskLevel.CRITICAL: {'tc_max': 1.1, 'r_squared_min': 0.85},
            RiskLevel.HIGH: {'tc_max': 1.2, 'r_squared_min': 0.75},
            RiskLevel.MEDIUM: {'tc_max': 1.5, 'r_squared_min': 0.65},
            RiskLevel.LOW: {'tc_max': 10.0, 'r_squared_min': 0.0}
        }
        
        self.urgency_thresholds = {
            UrgencyLevel.IMMEDIATE: 1.05,
            UrgencyLevel.NEAR_TERM: 1.1,
            UrgencyLevel.SHORT_TERM: 1.2,
            UrgencyLevel.LONG_TERM: float('inf')
        }
    
    def _load_catalog(self, catalog_path: str) -> Dict:
        """カタログデータの読み込み"""
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ カタログファイルが見つかりません: {catalog_path}")
            return {'symbols': {}}
    
    def _get_symbol_info(self, symbol: str) -> Dict:
        """シンボル情報の取得"""
        return self.catalog_data.get('symbols', {}).get(symbol, {})
    
    def _determine_risk_level(self, tc: float, r_squared: float) -> RiskLevel:
        """リスクレベルの判定"""
        for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            thresholds = self.alert_thresholds[level]
            if tc <= thresholds['tc_max'] and r_squared >= thresholds['r_squared_min']:
                return level
        return RiskLevel.LOW
    
    def _determine_urgency_level(self, tc: float) -> UrgencyLevel:
        """緊急度レベルの判定"""
        for level in [UrgencyLevel.IMMEDIATE, UrgencyLevel.NEAR_TERM, UrgencyLevel.SHORT_TERM]:
            if tc <= self.urgency_thresholds[level]:
                return level
        return UrgencyLevel.LONG_TERM
    
    def _calculate_confidence_score(self, tc: float, r_squared: float, beta: float, data_points: int) -> float:
        """信頼度スコアの計算"""
        # 基本スコア（R²ベース）
        base_score = r_squared * 100
        
        # tcによる調整（近いほど信頼度高）
        if tc <= 1.05:
            tc_bonus = 20
        elif tc <= 1.1:
            tc_bonus = 15
        elif tc <= 1.2:
            tc_bonus = 10
        elif tc <= 1.5:
            tc_bonus = 5
        else:
            tc_bonus = 0
        
        # βによる調整（理論値0.33に近いほど信頼度高）
        beta_distance = abs(beta - 0.33)
        if beta_distance <= 0.1:
            beta_bonus = 10
        elif beta_distance <= 0.2:
            beta_bonus = 5
        else:
            beta_bonus = 0
        
        # データ点数による調整
        if data_points >= 365:
            data_bonus = 10
        elif data_points >= 180:
            data_bonus = 5
        else:
            data_bonus = 0
        
        total_score = base_score + tc_bonus + beta_bonus + data_bonus
        return min(total_score, 100.0)  # 上限100
    
    def _estimate_crash_timing(self, tc: float, analysis_date: datetime, data_period_days: int) -> Tuple[Optional[datetime], Optional[int]]:
        """クラッシュ時期の推定"""
        if tc <= 1.0:
            return None, None  # 既にクラッシュ済み？
        
        # tcから相対的日数を推定（簡易計算）
        # tc = 1 + (days_until_crash / data_period_days)
        days_until = (tc - 1.0) * data_period_days
        
        if days_until > 365:  # 1年以上先は信頼性低い
            return None, None
        
        estimated_date = analysis_date + timedelta(days=int(days_until))
        return estimated_date, int(days_until)
    
    def _generate_investment_recommendation(self, alert: CrashAlert) -> Tuple[str, str]:
        """投資推奨の生成"""
        risk = alert.risk_level
        urgency = alert.urgency_level
        confidence = alert.confidence_score
        
        # アクション推奨
        if risk == RiskLevel.CRITICAL and urgency == UrgencyLevel.IMMEDIATE:
            action = "🚨 即座に売りポジション検討・保有資産の保護実行"
            sizing = "大きめ（資産の15-25%）"
        elif risk == RiskLevel.CRITICAL and urgency == UrgencyLevel.NEAR_TERM:
            action = "⚠️ 売りポジション準備・段階的な資産保護"
            sizing = "中程度（資産の10-20%）"
        elif risk == RiskLevel.HIGH:
            action = "📉 ショートポジション検討・リスク資産の削減"
            sizing = "小〜中程度（資産の5-15%）"
        elif risk == RiskLevel.MEDIUM:
            action = "👀 継続監視・必要に応じて保護準備"
            sizing = "小さめ（資産の3-8%）"
        else:
            action = "📊 定期的な分析継続"
            sizing = "ポジション取りは推奨せず"
        
        return action, sizing
    
    def scan_for_alerts(self, min_confidence: float = 60.0, max_results: int = 20) -> List[CrashAlert]:
        """
        警告スキャンの実行
        
        Args:
            min_confidence: 最小信頼度
            max_results: 最大結果数
            
        Returns:
            List[CrashAlert]: 警告リスト（優先度順）
        """
        alerts = []
        
        try:
            # データベースから最新の分析結果を取得
            with sqlite3.connect(self.database_path) as conn:
                query = """
                SELECT 
                    symbol, tc, beta, omega, phi, A, B, C, r_squared, rmse,
                    analysis_date, data_period_start, data_period_end, data_points
                FROM lppl_analysis_results 
                WHERE analysis_date >= date('now', '-7 days')
                ORDER BY analysis_date DESC
                """
                
                df = pd.read_sql_query(query, conn)
                
                if df.empty:
                    print("📊 警告スキャン: 最近の分析結果が見つかりません")
                    return alerts
        
        except Exception as e:
            print(f"❌ データベース読み込みエラー: {e}")
            return alerts
        
        # 各分析結果を評価
        for _, row in df.iterrows():
            symbol = row['symbol']
            symbol_info = self._get_symbol_info(symbol)
            
            if not symbol_info:
                continue  # 未知のシンボルはスキップ
            
            # 分析日付の処理
            analysis_date = pd.to_datetime(row['analysis_date'])
            data_points = row['data_points'] if pd.notna(row['data_points']) else 0
            
            # リスク・緊急度の判定
            risk_level = self._determine_risk_level(row['tc'], row['r_squared'])
            urgency_level = self._determine_urgency_level(row['tc'])
            
            # 信頼度スコアの計算
            confidence_score = self._calculate_confidence_score(
                row['tc'], row['r_squared'], row['beta'], data_points
            )
            
            # 最小信頼度チェック
            if confidence_score < min_confidence:
                continue
            
            # クラッシュ時期の推定
            estimated_crash_date, days_until_crash = self._estimate_crash_timing(
                row['tc'], analysis_date, data_points
            )
            
            # 警告オブジェクトの作成
            alert = CrashAlert(
                symbol=symbol,
                display_name=symbol_info.get('display_name', symbol),
                asset_class=symbol_info.get('asset_class', 'unknown'),
                instrument_type=symbol_info.get('instrument_type', 'unknown'),
                tc=row['tc'],
                beta=row['beta'],
                omega=row['omega'],
                r_squared=row['r_squared'],
                rmse=row['rmse'],
                risk_level=risk_level,
                urgency_level=urgency_level,
                confidence_score=confidence_score,
                estimated_crash_date=estimated_crash_date,
                days_until_crash=days_until_crash,
                analysis_date=analysis_date,
                data_period_days=data_points
            )
            
            # 投資推奨の生成
            action, sizing = self._generate_investment_recommendation(alert)
            alert.recommended_action = action
            alert.position_sizing = sizing
            
            alerts.append(alert)
        
        # 優先度でソート（リスクレベル > 緊急度 > 信頼度）
        alerts.sort(key=lambda x: (
            -list(RiskLevel).index(x.risk_level),  # リスクレベル高い順
            -list(UrgencyLevel).index(x.urgency_level),  # 緊急度高い順
            -x.confidence_score  # 信頼度高い順
        ))
        
        return alerts[:max_results]
    
    def generate_alert_report(self, alerts: List[CrashAlert]) -> str:
        """警告レポートの生成"""
        if not alerts:
            return "📊 現在、高確度のクラッシュ警告はありません。"
        
        report = "🚨 差し迫ったクラッシュ警告レポート\n"
        report += "=" * 60 + "\n"
        report += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"警告件数: {len(alerts)}\n\n"
        
        # カテゴリ別統計
        risk_counts = {}
        urgency_counts = {}
        
        for alert in alerts:
            risk_counts[alert.risk_level] = risk_counts.get(alert.risk_level, 0) + 1
            urgency_counts[alert.urgency_level] = urgency_counts.get(alert.urgency_level, 0) + 1
        
        report += "📊 警告分布:\n"
        report += f"   🔴 CRITICAL: {risk_counts.get(RiskLevel.CRITICAL, 0)}\n"
        report += f"   🟠 HIGH: {risk_counts.get(RiskLevel.HIGH, 0)}\n"
        report += f"   🟡 MEDIUM: {risk_counts.get(RiskLevel.MEDIUM, 0)}\n\n"
        
        # 個別警告詳細
        report += "📋 個別警告詳細:\n"
        report += "-" * 60 + "\n"
        
        for i, alert in enumerate(alerts, 1):
            # リスクレベルのアイコン
            risk_icons = {
                RiskLevel.CRITICAL: "🚨",
                RiskLevel.HIGH: "⚠️",
                RiskLevel.MEDIUM: "🟡",
                RiskLevel.LOW: "🔵"
            }
            
            urgency_icons = {
                UrgencyLevel.IMMEDIATE: "⏰",
                UrgencyLevel.NEAR_TERM: "📅",
                UrgencyLevel.SHORT_TERM: "📆",
                UrgencyLevel.LONG_TERM: "🗓️"
            }
            
            risk_icon = risk_icons.get(alert.risk_level, "❓")
            urgency_icon = urgency_icons.get(alert.urgency_level, "❓")
            
            report += f"{i}. {risk_icon} {alert.display_name} ({alert.symbol})\n"
            report += f"   アセットクラス: {alert.asset_class} | タイプ: {alert.instrument_type}\n"
            report += f"   tc={alert.tc:.4f} | R²={alert.r_squared:.3f} | 信頼度={alert.confidence_score:.1f}%\n"
            
            if alert.days_until_crash:
                report += f"   {urgency_icon} 推定クラッシュまで: {alert.days_until_crash}日\n"
                if alert.estimated_crash_date:
                    report += f"   推定日: {alert.estimated_crash_date.strftime('%Y-%m-%d')}\n"
            
            report += f"   💡 推奨アクション: {alert.recommended_action}\n"
            report += f"   📊 ポジションサイズ: {alert.position_sizing}\n"
            report += "\n"
        
        # 重要な注意事項
        report += "⚠️ 重要な注意事項:\n"
        report += "- この予測は統計的モデルに基づく推定です\n"
        report += "- 投資判断は複数の情報源を参考に行ってください\n"
        report += "- リスク管理を徹底し、許容範囲外の損失は避けてください\n"
        report += "- 市場状況は急変する可能性があります\n"
        
        return report
    
    def save_alerts_to_json(self, alerts: List[CrashAlert], file_path: str):
        """警告リストをJSONファイルに保存"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'alert_count': len(alerts),
            'alerts': [alert.to_dict() for alert in alerts]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 警告データ保存: {file_path}")

def main():
    """デモンストレーション"""
    print("🚨 差し迫ったクラッシュ警告システム デモ")
    print("=" * 50)
    
    # システム初期化
    alert_system = CrashAlertSystem()
    
    # 警告スキャン実行
    alerts = alert_system.scan_for_alerts(min_confidence=60.0, max_results=10)
    
    # レポート生成・表示
    report = alert_system.generate_alert_report(alerts)
    print(report)
    
    # JSON保存
    if alerts:
        output_dir = Path("results/crash_alerts")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = output_dir / f"crash_alerts_{timestamp}.json"
        
        alert_system.save_alerts_to_json(alerts, str(json_file))

if __name__ == "__main__":
    main()