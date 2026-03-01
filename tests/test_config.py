"""Tests for config.load_config and AppConfig."""

import json
from pathlib import Path

import pytest

from telegram_reader.config import AppConfig, load_config


def test_load_config_from_temp_file(temp_config_file: Path) -> None:
    config = load_config(temp_config_file)
    assert config.channels == ["channel1", "channel2"]
    assert config.message_limit_per_channel == 5
    assert config.email_subject_prefix == "Digest"
    assert config.show_unread_count is True
    assert config.mark_as_read_after_fetch is False
    assert config.only_unread is False
    assert config.output_mode == "email"
    assert "Line 1" in config.ai_instructions and "Line 2" in config.ai_instructions


def test_load_config_ai_instructions_as_list(
    temp_config_file: Path, sample_config_dict: dict
) -> None:
    sample_config_dict["ai_instructions"] = ["A", "B", "C"]
    with open(temp_config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config_dict, f)
    config = load_config(temp_config_file)
    assert config.ai_instructions == "A\nB\nC"


def test_load_config_ai_instructions_as_string(
    temp_config_file: Path, sample_config_dict: dict
) -> None:
    sample_config_dict["ai_instructions"] = "Single line"
    with open(temp_config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config_dict, f)
    config = load_config(temp_config_file)
    assert config.ai_instructions == "Single line"


def test_load_config_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(Path("/nonexistent/config.json"))


def test_load_config_defaults(
    temp_config_file: Path, sample_config_dict: dict
) -> None:
    # Minimal dict: only channels
    minimal = {"channels": ["one"]}
    with open(temp_config_file, "w", encoding="utf-8") as f:
        json.dump(minimal, f)
    config = load_config(temp_config_file)
    assert config.message_limit_per_channel == 10
    assert config.email_subject_prefix == "Telegram Digest"
    assert config.show_unread_count is True
    assert config.output_mode == "email"
