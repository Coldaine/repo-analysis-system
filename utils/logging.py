"""
Logging helpers used by many modules; kept in `src/utils/logging.py` for canonical imports.
A top-level wrapper exists to support local imports during test discovery.
"""
from __future__ import annotations

import logging
import uuid
import functools
import time
from contextlib import contextmanager


def get_logger(name: str = None) -> logging.Logger:
    return logging.getLogger(name or __name__)


@contextmanager
def correlation_context(run_id: str = None):
    run_id = run_id or str(uuid.uuid4())
    try:
        yield run_id
    finally:
        pass


def timer_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.time()
            get_logger(func.__module__).debug("%s took %.4f seconds", func.__name__, end - start)
    return wrapper


def correlation_id():
    return str(uuid.uuid4())
