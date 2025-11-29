"""File watcher for the complexity daemon."""

import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileDeletedEvent
import fnmatch
import git
from .git_ops import get_head_hash, stage_all, commit
from .calculator import calculate_complexity
from .state import (
    get_db_connection,
    get_repo_id,
    get_file_complexity,
    update_file_complexity,
    delete_file_complexity,
    get_cumulative_delta,
    update_cumulative_delta,
    reset_cumulative_delta,
    init_db,
)
from .config import load_config, get_state_db


class ChangeHandler(FileSystemEventHandler):
    def __init__(self, repo_path, include_patterns, exclude_patterns):
        self.repo_path = repo_path
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.config = load_config()

        # Initialize database
        db_path = str(get_state_db())
        init_db(db_path)

        self.db_conn = get_db_connection(db_path)
        self.repo_id = get_repo_id(self.db_conn, self.repo_path)
        self.threshold = self.config.get("defaults", {}).get("threshold", 50)
        self.debounce_seconds = self.config.get("daemon", {}).get("debounce_seconds", 5)

        # Track git state
        self.last_commit_hash = get_head_hash(repo_path)
        self.last_branch = self._get_current_branch()

        # Debouncing: track pending file changes
        self._pending_files = {}
        self._debounce_lock = threading.Lock()

    def _get_current_branch(self) -> str:
        """Gets the current git branch name."""
        try:
            repo = git.Repo(self.repo_path)
            return repo.active_branch.name
        except (git.exc.InvalidGitRepositoryError, TypeError):
            return ""

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if self.should_process(file_path):
            self._schedule_processing(file_path)

    def on_deleted(self, event):
        """Handle file deletion - subtract complexity from cumulative delta."""
        if event.is_directory:
            return

        file_path = event.src_path
        if self.should_process(file_path):
            self._handle_deletion(file_path)

    def _handle_deletion(self, file_path: str):
        """Process a deleted file by subtracting its complexity."""
        old_complexity = get_file_complexity(self.db_conn, self.repo_id, file_path)
        if old_complexity > 0:
            # Subtract the file's complexity from cumulative delta
            update_cumulative_delta(self.db_conn, self.repo_id, -old_complexity)
            delete_file_complexity(self.db_conn, self.repo_id, file_path)

            cumulative_delta = get_cumulative_delta(self.db_conn, self.repo_id)
            print(f"Deleted: {file_path}, Removed complexity: {old_complexity}, Cumulative Delta: {cumulative_delta}")

    def _schedule_processing(self, file_path: str):
        """Schedule file processing with debouncing."""
        with self._debounce_lock:
            # Cancel any existing timer for this file
            if file_path in self._pending_files:
                self._pending_files[file_path].cancel()

            # Schedule new processing after debounce delay
            timer = threading.Timer(
                self.debounce_seconds,
                self._debounced_process_file,
                args=[file_path]
            )
            self._pending_files[file_path] = timer
            timer.start()

    def _debounced_process_file(self, file_path: str):
        """Process file after debounce period."""
        with self._debounce_lock:
            self._pending_files.pop(file_path, None)

        # Check file still exists (might have been deleted)
        if not Path(file_path).exists():
            return

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
            print(f"File: {file_path}, Complexity Delta: {delta:+d}, Cumulative Delta: {cumulative_delta}")

            if cumulative_delta >= self.threshold:
                self.trigger_commit(cumulative_delta)

    def trigger_commit(self, cumulative_delta):
        """Triggers an auto-commit."""
        print(f"Threshold reached ({cumulative_delta} >= {self.threshold}). Committing changes...")
        message_template = self.config.get("defaults", {}).get("message_template", "checkpoint: complexity {delta} (auto)")
        commit_message = message_template.format(delta=cumulative_delta)

        stage_all(self.repo_path)
        commit(self.repo_path, commit_message)

        reset_cumulative_delta(self.db_conn, self.repo_id)
        self.last_commit_hash = get_head_hash(self.repo_path)
        print("Commit successful. Cumulative delta reset.")

    def should_process(self, file_path: str) -> bool:
        """Checks if a file should be processed based on include/exclude patterns."""
        # Skip .git directory
        if '/.git/' in file_path or file_path.endswith('/.git'):
            return False

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

    def check_for_branch_switch(self):
        """Checks for branch switches and resets state if necessary."""
        current_branch = self._get_current_branch()
        if current_branch and current_branch != self.last_branch:
            print(f"Branch switch detected: {self.last_branch} -> {current_branch}. Resetting complexity counter.")
            reset_cumulative_delta(self.db_conn, self.repo_id)
            self.last_branch = current_branch
            self.last_commit_hash = get_head_hash(self.repo_path)

    def cleanup(self):
        """Cancel pending timers and close connections."""
        with self._debounce_lock:
            for timer in self._pending_files.values():
                timer.cancel()
            self._pending_files.clear()
        self.db_conn.close()


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

    print(f"Watching {path} (threshold: {event_handler.threshold}, debounce: {event_handler.debounce_seconds}s)")

    try:
        while True:
            event_handler.check_for_manual_commit()
            event_handler.check_for_branch_switch()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    finally:
        observer.join()
        event_handler.cleanup()
