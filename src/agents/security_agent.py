"""
Security Analysis Agent

Scans dependencies for known vulnerabilities:
- Python (PyPI)
- JavaScript (npm)
- Rust (crates.io)
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from src.security.vulnerability_scanner import (
    VulnerabilityScanner,
    VulnerabilityReport,
    Severity,
)
from src.storage.adapter import StorageAdapter

logger = logging.getLogger(__name__)


@dataclass
class SecurityAnalysisResult:
    """Result from security/vulnerability analysis."""
    repository: str
    summary: Dict[str, int]
    vulnerabilities: List[Dict[str, Any]]
    scanned_files: List[str]
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'repository': self.repository,
            'summary': self.summary,
            'vulnerabilities': self.vulnerabilities,
            'scanned_files': self.scanned_files,
            'success': self.success,
            'error_message': self.error_message,
        }


class SecurityAgent:
    """
    Agent for analyzing security vulnerabilities in repositories.

    Integrates with LangGraph workflow to provide vulnerability scanning.
    """

    def __init__(self, storage: Optional[StorageAdapter] = None):
        """
        Initialize the security agent.

        Args:
            storage: Storage adapter for persisting results
        """
        self.storage = storage
        self.scanner = VulnerabilityScanner()

    def analyze_repository(
        self,
        repo_path: str,
        repo_name: str,
        analysis_run_id: Optional[int] = None,
    ) -> SecurityAnalysisResult:
        """
        Scan repository for security vulnerabilities.

        Args:
            repo_path: Path to the repository
            repo_name: Repository name (owner/repo)
            analysis_run_id: ID of the analysis run for persistence

        Returns:
            SecurityAnalysisResult with all vulnerabilities
        """
        logger.info(f"Starting security scan for {repo_name}")

        try:
            # Run vulnerability scan
            report = self.scanner.scan_repository(repo_path)

            # Convert to result format
            result = SecurityAnalysisResult(
                repository=repo_name,
                summary=report.summary,
                vulnerabilities=[v.to_dict() for v in report.vulnerabilities],
                scanned_files=report.scanned_files,
                success=True,
            )

            # Persist to database if storage is available
            if self.storage and analysis_run_id:
                self._persist_results(result, analysis_run_id, report)

            logger.info(
                f"Security scan complete for {repo_name}: "
                f"{result.summary['total_vulnerabilities']} vulnerabilities found "
                f"({result.summary['critical']} critical, {result.summary['high']} high)"
            )

            return result

        except Exception as e:
            logger.error(f"Security scan failed for {repo_name}: {e}")
            return SecurityAnalysisResult(
                repository=repo_name,
                summary={},
                vulnerabilities=[],
                scanned_files=[],
                success=False,
                error_message=str(e),
            )

    def _persist_results(
        self,
        result: SecurityAnalysisResult,
        analysis_run_id: int,
        report: VulnerabilityReport,
    ) -> None:
        """
        Persist security analysis results to database.

        Args:
            result: Security analysis result
            analysis_run_id: ID of the analysis run
            report: Full vulnerability report
        """
        try:
            # Store vulnerabilities as pain points
            for vuln in report.vulnerabilities:
                severity = self._map_severity_to_int(vuln.severity)

                description = (
                    f"Security vulnerability {vuln.vulnerability_id} found in "
                    f"{vuln.package_name} v{vuln.installed_version}. "
                    f"{vuln.title}"
                )

                pain_point = self.storage.create_pain_point(
                    analysis_run_id=analysis_run_id,
                    type="security_vulnerability",
                    severity=severity,
                    description=description,
                    confidence_score=0.95,  # High confidence for known CVEs
                    metadata={
                        'package_name': vuln.package_name,
                        'installed_version': vuln.installed_version,
                        'vulnerability_id': vuln.vulnerability_id,
                        'severity': vuln.severity.value,
                        'cvss_score': vuln.cvss_score,
                        'affected_versions': vuln.affected_versions,
                        'fixed_version': vuln.fixed_version,
                        'published_date': vuln.published_date,
                        'references': vuln.references,
                    }
                )

                # Add fix recommendation
                self.storage.create_recommendation(
                    pain_point_id=pain_point.id,
                    action=vuln.fix_recommendation,
                )

            logger.info(
                f"Persisted {len(report.vulnerabilities)} vulnerabilities "
                f"to analysis run {analysis_run_id}"
            )

        except Exception as e:
            logger.error(f"Failed to persist security results: {e}")

    def _map_severity_to_int(self, severity: Severity) -> int:
        """
        Map Severity enum to integer (1-5).

        Args:
            severity: Severity enum value

        Returns:
            Integer severity (1-5)
        """
        severity_map = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.UNKNOWN: 1,
        }
        return severity_map.get(severity, 1)

    def get_summary_metrics(self, result: SecurityAnalysisResult) -> Dict[str, Any]:
        """
        Get summary metrics for reporting.

        Args:
            result: Security analysis result

        Returns:
            Dictionary of summary metrics
        """
        return {
            'total_vulnerabilities': result.summary.get('total_vulnerabilities', 0),
            'critical_vulnerabilities': result.summary.get('critical', 0),
            'high_vulnerabilities': result.summary.get('high', 0),
            'medium_vulnerabilities': result.summary.get('medium', 0),
            'low_vulnerabilities': result.summary.get('low', 0),
            'files_scanned': len(result.scanned_files),
        }

    def get_top_vulnerabilities(
        self,
        result: SecurityAnalysisResult,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get the most severe vulnerabilities.

        Args:
            result: Security analysis result
            limit: Maximum number of vulnerabilities to return

        Returns:
            List of top vulnerabilities sorted by severity
        """
        # Sort by severity (critical > high > medium > low)
        severity_order = {
            'CRITICAL': 0,
            'HIGH': 1,
            'MEDIUM': 2,
            'LOW': 3,
            'UNKNOWN': 4,
        }

        sorted_vulns = sorted(
            result.vulnerabilities,
            key=lambda v: severity_order.get(v.get('severity', 'UNKNOWN'), 4)
        )

        return sorted_vulns[:limit]
