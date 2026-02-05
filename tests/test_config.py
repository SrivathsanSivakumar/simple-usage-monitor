"""Tests for config.py - JSON reading and writing"""

import pytest
import json
from pathlib import Path
from sumonitor.config import Config

class TestLoadConfig:
    """Test load_config() function with various scenarios"""

    def test_load_returns_empty_dict_when_file_missing(self, tmp_path):
        """load_config returns {} when config file doesnt exist"""
        config = Config()
        config.path = str(tmp_path / "nonexistent" / "config.json")
        assert config.load_config() == {}

    def test_load_returns_empty_dict_on_invalid_json(self, tmp_path):
        """load_config returns {} when file has corrupt JSON"""
        config = Config()
        config.path = str(tmp_path / "config.json")
        Path(config.path).write_text("not valid json{{")
        assert config.load_config() == {}

    def test_load_returns_dict_from_valid_file(self, tmp_path):
        """load config returns correct dict from valid JSON"""
        config = Config()
        config.path = str(tmp_path / "config.json")
        Path(config.path).write_text('{"plan": "max5"}')
        assert config.load_config() == {"plan": "max5"}

class TestSaveConfig:
    """Test save_config() function with various scenarios"""

    def test_save_creates_directory_and_file(self, tmp_path):
        """save_config creates parent dirs and file if they dont exist"""
        config = Config()
        config.path = str(tmp_path / "newdir" / "config.json")
        config.save_config({"plan": "pro"})
        assert Path(config.path).exists()

    def test_save_writes_correct_json(self, tmp_path):
        """File contains expected JSON after save"""
        config = Config()
        config.path = str(tmp_path / "config.json")
        config.save_config({"plan": "max20"})
        with open(config.path) as f:
            assert json.load(f) == {"plan": "max20"}

    def test_save_overwrites_existing_config(self, tmp_path):
        """Saving new values replaces old ones"""
        config = Config()
        config.path = str(tmp_path / "config.json")
        config.save_config({"plan": "max5"})
        config.save_config({"plan": "pro"})
        assert config.load_config() == {"plan": "pro"}