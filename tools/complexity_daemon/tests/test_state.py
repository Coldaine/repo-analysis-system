import unittest
import os
import sqlite3
from tools.complexity_daemon.state import (
    get_db_connection,
    init_db,
    get_repo_id,
    get_cumulative_delta,
    update_cumulative_delta,
    reset_cumulative_delta,
    get_file_complexity,
    update_file_complexity,
)

class TestState(unittest.TestCase):
    def setUp(self):
        self.db_path = "test.db"
        init_db(self.db_path)
        self.conn = get_db_connection(self.db_path)

    def tearDown(self):
        self.conn.close()
        os.remove(self.db_path)

    def test_repo_management(self):
        repo_path = "/path/to/repo"
        repo_id = get_repo_id(self.conn, repo_path)
        self.assertIsInstance(repo_id, int)

        # Test getting the same repo again
        repo_id_2 = get_repo_id(self.conn, repo_path)
        self.assertEqual(repo_id, repo_id_2)

    def test_cumulative_delta(self):
        repo_id = get_repo_id(self.conn, "/path/to/repo")
        delta = get_cumulative_delta(self.conn, repo_id)
        self.assertEqual(delta, 0)

        update_cumulative_delta(self.conn, repo_id, 10)
        delta = get_cumulative_delta(self.conn, repo_id)
        self.assertEqual(delta, 10)

        reset_cumulative_delta(self.conn, repo_id)
        delta = get_cumulative_delta(self.conn, repo_id)
        self.assertEqual(delta, 0)

    def test_file_complexity(self):
        repo_id = get_repo_id(self.conn, "/path/to/repo")
        file_path = "test.py"
        complexity = get_file_complexity(self.conn, repo_id, file_path)
        self.assertEqual(complexity, 0)

        update_file_complexity(self.conn, repo_id, file_path, 5)
        complexity = get_file_complexity(self.conn, repo_id, file_path)
        self.assertEqual(complexity, 5)

if __name__ == "__main__":
    unittest.main()
