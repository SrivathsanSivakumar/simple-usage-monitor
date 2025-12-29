"""Tests for session_tracker.py - Session building, windowing, and aggregation"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from session.session_tracker import SessionTracker, Session
from data.log_reader import UsageData


class TestSessionBuilding:
    """Test build_sessions() creates correct session windows"""

    def test_creates_single_session_from_recent_entries(self, mock_usage_entry):
        """Entries within 5 hours should create single session"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=1, input_tokens=200, output_tokens=100),
            mock_usage_entry(hours_ago=0.5, input_tokens=300, output_tokens=150)
        ]

        tracker.build_sessions(entries)

        assert len(tracker.sessions) == 1
        assert len(tracker.sessions[0].entries) == 3

    def test_creates_multiple_sessions_separated_by_5h_window(self, mock_usage_entry):
        """Entries >5 hours apart should create separate sessions"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=10, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=9.5, input_tokens=200, output_tokens=100),
            mock_usage_entry(hours_ago=2, input_tokens=300, output_tokens=150),
            mock_usage_entry(hours_ago=1, input_tokens=400, output_tokens=200)
        ]

        tracker.build_sessions(entries)

        assert len(tracker.sessions) == 2
        assert len(tracker.sessions[0].entries) == 2  # Old session: 10h, 9.5h
        assert len(tracker.sessions[1].entries) == 2  # New session: 2h, 1h

    def test_handles_empty_entries_list(self):
        """Empty entries should result in no sessions"""
        tracker = SessionTracker()
        tracker.build_sessions([])

        assert len(tracker.sessions) == 0

    def test_handles_single_entry(self, mock_usage_entry):
        """Single entry should create single-entry session"""
        tracker = SessionTracker()
        entry = mock_usage_entry(hours_ago=1, input_tokens=100, output_tokens=50)

        tracker.build_sessions([entry])

        assert len(tracker.sessions) == 1
        assert len(tracker.sessions[0].entries) == 1
        assert tracker.sessions[0].entries[0] == entry

    def test_out_of_order_entries_sorted_chronologically(self, mock_usage_entry):
        """Entries should be sorted by timestamp before processing"""
        tracker = SessionTracker()
        # Create entries in non-chronological order
        entry1 = mock_usage_entry(hours_ago=1, input_tokens=100, output_tokens=50)
        entry2 = mock_usage_entry(hours_ago=3, input_tokens=200, output_tokens=100)
        entry3 = mock_usage_entry(hours_ago=2, input_tokens=300, output_tokens=150)

        tracker.build_sessions([entry1, entry2, entry3])

        # Should all be in same session, sorted chronologically
        assert len(tracker.sessions) == 1
        assert tracker.sessions[0].entries[0] == entry2  # 3h ago (earliest)
        assert tracker.sessions[0].entries[1] == entry3  # 2h ago
        assert tracker.sessions[0].entries[2] == entry1  # 1h ago (latest)


class TestSessionStartTimeCorrection:
    """Test that session start_time is set to earliest entry timestamp"""

    def test_start_time_matches_earliest_entry(self, mock_usage_entry):
        """Session start_time should be set to earliest entry"""
        tracker = SessionTracker()
        entry_early = mock_usage_entry(hours_ago=3, input_tokens=100, output_tokens=50)
        entry_late = mock_usage_entry(hours_ago=1, input_tokens=200, output_tokens=100)

        tracker.build_sessions([entry_late, entry_early])

        session = tracker.sessions[0]
        assert session.start_time == entry_early.timestamp

    def test_session_end_time_based_on_corrected_start(self, mock_usage_entry):
        """Session end_time should be earliest_timestamp + 5 hours"""
        tracker = SessionTracker()
        entry_early = mock_usage_entry(hours_ago=4, input_tokens=100, output_tokens=50)
        entry_late = mock_usage_entry(hours_ago=1, input_tokens=200, output_tokens=100)

        tracker.build_sessions([entry_late, entry_early])

        session = tracker.sessions[0]
        expected_end = entry_early.timestamp + timedelta(hours=5)
        assert session.end_time == expected_end

    def test_single_entry_start_time(self, mock_usage_entry):
        """Single-entry session should have start_time = entry timestamp"""
        tracker = SessionTracker()
        entry = mock_usage_entry(hours_ago=2, input_tokens=100, output_tokens=50)

        tracker.build_sessions([entry])

        session = tracker.sessions[0]
        assert session.start_time == entry.timestamp


class TestSessionActivity:
    """Test is_active property and get_active_sessions()"""

    def test_recent_session_is_active(self, mock_usage_entry):
        """Session within 5-hour window should be active"""
        tracker = SessionTracker()
        entry = mock_usage_entry(hours_ago=1, input_tokens=100, output_tokens=50)

        tracker.build_sessions([entry])

        session = tracker.sessions[0]
        assert session.is_active is True

    def test_expired_session_not_active(self, mock_usage_entry):
        """Session >5 hours old should not be active"""
        tracker = SessionTracker()
        entry = mock_usage_entry(hours_ago=6, input_tokens=100, output_tokens=50)

        tracker.build_sessions([entry])

        session = tracker.sessions[0]
        assert session.is_active is False

    def test_get_active_sessions_filters_correctly(self, mock_usage_entry):
        """get_active_sessions() should return only active sessions"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=10, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=2, input_tokens=200, output_tokens=100)
        ]

        tracker.build_sessions(entries)
        active_sessions = tracker.get_active_sessions()

        assert len(active_sessions) == 1
        assert active_sessions[0].is_active is True

    def test_get_active_sessions_returns_empty_when_all_expired(self, mock_usage_entry):
        """get_active_sessions() should return empty list when all expired"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=10, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=6, input_tokens=200, output_tokens=100)
        ]

        tracker.build_sessions(entries)
        active_sessions = tracker.get_active_sessions()

        assert len(active_sessions) == 0


class TestCurrentSession:
    """Test get_current_session() returns most recent active session"""

    def test_returns_most_recent_active_session(self, mock_usage_entry):
        """get_current_session() should return last active session"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=20, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=10, input_tokens=200, output_tokens=100),
            mock_usage_entry(hours_ago=2, input_tokens=300, output_tokens=150)
        ]

        tracker.build_sessions(entries)
        current = tracker.get_current_session()

        assert current is not None
        assert current.is_active is True
        # Should be the session with 2h ago entry
        assert current.entries[-1].input_tokens == 300

    def test_returns_none_when_no_active_sessions(self, mock_usage_entry):
        """get_current_session() should return None when all expired"""
        tracker = SessionTracker()
        entries = [mock_usage_entry(hours_ago=10, input_tokens=100, output_tokens=50)]

        tracker.build_sessions(entries)
        current = tracker.get_current_session()

        assert current is None

    def test_returns_none_when_no_sessions(self):
        """get_current_session() should return None when no sessions"""
        tracker = SessionTracker()
        tracker.build_sessions([])

        current = tracker.get_current_session()

        assert current is None


class TestTokenAggregation:
    """Test session token counting properties"""

    def test_total_input_usage_sums_all_entries(self, mock_usage_entry):
        """total_input_usage should sum input tokens from all entries"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, input_tokens=1000, output_tokens=500),
            mock_usage_entry(hours_ago=1, input_tokens=2000, output_tokens=1000),
            mock_usage_entry(hours_ago=0.5, input_tokens=3000, output_tokens=1500)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        assert session.total_input_usage == 6000

    def test_total_output_usage_sums_all_entries(self, mock_usage_entry):
        """total_output_usage should sum output tokens from all entries"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, input_tokens=1000, output_tokens=500),
            mock_usage_entry(hours_ago=1, input_tokens=2000, output_tokens=1000),
            mock_usage_entry(hours_ago=0.5, input_tokens=3000, output_tokens=1500)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        assert session.total_output_usage == 3000

    def test_total_tokens_combines_input_and_output(self, mock_usage_entry):
        """total_tokens should return input + output tokens"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, input_tokens=1000, output_tokens=500),
            mock_usage_entry(hours_ago=1, input_tokens=2000, output_tokens=1000)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        # 1000 + 2000 + 500 + 1000 = 4500
        assert session.total_tokens == 4500

    def test_empty_session_zero_tokens(self):
        """Session with no entries should have zero tokens"""
        session = Session(
            session_id="test",
            start_time=datetime.now(timezone.utc),
            entries=[]
        )

        assert session.total_input_usage == 0
        assert session.total_output_usage == 0
        assert session.total_tokens == 0


class TestCostAggregation:
    """Test total_costs property calculation"""

    def test_total_costs_sums_all_entries(self, mock_usage_entry):
        """total_costs should sum cost field from all entries"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, cost=1.50),
            mock_usage_entry(hours_ago=1, cost=2.25),
            mock_usage_entry(hours_ago=0.5, cost=0.75)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        assert session.total_costs == pytest.approx(4.50)

    def test_total_costs_zero_for_empty_session(self):
        """Empty session should have total_costs = 0.0"""
        session = Session(
            session_id="test",
            start_time=datetime.now(timezone.utc),
            entries=[]
        )

        assert session.total_costs == 0.0

    def test_total_costs_handles_fractional_cents(self, mock_usage_entry):
        """total_costs should handle fractional cent precision"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2, cost=0.001234),
            mock_usage_entry(hours_ago=1, cost=0.005678)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        assert session.total_costs == pytest.approx(0.006912)


class TestMessagesCount:
    """Test total_messages property"""

    def test_total_messages_counts_entries(self, mock_usage_entry):
        """total_messages should count number of entries in session"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=2),
            mock_usage_entry(hours_ago=1),
            mock_usage_entry(hours_ago=0.5)
        ]

        tracker.build_sessions(entries)
        session = tracker.sessions[0]

        assert session.total_messages == 3

    def test_total_messages_zero_for_empty_session(self):
        """Empty session should have total_messages = 0"""
        session = Session(
            session_id="test",
            start_time=datetime.now(timezone.utc),
            entries=[]
        )

        assert session.total_messages == 0


class TestSessionIDGeneration:
    """Test generate_session_id() creates unique IDs"""

    def test_generates_id_from_timestamp(self):
        """Session ID should be generated from timestamp"""
        tracker = SessionTracker()
        timestamp = datetime(2025, 12, 29, 10, 30, 45, tzinfo=timezone.utc)

        session_id = tracker.generate_session_id(timestamp)

        assert session_id == "session_20251229_103045"

    def test_different_timestamps_different_ids(self):
        """Different timestamps should generate different IDs"""
        tracker = SessionTracker()
        ts1 = datetime(2025, 12, 29, 10, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2025, 12, 29, 11, 0, 0, tzinfo=timezone.utc)

        id1 = tracker.generate_session_id(ts1)
        id2 = tracker.generate_session_id(ts2)

        assert id1 != id2


class TestBuildSessionsMutation:
    """Test that build_sessions() properly resets state"""

    def test_multiple_calls_replace_sessions(self, mock_usage_entry):
        """Calling build_sessions() twice should replace sessions"""
        tracker = SessionTracker()

        # First call
        tracker.build_sessions([mock_usage_entry(hours_ago=1)])
        assert len(tracker.sessions) == 1

        # Second call with different data
        tracker.build_sessions([mock_usage_entry(hours_ago=2), mock_usage_entry(hours_ago=1)])
        assert len(tracker.sessions) == 1
        assert len(tracker.sessions[0].entries) == 2

    def test_empty_call_clears_sessions(self, mock_usage_entry):
        """Calling build_sessions([]) should clear all sessions"""
        tracker = SessionTracker()

        # First call with data
        tracker.build_sessions([mock_usage_entry(hours_ago=1)])
        assert len(tracker.sessions) == 1

        # Second call with empty list
        tracker.build_sessions([])
        assert len(tracker.sessions) == 0


class TestEdgeCases:
    """Edge cases and boundary conditions"""

    def test_entry_exactly_at_5h_boundary(self, mock_usage_entry):
        """Entry exactly at 5-hour mark should be in same session"""
        tracker = SessionTracker()

        # Create first entry
        first_entry = mock_usage_entry(hours_ago=5, input_tokens=100, output_tokens=50)
        # Create second entry exactly 5 hours later (at the boundary)
        boundary_timestamp = first_entry.timestamp + timedelta(hours=5)
        second_entry = mock_usage_entry(hours_ago=0, input_tokens=200, output_tokens=100)
        second_entry.timestamp = boundary_timestamp

        tracker.build_sessions([first_entry, second_entry])

        # Should create separate sessions since entry.timestamp > session.end_time
        # end_time is start + 5h, so entry at exactly end_time + 0 is > end_time? No.
        # Actually, entry at exactly 5h is NOT > end_time, so should be same session
        # Wait, let me check the logic: elif entry.timestamp > current_session.end_time
        # If end_time = start + 5h, and entry is at start + 5h, then entry == end_time, not >
        # So should be in same session
        assert len(tracker.sessions) == 1

    def test_multiple_sessions_with_gaps(self, mock_usage_entry):
        """Multiple sessions with varying gaps should be handled correctly"""
        tracker = SessionTracker()
        entries = [
            mock_usage_entry(hours_ago=30, input_tokens=100, output_tokens=50),
            mock_usage_entry(hours_ago=20, input_tokens=200, output_tokens=100),
            mock_usage_entry(hours_ago=10, input_tokens=300, output_tokens=150),
            mock_usage_entry(hours_ago=2, input_tokens=400, output_tokens=200),
            mock_usage_entry(hours_ago=1, input_tokens=500, output_tokens=250)
        ]

        tracker.build_sessions(entries)

        # Should create 4 sessions: 30h, 20h, 10h, (2h+1h)
        assert len(tracker.sessions) == 4
        assert len(tracker.sessions[3].entries) == 2  # Last session has 2 entries
