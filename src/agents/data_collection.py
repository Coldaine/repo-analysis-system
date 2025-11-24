"""
Data Collection Agent
Refactored from prototype for modular architecture with PostgreSQL backend
"""

import os
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.storage.adapter import StorageAdapter, Repository
from src.models.model_manager import ModelManager

logger = logging.getLogger(__name__)

@dataclass
class RepositoryData:
    """Data structure for repository information"""
    name: str
    owner: str
    path: str
    open_prs: List[Dict]
    ci_status: Dict
    conflicts: List[Dict]
    last_commit: datetime
    health_score: float
    github_id: Optional[int] = None
    description: Optional[str] = None
    language: Optional[str] = None

class GitHubClient:
    """Enhanced GitHub API client with better error handling."""

    def __init__(self, token: Optional[str], base_url: str = "https://api.github.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-analysis-system/2.0",
        }
        if token:
            headers["Authorization"] = f"token {token}"
        self.session.headers.update(headers)

    def _request(self, method: str, path: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated GitHub API request with rate limit handling"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.request(method, url, params=params, timeout=30)
            if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                reset_time = response.headers.get("X-RateLimit-Reset")
                logger.warning("GitHub rate limit hit. Resets at %s", reset_time)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except requests.RequestException as exc:
            logger.error("GitHub API request failed (%s %s): %s", method, url, exc)
            return None

    def get_repo(self, owner: str, repo: str) -> Optional[Dict]:
        """Get repository information"""
        return self._request("GET", f"repos/{owner}/{repo}")

    def get_pull_requests(self, owner: str, repo: str, state: str = "open", per_page: int = 20) -> List[Dict]:
        """Get pull requests with pagination support"""
        data = self._request(
            "GET",
            f"repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page, "sort": "updated"},
        )
        return data or []

    def get_pull_request_details(self, owner: str, repo: str, number: int) -> Optional[Dict]:
        """Get detailed pull request information"""
        return self._request("GET", f"repos/{owner}/{repo}/pulls/{number}")

    def get_latest_workflow_run(self, owner: str, repo: str) -> Optional[Dict]:
        """Get latest GitHub Actions workflow run"""
        runs = self._request(
            "GET",
            f"repos/{owner}/{repo}/actions/runs",
            params={"per_page": 1},
        )
        if runs and runs.get("workflow_runs"):
            return runs["workflow_runs"][0]
        return None
    
    def get_authenticated_user(self) -> Optional[Dict]:
        """Get authenticated user information"""
        return self._request("GET", "user")

def parse_github_datetime(timestamp: Optional[str]) -> Optional[datetime]:
    """Parse GitHub ISO timestamps into datetime objects."""
    if not timestamp:
        return None
    try:
        parsed = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            logger.debug("Unable to parse timestamp: %s", timestamp)
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp a value between minimum and maximum"""
    return max(minimum, min(maximum, value))

def calculate_health_score(open_prs: List[Dict], ci_status: Dict, conflicts: List[Dict], last_commit: datetime) -> float:
    """Compute repository health score with improved algorithm"""
    score = 0.9
    
    # PR count impact
    open_pr_count = len(open_prs)
    score -= min(open_pr_count * 0.03, 0.3)
    
    # CI status impact
    ci_conclusion = ci_status.get("conclusion", "").lower()
    ci_status_value = ci_status.get("status", "").lower()
    if ci_conclusion in {"failure", "timed_out", "cancelled"} or ci_status_value in {"failing", "failure"}:
        score -= 0.25
    elif ci_conclusion in {"success", "completed"} or ci_status_value in {"success", "passing"}:
        score += 0.05
    
    # Conflict impact
    score -= min(len(conflicts) * 0.05, 0.25)
    
    # Activity impact
    if last_commit:
        reference = last_commit.tzinfo and datetime.now(last_commit.tzinfo) or datetime.now(timezone.utc)
        days_inactive = (reference - last_commit).days
        if days_inactive > 30:
            score -= 0.25
        elif days_inactive > 14:
            score -= 0.15
        elif days_inactive < 5:
            score += 0.05
    
    return clamp(score)

class DataCollectionAgent:
    """Enhanced data collection agent with storage integration"""
    
    def __init__(self, config: Dict, storage: StorageAdapter, model_manager: ModelManager):
        self.config = config
        self.storage = storage
        self.model_manager = model_manager
        
        repo_settings = config.get('repositories', {})
        self.workspace_path = repo_settings.get('workspace_path', '')
        api_keys = config.get('api_keys', {})
        
        token_raw = api_keys.get('github_token') or os.getenv('GITHUB_TOKEN')
        token = self._sanitize_placeholder(token_raw)
        github_base = repo_settings.get('github_api_base', "https://api.github.com")
        
        self.github_client = GitHubClient(token, github_base)
        
        self.default_owner = (
            self._sanitize_placeholder(repo_settings.get('default_owner'))
            or self._sanitize_placeholder(repo_settings.get('github_owner'))
            or self._sanitize_placeholder(os.getenv('GITHUB_OWNER'))
            or self._discover_owner_from_token(token)
            or "Koldane"
        )
        
        self.max_prs = repo_settings.get('max_pull_requests', 10)
        self.batch_size = repo_settings.get('batch_size', 10)
        
    def collect_repository_data(self, repo_names: List[str], user_id: int = None) -> List[RepositoryData]:
        """Collect data for specified repositories with storage integration"""
        logger.info(f"Collecting data for {len(repo_names)} repositories")
        
        repositories = []
        for repo_name in repo_names:
            try:
                repo_data = self._collect_single_repo(repo_name, user_id)
                if repo_data:
                    repositories.append(repo_data)
                    
                    # Store repository in database if user_id provided
                    if user_id:
                        self._store_repository(repo_data, user_id)
                        
            except Exception as e:
                logger.error(f"Failed to collect data for {repo_name}: {e}")
                # Continue with other repositories instead of failing completely
                continue
        
        return repositories
    
    def _store_repository(self, repo_data: RepositoryData, user_id: int):
        """Store repository data in PostgreSQL"""
        try:
            # Check if repository already exists
            existing_repo = None
            with self.storage.get_session() as session:
                # Query for existing repository (this would need to be implemented in storage adapter)
                existing_repo = session.query(Repository).filter(
                    Repository.name == repo_data.name,
                    Repository.owner == repo_data.owner
                ).first()
                
                if not existing_repo:
                    # Create new repository
                    new_repo = self.storage.create_repository(
                        name=repo_data.name,
                        owner=repo_data.owner,
                        github_id=repo_data.github_id,
                        description=repo_data.description,
                        language=repo_data.language,
                        created_by=user_id
                    )
                    logger.info(f"Created new repository record: {repo_data.owner}/{repo_data.name}")
                else:
                    # Update existing repository
                    existing_repo.last_sync = datetime.now(timezone.utc)
                    existing_repo.description = repo_data.description
                    existing_repo.language = repo_data.language
                    logger.info(f"Updated repository record: {repo_data.owner}/{repo_data.name}")
                    
        except Exception as e:
            logger.error(f"Failed to store repository {repo_data.name}: {e}")
    
    def _collect_single_repo(self, repo_name: str, user_id: int = None) -> Optional[RepositoryData]:
        """Collect data for a single repository with enhanced error handling"""
        owner, repo = self._resolve_repo_identifier(repo_name)
        logger.info(f"Collecting data for {owner}/{repo}")
        
        try:
            repo_info = self.github_client.get_repo(owner, repo)
            if not repo_info:
                logger.error(f"Unable to fetch metadata for {owner}/{repo}")
                return None
            
            # Collect pull requests
            pulls = self.github_client.get_pull_requests(owner, repo, state="open", per_page=self.max_prs)
            open_prs = [self._transform_pull_request(owner, repo, pr) for pr in pulls]
            
            # Collect CI status
            ci_status = self._fetch_ci_status(owner, repo)
            
            # Derive conflicts from PR data
            conflicts = self._derive_conflicts(open_prs)
            
            # Parse last commit
            last_commit = parse_github_datetime(repo_info.get("pushed_at")) or datetime.now(timezone.utc)
            
            # Calculate health score
            health_score = calculate_health_score(open_prs, ci_status, conflicts, last_commit)
            
            return RepositoryData(
                name=repo,
                owner=owner,
                path=self._build_repo_path(repo_name),
                open_prs=open_prs,
                ci_status=ci_status,
                conflicts=conflicts,
                last_commit=last_commit,
                health_score=health_score,
                github_id=repo_info.get("id"),
                description=repo_info.get("description"),
                language=repo_info.get("language")
            )
            
        except Exception as exc:
            logger.error("GitHub data parsing failed for %s/%s: %s", owner, repo, exc)
            raise
    
    def _resolve_repo_identifier(self, repo_name: str) -> Tuple[str, str]:
        """Resolve repository identifier into owner and repo name"""
        if "/" in repo_name:
            owner, repo = repo_name.split("/", 1)
            return owner, repo
        if not self.default_owner:
            raise ValueError(
                f"No default owner configured for repository '{repo_name}'. "
                "Set repositories.default_owner or use owner/repo syntax."
            )
        return self.default_owner, repo_name
    
    def _discover_owner_from_token(self, token: Optional[str]) -> Optional[str]:
        """Discover GitHub owner from authentication token"""
        if not token:
            return None
        try:
            user = self.github_client.get_authenticated_user()
            if user and user.get("login"):
                logger.info("Auto-detected GitHub owner '%s' from token", user["login"])
                return user["login"]
        except Exception as exc:
            logger.warning("Unable to auto-detect GitHub owner from token: %s", exc)
        return None
    
    def _sanitize_placeholder(self, value: Optional[str]) -> Optional[str]:
        """Sanitize placeholder values"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            return None
        return value
    
    def _build_repo_path(self, repo_name: str) -> str:
        """Build local repository path"""
        if not self.workspace_path:
            return repo_name
        return f"{self.workspace_path.rstrip('/')}/{repo_name}"
    
    def _transform_pull_request(self, owner: str, repo: str, pr: Dict) -> Dict:
        """Transform pull request data into standardized format"""
        return {
            "id": pr.get("number"),
            "title": pr.get("title"),
            "description": pr.get("body"),
            "author": pr.get("user", {}).get("login"),
            "state": pr.get("state"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "mergeable": pr.get("mergeable"),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
            "review_comments": pr.get("review_comments", 0),
            "commits": pr.get("commits", 0)
        }
    
    def _fetch_ci_status(self, owner: str, repo: str) -> Dict:
        """Fetch CI status from GitHub Actions"""
        try:
            workflow_run = self.github_client.get_latest_workflow_run(owner, repo)
            if workflow_run:
                return {
                    "status": workflow_run.get("status"),
                    "conclusion": workflow_run.get("conclusion"),
                    "created_at": workflow_run.get("created_at"),
                    "updated_at": workflow_run.get("updated_at")
                }
        except Exception as e:
            logger.debug("Failed to fetch CI status for %s/%s: %s", owner, repo, e)
        return {"status": "unknown", "conclusion": "unknown"}
    
    def _derive_conflicts(self, open_prs: List[Dict]) -> List[Dict]:
        """Derive potential conflicts from PR data"""
        conflicts = []
        
        for pr in open_prs:
            # High conflict indicators
            if pr.get("review_comments", 0) > 10:
                conflicts.append({
                    "type": "excessive_review_comments",
                    "pr_id": pr.get("id"),
                    "severity": "medium",
                    "description": f"PR #{pr.get('id')} has {pr.get('review_comments')} review comments"
                })
            
            if pr.get("additions", 0) > 500 or pr.get("deletions", 0) > 500:
                conflicts.append({
                    "type": "large_changes",
                    "pr_id": pr.get("id"),
                    "severity": "high",
                    "description": f"PR #{pr.get('id')} has large changes ({pr.get('additions')} additions, {pr.get('deletions')} deletions)"
                })
            
            if not pr.get("mergeable", True):
                conflicts.append({
                    "type": "merge_conflicts",
                    "pr_id": pr.get("id"),
                    "severity": "high",
                    "description": f"PR #{pr.get('id')} has merge conflicts"
                })
        
        return conflicts
    
    def sync_repositories(self, user_id: int = None) -> List[RepositoryData]:
        """Sync all configured repositories"""
        repo_settings = self.config.get('repositories', {})
        target_repos = repo_settings.get('target_repos', [])
        
        if not target_repos:
            logger.warning("No target repositories configured")
            return []
        
        return self.collect_repository_data(target_repos, user_id)
    
    def get_repository_health(self, owner: str, repo: str) -> Optional[Dict]:
        """Get health status for a specific repository"""
        try:
            repo_data = self._collect_single_repo(f"{owner}/{repo}")
            if not repo_data:
                return None
                
            return {
                "repository": f"{owner}/{repo}",
                "health_score": repo_data.health_score,
                "open_prs": len(repo_data.open_prs),
                "ci_status": repo_data.ci_status,
                "conflicts": len(repo_data.conflicts),
                "last_commit": repo_data.last_commit.isoformat(),
                "last_sync": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get health for {owner}/{repo}: {e}")
            return None