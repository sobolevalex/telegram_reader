"""Shared pytest fixtures: temp config, minimal AppConfig."""

import json
from pathlib import Path

import pytest

from telegram_reader.config import AppConfig, load_config


@pytest.fixture
def sample_config_dict() -> dict:
    """Minimal valid config as dict."""
    return {
        "channels": ["channel1", "channel2"],
        "message_limit_per_channel": 5,
        "email_subject_prefix": "Digest",
        "show_unread_count": True,
        "mark_as_read_after_fetch": False,
        "only_unread": False,
        "output_mode": "email",
        "ai_instructions": ["Line 1", "Line 2"],
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_config_dict: dict) -> Path:
    """Write sample config to a temp JSON file and return its path."""
    path = tmp_path / "config.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample_config_dict, f, ensure_ascii=False)
    return path


@pytest.fixture
def app_config_from_temp(temp_config_file: Path) -> AppConfig:
    """Load AppConfig from the temp config file."""
    return load_config(temp_config_file)
