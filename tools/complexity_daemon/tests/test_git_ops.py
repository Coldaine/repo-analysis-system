"""Tests for Git operations."""

import unittest
import os
import shutil
import git
from tools.complexity_daemon.git_ops import get_head_hash, stage_all, commit, GitOperationError

class TestGitOps(unittest.TestCase):
    def setUp(self):
        self.repo_path = os.path.abspath("test_repo")
        os.makedirs(self.repo_path, exist_ok=True)
        self.repo = git.Repo.init(self.repo_path)

        # Initial commit is necessary to have a HEAD
        initial_file = os.path.join(self.repo_path, "initial.txt")
        with open(initial_file, "w") as f:
            f.write("initial")
        self.repo.index.add([initial_file])
        # Set a default author for tests
        self.repo.config_writer().set_value("user", "name", "Test User").release()
        self.repo.config_writer().set_value("user", "email", "test@example.com").release()
        self.repo.index.commit("initial commit")

    def tearDown(self):
        # On Windows, git processes can sometimes hold onto files,
        # so we need to be careful with cleanup.
        try:
            shutil.rmtree(self.repo_path)
        except PermissionError:
            print(f"Warning: Could not remove {self.repo_path}. It may be locked by a git process.")


    def test_get_head_hash_valid_repo(self):
        """Test getting the HEAD hash from a valid repository."""
        head_hash = get_head_hash(self.repo_path)
        self.assertEqual(head_hash, self.repo.head.commit.hexsha)

    def test_get_head_hash_empty_repo(self):
        """Test getting the HEAD hash from an empty (no commits) repository."""
        empty_repo_path = os.path.join(os.path.dirname(self.repo_path), "empty_repo")
        git.Repo.init(empty_repo_path)
        self.assertEqual(get_head_hash(empty_repo_path), "")
        shutil.rmtree(empty_repo_path)

    def test_stage_and_commit(self):
        """Test a successful staging and commit operation."""
        new_file_path = os.path.join(self.repo_path, "new_file.txt")
        with open(new_file_path, "w") as f:
            f.write("new content")

        stage_all(self.repo_path)
        commit_made = commit(self.repo_path, "new commit")

        self.assertTrue(commit_made)
        latest_commit = self.repo.head.commit
        self.assertEqual(latest_commit.message.strip(), "new commit")
        self.assertIn("new_file.txt", latest_commit.stats.files)

    def test_commit_no_changes(self):
        """Test that commit returns False when there are no staged changes."""
        commit_made = commit(self.repo_path, "no-op commit")
        self.assertFalse(commit_made)
        # Ensure no new commit was created
        self.assertEqual(self.repo.head.commit.message.strip(), "initial commit")

    def test_invalid_repo_path(self):
        """Test that operations on an invalid path raise an exception."""
        invalid_path = os.path.join(os.path.dirname(self.repo_path), "non_existent_repo")
        with self.assertRaises(GitOperationError):
            get_head_hash(invalid_path)

    def test_stage_failure(self):
        """Test that stage_all raises an exception on failure."""
        # This is hard to simulate reliably, but we can test the wrapper
        with unittest.mock.patch('git.Repo') as mock_repo:
            mock_repo.return_value.git.add.side_effect = git.exc.GitCommandError('add', 1)
            with self.assertRaises(GitOperationError):
                stage_all(self.repo_path)

if __name__ == "__main__":
    unittest.main()
