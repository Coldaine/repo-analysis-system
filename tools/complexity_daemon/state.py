"""State management for the complexity daemon."""

import sqlite3
import datetime
import logging
import threading
import contextlib

logger = logging.getLogger(__name__)

# Global lock for all database write operations to prevent corruption
_db_lock = threading.Lock()

@contextlib.contextmanager
def get_db_connection(db_path: str):
    """
    Context manager for database connections.
    Ensures the connection is closed even if errors occur.
    """
    conn = None
    try:
        # check_same_thread=False is necessary because the connection
        # is created in one thread and potentially used in another.
        # Serialization is handled by our own lock.
        conn = sqlite3.connect(db_path, check_same_thread=False)
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error on connection: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db(db_path: str):
    """Initializes the database schema and indexes."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            with _db_lock:
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
                # Add index for faster lookups
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON file_complexities (repo_id, file_path)")
                conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_repo_id(conn, repo_path: str) -> int:
    """Gets the ID of a repository, creating it if it doesn't exist."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM repos WHERE path = ?", (repo_path,))
        result = cursor.fetchone()
        if result:
            return result[0]

        with _db_lock:
            cursor.execute("INSERT INTO repos (path) VALUES (?)", (repo_path,))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Failed to get or create repo_id for {repo_path}: {e}")
        raise

def get_cumulative_delta(conn, repo_id: int) -> int:
    """Gets the cumulative delta for a repository."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT cumulative_delta FROM repos WHERE id = ?", (repo_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logger.error(f"Failed to get cumulative delta for repo_id {repo_id}: {e}")
        return 0

def update_cumulative_delta(conn, repo_id: int, delta: int):
    """Updates the cumulative delta for a repository."""
    try:
        with _db_lock:
            cursor = conn.cursor()
            cursor.execute("UPDATE repos SET cumulative_delta = cumulative_delta + ? WHERE id = ?", (delta, repo_id))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update cumulative delta for repo_id {repo_id}: {e}")
        raise

def reset_cumulative_delta(conn, repo_id: int):
    """Resets the cumulative delta for a repository."""
    try:
        with _db_lock:
            cursor = conn.cursor()
            cursor.execute("UPDATE repos SET cumulative_delta = 0 WHERE id = ?", (repo_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to reset cumulative delta for repo_id {repo_id}: {e}")
        raise

def get_file_complexity(conn, repo_id: int, file_path: str) -> int:
    """Gets the complexity of a file."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT complexity FROM file_complexities WHERE repo_id = ? AND file_path = ?", (repo_id, file_path))
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logger.error(f"Failed to get file complexity for {file_path}: {e}")
        return 0

def update_file_complexity(conn, repo_id: int, file_path: str, complexity: int):
    """Updates the complexity of a file."""
    try:
        with _db_lock:
            cursor = conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO file_complexities (repo_id, file_path, complexity, last_calculated)
                VALUES (?, ?, ?, ?)
            """, (repo_id, file_path, complexity, now))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update file complexity for {file_path}: {e}")
        raise

def delete_file_complexity(conn, repo_id: int, file_path: str):
    """Deletes the complexity record for a file."""
    try:
        with _db_lock:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM file_complexities WHERE repo_id = ? AND file_path = ?",
                (repo_id, file_path)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to delete file complexity for {file_path}: {e}")
        raise
