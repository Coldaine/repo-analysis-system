"""Tests for the config component."""

import unittest
import os
import shutil
import tempfile
from pathlib import Path
from tools.complexity_daemon.config import load_config, save_config, get_config_file, DEFAULT_CONFIG

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Set a temporary config file for testing to avoid interfering with user config
        self.temp_config_file = Path(self.test_dir) / "config.yaml"
        os.environ['COGLOAD_CONFIG_FILE'] = str(self.temp_config_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        del os.environ['COGLOAD_CONFIG_FILE']

    def test_default_config_creation(self):
        """Test that a default config is created if none exists."""
        self.assertFalse(self.temp_config_file.exists())
        config = load_config()
        self.assertTrue(self.temp_config_file.exists())
        self.assertEqual(config, DEFAULT_CONFIG)

    def test_load_existing_config(self):
        """Test loading an existing config file."""
        custom_config = {"daemon": {"log_level": "debug"}, "repos": []}
        save_config(custom_config)

        loaded_config = load_config()
        self.assertEqual(loaded_config["daemon"]["log_level"], "debug")

    def test_save_and_load(self):
        """Test that saving and then loading a config works correctly."""
        new_repo = {"path": "/test/repo", "enabled": True}
        config = load_config() # Starts with default
        config["repos"].append(new_repo)
        save_config(config)

        loaded_config = load_config()
        self.assertEqual(len(loaded_config["repos"]), 1)
        self.assertEqual(loaded_config["repos"][0]["path"], "/test/repo")

    def test_get_config_file_env_var(self):
        """Test that get_config_file respects the environment variable."""
        config_file = get_config_file()
        self.assertEqual(config_file, self.temp_config_file)

if __name__ == '__main__':
    unittest.main()
