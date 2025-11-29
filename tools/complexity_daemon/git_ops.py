"""Git operations for the complexity daemon."""

import git
import logging

logger = logging.getLogger(__name__)

class GitOperationError(Exception):
    """Custom exception for Git operations."""
    pass

def _get_repo(repo_path: str) -> git.Repo:
    """Gets a git.Repo object, initializing if necessary."""
    try:
        return git.Repo(repo_path)
    except git.exc.NoSuchPathError:
        logger.warning(f"No repository found at {repo_path}, initializing a new one.")
        return git.Repo.init(repo_path)
    except git.exc.InvalidGitRepositoryError:
        raise GitOperationError(f"Invalid Git repository at {repo_path}")

def stage_all(repo_path: str):
    """Stages all changes in the repository."""
    try:
        repo = _get_repo(repo_path)
        repo.git.add(A=True)
    except Exception as e:
        logger.error(f"Failed to stage changes in {repo_path}: {e}")
        raise GitOperationError(f"Failed to stage changes: {e}")

def commit(repo_path: str, message: str) -> bool:
    """
    Commits the staged changes.
    Returns True if a commit was made, False otherwise.
    """
    try:
        repo = _get_repo(repo_path)

        # Check if there's anything to commit
        if not repo.is_dirty(index=True, working_tree=False):
            logger.info("No changes staged for commit.")
            return False

        # Configure author if not set
        try:
            repo.config_reader().get_value('user', 'name')
            repo.config_reader().get_value('user', 'email')
        except Exception:
            logger.warning("Git user name/email not set, using default.")
            repo.config_writer().set_value("user", "name", "cogload").release()
            repo.config_writer().set_value("user", "email", "cogload@localhost").release()

        repo.index.commit(message)
        return True

    except Exception as e:
        logger.error(f"Failed to commit in {repo_path}: {e}")
        raise GitOperationError(f"Failed to commit: {e}")

def get_head_hash(repo_path: str) -> str:
    """Gets the current HEAD commit hash."""
    try:
        repo = _get_repo(repo_path)
        if repo.head.is_valid():
            return repo.head.commit.hexsha
        return ""
    except git.exc.GitError as e:
        logger.warning(f"Could not get HEAD hash for {repo_path} (likely empty repo): {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error getting HEAD hash for {repo_path}: {e}")
        raise GitOperationError(f"Could not get HEAD hash: {e}")
