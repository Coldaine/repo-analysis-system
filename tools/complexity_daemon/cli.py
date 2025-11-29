"""CLI for the complexity daemon."""

import typer
from pathlib import Path
import git
import threading
import time
from .watcher import watch_directory
from .logging.log_config import setup_logging
from .state import get_db_connection, get_repo_id, get_cumulative_delta, reset_cumulative_delta
from .git_ops import stage_all, commit as git_commit
from .config import load_config, save_config, get_config_dir, get_state_db, DEFAULT_CONFIG

app = typer.Typer()

@app.callback()
def main():
    """Main callback to create directories."""
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_state_db().parent.mkdir(parents=True, exist_ok=True)

@app.command()
def init():
    """Creates the default config file."""
    from .config import get_config_file
    config_file = get_config_file()
    if not config_file.exists():
        save_config(DEFAULT_CONFIG)
        print(f"Created default config file at {config_file}")
    else:
        print("Config file already exists.")

@app.command()
def add(path: Path):
    """Adds a repository to the watch list."""
    config = load_config()
    config["repos"].append({"path": str(path.resolve()), "enabled": True})
    save_config(config)
    print(f"Added {path.resolve()} to the watch list.")

@app.command()
def remove(path: Path):
    """Removes a repository from the watch list."""
    config = load_config()
    config["repos"] = [repo for repo in config["repos"] if repo["path"] != str(path.resolve())]
    save_config(config)
    print(f"Removed {path.resolve()} from the watch list.")

@app.command()
def list():
    """Lists the watched repositories."""
    config = load_config()
    for repo in config["repos"]:
        print(f"- {repo['path']} (enabled: {repo['enabled']})")

@app.command()
def status():
    """Shows the current cumulative delta per repo."""
    config = load_config()
    conn = get_db_connection(str(get_state_db()))
    for repo_config in config.get("repos", []):
        if repo_config.get("enabled"):
            repo_path = repo_config["path"]
            repo_id = get_repo_id(conn, repo_path)
            delta = get_cumulative_delta(conn, repo_id)
            print(f"- {repo_path}: {delta}")
    conn.close()

@app.command()
def watch(path: Path):
    """Watches a single repository in the foreground."""
    config = load_config()
    repo_path = str(path.resolve())

    repo_config = next((r for r in config.get("repos", []) if r["path"] == repo_path), {})

    include_patterns = repo_config.get("include_patterns", config.get("defaults", {}).get("include_patterns", []))
    exclude_patterns = repo_config.get("exclude_patterns", config.get("defaults", {}).get("exclude_patterns", []))

    print(f"Watching {repo_path}...")
    watch_directory(repo_path, include_patterns, exclude_patterns)

@app.command()
def daemon():
    """Runs the daemon for all configured repositories."""
    config = load_config()
    log_level = config.get("daemon", {}).get("log_level", "info").upper()
    logger = setup_logging(log_level)

    logger.info("Starting complexity daemon.")

    threads = []
    for repo in config.get("repos", []):
        if repo.get("enabled"):
            repo_path = repo["path"]
            include_patterns = repo.get("include_patterns", config.get("defaults", {}).get("include_patterns", []))
            exclude_patterns = repo.get("exclude_patterns", config.get("defaults", {}).get("exclude_patterns", []))

            thread = threading.Thread(
                target=watch_directory,
                args=(repo_path, include_patterns, exclude_patterns),
                daemon=True
            )
            threads.append(thread)
            print(f"Starting watcher for {repo_path}")
            thread.start()

    if not threads:
        print("No enabled repositories to watch. Add one with 'cogload add <path>'.")
        return

    print("Daemon started. Press Ctrl+C to stop.")

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
    config = load_config()
    conn = get_db_connection(str(get_state_db()))
    repo_id = get_repo_id(conn, str(repo_path.resolve()))
    delta = get_cumulative_delta(conn, repo_id)

    message_template = config.get("defaults", {}).get("message_template", "checkpoint: complexity {delta} (auto)")
    commit_message = message_template.format(delta=delta)

    stage_all(str(repo_path.resolve()))
    git_commit(str(repo_path.resolve()), commit_message)

    print(f"Committed changes in {repo_path} with message: {commit_message}")

    reset_cumulative_delta(conn, repo_id)
    conn.close()

@app.command()
def reset(repo_path: Path = typer.Argument(..., help="The path to the repository.")):
    """Resets the cumulative counter."""
    conn = get_db_connection(str(get_state_db()))
    repo_id = get_repo_id(conn, str(repo_path.resolve()))
    reset_cumulative_delta(conn, repo_id)
    conn.close()
    print(f"Reset cumulative complexity for {repo_path}")

@app.command()
def history(repo_path: Path = typer.Argument(..., help="The path to the repository.")) -> None:
    """Shows the auto-commit history."""
    try:
        repo = git.Repo(repo_path)
        commits = repo.iter_commits(grep="checkpoint: complexity")
        for c in commits:
            print(f"{c.hexsha[:7]} - {c.summary} ({c.authored_datetime})")
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: {repo_path} is not a valid git repository.")

if __name__ == "__main__":
    app()
