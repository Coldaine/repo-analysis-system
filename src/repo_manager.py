import os
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

@dataclass
class SyncResult:
    synced: int
    cloned: int
    updated: int
    failed: int
    details_path: str

class RepoManager:
    """Manage local mirrors of configured repositories (clone, fetch, pull)"""

    def __init__(self, config: Dict):
        repo_cfg = config.get('repositories', {})
        self.workspace_path = Path(repo_cfg.get('workspace_path', '.')).resolve()
        self.default_owner = repo_cfg.get('default_owner') or os.getenv('GITHUB_OWNER')
        self.state_dir = Path('state')
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.sync_state_path = self.state_dir / 'repo_sync_state.json'
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def sync(self, repos: List[str]) -> SyncResult:
        """Ensure each repo exists locally and is up to date"""
        details = []
        cloned = updated = failed = 0

        for repo in repos:
            try:
                owner, name = self._resolve(repo)
                local_path = self.workspace_path / owner / name
                remote_url = f"https://github.com/{owner}/{name}.git"

                # Ensure owner directory exists
                local_path.parent.mkdir(parents=True, exist_ok=True)

                if not local_path.exists():
                    self._run_git(['clone', remote_url, str(local_path)])
                    action = 'cloned'
                    cloned += 1
                else:
                    # Fetch and fast-forward pull
                    self._run_git(['-C', str(local_path), 'fetch', '--all', '--prune'])
                    self._run_git(['-C', str(local_path), 'pull', '--ff-only'])
                    action = 'updated'
                    updated += 1

                details.append({
                    'repo': f"{owner}/{name}",
                    'local_path': str(local_path),
                    'remote_url': remote_url,
                    'action': action,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Sync failed for {repo}: {e}")
                failed += 1
                details.append({
                    'repo': repo,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

        # Persist sync state
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'results': details
        }
        with open(self.sync_state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

        return SyncResult(
            synced=len(repos),
            cloned=cloned,
            updated=updated,
            failed=failed,
            details_path=str(self.sync_state_path)
        )

    def _run_git(self, args: List[str]) -> None:
        """Run a git command with subprocess and error handling"""
        cmd = ['git'] + args
        logger.info('Running: %s', ' '.join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or 'git command failed')

    def _resolve(self, repo: str) -> (str, str):
        if '/' in repo:
            owner, name = repo.split('/', 1)
            return owner, name
        if not self.default_owner:
            raise ValueError('No default_owner configured; use owner/repo format')
        return self.default_owner, repo