#!/usr/bin/env python3
"""
AAPL (Apple Inc.) 時系列解析スケジュール実行
Alpha Vantage API による個別株式分析
"""

import sys
import os
sys.path.append('.')

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
import pandas as pd
from src.fitting.fitter import LogarithmPeriodicFitter
from src.fitting.multi_criteria_selection import MultiCriteriaSelector
from src.database.integration_helpers import AnalysisResultSaver
from src.data_sources.unified_data_client import UnifiedDataClient
import time

class AAPLAnalysisScheduler:
    """AAPL解析スケジューラー（Alpha Vantage専用）"""
    
    def __init__(self):
        """初期化"""
        self.symbol = "AAPL"  # Apple Inc.
        self.data_client = UnifiedDataClient()
        self.fitter = LogarithmPeriodicFitter()
        self.selector = MultiCriteriaSelector()
        self.db_saver = AnalysisResultSaver()
        
    def create_analysis_schedule(self) -> list:
        """
        解析スケジュールを作成
        
        Returns:
            list: 解析スケジュール
        """
        base_date = datetime.now()
        
        # 週次スケジュール（過去4週間分）
        schedule = []
        for weeks_ago in range(4, 0, -1):
            analysis_date = base_date - timedelta(weeks=weeks_ago)
            end_date = analysis_date
            start_date = end_date - timedelta(days=730)  # 2年間のデータ（個別株は長期トレンド重要）
            
            schedule.append({
                'analysis_id': f"aapl_w{weeks_ago}",
                'analysis_date': analysis_date,
                'start_date': start_date,
                'end_date': end_date,
                'window_days': 730,
                'description': f"{weeks_ago}週間前のAAPL解析"
            })
        
        # 現在の解析も追加
        schedule.append({
            'analysis_id': "aapl_current",
            'analysis_date': base_date,
            'start_date': base_date - timedelta(days=730),
            'end_date': base_date,
            'window_days': 730,
            'description': "最新のAAPL解析"
        })
        
        return schedule
    
    def get_aapl_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        AAPLデータを取得（Alpha Vantage強制指定）
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            pd.DataFrame: 価格データ
        """
        try:
            print(f"📊 AAPL データ取得: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
            
            # Alpha Vantage API でAAPLデータ取得（強制指定）
            data, source = self.data_client.get_data_with_fallback(
                self.symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                preferred_source='alpha_vantage'  # Alpha Vantage強制
            )
            
            if data is not None and not data.empty:
                print(f"✅ AAPL データ取得成功: {len(data)}件 (Source: {source})")
                return data
            else:
                print("⚠️  AAPL データ取得失敗")
                return None
                
        except Exception as e:
            print(f"❌ AAPL データ取得エラー: {str(e)}")
            return None
    
    def run_analysis(self, schedule_item: dict) -> bool:
        """
        個別AAPL解析を実行
        
        Args:
            schedule_item: スケジュール項目
            
        Returns:
            bool: 成功/失敗
        """
        try:
            print(f"\n🍎 AAPL解析実行: {schedule_item['description']}")
            print(f"   ID: {schedule_item['analysis_id']}")
            print(f"   期間: {schedule_item['start_date'].strftime('%Y-%m-%d')} - {schedule_item['end_date'].strftime('%Y-%m-%d')}")
            
            # データ取得
            data = self.get_aapl_data(
                schedule_item['start_date'],
                schedule_item['end_date']
            )
            
            if data is None or data.empty:
                print("❌ AAPLデータが取得できないため解析をスキップ")
                return False
            
            # フィッティング実行
            print("🔧 AAPL LPPLフィッティング実行中...")
            
            # 包括的フィッティング実行
            try:
                fitting_result = self.selector.perform_comprehensive_fitting(data)
                
                if fitting_result and fitting_result.all_candidates:
                    # 最適候補を取得
                    best_result = fitting_result.get_selected_result()
                    if best_result:
                        print(f"✅ AAPL フィッティング成功: R²={best_result.r_squared:.4f}")
                        
                        # データベース保存（fitting_resultをそのまま使用）
                        analysis_id = self.db_saver.save_lppl_analysis(
                            symbol=self.symbol,
                            data=data,
                            result=fitting_result,
                            data_source="alpha_vantage"
                        )
                        
                        if analysis_id > 0:
                            print(f"💾 AAPL データベース保存成功: Analysis ID={analysis_id}")
                            return True
                        else:
                            print("❌ AAPL データベース保存失敗")
                            return False
                    else:
                        print("❌ AAPL 最適候補の選択に失敗")
                        return False
                else:
                    print("❌ AAPL フィッティング候補が見つかりません")
                    return False
            except Exception as e:
                print(f"❌ AAPL フィッティングエラー: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ AAPL 解析エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_full_schedule(self, delay_seconds: int = 12):
        """
        完全AAPL スケジュール実行
        
        Args:
            delay_seconds: 解析間の待機時間（Alpha Vantage制限対策: 12秒）
        """
        print("🍎 AAPL (Apple Inc.) 時系列解析スケジュール開始")
        print("=" * 60)
        
        schedule = self.create_analysis_schedule()
        
        print(f"📋 AAPL スケジュール概要:")
        for item in schedule:
            print(f"  - {item['description']}: {item['analysis_date'].strftime('%Y-%m-%d')}")
        
        print(f"\n🔒 API制限対策: Alpha Vantage 5calls/min → {delay_seconds}秒間隔")
        
        successful_analyses = 0
        total_analyses = len(schedule)
        
        for i, item in enumerate(schedule, 1):
            print(f"\n📊 AAPL 進捗: {i}/{total_analyses}")
            
            success = self.run_analysis(item)
            if success:
                successful_analyses += 1
            
            # Alpha Vantage API制限対策の待機（重要）
            if i < total_analyses:
                print(f"⏳ Alpha Vantage制限対策 待機中... ({delay_seconds}秒)")
                time.sleep(delay_seconds)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📈 AAPL 解析完了サマリー")
        print("=" * 60)
        print(f"✅ 成功: {successful_analyses}/{total_analyses} ({successful_analyses/total_analyses*100:.1f}%)")
        
        if successful_analyses > 0:
            print("\n🎯 次のステップ:")
            print("1. ダッシュボード起動: ./start_symbol_dashboard.sh")
            print("2. ブラウザアクセス: http://localhost:8501")
            print(f"3. 銘柄選択: {self.symbol} (Apple Inc.)")
            print("4. AAPL予測履歴とトレンドを確認")
            print("5. NASDAQ(FRED)とAAPL(Alpha Vantage)の比較分析")
        else:
            print("\n🔧 AAPL トラブルシューティング:")
            print("1. Alpha Vantage API設定の確認")
            print("2. インターネット接続の確認")
            print("3. Alpha Vantage API制限の確認（75calls/day, 5calls/min）")
            print("4. .env ファイルの ALPHA_VANTAGE_KEY 確認")

def main():
    """メイン実行"""
    scheduler = AAPLAnalysisScheduler()
    
    print("🍎 AAPL (Apple Inc.) 解析スケジュール設定")
    print("=" * 50)
    print("対象銘柄: AAPL (Apple Inc.)")
    print("データソース: Alpha Vantage API")
    print("解析期間: 過去4週間 + 現在")
    print("データ期間: 各解析で過去730日（2年間）")
    print("目的: 個別株式の時系列予測履歴蓄積")
    print("特徴: FREDでは取得不可の個別株式分析")
    
    # 実行確認
    response = input("\nAAPL解析を開始しますか？ (y/n): ")
    if response.lower() in ['y', 'yes']:
        scheduler.run_full_schedule()
    else:
        print("AAPL解析をキャンセルしました")

if __name__ == "__main__":
    main()