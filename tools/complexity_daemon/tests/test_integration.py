"""Integration tests for the complexity daemon."""

import unittest
import os
import shutil
import tempfile
import time
import threading
from pathlib import Path
from tools.complexity_daemon.main_loop import watch_directory
from tools.complexity_daemon.state import get_db_connection, get_cumulative_delta
from tools.complexity_daemon.config import save_config, DEFAULT_CONFIG, get_state_db
import git

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / "repo"
        os.makedirs(self.repo_path)

        # Initialize a git repository
        self.repo = git.Repo.init(self.repo_path)

        # Set up a temporary database
        self.db_path = Path(self.test_dir) / "state.db"
        os.environ['COGLOAD_STATE_DB'] = str(self.db_path)

        # Set up a temporary config
        config = DEFAULT_CONFIG.copy()
        config['defaults']['threshold'] = 10  # Low threshold for testing
        config['defaults']['include_patterns'] = ["*.py"]
        self.config_path = Path(self.test_dir) / "config.yaml"
        os.environ['COGLOAD_CONFIG_FILE'] = str(self.config_path)
        save_config(config)

        self.watcher_thread = None

    def tearDown(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            # This is a bit abrupt, but we need to stop the thread.
            # A more graceful shutdown mechanism would be better.
            self.watcher_thread.join(0.1)
        shutil.rmtree(self.test_dir)
        del os.environ['COGLOAD_STATE_DB']
        del os.environ['COGLOAD_CONFIG_FILE']

    def test_full_workflow_auto_commit(self):
        """
        Test the full workflow: file change -> complexity calculation -> auto-commit.
        """
        self.watcher_thread = threading.Thread(
            target=watch_directory,
            args=(str(self.repo_path), ["*.py"], []),
            daemon=True
        )
        self.watcher_thread.start()
        time.sleep(2) # Allow watcher to initialize

        # Create a new file that should trigger a commit
        file_to_change = self.repo_path / "test.py"
        with open(file_to_change, "w") as f:
            f.write("def func_a():\\n    pass\\n" * 5) # Complexity > 10

        # Wait for debouncing and processing
        time.sleep(DEFAULT_CONFIG['daemon']['debounce_seconds'] + 2)

        # Check that a commit was made
        commits = list(self.repo.iter_commits())
        self.assertEqual(len(commits), 1)
        self.assertIn("checkpoint: complexity", commits[0].message)

        # Check that the cumulative delta was reset
        with get_db_connection(str(self.db_path)) as conn:
            from tools.complexity_daemon.state import get_repo_id
            repo_id = get_repo_id(conn, str(self.repo_path))
            delta = get_cumulative_delta(conn, repo_id)
            self.assertEqual(delta, 0)


if __name__ == '__main__':
    unittest.main()
