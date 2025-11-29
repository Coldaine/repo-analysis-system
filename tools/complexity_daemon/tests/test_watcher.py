"""Tests for the watcher component."""

import unittest
from unittest.mock import MagicMock, patch
import time
import threading
from pathlib import Path
import os
import shutil
import tempfile
from tools.complexity_daemon.main_loop import watch_directory
from tools.complexity_daemon.config import save_config, DEFAULT_CONFIG

class TestWatcher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / "repo"
        os.makedirs(self.repo_path)

        # Create a dummy git repo
        os.system(f"git init {self.repo_path}")

        # Create a dummy config file
        config_dir = self.repo_path / ".cogload"
        os.makedirs(config_dir)
        save_config(DEFAULT_CONFIG, config_path=config_dir / "config.yaml")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('tools.complexity_daemon.main_loop.GitStateMonitor')
    @patch('tools.complexity_daemon.main_loop.ComplexityTracker')
    @patch('tools.complexity_daemon.main_loop.FileChangeDispatcher')
    def test_watch_directory_initialization(self, mock_dispatcher, mock_tracker, mock_monitor):
        """Test that watch_directory initializes components correctly."""

        mock_observer = MagicMock()
        with patch('tools.complexity_daemon.main_loop.Observer', return_value=mock_observer):
            # Run watch_directory in a separate thread so we can stop it
            watcher_thread = threading.Thread(
                target=watch_directory,
                args=(str(self.repo_path), ["*.py"], [])
            )
            watcher_thread.daemon = True
            watcher_thread.start()

            time.sleep(1)  # Allow time for setup

            mock_tracker.assert_called_once_with(self.repo_path)
            mock_dispatcher.assert_called_once()
            mock_monitor.assert_called_once()

            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()

            # Stop the watcher
            mock_observer.stop()
            watcher_thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
