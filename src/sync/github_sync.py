"""
GitHub Sync Service (Goal 1)
Auto-discover all repositories via GitHub API and clone/pull latest changes

Success Metrics:
- 100% repository coverage
- >99% sync success rate
- Handles rate limits and API failures gracefully
"""

import os
import logging
import subprocess
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import time
import requests

logger = logging.getLogger(__name__)


@dataclass
class RepositoryInfo:
    """Information about a discovered repository"""
    name: str
    owner: str
    github_id: int
    description: Optional[str]
    language: Optional[str]
    default_branch: str
    clone_url: str
    ssh_url: str
    is_private: bool
    is_fork: bool
    is_archived: bool
    size: int
    stars: int
    last_pushed: datetime


@dataclass
class SyncResult:
    """Result of syncing a single repository"""
    repo_name: str
    repo_owner: str
    success: bool
    action: str  # 'cloned', 'pulled', 'skipped', 'failed'
    message: str
    local_path: Optional[Path] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class GitHubSyncService:
    """
    Service for discovering and syncing repositories from GitHub

    Features:
    - Auto-discover all repos for a user/organization
    - Clone missing repositories
    - Pull latest changes for existing repositories
    - Track sync status and timestamps
    - Handle rate limits with exponential backoff
    - Robust error handling and recovery
    """

    def __init__(self, config: Dict[str, Any], storage=None):
        """
        Initialize GitHub sync service

        Args:
            config: Configuration dictionary with GitHub settings
            storage: Optional storage adapter for tracking sync status
        """
        self.config = config
        self.storage = storage

        # GitHub API configuration
        self.github_token = config.get('github', {}).get('token') or os.getenv('GITHUB_TOKEN')
        self.github_api_base = config.get('github', {}).get('api_base', 'https://api.github.com')
        self.default_owner = config.get('github', {}).get('default_owner')

        # Local storage configuration
        self.repos_directory = Path(config.get('sync', {}).get('repos_directory', './repos'))
        self.repos_directory.mkdir(parents=True, exist_ok=True)

        # Sync configuration
        self.max_retries = config.get('sync', {}).get('max_retries', 3)
        self.retry_delay = config.get('sync', {}).get('retry_delay', 2.0)
        self.rate_limit_buffer = config.get('sync', {}).get('rate_limit_buffer', 100)
        self.use_ssh = config.get('sync', {}).get('use_ssh', False)
        self.shallow_clone = config.get('sync', {}).get('shallow_clone', False)

        # Session for HTTP requests
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })

        logger.info(f"GitHub Sync Service initialized - Local directory: {self.repos_directory}")

    def discover_repositories(self, owner: Optional[str] = None,
                             include_forks: bool = False,
                             include_archived: bool = False) -> List[RepositoryInfo]:
        """
        Discover all repositories for a user or organization

        Args:
            owner: GitHub username or organization (uses default_owner if None)
            include_forks: Whether to include forked repositories
            include_archived: Whether to include archived repositories

        Returns:
            List of discovered repositories
        """
        owner = owner or self.default_owner
        if not owner:
            raise ValueError("No owner specified and no default_owner configured")

        logger.info(f"Discovering repositories for owner: {owner}")

        repos = []
        page = 1
        per_page = 100

        while True:
            url = f"{self.github_api_base}/users/{owner}/repos"
            params = {
                'per_page': per_page,
                'page': page,
                'type': 'all',
                'sort': 'updated',
                'direction': 'desc'
            }

            response = self._make_api_request(url, params)
            if not response:
                break

            batch = response.json()
            if not batch:
                break

            for repo_data in batch:
                # Apply filters
                if not include_forks and repo_data.get('fork', False):
                    continue
                if not include_archived and repo_data.get('archived', False):
                    continue

                repo_info = self._parse_repository_data(repo_data)
                repos.append(repo_info)

            logger.debug(f"Discovered {len(batch)} repositories on page {page}")

            # Check if there are more pages
            if len(batch) < per_page:
                break

            page += 1

        logger.info(f"Discovered {len(repos)} repositories for {owner}")
        return repos

    def sync_all_repositories(self, owner: Optional[str] = None,
                             include_forks: bool = False,
                             include_archived: bool = False) -> Dict[str, Any]:
        """
        Sync all repositories for an owner

        Args:
            owner: GitHub username or organization
            include_forks: Whether to sync forked repositories
            include_archived: Whether to sync archived repositories

        Returns:
            Sync summary with results and statistics
        """
        start_time = time.time()

        # Discover repositories
        repos = self.discover_repositories(owner, include_forks, include_archived)

        # Sync each repository
        results = []
        for repo in repos:
            result = self.sync_repository(repo)
            results.append(result)

            # Update database if storage is available
            if self.storage and result.success:
                try:
                    self._update_repository_in_db(repo, result)
                except Exception as e:
                    logger.warning(f"Failed to update database for {repo.name}: {e}")

        # Calculate statistics
        total_time = time.time() - start_time
        stats = self._calculate_sync_stats(results, total_time)

        logger.info(
            f"Sync completed - Success: {stats['success_count']}/{stats['total_count']} "
            f"({stats['success_rate']:.1f}%) in {total_time:.1f}s"
        )

        return {
            'status': 'completed',
            'results': results,
            'statistics': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def sync_repository(self, repo: RepositoryInfo) -> SyncResult:
        """
        Sync a single repository (clone or pull)

        Args:
            repo: Repository information

        Returns:
            Sync result with status and details
        """
        start_time = time.time()

        local_path = self.repos_directory / repo.owner / repo.name

        try:
            if local_path.exists():
                # Repository exists - pull latest changes
                result = self._pull_repository(repo, local_path)
            else:
                # Repository doesn't exist - clone it
                result = self._clone_repository(repo, local_path)

            result.duration_seconds = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"Failed to sync {repo.owner}/{repo.name}: {e}")
            return SyncResult(
                repo_name=repo.name,
                repo_owner=repo.owner,
                success=False,
                action='failed',
                message=f"Sync failed: {str(e)}",
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    def _clone_repository(self, repo: RepositoryInfo, local_path: Path) -> SyncResult:
        """Clone a repository to local filesystem"""
        logger.info(f"Cloning {repo.owner}/{repo.name}...")

        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Choose clone URL (SSH vs HTTPS)
        clone_url = repo.ssh_url if self.use_ssh else repo.clone_url

        # Build git clone command
        cmd = ['git', 'clone']

        if self.shallow_clone:
            cmd.extend(['--depth', '1'])

        cmd.extend([clone_url, str(local_path)])

        # Execute clone with retries
        for attempt in range(self.max_retries):
            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                logger.info(f"Successfully cloned {repo.owner}/{repo.name}")
                return SyncResult(
                    repo_name=repo.name,
                    repo_owner=repo.owner,
                    success=True,
                    action='cloned',
                    message=f"Successfully cloned to {local_path}",
                    local_path=local_path
                )

            except subprocess.TimeoutExpired:
                logger.warning(f"Clone timeout for {repo.owner}/{repo.name} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                raise

            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.strip() if e.stderr else str(e)
                logger.warning(f"Clone failed for {repo.owner}/{repo.name}: {error_msg}")

                if attempt < self.max_retries - 1:
                    # Clean up partial clone
                    if local_path.exists():
                        subprocess.run(['rm', '-rf', str(local_path)], check=False)

                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue

                raise Exception(f"Clone failed after {self.max_retries} attempts: {error_msg}")

    def _pull_repository(self, repo: RepositoryInfo, local_path: Path) -> SyncResult:
        """Pull latest changes for existing repository"""
        logger.debug(f"Pulling updates for {repo.owner}/{repo.name}...")

        try:
            # Check if directory is a valid git repository
            git_dir = local_path / '.git'
            if not git_dir.exists():
                logger.warning(f"{local_path} is not a git repository, will re-clone")
                subprocess.run(['rm', '-rf', str(local_path)], check=False)
                return self._clone_repository(repo, local_path)

            # Fetch latest changes
            for attempt in range(self.max_retries):
                try:
                    # First, fetch
                    subprocess.run(
                        ['git', '-C', str(local_path), 'fetch', 'origin'],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )

                    # Check current branch
                    branch_result = subprocess.run(
                        ['git', '-C', str(local_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    current_branch = branch_result.stdout.strip()

                    # Pull changes
                    pull_result = subprocess.run(
                        ['git', '-C', str(local_path), 'pull', 'origin', current_branch],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )

                    output = pull_result.stdout.strip()

                    if 'Already up to date' in output:
                        logger.debug(f"{repo.owner}/{repo.name} is already up to date")
                        action = 'skipped'
                        message = "Already up to date"
                    else:
                        logger.info(f"Successfully pulled updates for {repo.owner}/{repo.name}")
                        action = 'pulled'
                        message = f"Successfully pulled updates: {output}"

                    return SyncResult(
                        repo_name=repo.name,
                        repo_owner=repo.owner,
                        success=True,
                        action=action,
                        message=message,
                        local_path=local_path
                    )

                except subprocess.TimeoutExpired:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    raise

                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.strip() if e.stderr else str(e)

                    # If pull failed due to local changes, try to stash and pull
                    if 'overwritten by merge' in error_msg or 'uncommitted changes' in error_msg:
                        logger.warning(f"Local changes detected, stashing for {repo.owner}/{repo.name}")
                        subprocess.run(['git', '-C', str(local_path), 'stash'], check=False)
                        continue

                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue

                    raise Exception(f"Pull failed after {self.max_retries} attempts: {error_msg}")

        except Exception as e:
            logger.error(f"Failed to pull {repo.owner}/{repo.name}: {e}")
            return SyncResult(
                repo_name=repo.name,
                repo_owner=repo.owner,
                success=False,
                action='failed',
                message=f"Pull failed: {str(e)}",
                error=str(e)
            )

    def _make_api_request(self, url: str, params: Optional[Dict] = None,
                         retry_count: int = 0) -> Optional[requests.Response]:
        """
        Make GitHub API request with rate limit handling

        Args:
            url: API endpoint URL
            params: Query parameters
            retry_count: Current retry attempt

        Returns:
            Response object or None if failed
        """
        try:
            response = self.session.get(url, params=params, timeout=30)

            # Check rate limit
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            if remaining < self.rate_limit_buffer:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(reset_time - time.time(), 0) + 5  # Add 5s buffer
                logger.warning(f"Rate limit low ({remaining} remaining), waiting {wait_time:.0f}s...")
                time.sleep(wait_time)

            if response.status_code == 200:
                return response

            elif response.status_code == 403 and retry_count < self.max_retries:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded, waiting before retry...")
                time.sleep(60)  # Wait 1 minute
                return self._make_api_request(url, params, retry_count + 1)

            elif response.status_code in [500, 502, 503, 504] and retry_count < self.max_retries:
                # Server error, retry with backoff
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_api_request(url, params, retry_count + 1)

            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.warning(f"Request error: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_api_request(url, params, retry_count + 1)
            else:
                logger.error(f"API request failed after {self.max_retries} retries: {e}")
                return None

    def _parse_repository_data(self, data: Dict) -> RepositoryInfo:
        """Parse GitHub API repository data into RepositoryInfo"""
        return RepositoryInfo(
            name=data['name'],
            owner=data['owner']['login'],
            github_id=data['id'],
            description=data.get('description'),
            language=data.get('language'),
            default_branch=data.get('default_branch', 'main'),
            clone_url=data['clone_url'],
            ssh_url=data['ssh_url'],
            is_private=data.get('private', False),
            is_fork=data.get('fork', False),
            is_archived=data.get('archived', False),
            size=data.get('size', 0),
            stars=data.get('stargazers_count', 0),
            last_pushed=datetime.fromisoformat(data['pushed_at'].replace('Z', '+00:00'))
        )

    def _update_repository_in_db(self, repo: RepositoryInfo, sync_result: SyncResult):
        """Update repository information in database"""
        if not self.storage:
            return

        try:
            # Check if repository exists
            with self.storage.get_session() as session:
                from storage.adapter import Repository

                db_repo = session.query(Repository).filter(
                    Repository.owner == repo.owner,
                    Repository.name == repo.name
                ).first()

                if db_repo:
                    # Update existing repository
                    db_repo.github_id = repo.github_id
                    db_repo.description = repo.description
                    db_repo.language = repo.language
                    db_repo.last_sync = datetime.now(timezone.utc)
                    logger.debug(f"Updated repository in database: {repo.owner}/{repo.name}")
                else:
                    # Create new repository
                    # Note: This requires a user_id, which should be passed from the calling context
                    logger.debug(f"Repository {repo.owner}/{repo.name} not in database, skipping DB update")

        except Exception as e:
            logger.error(f"Failed to update repository in database: {e}")

    def _calculate_sync_stats(self, results: List[SyncResult], total_time: float) -> Dict[str, Any]:
        """Calculate statistics from sync results"""
        total = len(results)
        successes = sum(1 for r in results if r.success)
        failures = total - successes

        actions = {}
        for result in results:
            actions[result.action] = actions.get(result.action, 0) + 1

        avg_duration = sum(r.duration_seconds for r in results) / total if total > 0 else 0

        return {
            'total_count': total,
            'success_count': successes,
            'failure_count': failures,
            'success_rate': (successes / total * 100) if total > 0 else 0,
            'actions': actions,
            'total_time_seconds': total_time,
            'average_duration_seconds': avg_duration
        }

    def get_local_repositories(self) -> List[Path]:
        """Get list of all locally cloned repositories"""
        repos = []

        if not self.repos_directory.exists():
            return repos

        # Walk through owner directories
        for owner_dir in self.repos_directory.iterdir():
            if not owner_dir.is_dir():
                continue

            # Walk through repo directories
            for repo_dir in owner_dir.iterdir():
                if not repo_dir.is_dir():
                    continue

                git_dir = repo_dir / '.git'
                if git_dir.exists():
                    repos.append(repo_dir)

        return repos

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on sync service"""
        try:
            # Check GitHub API connectivity
            url = f"{self.github_api_base}/rate_limit"
            response = self._make_api_request(url)

            if response:
                rate_limit_data = response.json()
                rate_info = rate_limit_data.get('rate', {})
            else:
                rate_info = {'limit': 0, 'remaining': 0}

            # Check local repository directory
            local_repos = self.get_local_repositories()

            # Check disk space
            disk_usage = subprocess.run(
                ['df', '-h', str(self.repos_directory)],
                capture_output=True,
                text=True,
                check=False
            )

            return {
                'status': 'healthy' if response else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'github_api': {
                    'connected': response is not None,
                    'rate_limit': rate_info.get('limit', 0),
                    'rate_remaining': rate_info.get('remaining', 0)
                },
                'local_storage': {
                    'repos_directory': str(self.repos_directory),
                    'repos_count': len(local_repos),
                    'disk_usage': disk_usage.stdout if disk_usage.returncode == 0 else 'unknown'
                }
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
