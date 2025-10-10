#!/usr/bin/env python3
"""
価格データ保存用テーブルの作成スクリプト
"""

import sqlite3
import os
from pathlib import Path


def create_price_data_tables(db_path: str = "results/fco_analysis_results.db"):
    """価格データ保存用テーブルを作成"""

    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 市場価格データテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume REAL,
                -- ログスケール変換済みデータ（計算負荷削減用）
                log_open REAL,
                log_high REAL,
                log_low REAL,
                log_close REAL,

                -- データソース情報
                data_source TEXT,  -- 'fred', 'twelvedata', 'yahoo', etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- インデックス用
                UNIQUE(symbol, date)
            )
        """)

        # パフォーマンス用インデックス
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_symbol_date
            ON market_price_data(symbol, date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_date
            ON market_price_data(date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_symbol
            ON market_price_data(symbol)
        """)

        print("✅ Created market_price_data table")

        # 2. LPPLフィット結果保存テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lppl_fitted_curves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,

                -- フィット期間
                fit_start_date DATE NOT NULL,
                fit_end_date DATE NOT NULL,
                num_points INTEGER NOT NULL,

                -- LPPLパラメータ（再計算用）
                tc REAL,      -- Critical time
                m REAL,       -- Power law exponent
                omega REAL,   -- Log-periodic frequency
                phi REAL,     -- Phase
                a REAL,       -- Linear parameter
                b REAL,       -- Power law amplitude
                c REAL,       -- Log-periodic amplitude

                -- フィット品質
                r_squared REAL,
                rmse REAL,
                damping REAL,

                -- フィット済み曲線データ（JSON配列）
                fitted_values TEXT,  -- JSON array of fitted log prices
                dates TEXT,          -- JSON array of corresponding dates

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (analysis_id) REFERENCES fco_analysis_results(id) ON DELETE CASCADE,
                UNIQUE(analysis_id, symbol, fit_end_date)
            )
        """)

        # インデックス
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lppl_analysis_id
            ON lppl_fitted_curves(analysis_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lppl_symbol
            ON lppl_fitted_curves(symbol)
        """)

        print("✅ Created lppl_fitted_curves table")

        # コミット
        conn.commit()
        print("\n✅ All tables created successfully!")

        # テーブル情報を表示
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%price%' OR name LIKE '%lppl%'
        """)
        tables = cursor.fetchall()
        print("\n📊 Related tables in database:")
        for table in tables:
            print(f"  - {table[0]}")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()

    finally:
        conn.close()


def check_table_schema(db_path: str = "results/fco_analysis_results.db"):
    """作成したテーブルのスキーマを確認"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ['market_price_data', 'lppl_fitted_curves']

    for table in tables:
        print(f"\n📋 Schema for {table}:")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        if columns:
            for col in columns:
                print(f"  {col[1]:20s} {col[2]:15s} {'NOT NULL' if col[3] else 'NULL'}")
        else:
            print(f"  Table {table} does not exist")

    conn.close()


if __name__ == "__main__":
    # プロジェクトルートから実行
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "results" / "fco_analysis_results.db"

    print(f"📂 Database path: {db_path}")
    print(f"📊 Creating price data tables...\n")

    # テーブル作成
    create_price_data_tables(str(db_path))

    # スキーマ確認
    check_table_schema(str(db_path))