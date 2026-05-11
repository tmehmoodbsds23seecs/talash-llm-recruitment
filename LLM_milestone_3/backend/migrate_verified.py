import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "talash.db")

def migrate():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    tables_to_verify = ["publications", "books", "patents"]
    
    for table in tables_to_verify:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN verified INTEGER DEFAULT 0")
            print(f"Added 'verified' column to {table}")
        except sqlite3.OperationalError:
            print(f"Column 'verified' already exists in {table} or table missing.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
