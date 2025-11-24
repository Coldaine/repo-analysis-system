"""
Minimal change detection shim used to satisfy imports and allow tests to run.
This is intentionally minimal as a placeholder until full change detection is implemented.
"""
from typing import List, Dict


class ChangeDetector:
    """Simple placeholder change detector.

    The actual implementation should determine file diffs, changed paths, and compute
    reasons to re-run analysis for a repository. This shim returns a static response.
    """

    def __init__(self):
        pass

    def detect_changes(self, path: str) -> Dict[str, List[str]]:
        """Return a dict with changed file paths under `path`.

        Example: {"changed": ["file1.py", "dir/file2.md"]}
        """
        return {"changed": []}


__all__ = ["ChangeDetector"]
