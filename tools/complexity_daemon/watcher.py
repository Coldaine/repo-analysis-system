"""File watcher for the complexity daemon."""

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import fnmatch
from .git_ops import get_head_hash, stage_all, commit
from .calculator import calculate_complexity
from .state import get_db_connection, get_repo_id, get_file_complexity, update_file_complexity, get_cumulative_delta, update_cumulative_delta, reset_cumulative_delta
from .config import load_config, get_state_db

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, repo_path, include_patterns, exclude_patterns):
        self.repo_path = repo_path
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.last_commit_hash = get_head_hash(repo_path)
        self.config = load_config()
        self.db_conn = get_db_connection(str(get_state_db()))
        self.repo_id = get_repo_id(self.db_conn, self.repo_path)
        self.threshold = self.config.get("defaults", {}).get("threshold", 50)

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if self.should_process(file_path):
            self.process_file(file_path)

    def process_file(self, file_path: str):
        """Processes a modified file."""
        old_complexity = get_file_complexity(self.db_conn, self.repo_id, file_path)
        new_complexity = calculate_complexity(file_path)
        delta = new_complexity - old_complexity

        if delta != 0:
            update_file_complexity(self.db_conn, self.repo_id, file_path, new_complexity)
            update_cumulative_delta(self.db_conn, self.repo_id, delta)

            cumulative_delta = get_cumulative_delta(self.db_conn, self.repo_id)
            print(f"File: {file_path}, Complexity Delta: {delta}, Cumulative Delta: {cumulative_delta}")

            if cumulative_delta >= self.threshold:
                self.trigger_commit(cumulative_delta)

    def trigger_commit(self, cumulative_delta):
        """Triggers an auto-commit."""
        print(f"Threshold reached. Committing changes...")
        message_template = self.config.get("defaults", {}).get("message_template", "checkpoint: complexity {delta} (auto)")
        commit_message = message_template.format(delta=cumulative_delta)

        stage_all(self.repo_path)
        commit(self.repo_path, commit_message)

        reset_cumulative_delta(self.db_conn, self.repo_id)
        self.last_commit_hash = get_head_hash(self.repo_path)
        print("Commit successful. Cumulative delta reset.")

    def should_process(self, file_path: str) -> bool:
        """Checks if a file should be processed based on include/exclude patterns."""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return False
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def check_for_manual_commit(self):
        """Checks for manual commits and resets state if necessary."""
        current_hash = get_head_hash(self.repo_path)
        if current_hash != self.last_commit_hash:
            print("Manual commit detected. Resetting complexity counter.")
            reset_cumulative_delta(self.db_conn, self.repo_id)
            self.last_commit_hash = current_hash

from pathlib import Path

def watch_directory(path: str, include_patterns, exclude_patterns):
    """Watches a directory for changes."""
    repo_path = Path(path)
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"Error: Path {path} is not a valid directory.")
        return

    event_handler = ChangeHandler(path, include_patterns, exclude_patterns)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            event_handler.check_for_manual_commit()
            # TODO: Add branch switch handling
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    event_handler.db_conn.close()
