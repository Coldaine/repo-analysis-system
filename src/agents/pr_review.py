import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.models.model_manager import ModelManager
from src.storage.adapter import StorageAdapter
from src.agents.data_collection import GitHubClient
from src.agents.output import OutputAgent

import requests

logger = logging.getLogger(__name__)

class PRReviewAgent:
    """Pull Request Review Agent: fetch diffs and generate local review artifacts"""

    def __init__(self, config: Dict, storage: StorageAdapter, model_manager: ModelManager, output_agent: OutputAgent):
        self.config = config
        self.storage = storage
        self.model_manager = model_manager
        self.output_agent = output_agent

        repo_cfg = config.get('repositories', {})
        api_cfg = config.get('api_keys', {})
        token = api_cfg.get('github_token')
        base = repo_cfg.get('github_api_base', 'https://api.github.com')
        self.github = GitHubClient(token, base)

        pr_cfg = config.get('agents', {}).get('pr_review', {})
        self.enabled = pr_cfg.get('enabled', False)
        self.commenting = pr_cfg.get('enable_github_commenting', False)
        self.max_prs = pr_cfg.get('max_prs_per_repo', 10)

    def review_repo(self, owner: str, repo: str, analysis_run_id: Optional[int] = None) -> int:
        if not self.enabled:
            logger.info('PR review disabled by configuration')
            return 0

        prs = self.github.get_pull_requests(owner, repo, state='open', per_page=self.max_prs)
        count = 0
        for pr in prs:
            try:
                number = pr.get('number')
                detail = self.github.get_pull_request_details(owner, repo, number)
                diff = self._fetch_diff(owner, repo, number)
                review_md = self._generate_review(owner, repo, detail, diff)
                safe_repo = f"{owner}/{repo}__PR_{number}"
                self.output_agent.write_agent_log('pull_request_review', safe_repo, review_md, json_payload={
                    'pr_number': number,
                    'title': pr.get('title'),
                    'author': pr.get('user', {}).get('login'),
                    'changed_files': detail.get('changed_files'),
                    'additions': detail.get('additions'),
                    'deletions': detail.get('deletions')
                })
                count += 1
            except Exception as e:
                logger.error(f"PR review failed for {owner}/{repo}#{pr.get('number')}: {e}")
                continue

        return count

    def _fetch_diff(self, owner: str, repo: str, number: int) -> str:
        url = f"{self.github.base_url}/repos/{owner}/{repo}/pulls/{number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning(f"Failed to fetch diff for {owner}/{repo}#{number}: {e}")
            return ''

    def _generate_review(self, owner: str, repo: str, detail: Dict, diff: str) -> str:
        title = detail.get('title')
        author = detail.get('user', {}).get('login')
        number = detail.get('number')
        meta = {
            'title': title,
            'author': author,
            'number': number,
            'changed_files': detail.get('changed_files'),
            'additions': detail.get('additions'),
            'deletions': detail.get('deletions')
        }

        prompt = f"""
You are a senior code reviewer.
Repository: {owner}/{repo}
PR #{number}: {title}
Author: {author}

Changed files: {meta['changed_files']}
Additions: {meta['additions']}, Deletions: {meta['deletions']}

Diff:
{diff[:10000]}

Provide:
- Summary of changes
- Risk assessment
- Potential bugs or design issues
- Suggested tests or follow-ups
"""
        response = self.model_manager.call_model('glm_4_6', prompt, fallback_models=['minimax'])
        content = response.content if hasattr(response, 'content') else str(response)

        md = []
        md.append(f"# Pull Request Review: {owner}/{repo} #{number}")
        md.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append("")
        md.append(f"Title: {title}")
        md.append(f"Author: {author}")
        md.append(f"Changed files: {meta['changed_files']} | +{meta['additions']} -{meta['deletions']}")
        md.append("")
        md.append("## Review")
        md.append(content)
        return "\n".join(md)