"""
Tests for Baseline Initialization System
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from baseline.initializer import (
    BaselineInitializer,
    RepositoryBaseline,
    RepositoryClassification,
    RepositoryGoal,
    DevelopmentPhase
)


class TestBaselineInitializer:
    """Test suite for Baseline Initializer"""

    def test_initialization(self, test_config):
        """Test initializer setup"""
        initializer = BaselineInitializer(test_config)

        assert initializer.config == test_config
        assert initializer.min_goals == 4
        assert initializer.max_goals == 10

    def test_analyze_repository_structure(self, test_config, temp_repo_dir):
        """Test repository structure analysis"""
        initializer = BaselineInitializer(test_config)

        # Create test files
        (temp_repo_dir / 'README.md').touch()
        (temp_repo_dir / 'requirements.txt').touch()
        (temp_repo_dir / 'tests').mkdir()

        analysis = initializer._analyze_repository_structure(temp_repo_dir)

        assert analysis['has_readme'] is True
        assert 'Python' in analysis['languages']
        assert 'pip' in analysis['package_managers']
        assert analysis['has_tests'] is True

    def test_heuristic_classify_repository(self, test_config):
        """Test heuristic repository classification"""
        initializer = BaselineInitializer(test_config)

        # Small repository
        analysis = {
            'file_count': 30,
            'has_tests': False,
            'has_ci': False,
            'languages': ['Python']
        }

        classification = initializer._heuristic_classify_repository(analysis)

        assert isinstance(classification, RepositoryClassification)
        assert classification.type == 'greenfield'
        assert 0.0 <= classification.confidence <= 1.0

    def test_default_goals(self, test_config):
        """Test default goal generation"""
        initializer = BaselineInitializer(test_config)

        analysis = {
            'has_tests': False,
            'has_ci': False,
            'has_docs': False,
            'languages': ['Python']
        }

        classification = RepositoryClassification(
            type='greenfield',
            confidence=0.8,
            reasoning='New project'
        )

        goals = initializer._default_goals(analysis, classification)

        assert isinstance(goals, list)
        assert len(goals) >= initializer.min_goals
        assert all(isinstance(g, RepositoryGoal) for g in goals)
        assert all(1 <= g.priority <= 5 for g in goals)

    def test_calculate_baseline_hash(self, test_config):
        """Test baseline hash calculation"""
        initializer = BaselineInitializer(test_config)

        baseline = RepositoryBaseline(
            repo_name='test-repo',
            repo_owner='test-owner',
            classification=RepositoryClassification('greenfield', 0.8, 'New project'),
            goals=[
                RepositoryGoal(
                    id='goal-1',
                    title='Test Goal',
                    description='Test',
                    success_criteria=['Criterion 1'],
                    priority=1,
                    category='feature'
                )
            ],
            phases=[],
            metadata={},
            generated_at='2024-01-01T00:00:00Z',
            hash=''
        )

        hash_value = initializer._calculate_baseline_hash(baseline)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hash length

        # Hash should be deterministic
        hash_value2 = initializer._calculate_baseline_hash(baseline)
        assert hash_value == hash_value2

    def test_verify_baseline_integrity(self, test_config):
        """Test baseline integrity verification"""
        initializer = BaselineInitializer(test_config)

        baseline = RepositoryBaseline(
            repo_name='test-repo',
            repo_owner='test-owner',
            classification=RepositoryClassification('greenfield', 0.8, 'New project'),
            goals=[],
            phases=[],
            metadata={},
            generated_at='2024-01-01T00:00:00Z',
            hash=''
        )

        # Calculate correct hash
        baseline.hash = initializer._calculate_baseline_hash(baseline)

        # Verify
        assert initializer.verify_baseline_integrity(baseline) is True

        # Corrupt hash
        baseline.hash = 'invalid_hash'
        assert initializer.verify_baseline_integrity(baseline) is False


@pytest.mark.integration
class TestBaselineInitializerIntegration:
    """Integration tests for baseline initialization"""

    def test_initialize_repository_baseline(self, test_config, temp_repo_dir):
        """Test full baseline initialization"""
        initializer = BaselineInitializer(test_config)

        # Create test repository structure
        (temp_repo_dir / 'README.md').write_text('# Test Repo')
        (temp_repo_dir / 'requirements.txt').write_text('pytest\n')
        (temp_repo_dir / 'src').mkdir()
        (temp_repo_dir / 'tests').mkdir()

        baseline = initializer.initialize_repository_baseline(
            temp_repo_dir,
            'test-repo',
            'test-owner'
        )

        assert isinstance(baseline, RepositoryBaseline)
        assert baseline.repo_name == 'test-repo'
        assert baseline.repo_owner == 'test-owner'
        assert len(baseline.goals) >= 4
        assert len(baseline.phases) >= 1
        assert baseline.hash
        assert initializer.verify_baseline_integrity(baseline)

        # Check that .baseline.json was created
        baseline_file = temp_repo_dir / '.baseline.json'
        assert baseline_file.exists()

        # Verify file content
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
            assert baseline_data['hash'] == baseline.hash
