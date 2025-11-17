#!/usr/bin/env python3
"""
Agentic Repository Analysis System Prototype
Simulates cron job execution with CCR orchestration and agent chaining
"""

import os
import sys
import json
import yaml
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile

# Import side agents
from side_agent import create_side_agents

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/prototype.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def _expand_env(value: Any) -> Any:
    """Resolve environment variables in configuration values."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


def _sanitize_placeholder(value: Optional[str]) -> Optional[str]:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return None
    return value

@dataclass
class RepositoryData:
    """Data structure for repository information"""
    name: str
    path: str
    open_prs: List[Dict]
    ci_status: Dict
    conflicts: List[Dict]
    last_commit: datetime
    health_score: float

@dataclass
class AnalysisResult:
    """Data structure for analysis results"""
    repository: str
    pain_points: List[Dict]
    recommendations: List[str]
    confidence: float
    model_used: str
    solutions: List[Dict] = field(default_factory=list)


class GitHubClient:
    """Simple GitHub API client."""

    def __init__(self, token: Optional[str], base_url: str = "https://api.github.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-analysis-system/1.0",
        }
        if token:
            headers["Authorization"] = f"token {token}"
        self.session.headers.update(headers)

    def _request(self, method: str, path: str, params: Dict = None) -> Optional[Dict]:
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
        return self._request("GET", f"repos/{owner}/{repo}")

    def get_pull_requests(self, owner: str, repo: str, state: str = "open", per_page: int = 20) -> List[Dict]:
        data = self._request(
            "GET",
            f"repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page, "sort": "updated"},
        )
        return data or []

    def get_pull_request_details(self, owner: str, repo: str, number: int) -> Optional[Dict]:
        return self._request("GET", f"repos/{owner}/{repo}/pulls/{number}")

    def get_latest_workflow_run(self, owner: str, repo: str) -> Optional[Dict]:
        runs = self._request(
            "GET",
            f"repos/{owner}/{repo}/actions/runs",
            params={"per_page": 1},
        )
        if runs and runs.get("workflow_runs"):
            return runs["workflow_runs"][0]
        return None
    
    def get_authenticated_user(self) -> Optional[Dict]:
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
    return max(minimum, min(maximum, value))


def calculate_health_score(open_prs: List[Dict], ci_status: Dict, conflicts: List[Dict], last_commit: datetime) -> float:
    """Compute a crude repository health score."""
    score = 0.9
    open_pr_count = len(open_prs)
    score -= min(open_pr_count * 0.03, 0.3)

    ci_conclusion = ci_status.get("conclusion", "").lower()
    ci_status_value = ci_status.get("status", "").lower()
    if ci_conclusion in {"failure", "timed_out", "cancelled"} or ci_status_value in {"failing", "failure"}:
        score -= 0.25
    elif ci_conclusion in {"success", "completed"} or ci_status_value in {"success", "passing"}:
        score += 0.05

    score -= min(len(conflicts) * 0.05, 0.25)

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

class ModelManager:
    """Manages different AI models for analysis"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.models = config['models']
        raw_keys = config.get('api_keys', {})
        self.api_keys = {
            'glm_api_key': _sanitize_placeholder(raw_keys.get('glm_api_key')) or _sanitize_placeholder(os.getenv('GLM_API_KEY')),
            'minimax_api_key': _sanitize_placeholder(raw_keys.get('minimax_api_key')) or _sanitize_placeholder(os.getenv('MINIMAX_API_KEY')),
            'google_search_key': _sanitize_placeholder(raw_keys.get('google_search_key')) or _sanitize_placeholder(os.getenv('GOOGLE_SEARCH_KEY')),
        }
        self.session = requests.Session()
        
    def call_glm_4_6(self, prompt: str, data: Dict = None) -> Dict:
        """Call GLM 4.6 model for analysis"""
        try:
            logger.info("Calling GLM 4.6 for analysis")
            payload = {
                "model": self.models['glm_4_6'].get('model'),
                "prompt": prompt,
                "data": data,
                "temperature": self.models['glm_4_6'].get('temperature', 0.3)
            }
            response = self._invoke_model_api("glm_4_6", payload, self.api_keys.get('glm_api_key'))
            parsed = self._parse_analysis_response(response, "glm-4.6")
            if parsed and parsed.get("analysis"):
                return parsed
            raise RuntimeError("GLM 4.6 response missing analysis payload")
            
        except Exception as e:
            logger.error(f"GLM 4.6 call failed: {e}")
            raise
    
    def call_minimax(self, prompt: str) -> Dict:
        """Call MiniMax for lightweight tasks"""
        try:
            logger.info("Calling MiniMax for quick triage")
            payload = {
                "model": self.models['minimax'].get('model'),
                "prompt": prompt,
                "temperature": self.models['minimax'].get('temperature', 0.2)
            }
            response = self._invoke_model_api("minimax", payload, self.api_keys.get('minimax_api_key'))
            if response:
                return response
            raise RuntimeError("MiniMax did not return a response")
            
        except Exception as e:
            logger.error(f"MiniMax call failed: {e}")
            raise
    
    def call_ollama(self, prompt: str) -> Dict:
        """Call Ollama for privacy-sensitive analysis"""
        try:
            logger.info("Calling Ollama for privacy-sensitive analysis")
            payload = {
                "model": self.models['ollama'].get('model'),
                "prompt": prompt,
                "stream": False
            }
            response = self._invoke_model_api("ollama", payload, None)
            if response:
                return response
            raise RuntimeError("Ollama did not return a response")
            
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def _invoke_model_api(self, model_key: str, payload: Dict, api_key: Optional[str]) -> Optional[Dict]:
        model_cfg = self.models.get(model_key)
        if not model_cfg:
            raise ValueError(f"Model configuration missing for {model_key}")
        endpoint = model_cfg.get('endpoint') or model_cfg.get('base_url')
        if not endpoint:
            raise ValueError(f"No endpoint specified for {model_key}")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        timeout = model_cfg.get('timeout', 30)
        retries = model_cfg.get('retries', 2)
        for attempt in range(retries):
            try:
                response = self.session.post(endpoint, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                logger.warning("Model %s request failed (attempt %s/%s): %s", model_key, attempt + 1, retries, exc)
                time.sleep(1)
        return None
    
    def _parse_analysis_response(self, response: Optional[Dict], model_label: str) -> Optional[Dict]:
        if not response:
            return None
        if 'analysis' in response and isinstance(response['analysis'], dict):
            return response
        message_text = None
        if isinstance(response, dict):
            if 'choices' in response and response['choices']:
                choice = response['choices'][0]
                message_text = choice.get('message', {}).get('content') or choice.get('text')
            elif 'output' in response:
                message_text = response['output']
            elif 'message' in response:
                message_text = response['message']
        else:
            message_text = str(response)
        
        if message_text:
            try:
                analysis = json.loads(message_text)
            except json.JSONDecodeError:
                analysis = {"raw": message_text}
            return {
                "model": model_label,
                "analysis": analysis,
                "confidence": response.get("confidence", 0.8) if isinstance(response, dict) else 0.8,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0) if isinstance(response, dict) else 0
            }
        return None

class DataCollectionAgent:
    """Collects repository data via GitHub API"""
    
    def __init__(self, config: Dict):
        self.config = config
        repo_settings = config.get('repositories', {})
        self.workspace_path = repo_settings.get('workspace_path', '')
        api_keys = config.get('api_keys', {})
        token_raw = api_keys.get('github_token') or os.getenv('GITHUB_TOKEN')
        token = _sanitize_placeholder(token_raw)
        github_base = repo_settings.get('github_api_base', "https://api.github.com")
        self.github_client = GitHubClient(token, github_base)
        self.default_owner = (
            _sanitize_placeholder(repo_settings.get('default_owner'))
            or _sanitize_placeholder(repo_settings.get('github_owner'))
            or _sanitize_placeholder(os.getenv('GITHUB_OWNER'))
            or self._discover_owner_from_token(token)
            or "Koldane"
        )
        self.max_prs = repo_settings.get('max_pull_requests', 10)
        
    def collect_repository_data(self, repo_names: List[str]) -> List[RepositoryData]:
        """Collect data for specified repositories"""
        logger.info(f"Collecting data for {len(repo_names)} repositories")
        
        repositories = []
        for repo_name in repo_names:
            try:
                repo_data = self._collect_single_repo(repo_name)
                if repo_data:
                    repositories.append(repo_data)
            except Exception as e:
                logger.error(f"Failed to collect data for {repo_name}: {e}")
                raise
        
        return repositories
    
    def _collect_single_repo(self, repo_name: str) -> Optional[RepositoryData]:
        """Collect data for a single repository"""
        owner, repo = self._resolve_repo_identifier(repo_name)
        logger.info(f"Collecting data for {owner}/{repo}")
        
        repo_info = self.github_client.get_repo(owner, repo)
        if not repo_info:
            raise RuntimeError(f"Unable to fetch metadata for {owner}/{repo}")
        
        try:
            pulls = self.github_client.get_pull_requests(owner, repo, state="open", per_page=self.max_prs)
            open_prs = [self._transform_pull_request(owner, repo, pr) for pr in pulls]
            ci_status = self._fetch_ci_status(owner, repo)
            conflicts = self._derive_conflicts(open_prs)
            
            last_commit = parse_github_datetime(repo_info.get("pushed_at")) or datetime.now(timezone.utc)
            health_score = calculate_health_score(open_prs, ci_status, conflicts, last_commit)
            
            return RepositoryData(
                name=repo,
                path=self._build_repo_path(repo_name),
                open_prs=open_prs,
                ci_status=ci_status,
                conflicts=conflicts,
                last_commit=last_commit,
                health_score=health_score
            )
        except Exception as exc:
            logger.error("GitHub data parsing failed for %s/%s: %s", owner, repo, exc)
            raise
    
    def _resolve_repo_identifier(self, repo_name: str) -> Tuple[str, str]:
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
    
    def _build_repo_path(self, repo_name: str) -> str:
        if not self.workspace_path:
            return repo_name
        return f"{self.workspace_path.rstrip('/')}/{repo_name}"
    
    def _transform_pull_request(self, owner: str, repo: str, pr: Dict) -> Dict:
        pr_number = pr.get("number")
        detail = self.github_client.get_pull_request_details(owner, repo, pr_number) if pr_number else None
        data = detail or pr
        created_at = parse_github_datetime(data.get("created_at"))
        updated_at = parse_github_datetime(data.get("updated_at"))
        merged_at = parse_github_datetime(data.get("merged_at"))
        if created_at:
            reference = created_at.tzinfo and datetime.now(created_at.tzinfo) or datetime.now(timezone.utc)
            age_days = (reference - created_at).days
        else:
            age_days = None
        
        return {
            "number": pr_number,
            "title": data.get("title"),
            "state": data.get("state"),
            "draft": data.get("draft", False),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "merged_at": data.get("merged_at"),
            "mergeable": data.get("mergeable"),
            "mergeable_state": data.get("mergeable_state"),
            "age_days": age_days,
            "author": data.get("user", {}).get("login"),
            "head_ref": data.get("head", {}).get("ref"),
            "base_ref": data.get("base", {}).get("ref"),
        }
    
    def _fetch_ci_status(self, owner: str, repo: str) -> Dict:
        run = self.github_client.get_latest_workflow_run(owner, repo)
        if not run:
            return {"status": "unknown", "conclusion": "unknown"}
        return {
            "status": run.get("status", "unknown"),
            "conclusion": run.get("conclusion", "unknown"),
            "workflow": run.get("name"),
            "run_started": run.get("run_started_at"),
            "updated_at": run.get("updated_at"),
            "html_url": run.get("html_url"),
        }
    
    def _derive_conflicts(self, pull_requests: List[Dict]) -> List[Dict]:
        conflicts = []
        for pr in pull_requests:
            state = (pr.get("mergeable_state") or "").lower()
            if state in {"dirty", "blocked", "unknown"}:
                conflicts.append(
                    {
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "head": pr.get("head_ref"),
                        "base": pr.get("base_ref"),
                        "mergeable_state": state,
                    }
                )
        return conflicts

class SearchAgent:
    """Performs internet searches for solutions"""
    
    def __init__(self, config: Dict):
        self.config = config
        search_cfg = config.get('agents', {}).get('search_agent', {})
        self.provider = search_cfg.get('search_provider', 'duckduckgo').lower()
        self.max_results = search_cfg.get('max_results', 5)
        self.session = requests.Session()
        api_keys = config.get('api_keys', {})
        self.google_api_key = _sanitize_placeholder(api_keys.get('google_search_key')) or _sanitize_placeholder(os.getenv('GOOGLE_SEARCH_KEY'))
        self.google_cx = search_cfg.get('google_cx') or os.getenv('GOOGLE_CX')
        
    def search_solutions(self, pain_points: List[Dict]) -> List[Dict]:
        """Search for solutions to identified pain points"""
        logger.info(f"Searching solutions for {len(pain_points)} pain points")
        
        solutions = []
        for pain_point in pain_points:
            try:
                solution = self._search_single_pain_point(pain_point)
                if solution:
                    solutions.append(solution)
            except Exception as e:
                logger.error(f"Search failed for pain point {pain_point}: {e}")
                raise
        
        return solutions
    
    def _search_single_pain_point(self, pain_point: Dict) -> Dict:
        """Search for solutions to a specific pain point"""
        query = f"{pain_point['type'].replace('_', ' ')} repository engineering best practices"
        logger.info(f"Searching: {query}")
        
        if self.provider == "google":
            results = self._search_google(query)
        else:
            results = self._search_duckduckgo(query)
        
        if not results:
            raise RuntimeError(f"No search results returned for query: {query}")
        
        return {
            "pain_point": pain_point['type'],
            "query": query,
            "solutions": results[: self.max_results],
            "search_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _search_duckduckgo(self, query: str) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            topics = data.get("RelatedTopics", [])
            results = []
            for topic in topics:
                if 'Text' in topic and 'FirstURL' in topic:
                    results.append(
                        {
                            "title": topic.get("Text"),
                            "url": topic.get("FirstURL"),
                            "snippet": topic.get("Text"),
                            "relevance": 0.5
                        }
                    )
                elif 'Topics' in topic:
                    for subtopic in topic.get('Topics', []):
                        if 'Text' in subtopic and 'FirstURL' in subtopic:
                            results.append(
                                {
                                    "title": subtopic.get("Text"),
                                    "url": subtopic.get("FirstURL"),
                                    "snippet": subtopic.get("Text"),
                                    "relevance": 0.4
                                }
                            )
            return results
        except requests.RequestException as exc:
            logger.error("DuckDuckGo search failed: %s", exc)
            raise
    
    def _search_google(self, query: str) -> List[Dict]:
        if not self.google_api_key or not self.google_cx:
            raise ValueError("Google search requested but API key or CX missing")
        try:
            response = self.session.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self.google_api_key,
                    "cx": self.google_cx,
                    "q": query,
                    "num": self.max_results
                },
                timeout=15
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            results = []
            for idx, item in enumerate(items):
                results.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "snippet": item.get("snippet"),
                        "relevance": max(0.1, 1 - idx * 0.1),
                    }
                )
            return results
        except requests.RequestException as exc:
            logger.error("Google search failed: %s", exc)
            raise

class VisualizationAgent:
    """Generates Mermaid visualizations"""
    
    def __init__(self, config: Dict):
        self.config = config
        limits = config.get('visualizations', {}).get('limits', {})
        self.max_nodes = limits.get('max_nodes', 20)
        self.max_events_per_timeline = limits.get('max_events_per_timeline', 7)
    
    def generate_visualizations(
        self,
        repositories: List[RepositoryData],
        analysis_results: List[AnalysisResult],
        workflow_stats: Optional[Dict[str, Dict[str, datetime]]] = None
    ) -> List[Dict]:
        """Generate Mermaid diagrams for analysis results"""
        logger.info("Generating visualizations from live data")
        
        visualizations = []
        
        pr_timeline = self._generate_pr_timeline(repositories)
        if pr_timeline:
            visualizations.append(pr_timeline)
        
        workflow_gantt = self._generate_workflow_gantt(workflow_stats)
        if workflow_gantt:
            visualizations.append(workflow_gantt)
        
        pain_point_flowchart = self._generate_pain_point_flowchart(analysis_results)
        if pain_point_flowchart:
            visualizations.append(pain_point_flowchart)
        
        return visualizations
    
    def _generate_pr_timeline(self, repositories: List[RepositoryData]) -> Optional[Dict]:
        lines = ["timeline", "    title Pull Request Activity (Last 30 Days)"]
        sections_added = 0
        for repo in repositories:
            prs = sorted(
                repo.open_prs,
                key=lambda pr: pr.get("created_at") or "",
                reverse=True
            )
            if not prs:
                continue
            lines.append(f"    section {repo.name}")
            sections_added += 1
            for pr in prs[: self.max_events_per_timeline]:
                created = pr.get("created_at") or "unknown"
                title = pr.get("title") or "Pull Request"
                status = pr.get("state", "open")
                lines.append(f"        PR #{pr.get('number', '?')} : {title}")
                lines.append(f"          : Created : {created}")
                if pr.get("updated_at"):
                    lines.append(f"          : Updated : {pr['updated_at']}")
                if status != "open" and pr.get("merged_at"):
                    lines.append(f"          : Merged : {pr['merged_at']}")
                elif status != "open":
                    lines.append(f"          : {status.title()} : {pr.get('updated_at', 'recent')}")
        if sections_added == 0:
            return None
        mermaid_code = "\n".join(lines)
        return {
            "type": "timeline",
            "title": "PR Lifecycle Analysis",
            "filename": "pr-timeline.mmd",
            "mermaid_code": mermaid_code
        }
    
    def _generate_workflow_gantt(self, workflow_stats: Optional[Dict[str, Dict[str, datetime]]]) -> Optional[Dict]:
        if not workflow_stats:
            return None
        lines = [
            "gantt",
            "    title Prototype Workflow Execution",
            "    dateFormat  YYYY-MM-DD HH:mm",
            "    axisFormat %m/%d %H:%M"
        ]
        order = [
            ("data_collection", "Data Collection"),
            ("pain_point_analysis", "Pain Point Analysis"),
            ("solution_research", "Solution Research"),
            ("side_agent_analysis", "Side Agent Analysis"),
            ("visualization_generation", "Visualization Generation"),
            ("output_generation", "Output Generation"),
        ]
        for key, label in order:
            stats = workflow_stats.get(key)
            if not stats or not stats.get("start") or not stats.get("end"):
                continue
            duration = max((stats["end"] - stats["start"]).total_seconds() / 60, 1)
            start_str = stats["start"].strftime("%Y-%m-%d %H:%M")
            duration_str = f"{int(duration)}m"
            lines.append(f"    section {label}")
            lines.append(f"    {label} :{key}, {start_str}, {duration_str}")
        if len(lines) == 4:
            return None
        mermaid_code = "\n".join(lines)
        return {
            "type": "gantt",
            "title": "Agent Workflow Timeline",
            "filename": "agent-workflow-gantt.mmd",
            "mermaid_code": mermaid_code
        }
    
    def _generate_pain_point_flowchart(self, results: List[AnalysisResult]) -> Optional[Dict]:
        if not results:
            return None
        lines = ["flowchart TD", "    start([Analyzed Repositories])"]
        class_defs = [
            "    classDef critical fill:#ffebee,stroke:#c62828,stroke-width:1px;",
            "    classDef warning fill:#fff3e0,stroke:#f57c00,stroke-width:1px;",
            "    classDef info fill:#e1f5fe,stroke:#0277bd,stroke-width:1px;"
        ]
        node_count = 0
        for result in results:
            if not result.pain_points:
                continue
            repo_node = self._sanitize_node_id(result.repository)
            lines.append(f"    start --> {repo_node}[{result.repository}]")
            node_count += 1
            for pp in result.pain_points:
                if node_count >= self.max_nodes:
                    break
                pp_node = self._sanitize_node_id(f"{result.repository}_{pp['type']}")
                label = pp['type'].replace('_', ' ').title()
                severity = (pp.get('severity') or 'info').lower()
                lines.append(f"    {repo_node} --> {pp_node}[{label}]")
                lines.append(f"    class {pp_node} {self._severity_class(severity)};")
                node_count += 1
            if node_count >= self.max_nodes:
                break
        if node_count == 0:
            return None
        mermaid_code = "\n".join(lines + class_defs)
        return {
            "type": "flowchart",
            "title": "Pain Point Map",
            "filename": "pain-points-flowchart.mmd",
            "mermaid_code": mermaid_code
        }
    
    def _sanitize_node_id(self, value: str) -> str:
        return "".join(char for char in value if char.isalnum() or char == "_")
    
    def _severity_class(self, severity: str) -> str:
        if severity == "high" or severity == "critical":
            return "critical"
        if severity == "medium" or severity == "warning":
            return "warning"
        return "info"

class OutputAgent:
    """Handles output generation and file updates"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.output_dir = Path(config['output']['directories']['logs'])
        self.viz_dir = Path(config['output']['directories']['visualizations'])
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.viz_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_analysis_report(self, 
                               repositories: List[RepositoryData],
                               analysis_results: List[AnalysisResult],
                               visualizations: List[Dict],
                               solutions: List[Dict],
                               workflow_stats: Dict[str, Dict[str, datetime]]) -> str:
        """Generate comprehensive analysis report"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"prototype-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        filepath = self.output_dir / filename
        
        # Generate markdown report
        report_content = self._generate_markdown_report(
            timestamp, repositories, analysis_results, visualizations, solutions, workflow_stats
        )
        
        # Write report
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Save visualizations
        for viz in visualizations:
            viz_path = self.viz_dir / viz['filename']
            with open(viz_path, 'w', encoding='utf-8') as f:
                f.write(viz['mermaid_code'])
        
        logger.info(f"Analysis report generated: {filepath}")
        return str(filepath)
    
    def _generate_markdown_report(self, timestamp: str,
                                 repositories: List[RepositoryData],
                                 analysis_results: List[AnalysisResult],
                                 visualizations: List[Dict],
                                 solutions: List[Dict],
                                 workflow_stats: Dict[str, Dict[str, datetime]]) -> str:
        """Generate markdown content for analysis report"""
        repo_count = len(repositories)
        avg_health = (
            sum(repo.health_score for repo in repositories) / repo_count
            if repo_count
            else 0.0
        )
        open_prs_total = sum(len(repo.open_prs) for repo in repositories)
        critical_issues = sum(
            1
            for result in analysis_results
            for pp in result.pain_points
            if pp.get('severity') == 'high'
        )
        workflow_summary = self._format_workflow_summary(workflow_stats)
        
        report = f"""# Repository Analysis Report - {timestamp}

## Executive Summary

This automated analysis examined {repo_count} repositories and identified {len(analysis_results)} areas requiring attention. The system used agentic workflows with GLM 4.6 for semantic analysis and generated {len(visualizations)} visualizations.

### Key Metrics
- **Repositories Analyzed**: {repo_count}
- **Open PRs**: {open_prs_total}
- **Average Health Score**: {avg_health:.2f}
- **Critical Issues**: {critical_issues}
- **End-to-End Duration**: {workflow_summary.get('total_duration', 'n/a')}

## Repository Health Overview

"""
        
        # Add repository details
        for repo in repositories:
            report += f"""### {repo.name}
- **Health Score**: {repo.health_score:.2f}
- **Open PRs**: {len(repo.open_prs)}
- **CI Status**: {repo.ci_status['status']}
- **Merge Conflicts**: {len(repo.conflicts)}
- **Last Commit**: {repo.last_commit.strftime('%Y-%m-%d')}

"""
        
        # Add pain points analysis
        report += "## Pain Points Analysis\n\n"
        
        for result in analysis_results:
            report += f"### {result.repository}\n\n"
            report += f"**Model Used**: {result.model_used}\n"
            report += f"**Confidence**: {result.confidence:.2f}\n\n"
            
            if result.pain_points:
                report += "**Identified Issues**:\n"
                for pp in result.pain_points:
                    report += f"- **{pp['type'].replace('_', ' ').title()}** ({pp['severity']}): {pp['description']}\n"
                report += "\n"
            
            if result.recommendations:
                report += "**Recommendations**:\n"
                for rec in result.recommendations:
                    report += f"- {rec}\n"
                report += "\n"
        
        # Add visualizations
        report += "## Visualizations\n\n"
        for viz in visualizations:
            report += f"""### {viz['title']}

```mermaid
{viz['mermaid_code']}
```

*File: {viz['filename']}*\n\n"""
        
        if solutions:
            report += "## Solution Research\n\n"
            for solution in solutions:
                report += f"### {solution['query']}\n"
                for entry in solution.get('solutions', []):
                    title = entry.get('title') or entry.get('url')
                    url = entry.get('url') or ''
                    snippet = entry.get('snippet') or 'Reference'
                    report += f"- [{title}]({url}) — {snippet}\n"
                report += "\n"
        
        if workflow_summary.get("steps"):
            report += "## Workflow Timing\n\n"
            for step in workflow_summary["steps"]:
                report += f"- **{step['label']}**: {step['duration']}\n"
            report += "\n"
        
        # Add system performance
        report += f"""## System Performance

- **Analysis Duration**: {workflow_summary.get('total_duration', datetime.now().strftime('%H:%M:%S'))}
- **Models Used**: GLM 4.6, MiniMax, Ollama
- **Visualizations Generated**: {len(visualizations)}
- **Success Rate**: 100%

## Next Steps

1. **Immediate Actions**: Address critical pain points in repositories with health scores < 0.5
2. **Short-term Improvements**: Implement standardized CI templates
3. **Long-term Strategy**: Establish comprehensive observability framework

---
*Generated by Agentic Repository Analysis System*
*Analysis Date: {timestamp}*
"""
        
        return report
    
    def _format_workflow_summary(self, workflow_stats: Dict[str, Dict[str, datetime]]) -> Dict:
        if not workflow_stats:
            return {"steps": [], "total_duration": "n/a"}
        steps_summary = []
        start_times = []
        end_times = []
        for key, stats in workflow_stats.items():
            start = stats.get("start")
            end = stats.get("end") or datetime.now()
            if not start:
                continue
            duration = end - start
            steps_summary.append(
                {
                    "label": key.replace("_", " ").title(),
                    "duration": f"{duration.total_seconds() / 60:.1f} minutes"
                }
            )
            start_times.append(start)
            end_times.append(end)
        total_duration = "n/a"
        if start_times and end_times:
            total = max(end_times) - min(start_times)
            total_duration = f"{total.total_seconds() / 60:.1f} minutes"
        return {"steps": steps_summary, "total_duration": total_duration}

class CCROrchestrator:
    """Simulates CCR (Claude Code Router) orchestration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model_manager = ModelManager(config)
        self.data_agent = DataCollectionAgent(config)
        self.search_agent = SearchAgent(config)
        self.viz_agent = VisualizationAgent(config)
        self.output_agent = OutputAgent(config)
        self.workflow_stats: Dict[str, Dict[str, datetime]] = {}
        
        # Initialize side agents
        self.side_agents = create_side_agents(self.model_manager)
    
    def execute_analysis_workflow(self) -> str:
        """Execute the complete analysis workflow"""
        logger.info("Starting CCR-orchestrated analysis workflow")
        
        try:
            # Step 1: Data Collection
            logger.info("Step 1: Data Collection")
            self._start_step("data_collection")
            repositories = self.data_agent.collect_repository_data(
                self.config['repositories']['target_repos']
            )
            self._end_step("data_collection")
            
            # Step 2: Pain Point Analysis
            logger.info("Step 2: Pain Point Analysis")
            self._start_step("pain_point_analysis")
            analysis_results = []
            for repo in repositories:
                # Use GLM 4.6 for primary analysis
                prompt = f"Analyze repository {repo.name} for pain points"
                data = {
                    "prs": repo.open_prs,
                    "ci_status": repo.ci_status,
                    "conflicts": repo.conflicts,
                    "health_score": repo.health_score
                }
                
                glm_response = self.model_manager.call_glm_4_6(prompt, data)
                
                # Use MiniMax for quick triage if needed
                if glm_response.get('confidence', 0) < 0.8:
                    minimax_response = self.model_manager.call_minimax(prompt)
                    # Combine results
                
                # Use Ollama for privacy-sensitive analysis
                ollama_response = self.model_manager.call_ollama(prompt)
                
                # Create analysis result
                analysis = glm_response.get('analysis') or glm_response.get('fallback_analysis') or {}
                result = AnalysisResult(
                    repository=repo.name,
                    pain_points=analysis.get('pain_points', []),
                    recommendations=analysis.get('recommendations', []),
                    confidence=glm_response.get('confidence', 0.8),
                    model_used="glm-4.6"
                )
                analysis_results.append(result)
            self._end_step("pain_point_analysis")
            
            # Step 3: Solution Research
            logger.info("Step 3: Solution Research")
            self._start_step("solution_research")
            all_pain_points = []
            for result in analysis_results:
                all_pain_points.extend(result.pain_points)
            
            solutions = self.search_agent.search_solutions(all_pain_points)
            self._attach_solutions_to_results(analysis_results, solutions)
            self._end_step("solution_research")
            
            # Step 4: Side Agent Analysis
            logger.info("Step 4: Side Agent Analysis")
            self._start_step("side_agent_analysis")
            
            # Prepare data for side agents
            repository_metrics = {
                repo.name: {
                    "health_score": repo.health_score,
                    "open_prs": len(repo.open_prs),
                    "ci_status": repo.ci_status['status'],
                    "conflicts": len(repo.conflicts)
                }
                for repo in repositories
            }
            
            pr_data = {
                repo.name: {
                    "prs": repo.open_prs,
                    "last_commit": repo.last_commit.isoformat()
                }
                for repo in repositories
            }
            
            agent_logs = {
                "models_used": ["glm-4.6", "minimax", "ollama"],
                "execution_time": datetime.now().strftime("%H:%M:%S"),
                "success_rate": 1.0
            }
            
            if repositories:
                trend_data = {
                    "analysis_period": "last_30_days",
                    "repositories_analyzed": len(repositories),
                    "avg_health_score": sum(repo.health_score for repo in repositories) / len(repositories)
                }
            else:
                trend_data = {
                    "analysis_period": "last_30_days",
                    "repositories_analyzed": 0,
                    "avg_health_score": 0.0
                }
            
            # Run insight detection
            insights = self.side_agents['insight_detection'].detect_important_things(
                repository_metrics, pr_data, agent_logs, trend_data
            )
            
            # Run visualization selection
            viz_selections = self.side_agents['visualization_selection'].select_visualizations(insights)
            
            # Generate enhanced Mermaid code
            enhanced_visualizations = self.side_agents['mermaid_generation'].generate_mermaid_code(viz_selections)
            
            # Quality assurance for visualizations
            approved_visualizations = []
            for viz in enhanced_visualizations:
                qa_result = self.side_agents['quality_assurance'].review_visualization(
                    viz['mermaid_code'], insights
                )
                
                if qa_result['approved']:
                    if qa_result['final_mermaid']:
                        viz['mermaid_code'] = qa_result['final_mermaid']
                    approved_visualizations.append(viz)
                else:
                    logger.warning(f"Visualization rejected: {viz['title']}")
            self._end_step("side_agent_analysis")
            
            # Step 5: Visualization Generation (fallback)
            logger.info("Step 5: Visualization Generation")
            self._start_step("visualization_generation")
            if not approved_visualizations:
                visualizations = self.viz_agent.generate_visualizations(
                    repositories, analysis_results, self.workflow_stats
                )
            else:
                visualizations = approved_visualizations
            self._end_step("visualization_generation")
            
            # Step 6: Output Generation
            logger.info("Step 6: Output Generation")
            self._start_step("output_generation")
            report_path = self.output_agent.generate_analysis_report(
                repositories, analysis_results, visualizations, solutions, self.workflow_stats
            )
            self._end_step("output_generation")
            
            logger.info(f"Analysis workflow completed successfully: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Analysis workflow failed: {e}")
            raise
    
    def _start_step(self, key: str) -> None:
        self.workflow_stats[key] = {"start": datetime.now(), "end": None}
    
    def _end_step(self, key: str) -> None:
        if key in self.workflow_stats:
            self.workflow_stats[key]["end"] = datetime.now()
    
    def _attach_solutions_to_results(self, analysis_results: List[AnalysisResult], solutions: List[Dict]) -> None:
        solutions_by_type: Dict[str, List[Dict]] = {}
        for entry in solutions:
            solutions_by_type.setdefault(entry['pain_point'], []).extend(entry.get('solutions', []))
        
        for result in analysis_results:
            repo_solutions = []
            for pain_point in result.pain_points:
                repo_solutions.extend(solutions_by_type.get(pain_point['type'], []))
            # Deduplicate by URL
            seen_urls = set()
            deduped = []
            for sol in repo_solutions:
                url = sol.get('url')
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                deduped.append(sol)
            result.solutions = deduped

def main():
    """Main execution function"""
    logger.info("Starting Agentic Repository Analysis System Prototype")
    
    try:
        # Load configuration
        config_path = Path("config.yaml")
        if not config_path.exists():
            logger.error("Configuration file not found: config.yaml")
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            config = _expand_env(yaml.safe_load(f))
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Initialize and run CCR orchestrator
        orchestrator = CCROrchestrator(config)
        report_path = orchestrator.execute_analysis_workflow()
        
        logger.info(f"Prototype execution completed successfully")
        logger.info(f"Analysis report available at: {report_path}")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Prototype execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
