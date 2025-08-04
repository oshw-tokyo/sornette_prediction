#!/usr/bin/env python3
"""
自動スケジューラー・継続実行システム

定期的な分析実行とアラート通知の自動化
"""

import schedule
import time
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import logging
import sys
import os

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.monitoring.multi_market_monitor import MultiMarketMonitor, MarketIndex, TimeWindow
from src.data_management.prediction_database import PredictionDatabase, PredictionRecord

class AlertNotifier:
    """アラート通知システム"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 通知設定（SMTP、Slack、Teams等）
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_email_alert(self, subject: str, content: str, recipients: List[str]):
        """メールアラート送信"""
        
        try:
            smtp_config = self.config.get('smtp', {})
            
            if not smtp_config:
                self.logger.warning("SMTP設定がありません")
                return False
            
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = smtp_config['sender']
            msg['Subject'] = subject
            
            # HTML形式のコンテンツ
            html_content = f"""
            <html>
                <body>
                    <h2>Market Crash Prediction Alert</h2>
                    <p><strong>発生時刻:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <hr>
                    {content}
                    <hr>
                    <p><em>このアラートは自動生成されました。</em></p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 送信
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                if smtp_config.get('use_tls'):
                    server.starttls()
                
                if 'username' in smtp_config:
                    server.login(smtp_config['username'], smtp_config['password'])
                
                for recipient in recipients:
                    msg['To'] = recipient
                    server.send_message(msg)
                    del msg['To']
            
            self.logger.info(f"メールアラート送信完了: {len(recipients)}件")
            return True
            
        except Exception as e:
            self.logger.error(f"メールアラート送信エラー: {str(e)}")
            return False
    
    def send_slack_notification(self, message: str, channel: str = None):
        """Slack通知送信"""
        
        try:
            import requests
            
            slack_config = self.config.get('slack', {})
            webhook_url = slack_config.get('webhook_url')
            
            if not webhook_url:
                self.logger.warning("Slack webhook URLが設定されていません")
                return False
            
            payload = {
                'text': message,
                'username': 'Market Prediction Bot',
                'icon_emoji': ':chart_with_upwards_trend:'
            }
            
            if channel:
                payload['channel'] = channel
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            self.logger.info("Slack通知送信完了")
            return True
            
        except Exception as e:
            self.logger.error(f"Slack通知送信エラー: {str(e)}")
            return False

class PredictionScheduler:
    """予測スケジューラー"""
    
    def __init__(self, config_path: str = "config/scheduler_config.json"):
        """
        Args:
            config_path: 設定ファイルパス
        """
        self.config = self.load_config(config_path)
        self.monitor = MultiMarketMonitor()
        self.db = PredictionDatabase()
        self.notifier = AlertNotifier(self.config.get('notifications', {}))
        
        # ログ設定
        self.setup_logging()
        
        # スケジュール設定
        self.setup_schedules()
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        
        default_config = {
            'schedules': {
                'daily_analysis': '09:00',
                'weekly_report': 'monday 08:00',
                'monthly_cleanup': '1st 02:00'
            },
            'markets': ['NASDAQ', 'SP500', 'DJIA'],
            'windows': [365, 730, 1095],
            'alert_thresholds': {
                'critical_tc': 1.1,
                'high_risk_tc': 1.3,
                'min_confidence': 0.7
            },
            'notifications': {
                'smtp': {},
                'slack': {},
                'recipients': []
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
        
        return default_config
    
    def setup_logging(self):
        """ログ設定"""
        
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/scheduler.log'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def setup_schedules(self):
        """スケジュール設定"""
        
        schedules = self.config['schedules']
        
        # 日次分析
        if 'daily_analysis' in schedules:
            schedule.every().day.at(schedules['daily_analysis']).do(
                self.run_daily_analysis
            )
        
        # 週次レポート
        if 'weekly_report' in schedules:
            day, time_str = schedules['weekly_report'].split(' ')
            schedule.every().week.at(time_str).do(self.run_weekly_report)
        
        # 月次クリーンアップ
        if 'monthly_cleanup' in schedules:
            schedule.every().month.do(self.run_monthly_cleanup)
        
        # 緊急チェック（1時間毎）
        schedule.every().hour.do(self.run_emergency_check)
        
        self.logger.info("スケジュール設定完了")
    
    def run_daily_analysis(self):
        """日次分析の実行"""
        
        self.logger.info("日次分析開始")
        
        try:
            # 監視対象市場の設定
            markets = [MarketIndex(m) for m in self.config['markets']]
            windows = [TimeWindow(w) for w in self.config['windows'] if hasattr(TimeWindow, str(w))]
            
            # 分析実行
            self.monitor.markets = markets
            self.monitor.windows = windows
            
            snapshot = self.monitor.run_full_analysis()
            
            # 結果をデータベースに保存
            for result in snapshot.results:
                record = PredictionRecord(
                    market=result.market.value,
                    window_days=result.window_days,
                    start_date=result.start_date,
                    end_date=result.end_date,
                    tc=result.tc,
                    beta=result.beta,
                    omega=result.omega,
                    r_squared=result.r_squared,
                    rmse=result.rmse,
                    predicted_date=result.predicted_date,
                    tc_interpretation=result.tc_interpretation.value,
                    confidence_score=result.confidence_score
                )
                
                self.db.save_prediction(record)
                
                # アラート判定
                self.check_and_send_alerts(result)
            
            # 分析サマリー
            high_risk_count = len(snapshot.get_high_risk_markets())
            
            self.logger.info(f"日次分析完了: {len(snapshot.results)}件の分析、{high_risk_count}件の高リスク検出")
            
            # 日次サマリー通知
            if high_risk_count > 0:
                self.send_daily_summary(snapshot)
            
        except Exception as e:
            self.logger.error(f"日次分析エラー: {str(e)}")
    
    def run_weekly_report(self):
        """週次レポートの生成・送信"""
        
        self.logger.info("週次レポート生成開始")
        
        try:
            # 過去1週間のデータ取得
            week_ago = datetime.now() - timedelta(days=7)
            
            weekly_data = self.db.search_predictions({
                'date_from': week_ago.strftime('%Y-%m-%d')
            })
            
            if not weekly_data:
                self.logger.info("週次レポート: データなし")
                return
            
            # レポート生成
            report = self.generate_weekly_report(weekly_data)
            
            # レポート送信
            recipients = self.config['notifications'].get('recipients', [])
            
            if recipients:
                self.notifier.send_email_alert(
                    subject=f"Weekly Market Prediction Report - {datetime.now().strftime('%Y-%m-%d')}",
                    content=report,
                    recipients=recipients
                )
            
            # Slack通知
            slack_summary = self.generate_slack_weekly_summary(weekly_data)
            self.notifier.send_slack_notification(slack_summary)
            
            self.logger.info("週次レポート送信完了")
            
        except Exception as e:
            self.logger.error(f"週次レポート生成エラー: {str(e)}")
    
    def run_monthly_cleanup(self):
        """月次データクリーンアップ"""
        
        self.logger.info("月次クリーンアップ開始")
        
        try:
            # 古いデータの削除
            cleanup_days = self.config.get('cleanup_days', 365)
            self.db.cleanup_old_data(cleanup_days)
            
            # データベース統計
            stats = self.db.get_database_stats()
            
            self.logger.info(f"月次クリーンアップ完了: 予測データ{stats['predictions_count']}件")
            
        except Exception as e:
            self.logger.error(f"月次クリーンアップエラー: {str(e)}")
    
    def run_emergency_check(self):
        """緊急チェック（高リスク検出時の即座アラート）"""
        
        try:
            thresholds = self.config['alert_thresholds']
            
            # 最新の高リスク予測を確認
            critical_risks = self.db.get_current_risks(
                tc_threshold=thresholds['critical_tc'],
                confidence_threshold=thresholds['min_confidence']
            )
            
            # 新しい緊急アラートをチェック
            for risk in critical_risks:
                # 過去1時間以内に同じ市場でアラートが送信されているかチェック
                if not self.is_recent_alert_sent(risk['market'], risk['tc']):
                    self.send_emergency_alert(risk)
                    
                    # アラート履歴に記録
                    self.db.save_alert(
                        "CRITICAL_RISK",
                        risk['market'],
                        risk['tc'],
                        datetime.fromisoformat(risk['predicted_date']),
                        risk['confidence_score'],
                        f"緊急: tc={risk['tc']:.3f}の臨界的リスク検出"
                    )
            
        except Exception as e:
            self.logger.error(f"緊急チェックエラー: {str(e)}")
    
    def check_and_send_alerts(self, result):
        """個別結果のアラート判定・送信"""
        
        thresholds = self.config['alert_thresholds']
        
        if (result.confidence_score >= thresholds['min_confidence'] and
            result.tc <= thresholds['high_risk_tc']):
            
            alert_type = "CRITICAL" if result.tc <= thresholds['critical_tc'] else "HIGH_RISK"
            
            # アラート記録
            self.db.save_alert(
                alert_type,
                result.market.value,
                result.tc,
                result.predicted_date,
                result.confidence_score,
                f"{alert_type}リスク検出: tc={result.tc:.3f}"
            )
    
    def send_daily_summary(self, snapshot):
        """日次サマリーの送信"""
        
        high_risk_markets = snapshot.get_high_risk_markets()
        
        summary_content = f"""
        <h3>日次分析サマリー - {datetime.now().strftime('%Y-%m-%d')}</h3>
        <p><strong>高リスク市場数:</strong> {len(high_risk_markets)}</p>
        <ul>
        """
        
        for risk in high_risk_markets[:5]:  # 上位5件
            summary_content += f"""
            <li><strong>{risk.market.value}</strong>: 
                tc={risk.tc:.3f}, 
                予測日={risk.predicted_date.strftime('%Y-%m-%d')}, 
                信頼度={risk.confidence_score:.2f}
            </li>
            """
        
        summary_content += "</ul>"
        
        # Slack通知
        slack_msg = f"🚨 日次分析: {len(high_risk_markets)}市場で高リスク検出"
        self.notifier.send_slack_notification(slack_msg)
    
    def send_emergency_alert(self, risk_data):
        """緊急アラートの送信"""
        
        alert_content = f"""
        <h2>🚨 緊急市場アラート</h2>
        <p><strong>市場:</strong> {risk_data['market']}</p>
        <p><strong>tc値:</strong> {risk_data['tc']:.3f}</p>
        <p><strong>予測日:</strong> {risk_data['predicted_date'][:10]}</p>
        <p><strong>信頼度:</strong> {risk_data['confidence_score']:.2f}</p>
        <p><strong>緊急度:</strong> 🔴 CRITICAL</p>
        """
        
        # メール送信
        recipients = self.config['notifications'].get('emergency_recipients', 
                    self.config['notifications'].get('recipients', []))
        
        if recipients:
            self.notifier.send_email_alert(
                subject=f"🚨 EMERGENCY: {risk_data['market']} Critical Risk",
                content=alert_content,
                recipients=recipients
            )
        
        # Slack送信
        slack_msg = f"🚨 緊急アラート: {risk_data['market']} tc={risk_data['tc']:.3f}"
        self.notifier.send_slack_notification(slack_msg)
        
        self.logger.warning(f"緊急アラート送信: {risk_data['market']} tc={risk_data['tc']:.3f}")
    
    def is_recent_alert_sent(self, market: str, tc_value: float) -> bool:
        """最近同様のアラートが送信されているかチェック"""
        
        # 実装簡略化のため、ここではFalseを返す
        # 実際には過去1時間のアラート履歴をチェック
        return False
    
    def generate_weekly_report(self, weekly_data: List[Dict]) -> str:
        """週次レポートの生成"""
        
        df = pd.DataFrame(weekly_data)
        
        # 統計計算
        total_predictions = len(df)
        high_risk_count = len(df[df['tc'] <= 1.3])
        avg_confidence = df['confidence_score'].mean()
        
        # 市場別サマリー
        market_summary = df.groupby('market').agg({
            'tc': 'mean',
            'confidence_score': 'mean'
        }).round(3)
        
        report = f"""
        <h2>週次市場予測レポート</h2>
        <p><strong>期間:</strong> {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}</p>
        
        <h3>サマリー統計</h3>
        <ul>
            <li>総予測数: {total_predictions}</li>
            <li>高リスク市場数: {high_risk_count}</li>
            <li>平均信頼度: {avg_confidence:.3f}</li>
        </ul>
        
        <h3>市場別平均値</h3>
        <table border="1">
            <tr><th>市場</th><th>平均tc</th><th>平均信頼度</th></tr>
        """
        
        for market, data in market_summary.iterrows():
            report += f"<tr><td>{market}</td><td>{data['tc']:.3f}</td><td>{data['confidence_score']:.3f}</td></tr>"
        
        report += "</table>"
        
        return report
    
    def generate_slack_weekly_summary(self, weekly_data: List[Dict]) -> str:
        """週次Slackサマリーの生成"""
        
        df = pd.DataFrame(weekly_data)
        high_risk_count = len(df[df['tc'] <= 1.3])
        
        return f"📊 週次レポート: {len(df)}件の分析、{high_risk_count}件の高リスク検出"
    
    def start(self):
        """スケジューラーの開始"""
        
        self.logger.info("予測スケジューラー開始")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分毎にチェック
                
        except KeyboardInterrupt:
            self.logger.info("スケジューラー停止")
        except Exception as e:
            self.logger.error(f"スケジューラーエラー: {str(e)}")

def create_default_config():
    """デフォルト設定ファイルの作成"""
    
    config = {
        "schedules": {
            "daily_analysis": "09:00",
            "weekly_report": "monday 08:00", 
            "monthly_cleanup": "1st 02:00"
        },
        "markets": ["NASDAQ", "SP500", "DJIA"],
        "windows": [365, 730, 1095],
        "alert_thresholds": {
            "critical_tc": 1.1,
            "high_risk_tc": 1.3,
            "min_confidence": 0.7
        },
        "notifications": {
            "smtp": {
                "server": "smtp.gmail.com",
                "port": 587,
                "use_tls": True,
                "sender": "your-email@example.com",
                "username": "your-email@example.com",
                "password": "your-app-password"
            },
            "slack": {
                "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
            },
            "recipients": ["analyst@company.com"],
            "emergency_recipients": ["cto@company.com", "risk-manager@company.com"]
        },
        "cleanup_days": 365
    }
    
    os.makedirs('config', exist_ok=True)
    
    with open('config/scheduler_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("設定ファイルを作成しました: config/scheduler_config.json")
    print("必要に応じて通知設定を変更してください。")

def main():
    """メイン実行関数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="市場予測自動スケジューラー")
    parser.add_argument("--create-config", action="store_true", help="デフォルト設定ファイル作成")
    parser.add_argument("--config", default="config/scheduler_config.json", help="設定ファイルパス")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_default_config()
        return
    
    scheduler = PredictionScheduler(args.config)
    scheduler.start()

if __name__ == "__main__":
    main()