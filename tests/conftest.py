"""
Pytest configuration and shared fixtures
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture(scope='session')
def test_config() -> Dict[str, Any]:
    """Provide test configuration"""
    return {
        'github': {
            'token': os.getenv('GITHUB_TOKEN'),
            'api_base': 'https://api.github.com',
            'default_owner': os.getenv('TEST_GITHUB_OWNER', 'test-user')
        },
        'database': {
            'host': os.getenv('TEST_DB_HOST', 'localhost'),
            'port': int(os.getenv('TEST_DB_PORT', '5432')),
            'name': os.getenv('TEST_DB_NAME', 'repo_analysis_test'),
            'user': os.getenv('TEST_DB_USER', 'postgres'),
            'password': os.getenv('TEST_DB_PASSWORD', ''),
            'echo': False
        },
        'sync': {
            'repos_directory': tempfile.mkdtemp(prefix='test_repos_'),
            'max_retries': 2,
            'retry_delay': 0.5,
            'use_ssh': False,
            'shallow_clone': True
        },
        'baseline': {
            'min_goals': 4,
            'max_goals': 10,
            'force_regenerate': False
        },
        'preprocessing': {
            'commits_lookback_days': 30,
            'stale_pr_threshold_days': 30,
            'cache_ttl_minutes': 60,
            'output_directory': tempfile.mkdtemp(prefix='test_preproc_')
        },
        'parallel': {
            'max_concurrent_agents': 3,
            'agent_timeout_seconds': 60,
            'max_retries': 1,
            'output_directory': tempfile.mkdtemp(prefix='test_agents_')
        },
        'pr_report': {
            'ancient_threshold_days': 60,
            'recent_threshold_days': 30
        }
    }


@pytest.fixture
def temp_repo_dir():
    """Create temporary directory for test repositories"""
    temp_dir = tempfile.mkdtemp(prefix='test_repo_')
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response data"""
    return {
        'repository': {
            'id': 123456,
            'name': 'test-repo',
            'owner': {'login': 'test-owner'},
            'description': 'Test repository',
            'language': 'Python',
            'default_branch': 'main',
            'clone_url': 'https://github.com/test-owner/test-repo.git',
            'ssh_url': 'git@github.com:test-owner/test-repo.git',
            'private': False,
            'fork': False,
            'archived': False,
            'size': 1000,
            'stargazers_count': 10,
            'pushed_at': '2024-01-01T00:00:00Z'
        },
        'pull_request': {
            'number': 1,
            'title': 'Test PR',
            'state': 'open',
            'draft': False,
            'user': {'login': 'test-author'},
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z',
            'merged_at': None,
            'additions': 10,
            'deletions': 5,
            'changed_files': 2,
            'comments': 1,
            'review_comments': 2,
            'labels': [],
            'head': {'ref': 'feature-branch'},
            'base': {'ref': 'main'},
            'html_url': 'https://github.com/test-owner/test-repo/pull/1'
        }
    }


@pytest.fixture
def cleanup_temp_dirs(test_config):
    """Cleanup temporary directories after tests"""
    yield
    # Cleanup after all tests
    for key in ['sync', 'preprocessing', 'parallel']:
        if key in test_config:
            dir_key = 'repos_directory' if key == 'sync' else 'output_directory'
            temp_dir = test_config[key].get(dir_key)
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
