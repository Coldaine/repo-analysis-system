"""
Tests for Pre-Processing Engine
"""

import pytest
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from preprocessing.engine import (
    PreProcessingEngine,
    PreProcessedData,
    CommitInfo,
    PullRequestInfo,
    IssueInfo
)


class TestPreProcessingEngine:
    """Test suite for Pre-Processing Engine"""

    def test_initialization(self, test_config):
        """Test engine initialization"""
        engine = PreProcessingEngine(test_config)

        assert engine.config == test_config
        assert engine.commits_lookback_days == 30
        assert engine.output_directory.exists()

    def test_parse_pull_request(self, test_config, mock_github_response):
        """Test PR data parsing"""
        engine = PreProcessingEngine(test_config)
        pr_data = mock_github_response['pull_request']

        pr_info = engine._parse_pull_request(pr_data)

        assert isinstance(pr_info, PullRequestInfo)
        assert pr_info.number == 1
        assert pr_info.title == 'Test PR'
        assert pr_info.state == 'open'
        assert pr_info.author == 'test-author'

    def test_parse_issue(self, test_config):
        """Test issue data parsing"""
        engine = PreProcessingEngine(test_config)

        issue_data = {
            'number': 10,
            'title': 'Test Issue',
            'state': 'open',
            'user': {'login': 'test-user'},
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z',
            'closed_at': None,
            'labels': [{'name': 'bug'}],
            'comments': 3
        }

        issue_info = engine._parse_issue(issue_data)

        assert isinstance(issue_info, IssueInfo)
        assert issue_info.number == 10
        assert issue_info.title == 'Test Issue'
        assert 'bug' in issue_info.labels
        assert issue_info.comments == 3

    def test_health_check(self, test_config):
        """Test health check"""
        engine = PreProcessingEngine(test_config)

        health = engine.health_check()

        assert 'status' in health
        assert 'cache' in health
        assert 'configuration' in health


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'), reason="Requires GITHUB_TOKEN")
class TestPreProcessingEngineIntegration:
    """Integration tests with real GitHub API"""

    def test_gather_pull_requests_live(self, test_config):
        """Test gathering PRs from real GitHub repository"""
        engine = PreProcessingEngine(test_config)

        # Use a known repository with PRs
        prs = engine._gather_pull_requests('Coldaine', 'repo-analysis-system')

        assert isinstance(prs, list)
        if len(prs) > 0:
            assert all(isinstance(pr, PullRequestInfo) for pr in prs)

    def test_preprocess_repository_live(self, test_config, temp_repo_dir):
        """Test full preprocessing with real repository"""
        # First, we need a real git repository
        # Clone a small test repository
        subprocess.run(
            [
                'git', 'clone', '--depth', '1',
                'https://github.com/Coldaine/repo-analysis-system.git',
                str(temp_repo_dir)
            ],
            check=False,  # Don't fail if repo doesn't exist
            capture_output=True
        )

        if not (temp_repo_dir / '.git').exists():
            pytest.skip("Could not clone test repository")

        engine = PreProcessingEngine(test_config)

        preprocessed = engine.preprocess_repository(
            temp_repo_dir,
            'repo-analysis-system',
            'Coldaine',
            force=True
        )

        assert isinstance(preprocessed, PreProcessedData)
        assert preprocessed.repo_name == 'repo-analysis-system'
        assert preprocessed.repo_owner == 'Coldaine'
        assert preprocessed.latest_commit
        assert preprocessed.default_branch
        assert preprocessed.generation_time_seconds > 0
