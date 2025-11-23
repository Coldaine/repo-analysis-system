"""
Complexity Analyzer Module

Analyzes code complexity metrics including:
- Cyclomatic complexity
- Cognitive complexity
- Nesting depth
- Maintainability index
- Complexity hotspots
"""

import os
import ast
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

try:
    from radon.complexity import cc_visit, cc_rank
    from radon.metrics import mi_visit, mi_rank
    from radon.raw import analyze
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FunctionComplexity:
    """Represents complexity metrics for a single function."""
    name: str
    line_number: int
    complexity: int  # Cyclomatic complexity
    rank: str  # A-F ranking
    nesting_depth: int = 0
    cognitive_complexity: int = 0

    @property
    def is_hotspot(self) -> bool:
        """Returns True if complexity exceeds threshold (>10)."""
        return self.complexity > 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'line_number': self.line_number,
            'cyclomatic_complexity': self.complexity,
            'rank': self.rank,
            'nesting_depth': self.nesting_depth,
            'cognitive_complexity': self.cognitive_complexity,
            'is_hotspot': self.is_hotspot,
        }


@dataclass
class FileComplexity:
    """Represents complexity metrics for a single file."""
    file_path: str
    maintainability_index: float
    maintainability_rank: str
    functions: List[FunctionComplexity] = field(default_factory=list)
    lines_of_code: int = 0
    logical_lines: int = 0
    source_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    average_complexity: float = 0.0
    max_complexity: int = 0

    @property
    def hotspot_count(self) -> int:
        """Count of functions that are complexity hotspots."""
        return sum(1 for func in self.functions if func.is_hotspot)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'file_path': self.file_path,
            'maintainability_index': round(self.maintainability_index, 2),
            'maintainability_rank': self.maintainability_rank,
            'lines_of_code': self.lines_of_code,
            'logical_lines': self.logical_lines,
            'source_lines': self.source_lines,
            'comment_lines': self.comment_lines,
            'blank_lines': self.blank_lines,
            'average_complexity': round(self.average_complexity, 2),
            'max_complexity': self.max_complexity,
            'hotspot_count': self.hotspot_count,
            'functions': [func.to_dict() for func in self.functions],
        }


@dataclass
class ComplexityMetrics:
    """Overall complexity metrics for the repository."""
    total_files: int = 0
    total_functions: int = 0
    total_hotspots: int = 0
    average_maintainability_index: float = 0.0
    average_complexity: float = 0.0
    max_complexity: int = 0
    complexity_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'total_files': self.total_files,
            'total_functions': self.total_functions,
            'total_hotspots': self.total_hotspots,
            'average_maintainability_index': round(self.average_maintainability_index, 2),
            'average_complexity': round(self.average_complexity, 2),
            'max_complexity': self.max_complexity,
            'complexity_distribution': self.complexity_distribution,
        }


@dataclass
class ComplexityReport:
    """Complete complexity analysis report."""
    metrics: ComplexityMetrics
    files: List[FileComplexity] = field(default_factory=list)
    hotspots: List[Tuple[str, FunctionComplexity]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'metrics': self.metrics.to_dict(),
            'files': [file.to_dict() for file in self.files],
            'hotspots': [
                {
                    'file': file_path,
                    'function': func.to_dict()
                }
                for file_path, func in self.hotspots
            ],
        }


class ComplexityAnalyzer:
    """
    Analyzes code complexity metrics for Python files.

    Uses radon library to calculate:
    - Cyclomatic complexity (McCabe)
    - Maintainability index
    - Raw metrics (LOC, LLOC, etc.)
    """

    def __init__(self, hotspot_threshold: int = 10):
        """
        Initialize the complexity analyzer.

        Args:
            hotspot_threshold: Complexity threshold for identifying hotspots
        """
        if not RADON_AVAILABLE:
            raise ImportError(
                "radon library is required for complexity analysis. "
                "Install it with: pip install radon"
            )

        self.hotspot_threshold = hotspot_threshold

    def analyze_repository(self, repo_path: str) -> ComplexityReport:
        """
        Analyze all Python files in a repository.

        Args:
            repo_path: Path to the repository root

        Returns:
            ComplexityReport with all metrics and hotspots
        """
        repo_path = Path(repo_path)

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        files: List[FileComplexity] = []
        all_hotspots: List[Tuple[str, FunctionComplexity]] = []

        # Find all Python files
        python_files = list(repo_path.rglob("*.py"))

        logger.info(f"Analyzing {len(python_files)} Python files...")

        for py_file in python_files:
            try:
                file_complexity = self.analyze_file(str(py_file))
                files.append(file_complexity)

                # Collect hotspots
                for func in file_complexity.functions:
                    if func.is_hotspot:
                        all_hotspots.append((str(py_file), func))

            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
                continue

        # Calculate overall metrics
        metrics = self._calculate_metrics(files, all_hotspots)

        # Sort hotspots by complexity (descending)
        all_hotspots.sort(key=lambda x: x[1].complexity, reverse=True)

        return ComplexityReport(
            metrics=metrics,
            files=files,
            hotspots=all_hotspots,
        )

    def analyze_file(self, file_path: str) -> FileComplexity:
        """
        Analyze a single Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            FileComplexity object with all metrics
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Calculate cyclomatic complexity for all functions
        cc_results = cc_visit(code)

        # Calculate maintainability index
        mi_score = mi_visit(code, multi=True)
        mi_index = mi_score if isinstance(mi_score, (int, float)) else 0.0
        mi_ranking = mi_rank(mi_index)

        # Calculate raw metrics
        raw_metrics = analyze(code)

        # Parse AST for nesting depth and cognitive complexity
        try:
            tree = ast.parse(code)
            nesting_info = self._calculate_nesting_depth(tree)
        except Exception as e:
            logger.warning(f"Failed to parse AST for {file_path}: {e}")
            nesting_info = {}

        # Build function complexity objects
        functions = []
        for result in cc_results:
            func_name = result.name
            nesting_depth = nesting_info.get(func_name, 0)

            # Estimate cognitive complexity (simplified)
            # In practice, cognitive complexity requires more sophisticated analysis
            # For now, we use cyclomatic complexity as a proxy
            cognitive_complexity = self._estimate_cognitive_complexity(
                result.complexity, nesting_depth
            )

            # Use the higher of cyclomatic and cognitive complexity to better
            # capture deep nesting as part of the primary complexity score.
            effective_complexity = max(result.complexity, cognitive_complexity)

            func_complexity = FunctionComplexity(
                name=func_name,
                line_number=result.lineno,
                complexity=effective_complexity,
                rank=cc_rank(effective_complexity),
                nesting_depth=nesting_depth,
                cognitive_complexity=cognitive_complexity,
            )
            functions.append(func_complexity)

        # Calculate file-level statistics
        complexities = [f.complexity for f in functions] if functions else [0]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0
        max_complexity = max(complexities) if complexities else 0

        return FileComplexity(
            file_path=file_path,
            maintainability_index=mi_index,
            maintainability_rank=mi_ranking,
            functions=functions,
            lines_of_code=raw_metrics.loc,
            logical_lines=raw_metrics.lloc,
            source_lines=raw_metrics.sloc,
            comment_lines=raw_metrics.comments,
            blank_lines=raw_metrics.blank,
            average_complexity=avg_complexity,
            max_complexity=max_complexity,
        )

    def _calculate_nesting_depth(self, tree: ast.AST) -> Dict[str, int]:
        """
        Calculate nesting depth for each function in the AST.

        Args:
            tree: AST tree of the Python file

        Returns:
            Dictionary mapping function names to max nesting depth
        """
        nesting_info = {}

        class NestingVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_function = None
                self.current_depth = 0
                self.max_depths = {}

            def visit_FunctionDef(self, node):
                # Save previous context
                prev_function = self.current_function
                prev_depth = self.current_depth

                # Enter new function
                self.current_function = node.name
                self.current_depth = 0
                self.max_depths[node.name] = 0

                # Visit function body
                self.generic_visit(node)

                # Restore context
                self.current_function = prev_function
                self.current_depth = prev_depth

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_control_flow(self, node):
                if self.current_function:
                    self.current_depth += 1
                    self.max_depths[self.current_function] = max(
                        self.max_depths[self.current_function],
                        self.current_depth
                    )
                    self.generic_visit(node)
                    self.current_depth -= 1
                else:
                    self.generic_visit(node)

            visit_If = visit_control_flow
            visit_For = visit_control_flow
            visit_While = visit_control_flow
            visit_With = visit_control_flow
            visit_Try = visit_control_flow

        visitor = NestingVisitor()
        visitor.visit(tree)

        return visitor.max_depths

    def _estimate_cognitive_complexity(
        self, cyclomatic: int, nesting_depth: int
    ) -> int:
        """
        Estimate cognitive complexity based on cyclomatic complexity and nesting.

        This is a simplified estimation. True cognitive complexity requires
        analyzing incremental penalties for nested structures.

        Args:
            cyclomatic: Cyclomatic complexity
            nesting_depth: Maximum nesting depth

        Returns:
            Estimated cognitive complexity score
        """
        # Simple heuristic: cognitive complexity tends to be higher when
        # there's deep nesting, as it's harder to understand
        base = cyclomatic
        nesting_penalty = nesting_depth * 2  # Each nesting level adds 2 to cognitive load

        return base + nesting_penalty

    def _calculate_metrics(
        self,
        files: List[FileComplexity],
        hotspots: List[Tuple[str, FunctionComplexity]]
    ) -> ComplexityMetrics:
        """
        Calculate overall repository metrics.

        Args:
            files: List of analyzed files
            hotspots: List of complexity hotspots

        Returns:
            ComplexityMetrics object
        """
        if not files:
            return ComplexityMetrics()

        total_functions = sum(len(f.functions) for f in files)
        total_hotspots = len(hotspots)

        # Average maintainability index across all files
        mi_scores = [f.maintainability_index for f in files]
        avg_mi = sum(mi_scores) / len(mi_scores) if mi_scores else 0.0

        # Average complexity across all functions
        all_complexities = [
            func.complexity
            for file in files
            for func in file.functions
        ]
        avg_complexity = (
            sum(all_complexities) / len(all_complexities)
            if all_complexities else 0.0
        )
        max_complexity = max(all_complexities) if all_complexities else 0

        # Complexity distribution (histogram)
        distribution = {
            'A (1-5)': 0,    # Low risk, simple
            'B (6-10)': 0,   # Low risk, well-structured
            'C (11-20)': 0,  # Moderate risk
            'D (21-30)': 0,  # High risk
            'E (31-40)': 0,  # Very high risk
            'F (41+)': 0,    # Extremely high risk
        }

        for complexity in all_complexities:
            if complexity <= 5:
                distribution['A (1-5)'] += 1
            elif complexity <= 10:
                distribution['B (6-10)'] += 1
            elif complexity <= 20:
                distribution['C (11-20)'] += 1
            elif complexity <= 30:
                distribution['D (21-30)'] += 1
            elif complexity <= 40:
                distribution['E (31-40)'] += 1
            else:
                distribution['F (41+)'] += 1

        return ComplexityMetrics(
            total_files=len(files),
            total_functions=total_functions,
            total_hotspots=total_hotspots,
            average_maintainability_index=avg_mi,
            average_complexity=avg_complexity,
            max_complexity=max_complexity,
            complexity_distribution=distribution,
        )
