"""Tests for the ComplexityTracker."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import os
import time
from tools.complexity_daemon.complexity_tracker import ComplexityTracker
from tools.complexity_daemon.config import save_config, DEFAULT_CONFIG

class TestComplexityTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir)

        # Mock dependencies
        os.environ['COGLOAD_STATE_DB'] = str(self.repo_path / "state.db")
        os.environ['COGLOAD_CONFIG_FILE'] = str(self.repo_path / "config.yaml")
        save_config(DEFAULT_CONFIG)

        self.tracker = ComplexityTracker(self.repo_path)

    def tearDown(self):
        self.tracker.cleanup()
        shutil.rmtree(self.test_dir)
        del os.environ['COGLOAD_STATE_DB']
        del os.environ['COGLOAD_CONFIG_FILE']

    @patch('tools.complexity_daemon.complexity_tracker.calculate_complexity', return_value=15)
    @patch('tools.complexity_daemon.complexity_tracker.get_file_complexity', return_value=5)
    def test_file_processing_calculates_delta(self, mock_get_complexity, mock_calculate):
        """Test that processing a file correctly calculates and stores the complexity delta."""
        test_file = self.repo_path / "test.py"
        test_file.touch()

        with patch.object(self.tracker.auto_committer, 'check_and_commit') as mock_commit_check:
            self.tracker.enqueue_task('process', str(test_file))
            time.sleep(self.tracker.debounce_seconds + 1)

            # Verify that complexity was updated
            with patch('tools.complexity_daemon.state.update_cumulative_delta') as mock_update_delta:
                 # We need to manually trigger the processing that happens in the thread
                self.tracker._process_batch([('process', str(test_file))])
                mock_update_delta.assert_called_with(unittest.mock.ANY, self.tracker.repo_id, 10) # 15 - 5

            # Verify that it checked for a commit
            mock_commit_check.assert_called()

if __name__ == '__main__':
    unittest.main()
