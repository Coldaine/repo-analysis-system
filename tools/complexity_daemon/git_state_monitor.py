"""Monitors the Git repository for state changes."""

import logging
import git
from .git_ops import get_head_hash

logger = logging.getLogger(__name__)

class GitStateMonitor:
    """
    Detects branch switches and manual commits.
    """
    def __init__(self, complexity_tracker):
        self.complexity_tracker = complexity_tracker
        self.repo_path = str(complexity_tracker.repo_path)
        self._last_commit_hash = get_head_hash(self.repo_path)
        self._last_branch = self._get_current_branch()

    def _get_current_branch(self) -> str:
        """Gets the current git branch name."""
        try:
            repo = git.Repo(self.repo_path)
            # handle detached head
            if repo.head.is_detached:
                return f"DETACHED_AT_{repo.head.commit.hexsha[:7]}"
            return repo.active_branch.name
        except (git.exc.InvalidGitRepositoryError, TypeError):
            logger.warning("Could not determine current branch.")
            return ""

    def check_git_state(self):
        """
        Checks for manual commits and branch switches and resets state if necessary.
        """
        try:
            current_branch = self._get_current_branch()
            if current_branch and current_branch != self._last_branch:
                logger.info(f"Branch switch detected: {self._last_branch} -> {current_branch}. Resetting complexity delta.")
                self.complexity_tracker.reset_complexity_delta()
                self._last_branch = current_branch
                self._last_commit_hash = get_head_hash(self.repo_path)
                return

            current_hash = get_head_hash(self.repo_path)
            if current_hash != self._last_commit_hash:
                logger.info("Manual commit detected. Resetting complexity counter.")
                self.complexity_tracker.reset_complexity_delta()
                self._last_commit_hash = current_hash

        except Exception as e:
            logger.error(f"Error checking git state: {e}")
