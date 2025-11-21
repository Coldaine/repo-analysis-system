import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from models.model_manager import ModelManager
from storage.adapter import StorageAdapter
from agents.data_collection import GitHubClient
from agents.output import OutputAgent
from utils.logging import get_logger, correlation_context, timer_decorator

# Replace standard logging with enhanced structured logging
logger = get_logger(__name__)

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

        logger.info("PRReviewAgent initialized", extra={
            'enabled': self.enabled,
            'commenting_enabled': self.commenting,
            'max_prs': self.max_prs,
            'correlation_id': correlation_context.get_correlation_id(),
            'component': 'PRReviewAgent'
        })

    @timer_decorator("pr_review_operation")
    def review_repo(self, owner: str, repo: str, analysis_run_id: Optional[int] = None) -> int:
        """Review pull requests for a repository"""
        correlation_id = correlation_context.get_correlation_id()
        
        if not self.enabled:
            logger.info('PR review disabled by configuration', extra={
                'owner': owner,
                'repo': repo,
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            return 0

        logger.info(f'Starting PR review for repository', extra={
            'owner': owner,
            'repo': repo,
            'analysis_run_id': analysis_run_id,
            'correlation_id': correlation_id,
            'component': 'PRReviewAgent'
        })

        try:
            prs = self.github.get_pull_requests(owner, repo, state='open', per_page=self.max_prs)
            count = 0
            
            logger.info(f'Found open PRs for review', extra={
                'owner': owner,
                'repo': repo,
                'prs_found': len(prs),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })

            for pr in prs:
                try:
                    pr_number = pr.get('number')
                    logger.info(f'Processing PR review', extra={
                        'owner': owner,
                        'repo': repo,
                        'pr_number': pr_number,
                        'correlation_id': correlation_id,
                        'component': 'PRReviewAgent'
                    })

                    detail = self._fetch_pr_details(owner, repo, pr_number)
                    diff = self._fetch_diff(owner, repo, pr_number)
                    review_md = self._generate_review(owner, repo, detail, diff)
                    
                    safe_repo = f"{owner}/{repo}__PR_{pr_number}"
                    self.output_agent.write_agent_log('pull_request_review', safe_repo, review_md, json_payload={
                        'pr_number': pr_number,
                        'title': pr.get('title'),
                        'author': pr.get('user', {}).get('login'),
                        'changed_files': detail.get('changed_files'),
                        'additions': detail.get('additions'),
                        'deletions': detail.get('deletions'),
                        'correlation_id': correlation_id
                    })
                    
                    count += 1
                    logger.info(f'PR review completed', extra={
                        'owner': owner,
                        'repo': repo,
                        'pr_number': pr_number,
                        'correlation_id': correlation_id,
                        'component': 'PRReviewAgent'
                    })

                except Exception as e:
                    logger.error(f"PR review failed for individual PR", exc_info=True, extra={
                        'owner': owner,
                        'repo': repo,
                        'pr_number': pr.get('number'),
                        'error': str(e),
                        'correlation_id': correlation_id,
                        'component': 'PRReviewAgent'
                    })
                    continue

            logger.info(f'PR review operation completed', extra={
                'owner': owner,
                'repo': repo,
                'prs_reviewed': count,
                'total_prs_found': len(prs),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
            return count
            
        except Exception as e:
            logger.error(f"PR review operation failed", exc_info=True, extra={
                'owner': owner,
                'repo': repo,
                'error': str(e),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            return 0

    def _fetch_pr_details(self, owner: str, repo: str, number: int) -> Dict:
        """Fetch detailed information about a pull request"""
        correlation_id = correlation_context.get_correlation_id()
        
        try:
            logger.debug(f'Fetching PR details', extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
            detail = self.github.get_pull_request_details(owner, repo, number)
            
            logger.debug(f'PR details fetched successfully', extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'changed_files': detail.get('changed_files'),
                'additions': detail.get('additions'),
                'deletions': detail.get('deletions'),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
            return detail
            
        except Exception as e:
            logger.error(f"Failed to fetch PR details", exc_info=True, extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'error': str(e),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            raise

    @timer_decorator("diff_fetch")
    def _fetch_diff(self, owner: str, repo: str, number: int) -> str:
        """Fetch the diff for a pull request"""
        import requests
        correlation_id = correlation_context.get_correlation_id()
        
        url = f"{self.github.base_url}/repos/{owner}/{repo}/pulls/{number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        
        try:
            logger.debug(f'Fetching PR diff', extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'url': url,
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            diff_content = resp.text
            logger.debug(f'PR diff fetched successfully', extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'diff_length': len(diff_content),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
            return diff_content
            
        except Exception as e:
            logger.warning(f"Failed to fetch diff", exc_info=True, extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'error': str(e),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            return ''

    @timer_decorator("review_generation")
    def _generate_review(self, owner: str, repo: str, detail: Dict, diff: str) -> str:
        """Generate a review for the pull request using AI"""
        correlation_id = correlation_context.get_correlation_id()
        
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

        logger.info(f'Generating AI review for PR', extra={
            'owner': owner,
            'repo': repo,
            'pr_number': number,
            'title': title,
            'author': author,
            'changed_files': meta['changed_files'],
            'diff_length': len(diff),
            'correlation_id': correlation_id,
            'component': 'PRReviewAgent'
        })

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
        
        try:
            response = self.model_manager.call_model('glm_4_6', prompt, fallback_models=['minimax'])
            content = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f'AI review generated successfully', extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'model_used': response.model,
                'confidence': response.confidence,
                'content_length': len(content),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            
        except Exception as e:
            logger.error(f"Failed to generate AI review", exc_info=True, extra={
                'owner': owner,
                'repo': repo,
                'pr_number': number,
                'error': str(e),
                'correlation_id': correlation_id,
                'component': 'PRReviewAgent'
            })
            content = "AI review generation failed. Please review manually."

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
        
        review_content = "\n".join(md)
        
        logger.debug(f'PR review content assembled', extra={
            'owner': owner,
            'repo': repo,
            'pr_number': number,
            'review_length': len(review_content),
            'correlation_id': correlation_id,
            'component': 'PRReviewAgent'
        })
        
        return review_content