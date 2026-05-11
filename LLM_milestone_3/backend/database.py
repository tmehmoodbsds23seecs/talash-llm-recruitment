import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "talash.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            raw_text TEXT,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            degree TEXT,
            specialization TEXT,
            institution TEXT,
            start_year TEXT,
            end_year TEXT,
            marks TEXT,
            level TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            job_title TEXT,
            organization TEXT,
            start_date TEXT,
            end_date TEXT,
            description TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            skill_name TEXT,
            category TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            title TEXT,
            venue TEXT,
            year TEXT,
            authors TEXT,
            paper_type TEXT,
            authors_position TEXT,
            issn_doi TEXT,
            verified INTEGER DEFAULT 0,
            verification_detail TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            book_name TEXT,
            authors TEXT,
            isbn TEXT,
            publisher TEXT,
            year TEXT,
            link TEXT,
            verified INTEGER DEFAULT 0,
            verification_detail TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            patent_number TEXT,
            title TEXT,
            date TEXT,
            inventors TEXT,
            country TEXT,
            link TEXT,
            verified INTEGER DEFAULT 0,
            verification_detail TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supervision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            student_name TEXT,
            degree_level TEXT,
            role TEXT,
            year TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            section TEXT,
            analysis_output TEXT,
            score INTEGER DEFAULT 0,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            UNIQUE(candidate_id, section)
        )
    """)

    conn.commit()

    try:
        cursor.execute("ALTER TABLE publications ADD COLUMN issn_doi TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")