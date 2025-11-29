"""Main loop for the complexity daemon."""

import logging
import time
from pathlib import Path
from watchdog.observers import Observer
from .change_handler import FileChangeDispatcher
from .complexity_tracker import ComplexityTracker
from .git_state_monitor import GitStateMonitor

logger = logging.getLogger(__name__)

def watch_directory(path: str, include_patterns, exclude_patterns):
    """
    Watches a directory for changes and manages the complexity tracking workflow.
    """
    repo_path = Path(path)
    if not repo_path.exists() or not repo_path.is_dir():
        logger.error(f"Error: Path {path} is not a valid directory.")
        return

    complexity_tracker = ComplexityTracker(repo_path)

    # Pass the tracker to the event handler
    event_handler = FileChangeDispatcher(
        complexity_tracker,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns
    )

    git_monitor = GitStateMonitor(complexity_tracker)

    observer = Observer()
    observer.schedule(event_handler, str(repo_path), recursive=True)
    observer.start()

    logger.info(f"Watching {repo_path} (threshold: {complexity_tracker.threshold}, debounce: {complexity_tracker.debounce_seconds}s)")

    try:
        while True:
            git_monitor.check_git_state()
            time.sleep(5)  # Interval for git state checks
    except KeyboardInterrupt:
        logger.info("\nStopping watcher...")
    finally:
        observer.stop()
        observer.join()
        complexity_tracker.cleanup()
        logger.info("Watcher stopped.")
