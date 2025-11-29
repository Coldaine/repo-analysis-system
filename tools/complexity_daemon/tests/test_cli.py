import unittest
import os
import shutil
import toml
from typer.testing import CliRunner
from tools.complexity_daemon.cli import app
from tools.complexity_daemon.config import get_state_db, get_config_file
import git

class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = "test_cli_temp"
        os.makedirs(self.test_dir, exist_ok=True)
        self.repo_path = os.path.join(self.test_dir, "test_repo")
        os.makedirs(self.repo_path, exist_ok=True)
        self.repo = git.Repo.init(self.repo_path)

        # Configure git user
        with self.repo.config_writer() as git_config:
            git_config.set_value("user", "name", "Test User")
            git_config.set_value("user", "email", "test@example.com")

        # Set the HOME environment variable to the test directory
        os.environ["HOME"] = os.path.abspath(self.test_dir)

        # Create the necessary directories
        get_state_db().parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        del os.environ["HOME"]

    def test_init(self):
        result = self.runner.invoke(app, ["init"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(get_config_file().exists())

    def test_add_remove_list(self):
        self.runner.invoke(app, ["init"])

        # Add a repo
        result = self.runner.invoke(app, ["add", self.repo_path])
        self.assertEqual(result.exit_code, 0)

        with open(get_config_file(), "r") as f:
            config = toml.load(f)
        self.assertEqual(len(config["repos"]), 1)
        self.assertEqual(config["repos"][0]["path"], os.path.abspath(self.repo_path))

        # List repos
        result = self.runner.invoke(app, ["list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(os.path.abspath(self.repo_path), result.stdout)

        # Remove the repo
        result = self.runner.invoke(app, ["remove", self.repo_path])
        self.assertEqual(result.exit_code, 0)

        with open(get_config_file(), "r") as f:
            config = toml.load(f)
        self.assertEqual(len(config["repos"]), 0)

    def test_status_reset(self):
        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["add", self.repo_path])

        # Set a delta
        from tools.complexity_daemon.state import get_db_connection, get_repo_id, update_cumulative_delta, init_db
        db_path = get_state_db()
        init_db(str(db_path))
        conn = get_db_connection(str(db_path))
        repo_id = get_repo_id(conn, os.path.abspath(self.repo_path))
        update_cumulative_delta(conn, repo_id, 10)
        conn.close()

        # Check status
        result = self.runner.invoke(app, ["status"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("10", result.stdout)

        # Reset delta
        result = self.runner.invoke(app, ["reset", self.repo_path])
        self.assertEqual(result.exit_code, 0)

        # Check status again
        result = self.runner.invoke(app, ["status"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0", result.stdout)

    def test_commit_history(self):
        from tools.complexity_daemon.state import init_db
        db_path = get_state_db()
        init_db(str(db_path))

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["add", self.repo_path])

        # Make and stage a change using absolute paths
        abs_repo_path = os.path.abspath(self.repo_path)
        test_file_path = os.path.join(abs_repo_path, "test.py")
        with open(test_file_path, "w") as f:
            f.write("def foo(): pass")
        self.repo.index.add(["test.py"])  # Use relative path from repo root

        # Commit the change
        result = self.runner.invoke(app, ["commit", self.repo_path])
        self.assertEqual(result.exit_code, 0)

        # Check history
        result = self.runner.invoke(app, ["history", self.repo_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("checkpoint: complexity", result.stdout)

if __name__ == "__main__":
    unittest.main()
