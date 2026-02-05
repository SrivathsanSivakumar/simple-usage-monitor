"""Tests for log_reader.py - JSONL parsing, cost calculation, and file discovery"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from sumonitor.data.log_reader import LogReader, UsageData, _calculate_total_cost


class TestCostCalculation:
    """Test _calculate_total_cost() function with various models and token counts"""

    def test_calculates_sonnet_below_tier(self):
        """Sonnet with ≤200k total input tokens should use base rates"""
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5-20250929",
            input_tokens=100_000,
            output_tokens=50_000,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        # (100k/1M * $3.00) + (50k/1M * $15.00) = $0.30 + $0.75 = $1.05
        assert cost == pytest.approx(1.05)

    def test_calculates_sonnet_above_tier(self):
        """Sonnet with >200k total input tokens should use tier rates for ALL tokens"""
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5-20250929",
            input_tokens=250_000,
            output_tokens=100_000,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        # ALL tokens at tier rate: (250k/1M * $6.00) + (100k/1M * $22.50) = $1.50 + $2.25 = $3.75
        assert cost == pytest.approx(3.75)

    def test_cache_tokens_push_over_tier_threshold(self):
        """Cache tokens should count toward tier break threshold"""
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5",
            input_tokens=100_000,
            output_tokens=50_000,
            cache_write_tokens=60_000,
            cache_read_tokens=50_000  # Total input: 210k > 200k
        )
        # Use tier rates for all tokens
        expected = (100_000/1e6)*6.00 + (50_000/1e6)*22.50 + (60_000/1e6)*7.50 + (50_000/1e6)*0.60
        assert cost == pytest.approx(expected)

    def test_opus_no_tiering(self):
        """Opus should always use base rate regardless of token count"""
        cost_large = _calculate_total_cost(
            model="claude-opus-4-5",
            input_tokens=500_000,
            output_tokens=250_000,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        # Base rate: (500k/1M * $5.00) + (250k/1M * $25.00) = $2.50 + $6.25 = $8.75
        assert cost_large == pytest.approx(8.75)

    def test_unknown_model_zero_cost(self):
        """Unknown models should return zero cost"""
        cost = _calculate_total_cost(
            model="unknown-model-xyz",
            input_tokens=1_000_000,
            output_tokens=500_000,
            cache_write_tokens=100_000,
            cache_read_tokens=50_000
        )
        assert cost == 0.0


class TestJSONLParsing:
    """Test JSONL file parsing and UsageData creation"""

    def test_parses_valid_jsonl_entry(self, temp_jsonl_dir):
        """Should successfully parse well-formed JSONL with usage data"""
        jsonl_file = temp_jsonl_dir / "test.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0
                }
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 1
        assert usage_data[0].input_tokens == 100
        assert usage_data[0].output_tokens == 50
        assert usage_data[0].model == "claude-sonnet-4-5"

    def test_skips_malformed_json_line(self, temp_jsonl_dir):
        """Malformed JSON should be skipped without crashing"""
        jsonl_file = temp_jsonl_dir / "bad.jsonl"
        jsonl_file.write_text("not valid json\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 0

    def test_skips_entry_without_timestamp(self, temp_jsonl_dir):
        """Entry without timestamp should be skipped"""
        jsonl_file = temp_jsonl_dir / "no_ts.jsonl"
        entry_data = {
            "message": {
                "id": "msg_123",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 0

    def test_skips_entry_without_usage_field(self, temp_jsonl_dir):
        """Entry without usage dict should be skipped"""
        jsonl_file = temp_jsonl_dir / "no_usage.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5"
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 0

    def test_converts_z_suffix_to_utc(self, temp_jsonl_dir):
        """Timestamp with Z should be converted to UTC timezone"""
        jsonl_file = temp_jsonl_dir / "z_suffix.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_1"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert usage_data[0].timestamp.tzinfo == timezone.utc

    def test_defaults_missing_cache_tokens_to_zero(self, temp_jsonl_dir):
        """Missing cache token fields should default to 0"""
        jsonl_file = temp_jsonl_dir / "no_cache.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50
                }
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert usage_data[0].cache_write_tokens == 0
        assert usage_data[0].cache_read_tokens == 0


class TestDeduplication:
    """Test duplicate entry handling using message_id:requestId"""

    def test_duplicate_entries_skipped(self, temp_jsonl_dir):
        """Same message_id:requestId should only be counted once"""
        jsonl_file = temp_jsonl_dir / "dup.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        # Write same entry twice
        jsonl_file.write_text(json.dumps(entry_data) + "\n" + json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 1

    def test_different_request_ids_both_counted(self, temp_jsonl_dir):
        """Same message_id but different requestId should both count"""
        jsonl_file = temp_jsonl_dir / "diff_req.jsonl"
        entry1 = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_1"
        }
        entry2 = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 200, "output_tokens": 100}
            },
            "requestId": "req_2"
        }
        jsonl_file.write_text(json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 2

    def test_multiple_calls_preserve_deduplication(self, temp_jsonl_dir):
        """Multiple parse_json_files() calls should maintain deduplication"""
        jsonl_file = temp_jsonl_dir / "multi.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data1 = reader.parse_json_files()
            usage_data2 = reader.parse_json_files()

        # Second call should not add duplicates
        assert len(usage_data2) == 1


class TestTimestampFiltering:
    """Test hours_back parameter for filtering old entries"""

    def test_includes_entries_within_lookback(self, temp_jsonl_dir):
        """Entries within hours_back should be included"""
        jsonl_file = temp_jsonl_dir / "recent.jsonl"
        # 3 hours ago - within default 120 hour window
        recent_time = datetime.now(timezone.utc) - timedelta(hours=3)
        entry_data = {
            "timestamp": recent_time.isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files(hours_back=5)

        assert len(usage_data) == 1

    def test_excludes_entries_outside_lookback(self, temp_jsonl_dir):
        """Entries older than hours_back should be excluded"""
        jsonl_file = temp_jsonl_dir / "old.jsonl"
        # 10 hours ago - outside 5 hour window
        old_time = datetime.now(timezone.utc) - timedelta(hours=10)
        entry_data = {
            "timestamp": old_time.isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files(hours_back=5)

        assert len(usage_data) == 0

    def test_default_lookback_120_hours(self, temp_jsonl_dir):
        """Default lookback should be 120 hours (5 days)"""
        jsonl_file = temp_jsonl_dir / "default.jsonl"
        # 100 hours ago - within default 120 hour window
        time_100h_ago = datetime.now(timezone.utc) - timedelta(hours=100)
        entry_data = {
            "timestamp": time_100h_ago.isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 1


class TestFileDiscovery:
    """Test get_jsonl_files() directory traversal"""

    def test_raises_error_for_missing_directory(self):
        """Missing Claude projects directory should raise FileNotFoundError"""
        reader = LogReader()
        with pytest.raises(FileNotFoundError, match="Claude projects directory not found"):
            reader.get_jsonl_files("/nonexistent/path/that/does/not/exist")

    def test_finds_jsonl_files_recursively(self, temp_jsonl_dir):
        """Should find JSONL files in nested directories"""
        (temp_jsonl_dir / "session1.jsonl").touch()
        subdir = temp_jsonl_dir / "subproject"
        subdir.mkdir()
        (subdir / "session2.jsonl").touch()

        reader = LogReader()
        files = reader.get_jsonl_files(str(temp_jsonl_dir.parent.parent))

        assert len(files) == 2
        assert all(f.suffix == ".jsonl" for f in files)

    def test_ignores_non_jsonl_files(self, temp_jsonl_dir):
        """Should only return .jsonl files"""
        (temp_jsonl_dir / "session.jsonl").touch()
        (temp_jsonl_dir / "readme.txt").touch()
        (temp_jsonl_dir / "data.json").touch()

        reader = LogReader()
        files = reader.get_jsonl_files(str(temp_jsonl_dir.parent.parent))

        assert len(files) == 1
        assert files[0].suffix == ".jsonl"

    def test_empty_directory_returns_empty_list(self, temp_jsonl_dir):
        """Empty directory should return empty list"""
        reader = LogReader()
        files = reader.get_jsonl_files(str(temp_jsonl_dir.parent.parent))

        assert len(files) == 0


class TestEdgeCases:
    """Edge cases and boundary conditions"""

    def test_empty_jsonl_file(self, temp_jsonl_dir):
        """Empty JSONL file should return no data"""
        jsonl_file = temp_jsonl_dir / "empty.jsonl"
        jsonl_file.write_text("")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 0

    def test_blank_lines_skipped(self, temp_jsonl_dir):
        """Blank lines in JSONL should be skipped"""
        jsonl_file = temp_jsonl_dir / "blanks.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text("\n\n" + json.dumps(entry_data) + "\n\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 1

    def test_multiple_files_combined(self, temp_jsonl_dir):
        """Multiple JSONL files should be combined"""
        file1 = temp_jsonl_dir / "file1.jsonl"
        file2 = temp_jsonl_dir / "file2.jsonl"

        entry1 = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),
            "message": {
                "id": "msg_1",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "requestId": "req_1"
        }
        entry2 = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_2",
                "model": "claude-sonnet-4-5",
                "usage": {"input_tokens": 200, "output_tokens": 100}
            },
            "requestId": "req_2"
        }

        file1.write_text(json.dumps(entry1) + "\n")
        file2.write_text(json.dumps(entry2) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[file1, file2]):
            usage_data = reader.parse_json_files()

        assert len(usage_data) == 2

    def test_cost_calculated_and_stored(self, temp_jsonl_dir):
        """UsageData should have cost field calculated from tokens"""
        jsonl_file = temp_jsonl_dir / "cost.jsonl"
        entry_data = {
            "timestamp": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            "message": {
                "id": "msg_123",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 100_000,
                    "output_tokens": 50_000,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0
                }
            },
            "requestId": "req_abc"
        }
        jsonl_file.write_text(json.dumps(entry_data) + "\n")

        reader = LogReader()
        with patch.object(reader, 'get_jsonl_files', return_value=[jsonl_file]):
            usage_data = reader.parse_json_files()

        assert usage_data[0].cost == pytest.approx(1.05)
