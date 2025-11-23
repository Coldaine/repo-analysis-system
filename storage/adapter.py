"""
Top-level storage adapter alias to allow `import storage.adapter` when not running tests
with `PYTHONPATH=src`.
"""
from src.storage.adapter import *  # noqa: F401,F403
