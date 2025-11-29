"""Tracks and processes file complexity changes."""

import logging
import time
import threading
from pathlib import Path
from queue import Queue, Empty
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
from .auto_committer import AutoCommitter

logger = logging.getLogger(__name__)

MAX_PENDING_FILES = 5000

class ComplexityTracker:
    """
    Manages debouncing, complexity calculation, and database state.
    """
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.config = load_config()
        self.db_path = str(get_state_db())
        init_db(self.db_path)

        with get_db_connection(self.db_path) as conn:
            self.repo_id = get_repo_id(conn, str(repo_path))

        self.threshold = self.config.get("defaults", {}).get("threshold", 50)
        self.debounce_seconds = self.config.get("daemon", {}).get("debounce_seconds", 5)

        self.auto_committer = AutoCommitter(
            repo_path=str(self.repo_path),
            repo_id=self.repo_id,
            db_path=self.db_path,
            threshold=self.threshold,
            message_template=self.config.get("defaults", {}).get("message_template", "checkpoint: complexity {delta} (auto)")
        )

        self._task_queue = Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def enqueue_task(self, action, file_path):
        if self._task_queue.qsize() > MAX_PENDING_FILES:
            logger.warning("File processing queue is full, skipping...")
            return
        self._task_queue.put((action, file_path, time.time()))

    def _process_queue(self):
        pending_files = {}

        while not self._stop_event.is_set():
            try:
                action, file_path, timestamp = self._task_queue.get(timeout=self.debounce_seconds)
                pending_files[file_path] = (action, timestamp)
            except Empty:
                files_to_process = []
                now = time.time()
                for path, (act, ts) in list(pending_files.items()):
                    if now - ts >= self.debounce_seconds:
                        files_to_process.append((act, path))
                        del pending_files[path]

                if files_to_process:
                    self._process_batch(files_to_process)

    def _process_batch(self, files_to_process):
        with get_db_connection(self.db_path) as conn:
            for action, file_path in files_to_process:
                if action == 'process':
                    self._process_file(file_path, conn)
                elif action == 'delete':
                    self._handle_deletion(file_path, conn)

            # After processing the batch, check if a commit is needed
            self.auto_committer.check_and_commit(conn)

    def _handle_deletion(self, file_path: str, conn):
        try:
            old_complexity = get_file_complexity(conn, self.repo_id, file_path)
            if old_complexity > 0:
                update_cumulative_delta(conn, self.repo_id, -old_complexity)
                delete_file_complexity(conn, self.repo_id, file_path)
                logger.info(f"Deleted: {file_path}, Removed complexity: {old_complexity}")
        except Exception as e:
            logger.error(f"Failed to handle deletion of {file_path}: {e}")

    def _process_file(self, file_path: str, conn):
        try:
            if not Path(file_path).exists():
                return

            old_complexity = get_file_complexity(conn, self.repo_id, file_path)
            new_complexity = calculate_complexity(file_path)
            delta = new_complexity - old_complexity

            if delta != 0:
                update_file_complexity(conn, self.repo_id, file_path, new_complexity)
                update_cumulative_delta(conn, self.repo_id, delta)
                logger.info(f"File: {file_path}, Complexity Delta: {delta:+d}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    def reset_complexity_delta(self):
        """Resets the cumulative complexity delta in the database."""
        try:
            with get_db_connection(self.db_path) as conn:
                reset_cumulative_delta(conn, self.repo_id)
            logger.info("Complexity delta has been reset.")
        except Exception as e:
            logger.error(f"Failed to reset complexity delta: {e}")

    def cleanup(self):
        self._stop_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        logger.debug("ComplexityTracker cleaned up.")
