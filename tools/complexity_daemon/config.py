"""Configuration management for the complexity daemon."""

from pathlib import Path
import tomli
import toml

def get_config_dir() -> Path:
    return Path.home() / ".config" / "cogload"

def get_config_file() -> Path:
    return get_config_dir() / "config.toml"

def get_state_db() -> Path:
    return Path.home() / ".local" / "share" / "cogload" / "state.db"

DEFAULT_CONFIG = {
    "daemon": {
        "debounce_seconds": 5,
        "log_level": "info",
    },
    "defaults": {
        "threshold": 50,
        "complexity_tool": "lizard",
        "include_patterns": ["*.py", "*.rs", "*.ts", "*.js", "*.go"],
        "exclude_patterns": ["*_test.py", "test_*.py"],
        "message_template": "checkpoint: complexity {delta} (auto)",
    },
    "repos": [],
}

def load_config():
    """Loads the config file."""
    config_file = get_config_file()
    if not config_file.exists():
        return DEFAULT_CONFIG
    with open(config_file, "rb") as f:
        return tomli.load(f)

def save_config(config):
    """Saves the config file."""
    config_file = get_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        toml.dump(config, f)
