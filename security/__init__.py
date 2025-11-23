"""
Top-level security package wrapper to re-export `src.security` modules and allow `security` imports in tests.
"""
try:
    from src.security import *  # noqa: F401,F403
except Exception:
    pass
