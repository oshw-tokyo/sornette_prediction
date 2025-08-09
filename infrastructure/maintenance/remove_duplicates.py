#!/usr/bin/env python3
"""
重複データ削除スクリプト

同一銘柄・同一基準日の重複レコードのうち、
最新の分析日のものを残し、古いものを削除する
"""

import sqlite3
import os
import sys

def remove_duplicates(db_path: str):
    """重複データを削除"""
    
    if not os.path.exists(db_path):
        print(f"❌ データベースが見つかりません: {db_path}")
        return False
    
    # バックアップ作成
    backup_path = f"{db_path}.backup_{int(__import__('time').time())}"
    os.system(f"cp {db_path} {backup_path}")
    print(f"📋 バックアップ作成: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 重複確認
        cursor.execute('''
            SELECT symbol, analysis_basis_date, COUNT(*) as count
            FROM analysis_results
            GROUP BY symbol, analysis_basis_date
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        ''')
        duplicates = cursor.fetchall()
        
        if not duplicates:
            print("✅ 重複データはありません")
            return True
        
        print(f"⚠️ {len(duplicates)}組の重複データを発見")
        
        total_deleted = 0
        for symbol, basis_date, count in duplicates:
            print(f"  {symbol} {basis_date}: {count}件")
            
            # 最新の分析日以外を削除
            cursor.execute('''
                DELETE FROM analysis_results
                WHERE symbol = ? AND analysis_basis_date = ?
                AND id NOT IN (
                    SELECT id FROM analysis_results
                    WHERE symbol = ? AND analysis_basis_date = ?
                    ORDER BY analysis_date DESC
                    LIMIT 1
                )
            ''', (symbol, basis_date, symbol, basis_date))
            
            deleted = cursor.rowcount
            total_deleted += deleted
            print(f"    → {deleted}件削除")
        
        conn.commit()
        print(f"✅ 合計 {total_deleted}件の重複レコードを削除")
        
        # 最終確認
        cursor.execute('SELECT COUNT(*) FROM analysis_results')
        final_count = cursor.fetchone()[0]
        print(f"📊 残りレコード数: {final_count}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ エラーが発生しました: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, "results", "analysis_results.db")
    
    print("🔧 重複データ削除開始")
    print("=" * 50)
    
    success = remove_duplicates(db_path)
    
    if success:
        print("\n✅ 重複削除完了")
    else:
        print("\n❌ 重複削除失敗")
        sys.exit(1)