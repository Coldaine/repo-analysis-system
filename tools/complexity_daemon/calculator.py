"""Complexity calculation using lizard."""

import lizard

def calculate_complexity(file_path: str) -> int:
    """
    Calculates the cyclomatic complexity of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The cyclomatic complexity of the file.
    """
    try:
        analysis = lizard.analyze_file(file_path)
        total_complexity = sum(f.cyclomatic_complexity for f in analysis.function_list)
        return total_complexity
    except Exception:
        # If lizard fails to parse the file, return a complexity of 0.
        return 0
