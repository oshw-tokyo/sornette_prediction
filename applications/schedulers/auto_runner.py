#!/usr/bin/env python3
"""
NASDAQ自動解析実行（対話なし）
ダッシュボード表示用データの蓄積
"""

import sys
import os
sys.path.append('.')

from scheduled_nasdaq_analysis import NASDAQAnalysisScheduler

def main():
    """自動実行（対話なし）"""
    print("🚀 NASDAQ自動解析実行開始")
    print("=" * 50)
    
    scheduler = NASDAQAnalysisScheduler()
    
    print("🎯 実行設定:")
    print("対象銘柄: NASDAQCOM (FRED)")
    print("解析期間: 過去4週間 + 現在 (計5回)")
    print("データ期間: 各解析で過去365日")
    print("目的: ダッシュボード表示用時系列データの蓄積")
    print()
    
    # 自動実行（確認なし）
    scheduler.run_full_schedule(delay_seconds=2)  # 短い待機時間

if __name__ == "__main__":
    main()