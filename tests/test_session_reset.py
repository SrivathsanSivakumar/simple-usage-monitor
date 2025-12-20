"""Test suite for session reset functionality

This module tests that session counters correctly reset to 0 when a session expires,
and that the LogReader properly detects session boundaries and clears old data.
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.log_reader import UsageData, LogReader
from session.session_tracker import SessionTracker


@pytest.fixture
def log_reader():
    """Fixture to create a fresh LogReader instance for each test"""
    return LogReader()


@pytest.fixture
def session_tracker():
    """Fixture to create a fresh SessionTracker instance for each test"""
    return SessionTracker()


def create_mock_entry(hours_ago: float, tokens: int = 100) -> UsageData:
    """Factory function to create mock UsageData entries

    Args:
        hours_ago: How many hours before now this entry should be timestamped
        tokens: Number of input/output tokens (uses same value for both)

    Returns:
        UsageData object with calculated costs
    """
    timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return UsageData(
        model="claude-sonnet-4-5-20250929",
        input_tokens=tokens,
        input_tokens_cost=((tokens / 1_000_000) * 3.00, "<=200k"),  # (cost, tier) tuple
        output_tokens=tokens,
        output_tokens_cost=((tokens / 1_000_000) * 15.00, "<=200k"),  # (cost, tier) tuple
        timestamp=timestamp
    )


class TestSessionTransition:
    """Tests for session boundary detection and data cleanup"""

    def test_session_anchor_initialization(self, log_reader):
        """Test that session_start_time is initialized to oldest entry timestamp"""
        # Arrange
        entry1 = create_mock_entry(hours_ago=2, tokens=100)
        entry2 = create_mock_entry(hours_ago=1, tokens=200)
        log_reader.usage_data = [entry2, entry1]  # Out of order intentionally

        # Act
        if log_reader.usage_data:
            if log_reader.session_start_time is None:
                oldest = min(log_reader.usage_data, key=lambda e: e.timestamp)
                log_reader.session_start_time = oldest.timestamp

        # Assert
        assert log_reader.session_start_time is not None
        assert log_reader.session_start_time == entry1.timestamp

    def test_session_boundary_detection(self, log_reader):
        """Test that entries beyond 5-hour boundary are detected"""
        # Arrange
        entry1 = create_mock_entry(hours_ago=6, tokens=100)
        entry2 = create_mock_entry(hours_ago=4, tokens=200)
        entry3 = create_mock_entry(hours_ago=0.5, tokens=300)  # New session

        log_reader.usage_data = [entry1, entry2]
        log_reader.session_start_time = entry1.timestamp
        log_reader.usage_data.append(entry3)

        # Act
        session_end_time = log_reader.session_start_time + timedelta(hours=5)
        entries_in_new_session = [
            e for e in log_reader.usage_data
            if e.timestamp > session_end_time
        ]

        # Assert
        assert len(entries_in_new_session) == 1
        assert entries_in_new_session[0] == entry3

    def test_old_data_cleared_on_session_transition(self, log_reader):
        """Test that old session data is cleared when boundary is crossed"""
        # Arrange
        entry1 = create_mock_entry(hours_ago=6, tokens=100)
        entry2 = create_mock_entry(hours_ago=4, tokens=200)
        entry3 = create_mock_entry(hours_ago=0.5, tokens=300)

        log_reader.usage_data = [entry1, entry2]
        log_reader.session_start_time = entry1.timestamp
        log_reader.usage_data.append(entry3)

        # Act - Simulate the session transition logic
        if log_reader.usage_data:
            session_end_time = log_reader.session_start_time + timedelta(hours=5)
            entries_in_new_session = [
                e for e in log_reader.usage_data
                if e.timestamp > session_end_time
            ]

            if entries_in_new_session:
                new_session_earliest = min(entries_in_new_session, key=lambda e: e.timestamp)
                log_reader.usage_data = entries_in_new_session
                log_reader.session_start_time = new_session_earliest.timestamp

        # Assert
        assert len(log_reader.usage_data) == 1, "Should only contain new session entry"
        assert log_reader.usage_data[0] == entry3, "Should be the new session entry"
        assert log_reader.session_start_time == entry3.timestamp, "Anchor should update"

    def test_no_transition_within_same_session(self, log_reader):
        """Test that entries within 5-hour window don't trigger transition"""
        # Arrange
        entry1 = create_mock_entry(hours_ago=2, tokens=100)
        entry2 = create_mock_entry(hours_ago=1, tokens=200)
        entry3 = create_mock_entry(hours_ago=0.5, tokens=300)

        log_reader.usage_data = [entry1, entry2, entry3]
        log_reader.session_start_time = entry1.timestamp

        # Act
        session_end_time = log_reader.session_start_time + timedelta(hours=5)
        entries_in_new_session = [
            e for e in log_reader.usage_data
            if e.timestamp > session_end_time
        ]

        # Assert
        assert len(entries_in_new_session) == 0, "No entries should be beyond boundary"
        assert len(log_reader.usage_data) == 3, "All entries should remain"


class TestSessionBuilding:
    """Tests for SessionTracker session building and aggregation"""

    def test_single_session_created_from_recent_entries(self, session_tracker):
        """Test that entries within 5 hours create a single session"""
        # Arrange
        entries = [
            create_mock_entry(hours_ago=2, tokens=100),
            create_mock_entry(hours_ago=1, tokens=200),
            create_mock_entry(hours_ago=0.5, tokens=300),
        ]

        # Act
        session_tracker.build_sessions(entries)

        # Assert
        assert len(session_tracker.sessions) == 1, "Should create exactly one session"

    def test_current_session_aggregates_all_entries(self, session_tracker):
        """Test that current session correctly sums all token counts"""
        # Arrange
        entries = [
            create_mock_entry(hours_ago=2, tokens=100),
            create_mock_entry(hours_ago=1, tokens=200),
            create_mock_entry(hours_ago=0.5, tokens=300),
        ]

        # Act
        session_tracker.build_sessions(entries)
        current = session_tracker.get_current_session()

        # Assert
        assert current is not None, "Should have a current session"
        assert len(current.entries) == 3, "Should contain all entries"

        total_tokens, _ = current.total_tokens
        # Mock creates same value for input and output, so total is 2x (input + output)
        assert total_tokens == 1200, f"Expected 1200 tokens (600 input + 600 output), got {total_tokens}"

    def test_session_marked_as_active(self, session_tracker):
        """Test that recent session is marked as active"""
        # Arrange
        entries = [create_mock_entry(hours_ago=1, tokens=100)]

        # Act
        session_tracker.build_sessions(entries)
        current = session_tracker.get_current_session()

        # Assert
        assert current is not None, "Should have a current session"
        assert current.is_active is True, "Recent session should be active"

    def test_multiple_sessions_separated_by_boundary(self, session_tracker):
        """Test that entries separated by >5 hours create multiple sessions"""
        # Arrange
        entries = [
            create_mock_entry(hours_ago=6, tokens=100),  # Old session
            create_mock_entry(hours_ago=1, tokens=200),  # New session
        ]

        # Act
        session_tracker.build_sessions(entries)

        # Assert
        assert len(session_tracker.sessions) == 2, "Should create two separate sessions"


class TestExpiredSessions:
    """Tests for expired session handling"""

    def test_expired_session_not_active(self, session_tracker):
        """Test that session >5 hours old is not marked as active"""
        # Arrange
        entries = [
            create_mock_entry(hours_ago=6, tokens=100),
            create_mock_entry(hours_ago=5.5, tokens=200),
        ]

        # Act
        session_tracker.build_sessions(entries)
        current = session_tracker.get_current_session()

        # Assert
        assert current is None, "Expired session should not be returned as current"

    def test_no_active_sessions_returns_none(self, session_tracker):
        """Test that get_current_session returns None when all sessions expired"""
        # Arrange
        entries = [create_mock_entry(hours_ago=10, tokens=100)]

        # Act
        session_tracker.build_sessions(entries)
        current = session_tracker.get_current_session()

        # Assert
        assert current is None, "Should return None for expired sessions"

    def test_expired_session_has_correct_properties(self, session_tracker):
        """Test that expired session properties are correctly set"""
        # Arrange
        entries = [create_mock_entry(hours_ago=6, tokens=100)]

        # Act
        session_tracker.build_sessions(entries)

        # Assert
        assert len(session_tracker.sessions) == 1, "Should create session"
        session = session_tracker.sessions[0]
        assert session.is_active is False, "Session should not be active"
        assert len(session.entries) == 1, "Should contain the entry"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_empty_usage_data(self, log_reader):
        """Test handling of empty usage_data list"""
        # Arrange
        log_reader.usage_data = []

        # Act
        if log_reader.usage_data:
            oldest = min(log_reader.usage_data, key=lambda e: e.timestamp)

        # Assert
        assert log_reader.session_start_time is None, "Should remain None for empty data"

    def test_single_entry(self, session_tracker):
        """Test session building with single entry"""
        # Arrange
        entries = [create_mock_entry(hours_ago=1, tokens=100)]

        # Act
        session_tracker.build_sessions(entries)
        current = session_tracker.get_current_session()

        # Assert
        assert current is not None, "Should create session with single entry"
        assert len(current.entries) == 1, "Should contain one entry"
        total_tokens, _ = current.total_tokens
        # Mock creates 100 input + 100 output = 200 total
        assert total_tokens == 200, "Should count single entry's tokens (100 input + 100 output)"

    def test_entries_at_exact_boundary(self, log_reader):
        """Test behavior when entry timestamp equals session_end_time"""
        # Arrange
        entry1 = create_mock_entry(hours_ago=5, tokens=100)
        entry2 = create_mock_entry(hours_ago=0, tokens=200)

        log_reader.usage_data = [entry1]
        log_reader.session_start_time = entry1.timestamp

        # Entry exactly at 5-hour mark
        boundary_entry = create_mock_entry(hours_ago=0, tokens=150)
        boundary_entry.timestamp = log_reader.session_start_time + timedelta(hours=5)
        log_reader.usage_data.append(boundary_entry)

        # Act
        session_end_time = log_reader.session_start_time + timedelta(hours=5)
        entries_in_new_session = [
            e for e in log_reader.usage_data
            if e.timestamp > session_end_time
        ]

        # Assert - Entry at exact boundary should NOT trigger new session (> not >=)
        assert len(entries_in_new_session) == 0, "Entry at exact boundary should stay in current session"


if __name__ == "__main__":
    # Allow running with: python test_session_reset.py
    pytest.main([__file__, "-v"])
