import logging
import subprocess
from typing import Dict, List

from models.model_manager import ModelManager

logger = logging.getLogger(__name__)

class DocAlignmentInvestigator:
    """
    Investigates and resolves conflicts between documentation sources
    using Git history as the ultimate source of truth.
    """

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def investigate(self, conflict_description: str, involved_files: List[str]) -> Dict:
        """
        Investigates a documentation conflict and returns a verdict.

        :param conflict_description: A description of the conflicting claims.
        :param involved_files: A list of file paths involved in the conflict.
        :return: A dictionary containing the verdict and supporting evidence.
        """
        file_histories = {file: self._get_file_history(file) for file in involved_files}
        pivots = {file: self._detect_pivots(history) for file, history in file_histories.items()}

        prompt = self._build_prompt(conflict_description, file_histories, pivots)

        response = self.model_manager.call_model('glm_4_6', prompt, fallback_models=['minimax'])
        verdict = response.content if hasattr(response, 'content') else str(response)

        return {
            "verdict": verdict,
            "evidence": {
                "file_histories": file_histories,
                "pivots": pivots,
            },
        }

    def _build_prompt(self, conflict_description: str, file_histories: Dict, pivots: Dict) -> str:
        prompt = f"""
        You are a forensic software engineering expert.
        Your task is to determine the "True Intent" behind conflicting documentation.
        Analyze the following conflict and the git history of the involved files.

        Conflict: {conflict_description}

        Evidence:
        """

        for file_path, history in file_histories.items():
            prompt += f"\n--- History for {file_path} ---\n"
            if not history:
                prompt += "No history found.\n"
                continue

            # Recency: newest is first
            latest_commit = history[0]
            prompt += f"Latest commit on {latest_commit['date']} by {latest_commit['author']}: '{latest_commit['subject']}'\n"

            # Specificity: docs are more specific than README
            if "/docs/" in file_path:
                prompt += "This file is from the /docs/ directory, suggesting it contains detailed information.\n"
            elif "README.md" in file_path:
                 prompt += "This is a README.md, which is often a general overview.\n"

            file_pivots = pivots.get(file_path, [])
            if file_pivots:
                prompt += f"\nArchitectural Pivot Commits for {file_path}:\n"
                for pivot in file_pivots:
                    prompt += f"- {pivot['date']} by {pivot['author']}: '{pivot['subject']}' (Commit: {pivot['commit_hash'][:7]})\n"

        prompt += """
        Based on the evidence, synthesize a verdict.
        - Prioritize recency: newer information is more likely to be correct.
        - Give more weight to commits with intent-driven messages (e.g., "Refactor", "Architecture").
        - Consider file location: `/docs/` is typically more authoritative than `README.md`.

        Verdict:
        """
        return prompt

    def _get_file_history(self, file_path: str) -> List[Dict]:
        """
        Retrieves the commit history for a given file.

        :param file_path: The path to the file.
        :return: A list of dictionaries, where each dictionary represents a commit.
        """
        try:
            # Using a custom format to easily parse the log output
            log_format = "--pretty=format:%H||%an||%ad||%s"
            command = ["git", "log", log_format, "--follow", file_path]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = result.stdout.strip()

            history = []
            if not output:
                return history

            for line in output.split("\n"):
                parts = line.split("||")
                if len(parts) == 4:
                    history.append({
                        "commit_hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "subject": parts[3],
                    })
            return history
        except FileNotFoundError:
            logger.error(f"Git command not found. Make sure Git is installed and in your PATH.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting git log for {file_path}: {e.stderr}")
            return []

    def _detect_pivots(self, history: List[Dict]) -> List[Dict]:
        """
        Detects significant architectural shifts in the commit history.

        :param history: A list of commits.
        :return: A list of commits identified as pivots.
        """
        pivot_keywords = ["refactor", "architecture", "rework", "redesign", "big change"]
        pivots = []
        for commit in history:
            subject = commit["subject"].lower()
            if any(keyword in subject for keyword in pivot_keywords):
                pivots.append(commit)
        return pivots
