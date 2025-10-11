#!/usr/bin/env python3
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from infrastructure.database.fco_results_database import FCOResultsDatabase
import sqlite3

# Create database instance
db = FCOResultsDatabase()
print(f"Default DB path: {db.db_path}")

# Try with absolute path
db_abs = FCOResultsDatabase(db_path="/home/no-rules/projects/12_sornnet_prediction/sornette_prediction/results/fco_analysis_results.db")
print(f"Absolute DB path: {db_abs.db_path}")

# Check if file exists
import os
if os.path.exists(db_abs.db_path):
    print(f"✅ Database file exists at: {db_abs.db_path}")
    
    # Try to query it
    with sqlite3.connect(db_abs.db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT symbol FROM fco_analysis_results ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(symbols)} symbols: {symbols[:5]}...")
else:
    print("❌ Database file not found")
