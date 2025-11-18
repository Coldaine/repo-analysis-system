"""
Unit and integration tests for GitHub Sync Service
"""

import os
import pytest
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from sync.github_sync import GitHubSyncService, RepositoryInfo, SyncResult


class TestGitHubSyncService:
    """Test suite for GitHub Sync Service"""

    def test_initialization(self, test_config):
        """Test service initialization"""
        service = GitHubSyncService(test_config)

        assert service.config == test_config
        assert service.github_token == test_config['github']['token']
        assert service.repos_directory.exists()
        assert service.max_retries == test_config['sync']['max_retries']

    def test_parse_repository_data(self, test_config, mock_github_response):
        """Test parsing GitHub API repository data"""
        service = GitHubSyncService(test_config)
        repo_data = mock_github_response['repository']

        repo_info = service._parse_repository_data(repo_data)

        assert isinstance(repo_info, RepositoryInfo)
        assert repo_info.name == 'test-repo'
        assert repo_info.owner == 'test-owner'
        assert repo_info.github_id == 123456
        assert repo_info.language == 'Python'

    @patch('sync.github_sync.requests.Session.get')
    def test_discover_repositories(self, mock_get, test_config, mock_github_response):
        """Test repository discovery"""
        service = GitHubSyncService(test_config)

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_github_response['repository']]
        mock_response.headers = {'X-RateLimit-Remaining': '5000'}
        mock_get.return_value = mock_response

        repos = service.discover_repositories('test-owner')

        assert len(repos) == 1
        assert repos[0].name == 'test-repo'
        assert repos[0].owner == 'test-owner'

    def test_health_check(self, test_config):
        """Test health check"""
        service = GitHubSyncService(test_config)

        health = service.health_check()

        assert 'status' in health
        assert 'timestamp' in health
        assert 'local_storage' in health
        assert health['local_storage']['repos_directory'] == str(service.repos_directory)


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'), reason="Requires GITHUB_TOKEN")
class TestGitHubSyncIntegration:
    """Integration tests with real GitHub API"""

    def test_discover_repositories_live(self, test_config):
        """Test discovering repositories from real GitHub account"""
        service = GitHubSyncService(test_config)

        owner = test_config['github'].get('default_owner')
        if not owner:
            pytest.skip("No default_owner configured")

        repos = service.discover_repositories(owner, include_forks=False)

        assert isinstance(repos, list)
        # Should have at least 1 repository for most accounts
        if len(repos) > 0:
            assert all(isinstance(r, RepositoryInfo) for r in repos)
            assert all(r.owner == owner for r in repos)

    def test_sync_repository_live(self, test_config, temp_repo_dir):
        """Test syncing a real repository (shallow clone)"""
        # Use a small public repository for testing
        test_repo = RepositoryInfo(
            name='repo-analysis-system',
            owner='Coldaine',
            github_id=999999,
            description='Test',
            language='Python',
            default_branch='main',
            clone_url='https://github.com/Coldaine/repo-analysis-system.git',
            ssh_url='git@github.com:Coldaine/repo-analysis-system.git',
            is_private=False,
            is_fork=False,
            is_archived=False,
            size=100,
            stars=0,
            last_pushed=datetime.now(timezone.utc)
        )

        # Override repos directory
        config = test_config.copy()
        config['sync']['repos_directory'] = str(temp_repo_dir)
        config['sync']['shallow_clone'] = True

        service = GitHubSyncService(config)
        result = service.sync_repository(test_repo)

        # Check result
        assert isinstance(result, SyncResult)
        if result.success:
            assert result.action in ['cloned', 'pulled', 'skipped']
            assert result.local_path.exists()
            assert (result.local_path / '.git').exists()
