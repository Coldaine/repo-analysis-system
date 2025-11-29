import unittest
import os
import shutil
import git
from tools.complexity_daemon.git_ops import get_head_hash, stage_all, commit

class TestGitOps(unittest.TestCase):
    def setUp(self):
        self.repo_path = "test_repo"
        os.makedirs(self.repo_path, exist_ok=True)
        self.repo = git.Repo.init(self.repo_path)
        with open(os.path.join(self.repo_path, "test.txt"), "w") as f:
            f.write("initial commit")
        self.repo.index.add(["test.txt"])
        self.repo.index.commit("initial commit")

    def tearDown(self):
        shutil.rmtree(self.repo_path)

    def test_get_head_hash(self):
        head_hash = get_head_hash(self.repo_path)
        self.assertEqual(head_hash, self.repo.head.commit.hexsha)

    def test_stage_and_commit(self):
        new_file_path = os.path.join(self.repo_path, "new_file.txt")
        with open(new_file_path, "w") as f:
            f.write("new content")

        stage_all(self.repo_path)
        commit(self.repo_path, "new commit")

        latest_commit = self.repo.head.commit
        self.assertEqual(latest_commit.message.strip(), "new commit")
        self.assertIn("new_file.txt", latest_commit.stats.files)

if __name__ == "__main__":
    unittest.main()
