import sqlite3
import os

db_path = r'd:\UNIVERSITY\6th Semester\asifpapa\talash.db'

if not os.path.exists(db_path):
    print(f"❌ Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists first
    cursor.execute("PRAGMA table_info(analysis_results)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'score' not in columns:
        print("Adding 'score' column to analysis_results...")
        cursor.execute("ALTER TABLE analysis_results ADD COLUMN score INTEGER DEFAULT 0")
        conn.commit()
        print("✅ SUCCESS: Score column added!")
    else:
        print("ℹ️ Info: Score column already exists.")
        
    conn.close()
except Exception as e:
    print(f"❌ ERROR: {e}")
