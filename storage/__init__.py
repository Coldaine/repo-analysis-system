"""
Top-level storage package to support imports like `from storage.adapter import ...`.
This is a thin wrapper that re-exports the `src.storage.adapter` module's public API so
existing code that uses `storage.adapter` will work without requiring `PYTHONPATH=src`.

Consider adopting a packaging structure that avoids these alias wrappers in the future
(e.g., setuptools with `src/` layout and `pip install -e .` or use `src.` imports).
"""
try:
    # Re-export common storage module objects
    from src.storage.adapter import *  # noqa: F401,F403
except Exception as e:
    # If for some reason the src package path isn't present, fail gracefully.
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("storage wrapper failed to import src.storage.adapter: %s", e)

__all__ = [name for name in globals().keys() if not name.startswith("_")]
