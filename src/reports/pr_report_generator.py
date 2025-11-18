"""
PR Report Generator
Auto-generate comprehensive pull request triage reports

Based on the user-provided script, this generates:
- Executive summary (counts, top repos, age bands)
- Author breakdown (%)
- Status breakdown
- Markdown table with all PRs
- Actionable recommendations
"""

import os
import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class PRInfo:
    """Pull request information for reporting"""
    repo: str
    full_repo: str
    number: int
    title: str
    html_url: str
    created_at: datetime
    age_days: int
    age_category: str  # Ancient, Recent, Active
    age_emoji: str  # 🔴, 🟡, 🟢
    status: str  # Draft, Ready
    author_login: str
    author_type: str  # Human, Bot, Dependabot, PrimaryHuman
    comments: int


class PRReportGenerator:
    """
    Generate comprehensive PR triage reports

    Features:
    - Fetch all open PRs from multiple repositories
    - Categorize by age, status, and author type
    - Generate executive summary with statistics
    - Create markdown tables with actionable recommendations
    - Heuristic-based action suggestions (MERGE, REVIEW, CLOSE)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PR report generator

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # GitHub API configuration
        self.github_token = config.get('github', {}).get('token') or os.getenv('GITHUB_TOKEN')
        self.github_api_base = config.get('github', {}).get('api_base', 'https://api.github.com')
        self.primary_author = config.get('github', {}).get('primary_author') or os.getenv('PRIMARY_AUTHOR')

        # Report configuration
        self.report_config = config.get('pr_report', {})
        self.ancient_threshold_days = self.report_config.get('ancient_threshold_days', 60)
        self.recent_threshold_days = self.report_config.get('recent_threshold_days', 30)

        # Session for HTTP requests
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })

        logger.info("PR Report Generator initialized")

    def generate_report(self, repos: List[str]) -> str:
        """
        Generate comprehensive PR report for multiple repositories

        Args:
            repos: List of repository names in "owner/repo" format

        Returns:
            Markdown-formatted report
        """
        logger.info(f"Generating PR report for {len(repos)} repositories")

        # Collect all PRs
        all_prs = self._collect_all_prs(repos)

        if not all_prs:
            return self._generate_empty_report()

        # Generate report sections
        report_lines = []

        # Header
        report_lines.extend(self._generate_header(all_prs))

        # Executive Summary
        report_lines.extend(self._generate_executive_summary(all_prs))

        # Markdown Table
        report_lines.extend(self._generate_markdown_table(all_prs))

        # Recommendations
        report_lines.extend(self._generate_recommendations(all_prs))

        # Footer
        report_lines.append("\n*Analysis complete. This report was auto-generated from live GitHub data.*\n")

        return '\n'.join(report_lines)

    def _collect_all_prs(self, repos: List[str]) -> List[PRInfo]:
        """Collect all open PRs from repositories"""
        now = datetime.now(timezone.utc)
        collected = []

        for full_repo in repos:
            try:
                owner, repo = full_repo.split('/')
                prs = self._fetch_open_prs(full_repo)

                for pr in prs:
                    created_at = self._parse_datetime(pr['created_at'])
                    days = self._age_in_days(created_at, now)
                    age_cat, age_emoji = self._age_category(days)
                    status = 'Draft' if pr.get('draft', False) else 'Ready'
                    author_login = pr['user']['login']
                    author_type = self._classify_author(author_login)

                    # GitHub PR object includes comments & review_comments counts
                    comments_count = pr.get('comments', 0) + pr.get('review_comments', 0)

                    collected.append(PRInfo(
                        repo=repo,
                        full_repo=full_repo,
                        number=pr['number'],
                        title=pr['title'],
                        html_url=pr['html_url'],
                        created_at=created_at,
                        age_days=days,
                        age_category=age_cat,
                        age_emoji=age_emoji,
                        status=status,
                        author_login=author_login,
                        author_type=author_type,
                        comments=comments_count
                    ))

            except Exception as e:
                logger.error(f"Failed to fetch PRs for {full_repo}: {e}")
                continue

        return collected

    def _fetch_open_prs(self, full_repo: str) -> List[Dict]:
        """Fetch open PRs for a repository"""
        url = f"{self.github_api_base}/repos/{full_repo}/pulls"
        params = {
            'state': 'open',
            'per_page': 100
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch PRs: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse GitHub ISO 8601 datetime"""
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

    def _age_in_days(self, created_at: datetime, now: datetime) -> int:
        """Calculate age in days"""
        delta = now - created_at
        return delta.days

    def _age_category(self, days: int) -> tuple[str, str]:
        """Categorize PR by age"""
        if days >= self.ancient_threshold_days:
            return "Ancient", "🔴"
        elif days >= self.recent_threshold_days:
            return "Recent", "🟡"
        else:
            return "Active", "🟢"

    def _classify_author(self, login: str) -> str:
        """Classify author type"""
        if login.lower().startswith("dependabot"):
            return "Dependabot"
        if login.lower().endswith("[bot]"):
            return "Bot"
        if self.primary_author and login == self.primary_author:
            return "PrimaryHuman"
        return "Human"

    def _heuristic_action(self, pr: PRInfo) -> str:
        """Generate heuristic action recommendation"""
        days = pr.age_days
        status = pr.status
        author_type = pr.author_type

        if author_type == "Dependabot" and status == "Ready":
            return "MERGE (dependency update)"

        if days >= self.ancient_threshold_days and status == "Ready":
            return "MERGE or CLOSE (stale)"
        if days >= self.ancient_threshold_days and status == "Draft":
            return "REVIEW or CLOSE (stale draft)"

        if self.recent_threshold_days <= days < self.ancient_threshold_days:
            return "REVIEW (aging)"

        if status == "Ready":
            return "MERGE (fresh)"
        else:
            return "REVIEW"

    def _safe_md(self, text: str) -> str:
        """Escape characters that break markdown tables"""
        if text is None:
            return ""
        return text.replace("|", "\\|")

    def _generate_header(self, prs: List[PRInfo]) -> List[str]:
        """Generate report header"""
        now = datetime.now()
        repo_count = len(set(pr.full_repo for pr in prs))

        return [
            "# Open Pull Requests Analysis",
            f"**Generated:** {now.strftime('%B %d, %Y, %I:%M %p %Z')}  ",
            f"**Total Open PRs:** {len(prs)} across {repo_count} repositories\n",
            "---\n"
        ]

    def _generate_executive_summary(self, prs: List[PRInfo]) -> List[str]:
        """Generate executive summary"""
        total = len(prs)

        # Calculate statistics
        age_counter = Counter(pr.age_category for pr in prs)
        repo_counts = Counter(pr.repo for pr in prs)
        author_type_counts = Counter(pr.author_type for pr in prs)
        status_counts = Counter(pr.status for pr in prs)

        def pct(count):
            return math.floor((count / total) * 100) if total > 0 else 0

        # Top 5 repos
        top_repos = repo_counts.most_common(5)

        lines = ["## Executive Summary\n", "### By Age Category"]

        ancient = age_counter.get("Ancient", 0)
        recent = age_counter.get("Recent", 0)
        active = age_counter.get("Active", 0)

        lines.extend([
            f"- 🔴 **Ancient ({self.ancient_threshold_days}+ days):** {ancient} PRs - **NEED DECISION**",
            f"- 🟡 **Recent ({self.recent_threshold_days}-{self.ancient_threshold_days-1} days):** {recent} PRs - **NEED ATTENTION**",
            f"- 🟢 **Active (0-{self.recent_threshold_days-1} days):** {active} PRs - **ACTIVE WORK**\n",
            "### By Repository (Top 5)"
        ])

        for repo, count in top_repos:
            lines.append(f"- **{repo}:** {count} PRs")

        lines.extend(["\n### By Author Type"])

        for author_type, count in author_type_counts.items():
            lines.append(f"- **{author_type}:** ~{pct(count)}%")

        lines.extend(["\n### By Status"])

        for status, count in status_counts.items():
            lines.append(f"- **{status}:** ~{pct(count)}%")

        lines.append("\n---\n")

        return lines

    def _generate_markdown_table(self, prs: List[PRInfo]) -> List[str]:
        """Generate markdown table with all PRs"""
        lines = [
            "## 📊 Markdown Table Format\n",
            "| Repo | PR# | Age (days) | Title | Status | Author | Comments | Action |",
            "|------|-----|-----------|-------|--------|--------|----------|--------|"
        ]

        # Sort by age desc (oldest first)
        sorted_prs = sorted(prs, key=lambda p: p.age_days, reverse=True)

        for pr in sorted_prs:
            action = self._heuristic_action(pr)
            repo = self._safe_md(pr.repo)
            title = self._safe_md(pr.title)
            age_display = f"{pr.age_emoji} {pr.age_days}"

            lines.append(
                f"| {repo} | #{pr.number} | {age_display} | {title} | "
                f"{pr.status} | {pr.author_login} | {pr.comments} | {action} |"
            )

        lines.append("\n---\n")

        return lines

    def _generate_recommendations(self, prs: List[PRInfo]) -> List[str]:
        """Generate actionable recommendations"""
        lines = [
            "## 📝 Auto-Generated Recommendations (Heuristic)\n"
        ]

        # P0: Ancient PRs
        ancient_prs = [p for p in prs if p.age_category == "Ancient"]
        if ancient_prs:
            lines.append("### P0 - Immediate (Ancient PRs)")
            for pr in sorted(ancient_prs, key=lambda x: x.age_days, reverse=True):
                action = self._heuristic_action(pr)
                lines.append(
                    f"- **{pr.repo} #{pr.number}** ({pr.age_days} days, {pr.status}): {action}"
                )
            lines.append("")

        # P1: Recent Ready
        recent_ready = [
            p for p in prs
            if p.age_category == "Recent" and p.status == "Ready"
        ]
        if recent_ready:
            lines.append("### P1 - High Priority (Recent, Ready PRs)")
            for pr in sorted(recent_ready, key=lambda x: x.age_days, reverse=True):
                action = self._heuristic_action(pr)
                lines.append(
                    f"- **{pr.repo} #{pr.number}** ({pr.age_days} days): {action}"
                )
            lines.append("")

        # P2: Dependabot and quick merges
        quick_merge = [
            p for p in prs
            if p.author_type == "Dependabot" and p.status == "Ready"
        ]
        if quick_merge:
            lines.append("### P2 - Maintenance (Quick Merges)")
            for pr in quick_merge:
                lines.append(f"- **{pr.repo} #{pr.number}**: MERGE dependency update")
            lines.append("")

        return lines

    def _generate_empty_report(self) -> str:
        """Generate report when no PRs found"""
        return """# Open Pull Requests Analysis

No open PRs found for the configured repositories.
"""

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on PR report generator"""
        try:
            # Check GitHub API connectivity
            url = f"{self.github_api_base}/rate_limit"
            response = self.session.get(url, timeout=10)
            github_ok = response.status_code == 200

            if github_ok:
                rate_data = response.json().get('rate', {})
            else:
                rate_data = {}

            return {
                'status': 'healthy' if github_ok else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'github_api': {
                    'connected': github_ok,
                    'rate_limit': rate_data.get('limit', 0),
                    'rate_remaining': rate_data.get('remaining', 0)
                },
                'configuration': {
                    'ancient_threshold_days': self.ancient_threshold_days,
                    'recent_threshold_days': self.recent_threshold_days,
                    'primary_author': self.primary_author or 'not set'
                }
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
