"""
Complexity Analysis Agent

Analyzes code complexity metrics for repositories:
- Cyclomatic complexity
- Cognitive complexity
- Maintainability index
- Complexity hotspots
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from src.analysis.complexity_analyzer import ComplexityAnalyzer
from src.storage.adapter import StorageAdapter

logger = logging.getLogger(__name__)


@dataclass
class ComplexityAnalysisResult:
    """Result from complexity analysis."""
    repository: str
    metrics: Dict[str, Any]
    hotspots: List[Dict[str, Any]]
    files: List[Dict[str, Any]]
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'repository': self.repository,
            'metrics': self.metrics,
            'hotspots': self.hotspots,
            'files': self.files,
            'success': self.success,
            'error_message': self.error_message,
        }


class ComplexityAgent:
    """
    Agent for analyzing code complexity in repositories.

    Integrates with LangGraph workflow to provide complexity metrics.
    """

    def __init__(
        self,
        storage: Optional[StorageAdapter] = None,
        hotspot_threshold: int = 10,
    ):
        """
        Initialize the complexity agent.

        Args:
            storage: Storage adapter for persisting results
            hotspot_threshold: Complexity threshold for identifying hotspots
        """
        self.storage = storage
        self.analyzer = ComplexityAnalyzer(hotspot_threshold=hotspot_threshold)
        self.hotspot_threshold = hotspot_threshold

    def analyze_repository(
        self,
        repo_path: str,
        repo_name: str,
        analysis_run_id: Optional[int] = None,
    ) -> ComplexityAnalysisResult:
        """
        Analyze complexity metrics for a repository.

        Args:
            repo_path: Path to the repository
            repo_name: Repository name (owner/repo)
            analysis_run_id: ID of the analysis run for persistence

        Returns:
            ComplexityAnalysisResult with all metrics
        """
        logger.info(f"Starting complexity analysis for {repo_name}")

        try:
            # Run complexity analysis
            report = self.analyzer.analyze_repository(repo_path)

            # Convert to result format
            result = ComplexityAnalysisResult(
                repository=repo_name,
                metrics=report.metrics.to_dict(),
                hotspots=[
                    {
                        'file': str(file_path),
                        'function': func.to_dict(),
                    }
                    for file_path, func in report.hotspots
                ],
                files=[file.to_dict() for file in report.files],
                success=True,
            )

            # Persist to database if storage is available
            if self.storage and analysis_run_id:
                self._persist_results(result, analysis_run_id)

            logger.info(
                f"Complexity analysis complete for {repo_name}: "
                f"{result.metrics['total_hotspots']} hotspots found"
            )

            return result

        except Exception as e:
            logger.error(f"Complexity analysis failed for {repo_name}: {e}")
            return ComplexityAnalysisResult(
                repository=repo_name,
                metrics={},
                hotspots=[],
                files=[],
                success=False,
                error_message=str(e),
            )

    def _persist_results(
        self,
        result: ComplexityAnalysisResult,
        analysis_run_id: int,
    ) -> None:
        """
        Persist complexity analysis results to database.

        Args:
            result: Complexity analysis result
            analysis_run_id: ID of the analysis run
        """
        try:
            # Store complexity hotspots as pain points
            for hotspot_data in result.hotspots:
                file_path = hotspot_data['file']
                func = hotspot_data['function']

                severity = self._calculate_severity(func['cyclomatic_complexity'])

                description = (
                    f"High complexity detected in function '{func['name']}' "
                    f"at {file_path}:{func['line_number']}. "
                    f"Cyclomatic complexity: {func['cyclomatic_complexity']}, "
                    f"Cognitive complexity: {func['cognitive_complexity']}, "
                    f"Nesting depth: {func['nesting_depth']}"
                )

                pain_point = self.storage.create_pain_point(
                    analysis_run_id=analysis_run_id,
                    type="complexity_hotspot",
                    severity=severity,
                    description=description,
                    confidence_score=0.9,  # High confidence for static analysis
                    metadata={
                        'file': file_path,
                        'function': func['name'],
                        'line_number': func['line_number'],
                        'cyclomatic_complexity': func['cyclomatic_complexity'],
                        'cognitive_complexity': func['cognitive_complexity'],
                        'nesting_depth': func['nesting_depth'],
                        'rank': func['rank'],
                    }
                )

                # Add recommendations
                recommendations = self._generate_recommendations(func)
                for rec in recommendations:
                    self.storage.create_recommendation(
                        pain_point_id=pain_point.id,
                        action=rec,
                    )

            logger.info(
                f"Persisted {len(result.hotspots)} complexity hotspots "
                f"to analysis run {analysis_run_id}"
            )

        except Exception as e:
            logger.error(f"Failed to persist complexity results: {e}")

    def _calculate_severity(self, complexity: int) -> int:
        """
        Calculate severity level based on complexity.

        Args:
            complexity: Cyclomatic complexity value

        Returns:
            Severity level (1-5)
        """
        if complexity > 40:
            return 5  # Critical
        elif complexity > 30:
            return 4  # High
        elif complexity > 20:
            return 3  # Medium
        elif complexity > 10:
            return 2  # Low
        else:
            return 1  # Info

    def _generate_recommendations(self, func: Dict[str, Any]) -> List[str]:
        """
        Generate refactoring recommendations based on complexity metrics.

        Args:
            func: Function complexity data

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        complexity = func['cyclomatic_complexity']
        nesting_depth = func['nesting_depth']

        if complexity > 20:
            recommendations.append(
                f"Refactor {func['name']} by extracting logical units into smaller functions"
            )

        if nesting_depth > 3:
            recommendations.append(
                f"Reduce nesting depth in {func['name']} using early returns or guard clauses"
            )

        if complexity > 10:
            recommendations.append(
                f"Add unit tests for {func['name']} to ensure behavior is preserved during refactoring"
            )

        if not recommendations:
            recommendations.append(
                f"Consider refactoring {func['name']} to improve maintainability"
            )

        return recommendations

    def get_summary_metrics(self, result: ComplexityAnalysisResult) -> Dict[str, Any]:
        """
        Get summary metrics for reporting.

        Args:
            result: Complexity analysis result

        Returns:
            Dictionary of summary metrics
        """
        return {
            'total_files_analyzed': result.metrics.get('total_files', 0),
            'total_functions_analyzed': result.metrics.get('total_functions', 0),
            'complexity_hotspots': result.metrics.get('total_hotspots', 0),
            'average_maintainability_index': result.metrics.get('average_maintainability_index', 0),
            'average_complexity': result.metrics.get('average_complexity', 0),
            'max_complexity': result.metrics.get('max_complexity', 0),
            'complexity_distribution': result.metrics.get('complexity_distribution', {}),
        }
