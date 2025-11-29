"""Tests for the state management component."""

import unittest
import os
import sqlite3
import threading
from tools.complexity_daemon.state import (
    get_db_connection,
    init_db,
    get_repo_id,
    get_cumulative_delta,
    update_cumulative_delta,
    reset_cumulative_delta,
    get_file_complexity,
    update_file_complexity,
    delete_file_complexity,
)

class TestState(unittest.TestCase):
    def setUp(self):
        self.db_path = "test.db"
        # Ensure the file does not exist from a previous failed run
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_repo_management(self):
        with get_db_connection(self.db_path) as conn:
            repo_path = "/path/to/repo"
            repo_id = get_repo_id(conn, repo_path)
            self.assertIsInstance(repo_id, int)
            # Test getting the same repo again
            repo_id_2 = get_repo_id(conn, repo_path)
            self.assertEqual(repo_id, repo_id_2)

    def test_cumulative_delta(self):
        with get_db_connection(self.db_path) as conn:
            repo_id = get_repo_id(conn, "/path/to/repo")
            self.assertEqual(get_cumulative_delta(conn, repo_id), 0)
            update_cumulative_delta(conn, repo_id, 10)
            self.assertEqual(get_cumulative_delta(conn, repo_id), 10)
            update_cumulative_delta(conn, repo_id, -5)
            self.assertEqual(get_cumulative_delta(conn, repo_id), 5)
            reset_cumulative_delta(conn, repo_id)
            self.assertEqual(get_cumulative_delta(conn, repo_id), 0)

    def test_file_complexity(self):
        with get_db_connection(self.db_path) as conn:
            repo_id = get_repo_id(conn, "/path/to/repo")
            file_path = "test.py"
            self.assertEqual(get_file_complexity(conn, repo_id, file_path), 0)
            update_file_complexity(conn, repo_id, file_path, 5)
            self.assertEqual(get_file_complexity(conn, repo_id, file_path), 5)
            update_file_complexity(conn, repo_id, file_path, 8) # Test replacement
            self.assertEqual(get_file_complexity(conn, repo_id, file_path), 8)
            delete_file_complexity(conn, repo_id, file_path)
            self.assertEqual(get_file_complexity(conn, repo_id, file_path), 0)

    def test_concurrent_writes(self):
        """Test that concurrent writes do not corrupt the database."""
        repo_path = "/path/to/concurrent"
        num_threads = 10
        iterations = 50

        def worker():
            with get_db_connection(self.db_path) as conn:
                repo_id = get_repo_id(conn, repo_path)
                for _ in range(iterations):
                    update_cumulative_delta(conn, repo_id, 1)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        with get_db_connection(self.db_path) as conn:
            repo_id = get_repo_id(conn, repo_path)
            final_delta = get_cumulative_delta(conn, repo_id)
            self.assertEqual(final_delta, num_threads * iterations)

if __name__ == "__main__":
    unittest.main()
