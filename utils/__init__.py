"""
Top-level utils package wrapper exporting `src.utils` for easier imports during local development.
"""
try:
    from src.utils import *  # noqa: F401,F403
except Exception:
    pass
