"""Git operations for the complexity daemon."""

import git

def stage_all(repo_path: str):
    """Stages all changes in the repository."""
    try:
        repo = git.Repo(repo_path)
    except git.exc.NoSuchPathError:
        repo = git.Repo.init(repo_path)
    repo.git.add(A=True)
    repo.git.status() # Wait for the index to be updated

def commit(repo_path: str, message: str):
    """Commits the staged changes."""
    try:
        repo = git.Repo(repo_path)
    except git.exc.NoSuchPathError:
        repo = git.Repo.init(repo_path)
    repo.index.commit(
        message,
        author=git.Actor("cogload", "cogload@localhost"),
        committer=git.Actor("cogload", "cogload@localhost"),
    )

def get_head_hash(repo_path: str) -> str:
    """Gets the current HEAD commit hash."""
    try:
        repo = git.Repo(repo_path)
        return repo.head.commit.hexsha
    except (git.exc.InvalidGitRepositoryError, ValueError):
        # ValueError is raised if there are no commits yet
        return ""
