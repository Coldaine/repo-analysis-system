"""CLI for the complexity daemon."""

import typer
from pathlib import Path
import git
import threading
import time
import logging
from .main_loop import watch_directory
from .logging.log_config import setup_logging
from .state import get_db_connection, get_repo_id, get_cumulative_delta, reset_cumulative_delta
from .git_ops import stage_all, commit as git_commit
from .config import load_config, save_config, get_config_dir, get_state_db, DEFAULT_CONFIG

app = typer.Typer()
logger = logging.getLogger(__name__)

# List of forbidden paths to prevent watching sensitive directories
FORBIDDEN_PATHS = {'/etc', '/root', '/sys', '/proc', '/dev'}

def _validate_path(path: Path):
    """
    Validates that the given path is not a forbidden system directory.
    Raises ValueError if the path is forbidden.
    """
    resolved_path = path.resolve()
    for forbidden in FORBIDDEN_PATHS:
        if resolved_path == Path(forbidden).resolve():
            raise ValueError(f"Watching system directory '{forbidden}' is not allowed.")
    if not resolved_path.is_dir():
        raise ValueError(f"Path '{resolved_path}' is not a valid directory.")

@app.callback()
def main():
    """Main callback to create directories and setup logging."""
    try:
        get_config_dir().mkdir(parents=True, exist_ok=True)
        get_state_db().parent.mkdir(parents=True, exist_ok=True)
        config = load_config()
        log_level = config.get("daemon", {}).get("log_level", "info").upper()
        setup_logging(log_level)
    except Exception as e:
        # Use print here since logger might not be configured yet
        print(f"Error during initialization: {e}")
        raise typer.Exit(code=1)

@app.command()
def init():
    """Creates the default config file."""
    from .config import get_config_file
    config_file = get_config_file()
    if not config_file.exists():
        save_config(DEFAULT_CONFIG)
        logger.info(f"Created default config file at {config_file}")
    else:
        logger.info("Config file already exists.")

@app.command()
def add(path: Path):
    """Adds a repository to the watch list."""
    try:
        _validate_path(path)
        config = load_config()
        repos = config.setdefault("repos", [])
        if any(r["path"] == str(path.resolve()) for r in repos):
            logger.warning(f"{path.resolve()} is already in the watch list.")
            return
        repos.append({"path": str(path.resolve()), "enabled": True})
        save_config(config)
        logger.info(f"Added {path.resolve()} to the watch list.")
    except (ValueError, Exception) as e:
        logger.error(f"Failed to add repository: {e}")
        raise typer.Exit(code=1)

@app.command()
def remove(path: Path):
    """Removes a repository from the watch list."""
    try:
        config = load_config()
        original_len = len(config["repos"])
        config["repos"] = [repo for repo in config["repos"] if repo["path"] != str(path.resolve())]
        if len(config["repos"]) == original_len:
            logger.warning(f"{path.resolve()} was not in the watch list.")
            return
        save_config(config)
        logger.info(f"Removed {path.resolve()} from the watch list.")
    except Exception as e:
        logger.error(f"Failed to remove repository: {e}")
        raise typer.Exit(code=1)

@app.command(name="list")
def list_repos():
    """Lists the watched repositories."""
    try:
        config = load_config()
        for repo in config.get("repos", []):
            print(f"- {repo['path']} (enabled: {repo['enabled']})")
    except Exception as e:
        logger.error(f"Failed to list repositories: {e}")
        raise typer.Exit(code=1)

@app.command()
def status():
    """Shows the current cumulative delta per repo."""
    try:
        config = load_config()
        with get_db_connection(str(get_state_db())) as conn:
            for repo_config in config.get("repos", []):
                if repo_config.get("enabled"):
                    repo_path = repo_config["path"]
                    repo_id = get_repo_id(conn, repo_path)
                    delta = get_cumulative_delta(conn, repo_id)
                    print(f"- {repo_path}: {delta}")
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise typer.Exit(code=1)

@app.command()
def watch(path: Path):
    """Watches a single repository in the foreground."""
    try:
        _validate_path(path)
        config = load_config()
        repo_path = str(path.resolve())

        repo_config = next((r for r in config.get("repos", []) if r["path"] == repo_path), {})

        include_patterns = repo_config.get("include_patterns", config.get("defaults", {}).get("include_patterns", []))
        exclude_patterns = repo_config.get("exclude_patterns", config.get("defaults", {}).get("exclude_patterns", []))

        logger.info(f"Watching {repo_path}...")
        watch_directory(repo_path, include_patterns, exclude_patterns)
    except (ValueError, Exception) as e:
        logger.error(f"Failed to watch repository: {e}")
        raise typer.Exit(code=1)

@app.command()
def daemon():
    """Runs the daemon for all configured repositories."""
    logger.info("Starting complexity daemon.")
    config = load_config()
    threads = []

    for repo in config.get("repos", []):
        if repo.get("enabled"):
            repo_path = repo["path"]
            try:
                _validate_path(Path(repo_path))
                include_patterns = repo.get("include_patterns", config.get("defaults", {}).get("include_patterns", []))
                exclude_patterns = repo.get("exclude_patterns", config.get("defaults", {}).get("exclude_patterns", []))

                thread = threading.Thread(
                    target=watch_directory,
                    args=(repo_path, include_patterns, exclude_patterns),
                    daemon=True
                )
                threads.append(thread)
                logger.info(f"Starting watcher for {repo_path}")
                thread.start()
            except (ValueError, Exception) as e:
                logger.error(f"Skipping repository {repo_path}: {e}")

    if not threads:
        logger.warning("No enabled repositories to watch. Add one with 'cogload add <path>'.")
        return

    logger.info("Daemon started. Press Ctrl+C to stop.")
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping daemon.")
    finally:
        logger.info("Daemon shutdown.")

@app.command()
def commit(repo_path: Path = typer.Argument(..., help="The path to the repository.")):
    """Forces a commit now."""
    try:
        with get_db_connection(str(get_state_db())) as conn:
            config = load_config()
            repo_id = get_repo_id(conn, str(repo_path.resolve()))
            delta = get_cumulative_delta(conn, repo_id)

            message_template = config.get("defaults", {}).get("message_template", "checkpoint: complexity {delta} (auto)")
            commit_message = message_template.format(delta=delta)

            stage_all(str(repo_path.resolve()))
            git_commit(str(repo_path.resolve()), commit_message)

            logger.info(f"Committed changes in {repo_path} with message: {commit_message}")

            reset_cumulative_delta(conn, repo_id)
    except Exception as e:
        logger.error(f"Failed to force commit: {e}")
        raise typer.Exit(code=1)

@app.command()
def reset(repo_path: Path = typer.Argument(..., help="The path to the repository.")):
    """Resets the cumulative counter."""
    try:
        with get_db_connection(str(get_state_db())) as conn:
            repo_id = get_repo_id(conn, str(repo_path.resolve()))
            reset_cumulative_delta(conn, repo_id)
        logger.info(f"Reset cumulative complexity for {repo_path}")
    except Exception as e:
        logger.error(f"Failed to reset counter: {e}")
        raise typer.Exit(code=1)

@app.command()
def history(repo_path: Path = typer.Argument(..., help="The path to the repository.")) -> None:
    """Shows the auto-commit history."""
    try:
        repo = git.Repo(repo_path)
        commits = repo.iter_commits(grep="checkpoint: complexity")
        for c in commits:
            print(f"{c.hexsha[:7]} - {c.summary} ({c.authored_datetime})")
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"Error: {repo_path} is not a valid git repository.")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
