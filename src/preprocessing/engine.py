"""
Pre-Processing Engine (Goal 6)
Gather review items BEFORE AI analysis to save time and cost

Success Metrics:
- 60-70% time savings compared to live API calls during analysis
- 60% cost reduction by minimizing redundant AI calls
- Structured JSON output for agent consumption
"""

import os
import logging
import subprocess
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import requests

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Information about a commit"""
    sha: str
    author: str
    author_email: str
    date: datetime
    message: str
    files_changed: int
    additions: int
    deletions: int


@dataclass
class PullRequestInfo:
    """Information about a pull request"""
    number: int
    title: str
    state: str  # open, closed, merged
    author: str
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime]
    is_draft: bool
    additions: int
    deletions: int
    changed_files: int
    comments: int
    review_comments: int
    labels: List[str]
    head_branch: str
    base_branch: str


@dataclass
class IssueInfo:
    """Information about an issue"""
    number: int
    title: str
    state: str  # open, closed
    author: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    labels: List[str]
    comments: int
    is_pull_request: bool


@dataclass
class FileChangeInfo:
    """Information about file changes"""
    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    changes: int


@dataclass
class PreProcessedData:
    """Complete pre-processed data for a repository"""
    repo_name: str
    repo_owner: str
    repo_path: str

    # Repository metadata
    default_branch: str
    latest_commit: str
    total_commits: int

    # Recent activity
    commits_last_30_days: List[CommitInfo]
    commits_last_7_days: List[CommitInfo]

    # Pull requests
    open_prs: List[PullRequestInfo]
    recently_merged_prs: List[PullRequestInfo]
    stale_prs: List[PullRequestInfo]  # Open > 30 days

    # Issues
    open_issues: List[IssueInfo]
    recently_closed_issues: List[IssueInfo]

    # File changes
    recent_file_changes: List[FileChangeInfo]

    # Baseline comparison
    baseline_hash: Optional[str]
    baseline_divergence: Optional[Dict[str, Any]]

    # Metadata
    generated_at: str
    generation_time_seconds: float


class PreProcessingEngine:
    """
    Engine for pre-processing repository data before AI analysis

    Features:
    - Gather commits, PRs, issues, and file changes
    - Baseline comparison upfront
    - Output structured JSON for agent consumption
    - Cache results for repeated analysis
    """

    def __init__(self, config: Dict[str, Any], storage=None):
        """
        Initialize pre-processing engine

        Args:
            config: Configuration dictionary
            storage: Optional storage adapter
        """
        self.config = config
        self.storage = storage

        # GitHub API configuration
        self.github_token = config.get('github', {}).get('token') or os.getenv('GITHUB_TOKEN')
        self.github_api_base = config.get('github', {}).get('api_base', 'https://api.github.com')

        # Pre-processing configuration
        self.preproc_config = config.get('preprocessing', {})
        self.commits_lookback_days = self.preproc_config.get('commits_lookback_days', 30)
        self.stale_pr_threshold_days = self.preproc_config.get('stale_pr_threshold_days', 30)
        self.cache_ttl_minutes = self.preproc_config.get('cache_ttl_minutes', 60)
        self.output_directory = Path(self.preproc_config.get('output_directory', './preprocessing_cache'))
        self.output_directory.mkdir(parents=True, exist_ok=True)

        # Session for HTTP requests
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })

        logger.info("Pre-Processing Engine initialized")

    def preprocess_repository(self, repo_path: Path, repo_name: str,
                             repo_owner: str, force: bool = False) -> PreProcessedData:
        """
        Pre-process a repository and gather all review items

        Args:
            repo_path: Path to local repository
            repo_name: Repository name
            repo_owner: Repository owner
            force: Force regeneration even if cache exists

        Returns:
            Complete pre-processed data
        """
        import time
        start_time = time.time()

        logger.info(f"Pre-processing repository: {repo_owner}/{repo_name}")

        # Check cache
        if not force:
            cached_data = self._load_from_cache(repo_owner, repo_name)
            if cached_data:
                logger.info(f"Using cached pre-processed data for {repo_owner}/{repo_name}")
                return cached_data

        # Gather repository metadata
        default_branch = self._get_default_branch(repo_path)
        latest_commit = self._get_latest_commit(repo_path)
        total_commits = self._get_total_commit_count(repo_path)

        # Gather commits
        commits_30d = self._gather_commits(repo_path, days=30)
        commits_7d = [c for c in commits_30d if c.date >= datetime.now(timezone.utc) - timedelta(days=7)]

        # Gather pull requests from GitHub API
        all_prs = self._gather_pull_requests(repo_owner, repo_name)
        open_prs = [pr for pr in all_prs if pr.state == 'open']
        merged_prs = [pr for pr in all_prs if pr.state == 'closed' and pr.merged_at]
        recently_merged_prs = [
            pr for pr in merged_prs
            if pr.merged_at and pr.merged_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ]

        # Identify stale PRs
        stale_threshold = datetime.now(timezone.utc) - timedelta(days=self.stale_pr_threshold_days)
        stale_prs = [pr for pr in open_prs if pr.created_at < stale_threshold]

        # Gather issues from GitHub API
        all_issues = self._gather_issues(repo_owner, repo_name)
        open_issues = [issue for issue in all_issues if issue.state == 'open' and not issue.is_pull_request]
        closed_issues = [issue for issue in all_issues if issue.state == 'closed']
        recently_closed_issues = [
            issue for issue in closed_issues
            if issue.closed_at and issue.closed_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ]

        # Gather recent file changes
        file_changes = self._gather_file_changes(repo_path, days=30)

        # Load baseline and check for divergence
        baseline_hash, baseline_divergence = self._check_baseline_divergence(repo_path, repo_owner, repo_name)

        # Create pre-processed data object
        preprocessed_data = PreProcessedData(
            repo_name=repo_name,
            repo_owner=repo_owner,
            repo_path=str(repo_path),
            default_branch=default_branch,
            latest_commit=latest_commit,
            total_commits=total_commits,
            commits_last_30_days=commits_30d,
            commits_last_7_days=commits_7d,
            open_prs=open_prs,
            recently_merged_prs=recently_merged_prs,
            stale_prs=stale_prs,
            open_issues=open_issues,
            recently_closed_issues=recently_closed_issues,
            recent_file_changes=file_changes,
            baseline_hash=baseline_hash,
            baseline_divergence=baseline_divergence,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generation_time_seconds=time.time() - start_time
        )

        # Save to cache
        self._save_to_cache(preprocessed_data)

        logger.info(
            f"Pre-processing complete for {repo_owner}/{repo_name} - "
            f"{len(commits_30d)} commits, {len(open_prs)} open PRs, "
            f"{len(open_issues)} open issues in {preprocessed_data.generation_time_seconds:.1f}s"
        )

        return preprocessed_data

    def _get_default_branch(self, repo_path: Path) -> str:
        """Get default branch name"""
        try:
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            # Output is like: refs/remotes/origin/main
            branch = result.stdout.strip().split('/')[-1]
            return branch
        except subprocess.CalledProcessError:
            # Fallback to common default branches
            for branch in ['main', 'master', 'develop']:
                try:
                    subprocess.run(
                        ['git', '-C', str(repo_path), 'rev-parse', '--verify', branch],
                        check=True,
                        capture_output=True
                    )
                    return branch
                except subprocess.CalledProcessError:
                    continue
            return 'main'  # Ultimate fallback

    def _get_latest_commit(self, repo_path: Path) -> str:
        """Get latest commit SHA"""
        try:
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'rev-parse', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get latest commit: {e}")
            return ''

    def _get_total_commit_count(self, repo_path: Path) -> int:
        """Get total number of commits"""
        try:
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'rev-list', '--count', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Failed to get commit count: {e}")
            return 0

    def _gather_commits(self, repo_path: Path, days: int = 30) -> List[CommitInfo]:
        """Gather commits from the last N days"""
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)
            since_str = since_date.strftime('%Y-%m-%d')

            result = subprocess.run(
                [
                    'git', '-C', str(repo_path), 'log',
                    f'--since={since_str}',
                    '--pretty=format:%H|%an|%ae|%aI|%s',
                    '--numstat'
                ],
                check=True,
                capture_output=True,
                text=True
            )

            commits = []
            lines = result.stdout.strip().split('\n')
            i = 0

            while i < len(lines):
                if not lines[i]:
                    i += 1
                    continue

                # Parse commit line
                parts = lines[i].split('|')
                if len(parts) < 5:
                    i += 1
                    continue

                sha, author, email, date_str, message = parts[0], parts[1], parts[2], parts[3], parts[4]
                commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                # Count stats from following lines
                additions = 0
                deletions = 0
                files_changed = 0
                i += 1

                while i < len(lines) and lines[i] and not lines[i].startswith('|'):
                    # Numstat line: additions deletions filename
                    stat_parts = lines[i].split('\t')
                    if len(stat_parts) >= 3:
                        try:
                            adds = int(stat_parts[0]) if stat_parts[0] != '-' else 0
                            dels = int(stat_parts[1]) if stat_parts[1] != '-' else 0
                            additions += adds
                            deletions += dels
                            files_changed += 1
                        except ValueError:
                            pass
                    i += 1

                commits.append(CommitInfo(
                    sha=sha,
                    author=author,
                    author_email=email,
                    date=commit_date,
                    message=message,
                    files_changed=files_changed,
                    additions=additions,
                    deletions=deletions
                ))

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to gather commits: {e}")
            return []

    def _gather_pull_requests(self, repo_owner: str, repo_name: str) -> List[PullRequestInfo]:
        """Gather pull requests from GitHub API"""
        try:
            prs = []
            page = 1

            while True:
                url = f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/pulls"
                params = {
                    'state': 'all',
                    'per_page': 100,
                    'page': page,
                    'sort': 'updated',
                    'direction': 'desc'
                }

                response = self.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch PRs: {response.status_code}")
                    break

                batch = response.json()
                if not batch:
                    break

                for pr_data in batch:
                    pr = self._parse_pull_request(pr_data)
                    prs.append(pr)

                # Only fetch recent PRs (updated in last 90 days)
                last_pr_updated = datetime.fromisoformat(batch[-1]['updated_at'].replace('Z', '+00:00'))
                if last_pr_updated < datetime.now(timezone.utc) - timedelta(days=90):
                    break

                if len(batch) < 100:
                    break

                page += 1

            return prs

        except Exception as e:
            logger.error(f"Failed to gather pull requests: {e}")
            return []

    def _parse_pull_request(self, pr_data: Dict) -> PullRequestInfo:
        """Parse GitHub API PR data"""
        merged_at = pr_data.get('merged_at')
        if merged_at:
            merged_at = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))

        return PullRequestInfo(
            number=pr_data['number'],
            title=pr_data['title'],
            state='merged' if pr_data.get('merged_at') else pr_data['state'],
            author=pr_data['user']['login'],
            created_at=datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(pr_data['updated_at'].replace('Z', '+00:00')),
            merged_at=merged_at,
            is_draft=pr_data.get('draft', False),
            additions=pr_data.get('additions', 0),
            deletions=pr_data.get('deletions', 0),
            changed_files=pr_data.get('changed_files', 0),
            comments=pr_data.get('comments', 0),
            review_comments=pr_data.get('review_comments', 0),
            labels=[label['name'] for label in pr_data.get('labels', [])],
            head_branch=pr_data['head']['ref'],
            base_branch=pr_data['base']['ref']
        )

    def _gather_issues(self, repo_owner: str, repo_name: str) -> List[IssueInfo]:
        """Gather issues from GitHub API"""
        try:
            issues = []
            page = 1

            while True:
                url = f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/issues"
                params = {
                    'state': 'all',
                    'per_page': 100,
                    'page': page,
                    'sort': 'updated',
                    'direction': 'desc'
                }

                response = self.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch issues: {response.status_code}")
                    break

                batch = response.json()
                if not batch:
                    break

                for issue_data in batch:
                    issue = self._parse_issue(issue_data)
                    issues.append(issue)

                # Only fetch recent issues (updated in last 90 days)
                last_issue_updated = datetime.fromisoformat(batch[-1]['updated_at'].replace('Z', '+00:00'))
                if last_issue_updated < datetime.now(timezone.utc) - timedelta(days=90):
                    break

                if len(batch) < 100:
                    break

                page += 1

            return issues

        except Exception as e:
            logger.error(f"Failed to gather issues: {e}")
            return []

    def _parse_issue(self, issue_data: Dict) -> IssueInfo:
        """Parse GitHub API issue data"""
        closed_at = issue_data.get('closed_at')
        if closed_at:
            closed_at = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))

        return IssueInfo(
            number=issue_data['number'],
            title=issue_data['title'],
            state=issue_data['state'],
            author=issue_data['user']['login'],
            created_at=datetime.fromisoformat(issue_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(issue_data['updated_at'].replace('Z', '+00:00')),
            closed_at=closed_at,
            labels=[label['name'] for label in issue_data.get('labels', [])],
            comments=issue_data.get('comments', 0),
            is_pull_request='pull_request' in issue_data
        )

    def _gather_file_changes(self, repo_path: Path, days: int = 30) -> List[FileChangeInfo]:
        """Gather file changes from the last N days"""
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)
            since_str = since_date.strftime('%Y-%m-%d')

            result = subprocess.run(
                [
                    'git', '-C', str(repo_path), 'diff',
                    '--numstat',
                    f'HEAD@{{{since_str}}}..HEAD'
                ],
                check=True,
                capture_output=True,
                text=True
            )

            changes = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) < 3:
                    continue

                try:
                    additions = int(parts[0]) if parts[0] != '-' else 0
                    deletions = int(parts[1]) if parts[1] != '-' else 0
                    filename = parts[2]

                    changes.append(FileChangeInfo(
                        filename=filename,
                        status='modified',
                        additions=additions,
                        deletions=deletions,
                        changes=additions + deletions
                    ))
                except (ValueError, IndexError):
                    continue

            return changes

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to gather file changes: {e}")
            return []

    def _check_baseline_divergence(self, repo_path: Path, repo_owner: str,
                                   repo_name: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Check for baseline divergence"""
        try:
            # Load baseline from repository
            baseline_file = repo_path / '.baseline.json'
            if not baseline_file.exists():
                return None, None

            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)

            baseline_hash = baseline_data.get('hash')

            # For now, just return the hash
            # Divergence detection would compare current state with baseline goals
            divergence = {
                'has_baseline': True,
                'baseline_hash': baseline_hash,
                'divergence_detected': False  # TODO: Implement actual divergence detection
            }

            return baseline_hash, divergence

        except Exception as e:
            logger.warning(f"Failed to check baseline divergence: {e}")
            return None, None

    def _load_from_cache(self, repo_owner: str, repo_name: str) -> Optional[PreProcessedData]:
        """Load pre-processed data from cache"""
        try:
            cache_file = self.output_directory / f"{repo_owner}_{repo_name}.json"
            if not cache_file.exists():
                return None

            # Check cache age
            cache_age = datetime.now(timezone.utc) - datetime.fromtimestamp(
                cache_file.stat().st_mtime, tz=timezone.utc
            )
            if cache_age.total_seconds() > self.cache_ttl_minutes * 60:
                logger.debug(f"Cache expired for {repo_owner}/{repo_name}")
                return None

            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Convert back to dataclass (simplified - would need proper deserialization)
            return data

        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return None

    def _save_to_cache(self, data: PreProcessedData):
        """Save pre-processed data to cache"""
        try:
            cache_file = self.output_directory / f"{data.repo_owner}_{data.repo_name}.json"

            # Convert to dict (with proper serialization)
            data_dict = asdict(data)

            # Convert datetime objects to ISO strings
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                return obj

            data_dict = serialize_datetime(data_dict)

            with open(cache_file, 'w') as f:
                json.dump(data_dict, f, indent=2)

            logger.debug(f"Saved pre-processed data to cache: {cache_file}")

        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on pre-processing engine"""
        try:
            # Check GitHub API connectivity
            url = f"{self.github_api_base}/rate_limit"
            response = self.session.get(url, timeout=10)
            github_ok = response.status_code == 200

            # Check cache directory
            cache_ok = self.output_directory.exists()

            return {
                'status': 'healthy' if (github_ok and cache_ok) else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'github_api': {
                    'connected': github_ok
                },
                'cache': {
                    'directory': str(self.output_directory),
                    'exists': cache_ok,
                    'cached_repos': len(list(self.output_directory.glob('*.json')))
                },
                'configuration': {
                    'commits_lookback_days': self.commits_lookback_days,
                    'stale_pr_threshold_days': self.stale_pr_threshold_days,
                    'cache_ttl_minutes': self.cache_ttl_minutes
                }
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
