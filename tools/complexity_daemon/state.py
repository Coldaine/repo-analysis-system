"""State management for the complexity daemon."""

import sqlite3
import datetime

def get_db_connection(db_path: str):
    """Gets a database connection."""
    return sqlite3.connect(db_path)

def init_db(db_path: str):
    """Initializes the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            last_commit_hash TEXT,
            cumulative_delta INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_complexities (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            complexity INTEGER NOT NULL,
            last_calculated TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repos (id),
            UNIQUE (repo_id, file_path)
        )
    """)
    conn.commit()
    conn.close()

def get_repo_id(conn, repo_path: str) -> int:
    """Gets the ID of a repository."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM repos WHERE path = ?", (repo_path,))
    result = cursor.fetchone()
    if result:
        return result[0]

    # If the repo doesn't exist, create it
    cursor.execute("INSERT INTO repos (path) VALUES (?)", (repo_path,))
    conn.commit()
    return cursor.lastrowid

def get_cumulative_delta(conn, repo_id: int) -> int:
    """Gets the cumulative delta for a repository."""
    cursor = conn.cursor()
    cursor.execute("SELECT cumulative_delta FROM repos WHERE id = ?", (repo_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_cumulative_delta(conn, repo_id: int, delta: int):
    """Updates the cumulative delta for a repository."""
    cursor = conn.cursor()
    cursor.execute("UPDATE repos SET cumulative_delta = cumulative_delta + ? WHERE id = ?", (delta, repo_id))
    conn.commit()

def reset_cumulative_delta(conn, repo_id: int):
    """Resets the cumulative delta for a repository."""
    cursor = conn.cursor()
    cursor.execute("UPDATE repos SET cumulative_delta = 0 WHERE id = ?", (repo_id,))
    conn.commit()

def get_file_complexity(conn, repo_id: int, file_path: str) -> int:
    """Gets the complexity of a file."""
    cursor = conn.cursor()
    cursor.execute("SELECT complexity FROM file_complexities WHERE repo_id = ? AND file_path = ?", (repo_id, file_path))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_file_complexity(conn, repo_id: int, file_path: str, complexity: int):
    """Updates the complexity of a file."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO file_complexities (repo_id, file_path, complexity, last_calculated)
        VALUES (?, ?, ?, ?)
    """, (repo_id, file_path, complexity, now))
    conn.commit()
