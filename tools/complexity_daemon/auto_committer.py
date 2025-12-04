"""Handles automatic commits based on complexity thresholds."""

import logging
from .git_ops import stage_all, commit, get_head_hash, GitOperationError
from .state import get_cumulative_delta, reset_cumulative_delta

logger = logging.getLogger(__name__)

class AutoCommitter:
    """
    Triggers commits when the complexity delta exceeds a threshold.
    """
    def __init__(self, repo_path: str, repo_id: int, db_path: str, threshold: int, message_template: str):
        self.repo_path = repo_path
        self.repo_id = repo_id
        self.db_path = db_path
        self.threshold = threshold
        self.message_template = message_template

    def check_and_commit(self, conn):
        """
        Checks the cumulative delta and triggers a commit if the threshold is met.
        """
        try:
            cumulative_delta = get_cumulative_delta(conn, self.repo_id)
            logger.debug(f"Checking threshold: current delta is {cumulative_delta}, threshold is {self.threshold}")
            if cumulative_delta >= self.threshold:
                self._trigger_commit(cumulative_delta, conn)
        except Exception as e:
            logger.error(f"Error during threshold check: {e}")

    def _trigger_commit(self, cumulative_delta, conn):
        """
        Stages changes and commits them.
        """
        try:
            logger.info(f"Threshold reached ({cumulative_delta} >= {self.threshold}). Committing changes...")
            commit_message = self.message_template.format(delta=cumulative_delta)

            stage_all(self.repo_path)
            commit_made = commit(self.repo_path, commit_message)

            if commit_made:
                reset_cumulative_delta(conn, self.repo_id)
                # The GitStateMonitor will see the new hash and update itself.
                logger.info("Commit successful. Cumulative delta reset.")
            else:
                logger.warning("Commit was a no-op (no changes to commit), not resetting delta.")

        except GitOperationError as e:
            logger.error(f"Git commit failed: {e}. Cumulative delta NOT reset.")
        except Exception as e:
            logger.error(f"Failed to trigger commit: {e}")
