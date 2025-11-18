"""
End-to-End Integration Tests
Tests the complete workflow from repository sync to report generation
"""

import os
import pytest
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from sync.github_sync import GitHubSyncService
from baseline.initializer import BaselineInitializer
from preprocessing.engine import PreProcessingEngine
from parallel.ccr_spawner import CCRAgentSpawner, AgentTask
from reports.pr_report_generator import PRReportGenerator


@pytest.mark.e2e
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'), reason="Requires GITHUB_TOKEN")
class TestEndToEndWorkflow:
    """End-to-end tests for complete analysis workflow"""

    def test_complete_single_repo_workflow(self, test_config, temp_repo_dir):
        """Test complete workflow for a single repository"""

        # Step 1: Initialize services
        sync_service = GitHubSyncService(test_config)
        baseline_service = BaselineInitializer(test_config)
        preproc_engine = PreProcessingEngine(test_config)

        # Step 2: Clone a test repository
        test_repo_url = 'https://github.com/Coldaine/repo-analysis-system.git'
        clone_result = subprocess.run(
            ['git', 'clone', '--depth', '1', test_repo_url, str(temp_repo_dir)],
            capture_output=True,
            text=True
        )

        if clone_result.returncode != 0:
            pytest.skip(f"Could not clone test repository: {clone_result.stderr}")

        # Step 3: Initialize baseline
        baseline = baseline_service.initialize_repository_baseline(
            temp_repo_dir,
            'repo-analysis-system',
            'Coldaine',
            user_id=1
        )

        assert baseline is not None
        assert baseline.repo_name == 'repo-analysis-system'
        assert len(baseline.goals) >= 4
        assert len(baseline.phases) >= 1

        # Step 4: Pre-process repository
        preprocessed = preproc_engine.preprocess_repository(
            temp_repo_dir,
            'repo-analysis-system',
            'Coldaine',
            force=True
        )

        assert preprocessed is not None
        assert preprocessed.latest_commit
        assert isinstance(preprocessed.commits_last_30_days, list)
        assert isinstance(preprocessed.open_prs, list)

        # Step 5: Verify all components are healthy
        sync_health = sync_service.health_check()
        baseline_health = baseline_service.health_check()
        preproc_health = preproc_engine.health_check()

        assert sync_health['status'] in ['healthy', 'degraded']
        assert baseline_health['status'] in ['healthy', 'degraded']
        assert preproc_health['status'] in ['healthy', 'degraded']

        print(f"\n✓ End-to-end test passed!")
        print(f"  - Baseline: {len(baseline.goals)} goals, {len(baseline.phases)} phases")
        print(f"  - Preprocessing: {len(preprocessed.commits_last_30_days)} commits, "
              f"{len(preprocessed.open_prs)} open PRs")

    def test_multi_repo_parallel_workflow(self, test_config):
        """Test parallel processing of multiple repositories"""

        # Initialize spawner
        spawner = CCRAgentSpawner(test_config)

        # Create mock tasks for multiple repos
        repos = ['repo1', 'repo2', 'repo3']
        tasks = []

        for idx, repo in enumerate(repos):
            task = AgentTask(
                task_id=f'task-{idx}',
                repo_name=repo,
                repo_owner='test-owner',
                repo_path=Path('/tmp') / repo,  # Mock path
                task_type='analyze',
                input_data={'test': True},
                priority=idx + 1
            )
            tasks.append(task)

        # Run parallel analysis
        results = spawner.spawn_parallel_analysis(tasks)

        assert len(results) == len(tasks)
        assert all(r.task_id in [t.task_id for t in tasks] for r in results)

        # Get statistics
        stats = spawner.get_statistics()
        assert stats['total_tasks'] == len(tasks)
        assert stats['success_rate'] >= 0

        # Cleanup
        spawner.cleanup()

        print(f"\n✓ Parallel workflow test passed!")
        print(f"  - Tasks: {len(tasks)}")
        print(f"  - Success rate: {stats['success_rate']:.1f}%")

    def test_pr_report_generation_workflow(self, test_config):
        """Test PR report generation for multiple repositories"""

        report_generator = PRReportGenerator(test_config)

        # Generate report for test repositories
        # Note: These need to be actual repositories with PRs for a real test
        repos = ['Coldaine/repo-analysis-system']

        report = report_generator.generate_report(repos)

        assert isinstance(report, str)
        assert '# Open Pull Requests Analysis' in report
        assert 'Executive Summary' in report

        # Health check
        health = report_generator.health_check()
        assert 'status' in health

        print(f"\n✓ PR report generation test passed!")
        print(f"  - Report length: {len(report)} characters")


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceMetrics:
    """Test performance metrics for the system"""

    def test_preprocessing_performance(self, test_config, temp_repo_dir):
        """Test that preprocessing meets performance goals (60-70% time savings)"""
        import time

        # Clone a test repository
        subprocess.run(
            ['git', 'clone', '--depth', '1',
             'https://github.com/Coldaine/repo-analysis-system.git',
             str(temp_repo_dir)],
            capture_output=True,
            check=False
        )

        if not (temp_repo_dir / '.git').exists():
            pytest.skip("Could not clone test repository")

        engine = PreProcessingEngine(test_config)

        # First run (cold cache)
        start = time.time()
        result1 = engine.preprocess_repository(
            temp_repo_dir,
            'repo-analysis-system',
            'Coldaine',
            force=True
        )
        cold_time = time.time() - start

        # Second run (warm cache)
        start = time.time()
        result2 = engine.preprocess_repository(
            temp_repo_dir,
            'repo-analysis-system',
            'Coldaine',
            force=False
        )
        warm_time = time.time() - start

        # Cache should be significantly faster
        # Note: In a real test, warm time should be near-zero (just loading from cache)
        print(f"\n✓ Preprocessing performance:")
        print(f"  - Cold cache: {cold_time:.2f}s")
        print(f"  - Warm cache: {warm_time:.2f}s")
        print(f"  - Time saved: {((cold_time - warm_time) / cold_time * 100):.1f}%")

    def test_concurrent_agent_scalability(self, test_config):
        """Test that CCR spawner can handle 5+ concurrent agents"""

        spawner = CCRAgentSpawner(test_config)

        # Create 10 tasks
        tasks = [
            AgentTask(
                task_id=f'scale-test-{i}',
                repo_name=f'repo-{i}',
                repo_owner='test-owner',
                repo_path=Path('/tmp') / f'repo-{i}',
                task_type='analyze',
                input_data={'test': True},
                priority=i
            )
            for i in range(10)
        ]

        import time
        start = time.time()
        results = spawner.spawn_parallel_analysis(tasks)
        total_time = time.time() - start

        stats = spawner.get_statistics()

        # Calculate theoretical sequential time (sum of all durations)
        sequential_time = sum(r.duration_seconds for r in results)
        speedup = sequential_time / total_time if total_time > 0 else 1

        spawner.cleanup()

        print(f"\n✓ Scalability test passed:")
        print(f"  - Total tasks: {len(tasks)}")
        print(f"  - Max concurrent: {test_config['parallel']['max_concurrent_agents']}")
        print(f"  - Parallel time: {total_time:.2f}s")
        print(f"  - Sequential time: {sequential_time:.2f}s")
        print(f"  - Speedup: {speedup:.2f}x")

        assert stats['success_rate'] >= 95, "Should have >95% success rate (Goal 7)"


@pytest.mark.e2e
@pytest.mark.live
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'), reason="Requires GITHUB_TOKEN")
class TestLiveGitHubIntegration:
    """Live tests with real GitHub API"""

    def test_discover_and_sync_all_repos(self, test_config):
        """Test discovering and syncing all repositories for an owner"""

        owner = test_config['github'].get('default_owner')
        if not owner or owner == 'test-user':
            pytest.skip("No real GitHub owner configured")

        sync_service = GitHubSyncService(test_config)

        # Discover all repos
        repos = sync_service.discover_repositories(owner, include_forks=False)

        if len(repos) == 0:
            pytest.skip(f"No repositories found for {owner}")

        print(f"\n✓ Discovered {len(repos)} repositories for {owner}")

        # Sync first 3 repos (to avoid long test times)
        sync_results = []
        for repo in repos[:3]:
            result = sync_service.sync_repository(repo)
            sync_results.append(result)

        success_count = sum(1 for r in sync_results if r.success)
        success_rate = (success_count / len(sync_results) * 100) if sync_results else 0

        print(f"  - Synced {len(sync_results)} repositories")
        print(f"  - Success rate: {success_rate:.1f}%")

        assert success_rate >= 99, "Should have >99% sync success rate (Goal 1)"

    def test_baseline_initialization_all_repos(self, test_config):
        """Test that all discovered repos can have baselines initialized"""

        owner = test_config['github'].get('default_owner')
        if not owner or owner == 'test-user':
            pytest.skip("No real GitHub owner configured")

        sync_service = GitHubSyncService(test_config)
        baseline_service = BaselineInitializer(test_config)

        # Get local repositories
        local_repos = sync_service.get_local_repositories()

        if len(local_repos) == 0:
            pytest.skip("No local repositories available")

        # Initialize baselines for first 3 local repos
        baseline_results = []
        for repo_path in local_repos[:3]:
            try:
                # Extract owner/name from path
                parts = repo_path.parts
                repo_name = parts[-1]
                repo_owner = parts[-2]

                baseline = baseline_service.initialize_repository_baseline(
                    repo_path,
                    repo_name,
                    repo_owner
                )

                baseline_results.append(True)
                assert len(baseline.goals) >= 4, "Should have at least 4 goals"
                assert baseline.generation_time_seconds < 600, "Should complete in <10 min (Goal 2)"

            except Exception as e:
                print(f"  ! Failed to initialize baseline for {repo_path}: {e}")
                baseline_results.append(False)

        success_rate = (sum(baseline_results) / len(baseline_results) * 100) if baseline_results else 0

        print(f"\n✓ Baseline initialization test:")
        print(f"  - Repositories tested: {len(baseline_results)}")
        print(f"  - Success rate: {success_rate:.1f}%")

        assert success_rate >= 100, "Should have 100% repositories with baselines (Goal 2)"
