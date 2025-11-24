"""
Documentation Alignment Investigator Agent
Performs forensic analysis on repository history to resolve documentation conflicts.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.models.model_manager import ModelManager

logger = logging.getLogger(__name__)

@dataclass
class ForensicEvidence:
    file_path: str
    last_modified: str
    author: str
    commit_hash: str
    commit_message: str
    content_snippet: str

class DocAlignmentInvestigator:
    """
    Agent that investigates documentation conflicts using Git forensics.
    """

    def __init__(self, config: Dict[str, Any], model_manager: ModelManager):
        self.config = config
        self.model_manager = model_manager
        self.repo_path = config.get('repo_path', '.')

    def investigate(self, conflict_description: str, involved_files: List[str]) -> Dict[str, Any]:
        """
        Investigate a specific conflict by analyzing the history of involved files.
        
        Args:
            conflict_description: Description of the conflict (e.g. "README says X, docs says Y")
            involved_files: List of file paths relevant to the conflict
            
        Returns:
            Dictionary containing the verdict and supporting forensic evidence
        """
        logger.info(f"Starting forensic investigation for: {conflict_description}")
        
        evidence_list = []
        for file_path in involved_files:
            evidence = self._gather_file_evidence(file_path)
            if evidence:
                evidence_list.append(evidence)
                
        pivot_commits = self._detect_potential_pivots(involved_files)
        
        verdict = self._synthesize_verdict(conflict_description, evidence_list, pivot_commits)
        
        return {
            "conflict": conflict_description,
            "verdict": verdict,
            "evidence": [vars(e) for e in evidence_list],
            "pivot_commits": pivot_commits
        }

    def _gather_file_evidence(self, file_path: str) -> Optional[ForensicEvidence]:
        """Get the last modification details for a file."""
        try:
            # Get last commit info for the file
            cmd = ["git", "log", "-1", "--format=%h|%an|%ad|%s", "--date=iso", "--", file_path]
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            if not result.stdout.strip():
                return None
                
            hash_id, author, date, msg = result.stdout.strip().split("|", 3)
            
            # Get a snippet of the file (first 50 lines or specific search could be added)
            # For now, we assume the content is passed in context or we read the head
            # This is a placeholder for reading the actual content if needed
            content_snippet = "(Content analysis handled by upstream agents)"
            
            return ForensicEvidence(
                file_path=file_path,
                last_modified=date,
                author=author,
                commit_hash=hash_id,
                commit_message=msg,
                content_snippet=content_snippet
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to gather evidence for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error gathering evidence for {file_path}: {e}")
            return None

    def _detect_potential_pivots(self, files: List[str]) -> List[Dict[str, Any]]:
        """
        Scan history for 'Pivot Commits' - large refactors or architectural changes.
        """
        pivots = []
        try:
            # Look for commits with keywords in the last 50 commits
            keywords = ["refactor", "rewrite", "migrate", "architecture", "v2", "redesign"]
            grep_pattern = "|".join(keywords)
            
            cmd = [
                "git", "log", "-n", "50", 
                "--format=%h|%ad|%s", 
                "--date=iso", 
                f"--grep={grep_pattern}", 
                "-i",  # Case insensitive
                "--"
            ] + files
            
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True
            )
            
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    hash_id, date, msg = line.split("|", 2)
                    pivots.append({
                        "hash": hash_id,
                        "date": date,
                        "message": msg,
                        "type": "Potential Pivot"
                    })
                    
        except Exception as e:
            logger.warning(f"Pivot detection failed: {e}")
            
        return pivots

    def _synthesize_verdict(self, conflict: str, evidence: List[ForensicEvidence], pivots: List[Dict]) -> str:
        """
        Use LLM to determine the truth based on evidence.
        """
        
        prompt = f"""
        You are a Forensic Software Historian. Resolve this documentation conflict.
        
        THE GOLDEN RULE:
        - The `README.md` is often an afterthought and "rots" quickly.
        - Detailed files in `/docs/` are usually the authoritative Source of Truth.
        - However, the *most recent* major commit (Pivot) overrides everything.
        
        CONFLICT:
        {conflict}
        
        EVIDENCE FROM GIT HISTORY:
        """
        
        for e in evidence:
            prompt += f"""
            File: {e.file_path}
            Last Modified: {e.last_modified}
            Author: {e.author}
            Commit: {e.commit_message} ({e.commit_hash})
            ----------------------------------------
            """
            
        if pivots:
            prompt += "\nDETECTED PIVOT COMMITS (Possible Architectural Shifts):\n"
            for p in pivots:
                prompt += f"- {p['date']}: {p['message']} ({p['hash']})\n"
        
        prompt += """
        
        TASK:
        1. Compare the dates. Which source is newer?
        2. Analyze the commit messages. Did a "Refactor" or "Redesign" happen recently?
        3. Apply the Golden Rule: If README is old and docs are new, trust docs. If everything is old but a recent commit changed the framework, trust the commit.
        4. Determine the "True Intent". Is the README rotting? Did the project pivot?
        
        OUTPUT:
        Provide a concise verdict explaining which source is correct and why.
        """
        
        # Call the LLM
        try:
            # Prepend system role to prompt as ModelManager.call_model takes a single prompt string
            full_prompt = f"SYSTEM: You are an expert software architect and historian.\n\n{prompt}"
            
            response_obj = self.model_manager.call_model(
                model_name=self.model_manager.default_model,
                prompt=full_prompt
            )
            return response_obj.content
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return "Unable to synthesize verdict due to LLM error."
