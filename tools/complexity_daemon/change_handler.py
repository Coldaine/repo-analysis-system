"""Event handler for file changes."""

import logging
import fnmatch
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class FileChangeDispatcher(FileSystemEventHandler):
    """
    Dispatches file system events to the ComplexityTracker.
    """
    def __init__(self, complexity_tracker, include_patterns, exclude_patterns):
        self.complexity_tracker = complexity_tracker
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.complexity_tracker.enqueue_task('process', event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.complexity_tracker.enqueue_task('delete', event.src_path)

    def _should_process(self, file_path: str) -> bool:
        """
        Checks if a file should be processed based on include/exclude patterns.
        """
        # Normalize path separators for matching
        file_path = file_path.replace("\\\\", "/")

        if '/.git/' in file_path or file_path.endswith('/.git'):
            return False

        # Exclude patterns take precedence
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return False

        # If include_patterns is empty, process all non-excluded files.
        # Otherwise, only process files matching an include pattern.
        if not self.include_patterns:
            return True
        else:
            for pattern in self.include_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return True
            return False
