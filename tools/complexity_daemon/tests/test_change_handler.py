"""Tests for the FileChangeDispatcher."""

import unittest
from unittest.mock import MagicMock
from tools.complexity_daemon.change_handler import FileChangeDispatcher

class TestFileChangeDispatcher(unittest.TestCase):
    def setUp(self):
        self.mock_tracker = MagicMock()
        self.include_patterns = ["*.py", "src/*.js"]
        self.exclude_patterns = ["*.tmp", "build/*"]
        self.dispatcher = FileChangeDispatcher(
            self.mock_tracker,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns
        )

    def test_on_modified_should_process(self):
        """Test that on_modified enqueues a task for matching files."""
        mock_event = MagicMock(is_directory=False, src_path="/path/to/my_file.py")
        self.dispatcher.on_modified(mock_event)
        self.mock_tracker.enqueue_task.assert_called_once_with('process', mock_event.src_path)

    def test_on_modified_should_not_process_excluded(self):
        """Test that on_modified ignores excluded files."""
        mock_event = MagicMock(is_directory=False, src_path="/path/to/build/app.js")
        self.dispatcher.on_modified(mock_event)
        self.mock_tracker.enqueue_task.assert_not_called()

    def test_on_modified_should_not_process_non_included(self):
        """Test that on_modified ignores files that don't match include patterns."""
        mock_event = MagicMock(is_directory=False, src_path="/path/to/my_file.txt")
        self.dispatcher.on_modified(mock_event)
        self.mock_tracker.enqueue_task.assert_not_called()

    def test_on_deleted_should_process(self):
        """Test that on_deleted enqueues a task for matching files."""
        mock_event = MagicMock(is_directory=False, src_path="/path/to/src/app.js")
        self.dispatcher.on_deleted(mock_event)
        self.mock_tracker.enqueue_task.assert_called_once_with('delete', mock_event.src_path)

    def test_should_process_git_dir(self):
        """Test that files in .git directory are ignored."""
        self.assertFalse(self.dispatcher._should_process("/my/repo/.git/HEAD"))


if __name__ == '__main__':
    unittest.main()
