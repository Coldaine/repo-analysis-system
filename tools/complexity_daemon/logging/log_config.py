"""Logging configuration for the complexity daemon."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "share" / "cogload"
LOG_FILE = LOG_DIR / "daemon.log"

def setup_logging(log_level="INFO"):
    """Sets up logging for the daemon."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("cogload")
    logger.setLevel(log_level)

    handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
