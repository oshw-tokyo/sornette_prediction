#!/usr/bin/env python3
"""
NASDAQ時系列解析スケジュール実行
複数期間でのデータ蓄積によるダッシュボード表示テスト
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

class NASDAQAnalysisScheduler:
    """NASDAQ解析スケジューラー"""
    
    def __init__(self):
        """初期化"""
        self.symbol = "NASDAQCOM"  # FREDでのNASDAQ指数
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
            start_date = end_date - timedelta(days=365)  # 1年間のデータ
            
            schedule.append({
                'analysis_id': f"nasdaq_w{weeks_ago}",
                'analysis_date': analysis_date,
                'start_date': start_date,
                'end_date': end_date,
                'window_days': 365,
                'description': f"{weeks_ago}週間前の解析"
            })
        
        # 現在の解析も追加
        schedule.append({
            'analysis_id': "nasdaq_current",
            'analysis_date': base_date,
            'start_date': base_date - timedelta(days=365),
            'end_date': base_date,
            'window_days': 365,
            'description': "最新の解析"
        })
        
        return schedule
    
    def get_nasdaq_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        NASDAQデータを取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            pd.DataFrame: 価格データ
        """
        try:
            print(f"📊 データ取得: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
            
            # FRED APIでNASDAQデータ取得（FRED強制指定）
            data, source = self.data_client.get_data_with_fallback(
                self.symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                preferred_source='fred'  # FRED強制指定
            )
            
            if data is not None and not data.empty:
                print(f"✅ データ取得成功: {len(data)}件 (Source: {source})")
                return data
            else:
                print("⚠️  データ取得失敗")
                return None
                
        except Exception as e:
            print(f"❌ データ取得エラー: {str(e)}")
            return None
    
    def run_analysis(self, schedule_item: dict) -> bool:
        """
        個別解析を実行
        
        Args:
            schedule_item: スケジュール項目
            
        Returns:
            bool: 成功/失敗
        """
        try:
            print(f"\n🔬 解析実行: {schedule_item['description']}")
            print(f"   ID: {schedule_item['analysis_id']}")
            print(f"   期間: {schedule_item['start_date'].strftime('%Y-%m-%d')} - {schedule_item['end_date'].strftime('%Y-%m-%d')}")
            
            # データ取得
            data = self.get_nasdaq_data(
                schedule_item['start_date'],
                schedule_item['end_date']
            )
            
            if data is None or data.empty:
                print("❌ データが取得できないため解析をスキップ")
                return False
            
            # フィッティング実行
            print("🔧 LPPLフィッティング実行中...")
            
            # 包括的フィッティング実行
            try:
                fitting_result = self.selector.perform_comprehensive_fitting(data)
                
                if fitting_result and fitting_result.all_candidates:
                    # 最適候補を取得
                    best_result = fitting_result.get_selected_result()
                    if best_result:
                        print(f"✅ フィッティング成功: R²={best_result.r_squared:.4f}")
                        
                        # データベース保存（fitting_resultをそのまま使用）
                        analysis_id = self.db_saver.save_lppl_analysis(
                            symbol=self.symbol,
                            data=data,
                            result=fitting_result,
                            data_source="fred"
                        )
                        
                        if analysis_id > 0:
                            print(f"💾 データベース保存成功: Analysis ID={analysis_id}")
                            return True
                        else:
                            print("❌ データベース保存失敗")
                            return False
                    else:
                        print("❌ 最適候補の選択に失敗")
                        return False
                else:
                    print("❌ フィッティング候補が見つかりません")
                    return False
            except Exception as e:
                print(f"❌ フィッティングエラー: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ 解析エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_full_schedule(self, delay_seconds: int = 5):
        """
        完全スケジュール実行
        
        Args:
            delay_seconds: 解析間の待機時間
        """
        print("🚀 NASDAQ時系列解析スケジュール開始")
        print("=" * 60)
        
        schedule = self.create_analysis_schedule()
        
        print(f"📋 スケジュール概要:")
        for item in schedule:
            print(f"  - {item['description']}: {item['analysis_date'].strftime('%Y-%m-%d')}")
        
        successful_analyses = 0
        total_analyses = len(schedule)
        
        for i, item in enumerate(schedule, 1):
            print(f"\n📊 進捗: {i}/{total_analyses}")
            
            success = self.run_analysis(item)
            if success:
                successful_analyses += 1
            
            # API制限対策の待機
            if i < total_analyses:
                print(f"⏳ 待機中... ({delay_seconds}秒)")
                time.sleep(delay_seconds)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📈 解析完了サマリー")
        print("=" * 60)
        print(f"✅ 成功: {successful_analyses}/{total_analyses} ({successful_analyses/total_analyses*100:.1f}%)")
        
        if successful_analyses > 0:
            print("\n🎯 次のステップ:")
            print("1. ダッシュボード起動: ./start_symbol_dashboard.sh")
            print("2. ブラウザアクセス: http://localhost:8501")
            print(f"3. 銘柄選択: {self.symbol}")
            print("4. 予測履歴とトレンドを確認")
        else:
            print("\n🔧 トラブルシューティング:")
            print("1. API設定の確認")
            print("2. インターネット接続の確認")
            print("3. データソースの確認")

def main():
    """メイン実行"""
    scheduler = NASDAQAnalysisScheduler()
    
    print("🎯 NASDAQ解析スケジュール設定")
    print("=" * 40)
    print("対象銘柄: NASDAQCOM (FRED)")
    print("解析期間: 過去4週間 + 現在")
    print("データ期間: 各解析で過去365日")
    print("目的: 時系列予測履歴の蓄積")
    
    # 実行確認
    response = input("\n解析を開始しますか？ (y/n): ")
    if response.lower() in ['y', 'yes']:
        scheduler.run_full_schedule()
    else:
        print("解析をキャンセルしました")

if __name__ == "__main__":
    main()