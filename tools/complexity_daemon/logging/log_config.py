"""Logging configuration for the complexity daemon."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from ..config import get_log_dir

def setup_logging(log_level="INFO"):
    """
    Sets up logging for the daemon, including file and console handlers.
    """
    log_dir = get_log_dir()
    log_file = log_dir / "daemon.log"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Use print as this is a critical setup failure
        print(f"Error creating log directory {log_dir}: {e}", file=sys.stderr)
        return None

    # Get the root logger
    logger = logging.getLogger()

    # Avoid adding handlers multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    try:
        log_level_enum = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(log_level_enum)
    except AttributeError:
        logger.setLevel(logging.INFO)
        print(f"Warning: Invalid log level '{log_level}'. Defaulting to INFO.", file=sys.stderr)

    # File handler for persistent logging
    try:
        handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except (OSError, IOError) as e:
        print(f"Error setting up file handler {log_file}: {e}", file=sys.stderr)

    # Console handler for immediate feedback
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
