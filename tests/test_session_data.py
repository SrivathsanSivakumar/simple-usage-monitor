"""Tests for session_data.py - Session metrics calculation and formatting"""

import pytest
from datetime import datetime, timezone, timedelta
from freezegun import freeze_time

from sumonitor.session.session_data import SessionData
from sumonitor.data.pricing import PlanLimits


class TestInitialization:
    """Test SessionData initialization and plan limit loading"""

    def test_initializes_with_pro_plan(self, mock_usage_entry):
        """Should load PRO plan limits correctly"""
        data = SessionData([mock_usage_entry()], plan="pro")

        assert data.plan_limits.tokens == 19_000
        assert data.plan_limits.cost == 18.00
        assert data.plan_limits.messages == 250

    def test_initializes_with_max5_plan(self, mock_usage_entry):
        """Should load MAX5 plan limits correctly"""
        data = SessionData([mock_usage_entry()], plan="max5")

        assert data.plan_limits.tokens == 88_000
        assert data.plan_limits.cost == 35.00
        assert data.plan_limits.messages == 1000

    def test_initializes_with_max20_plan(self, mock_usage_entry):
        """Should load MAX20 plan limits correctly"""
        data = SessionData([mock_usage_entry()], plan="max20")

        assert data.plan_limits.tokens == 220_000
        assert data.plan_limits.cost == 140.00
        assert data.plan_limits.messages == 2000

    def test_unknown_plan_defaults_to_pro(self, mock_usage_entry):
        """Unknown plan should fall back to PRO"""
        data = SessionData([mock_usage_entry()], plan="invalid-plan")

        assert data.plan_limits.tokens == 19_000

    def test_case_insensitive_plan_names(self, mock_usage_entry):
        """Plan names should be case-insensitive"""
        data = SessionData([mock_usage_entry()], plan="PRO")

        assert data.plan_limits.tokens == 19_000

    def test_builds_sessions_on_init(self, mock_usage_entry):
        """Should call SessionTracker.build_sessions() during init"""
        entries = [
            mock_usage_entry(hours_ago=1),
            mock_usage_entry(hours_ago=0.5)
        ]
        data = SessionData(entries, plan="pro")

        assert data.current_session is not None
        assert data.current_session.total_messages == 2


class TestTotalTokens:
    """Test total_tokens() method"""

    def test_returns_sum_of_input_and_output(self, mock_usage_entry):
        """total_tokens should return input + output from current session"""
        entries = [
            mock_usage_entry(hours_ago=1, input_tokens=1000, output_tokens=500),
            mock_usage_entry(hours_ago=0.5, input_tokens=2000, output_tokens=1000)
        ]
        data = SessionData(entries, plan="pro")

        # 1000 + 500 + 2000 + 1000 = 4500
        assert data.total_tokens() == 4500

    def test_returns_zero_when_no_active_session(self):
        """Should return 0 when no active session"""
        data = SessionData([], plan="pro")

        assert data.total_tokens() == 0

    def test_returns_zero_when_session_expired(self, mock_usage_entry):
        """Should return 0 when only expired sessions exist"""
        entries = [mock_usage_entry(hours_ago=10, input_tokens=1000, output_tokens=500)]
        data = SessionData(entries, plan="pro")

        assert data.total_tokens() == 0


class TestTotalCost:
    """Test total_cost() method"""

    def test_returns_sum_of_entry_costs(self, mock_usage_entry):
        """Should sum cost fields from all entries in session"""
        entries = [
            mock_usage_entry(hours_ago=2, cost=1.50),
            mock_usage_entry(hours_ago=1, cost=2.25),
            mock_usage_entry(hours_ago=0.5, cost=0.75)
        ]
        data = SessionData(entries, plan="pro")

        assert data.total_cost() == pytest.approx(4.50)

    def test_returns_zero_when_no_active_session(self):
        """Should return 0.0 when no active session"""
        data = SessionData([], plan="pro")

        assert data.total_cost() == 0.0

    def test_returns_float_not_int(self, mock_usage_entry):
        """total_cost() should return float even for whole number costs"""
        entries = [mock_usage_entry(hours_ago=1, cost=2.00)]
        data = SessionData(entries, plan="pro")

        cost = data.total_cost()
        assert isinstance(cost, float)
        assert cost == pytest.approx(2.00)


class TestSessionMessages:
    """Test session_messages() method"""

    def test_returns_message_count(self, mock_usage_entry):
        """Should return number of messages in current session"""
        entries = [
            mock_usage_entry(hours_ago=2),
            mock_usage_entry(hours_ago=1),
            mock_usage_entry(hours_ago=0.5)
        ]
        data = SessionData(entries, plan="pro")

        assert data.session_messages() == 3

    def test_returns_zero_when_no_active_session(self):
        """Should return 0 when no active session"""
        data = SessionData([], plan="pro")

        assert data.session_messages() == 0


class TestSessionResetTime:
    """Test session_reset_time() formatting"""

    @freeze_time("2025-12-29 10:00:00")
    def test_formats_hours_and_minutes(self, mock_usage_entry):
        """Should format as 'Xh Ym' when hours remaining"""
        # Create entry 4 hours ago, session ends at 10:00 + 1h = 11:00 (1h from now)
        # Entry at 06:00, session ends at 11:00, current time 10:00 = 1h 0m left
        entry = mock_usage_entry(hours_ago=4)
        data = SessionData([entry], plan="pro")

        assert data.session_reset_time() == "1h 0m"

    @freeze_time("2025-12-29 10:00:00")
    def test_formats_hours_and_minutes_with_partial(self, mock_usage_entry):
        """Should format hours and minutes correctly"""
        # Entry 3.5 hours ago: 06:30, ends at 11:30, current 10:00 = 1h 30m left
        entry = mock_usage_entry(hours_ago=3.5)
        data = SessionData([entry], plan="pro")

        assert data.session_reset_time() == "1h 30m"

    @freeze_time("2025-12-29 10:59:30")
    def test_formats_minutes_and_seconds(self, mock_usage_entry):
        """Should format as 'Xm Ys' when less than 1 hour"""
        # Entry 4.5 hours ago: 06:29:30, ends at 11:29:30, current 10:59:30 = 30m 0s left
        entry = mock_usage_entry(hours_ago=4.5)
        data = SessionData([entry], plan="pro")

        assert data.session_reset_time() == "30m 0s"

    @freeze_time("2025-12-29 10:59:30")
    def test_formats_seconds_only(self, mock_usage_entry):
        """Should format as 'Xs' when less than 1 minute"""
        # Entry 4 hours 59 minutes 30 seconds ago, ends in 30s
        entry_time = datetime.now(timezone.utc) - timedelta(hours=4, minutes=59, seconds=30)
        entry = mock_usage_entry(hours_ago=0)
        entry.timestamp = entry_time
        data = SessionData([entry], plan="pro")

        result = data.session_reset_time()
        assert result == "30s"

    def test_returns_message_when_no_session(self):
        """Should return 'No active session' when no session"""
        data = SessionData([], plan="pro")

        assert data.session_reset_time() == "No active session"

    @freeze_time("2025-12-29 12:00:00")
    def test_returns_expired_message_when_past_end(self, mock_usage_entry):
        """Should return 'No active session' when session expired"""
        # Entry 6 hours ago, session ended 1 hour ago
        entry = mock_usage_entry(hours_ago=6)
        data = SessionData([entry], plan="pro")

        result = data.session_reset_time()
        assert result == "No active session"


class TestCurrentSessionReference:
    """Test that current_session is correctly set"""

    def test_current_session_set_on_init(self, mock_usage_entry):
        """current_session should be set during initialization"""
        entries = [mock_usage_entry(hours_ago=1)]
        data = SessionData(entries, plan="pro")

        assert data.current_session is not None
        assert data.current_session.is_active is True

    def test_current_session_none_when_no_data(self):
        """current_session should be None when no data"""
        data = SessionData([], plan="pro")

        assert data.current_session is None

    def test_current_session_none_when_expired(self, mock_usage_entry):
        """current_session should be None when all sessions expired"""
        entries = [mock_usage_entry(hours_ago=10)]
        data = SessionData(entries, plan="pro")

        assert data.current_session is None


class TestPlanLimitsIntegration:
    """Test integration with plan limits"""

    def test_plan_limits_accessible(self, mock_usage_entry):
        """plan_limits should be accessible as attribute"""
        data = SessionData([mock_usage_entry()], plan="pro")

        # Should be accessible without parentheses
        limits = data.plan_limits
        assert isinstance(limits, PlanLimits)
        assert limits.tokens == 19_000

    def test_different_plans_different_limits(self, mock_usage_entry):
        """Different plans should have different limits"""
        entry = mock_usage_entry()

        data_pro = SessionData([entry], plan="pro")
        data_max5 = SessionData([entry], plan="max5")
        data_max20 = SessionData([entry], plan="max20")

        assert data_pro.plan_limits.tokens == 19_000
        assert data_max5.plan_limits.tokens == 88_000
        assert data_max20.plan_limits.tokens == 220_000


class TestEdgeCases:
    """Edge cases and boundary conditions"""

    def test_handles_multiple_sessions(self, mock_usage_entry):
        """Should only consider current (most recent active) session"""
        entries = [
            mock_usage_entry(hours_ago=10, input_tokens=1000, output_tokens=500),
            mock_usage_entry(hours_ago=2, input_tokens=2000, output_tokens=1000),
            mock_usage_entry(hours_ago=1, input_tokens=3000, output_tokens=1500)
        ]
        data = SessionData(entries, plan="pro")

        # Should only count last 2 entries (current session): 2000 + 1000 + 3000 + 1500
        assert data.total_tokens() == 7500

    def test_single_entry_session(self, mock_usage_entry):
        """Should handle session with single entry"""
        entry = mock_usage_entry(hours_ago=1, input_tokens=1000, output_tokens=500, cost=1.50)
        data = SessionData([entry], plan="pro")

        assert data.total_tokens() == 1500
        assert data.total_cost() == pytest.approx(1.50)
        assert data.session_messages() == 1

    @freeze_time("2025-12-29 10:00:00")
    def test_session_at_exact_expiry(self, mock_usage_entry):
        """Session at exact expiry time should return 'No active session'"""
        # Entry exactly 5 hours ago
        entry = mock_usage_entry(hours_ago=5)
        data = SessionData([entry], plan="pro")

        # Session end_time is start + 5h, so exactly at current time
        # is_active checks: datetime.now(timezone.utc) < end_time
        # If now == end_time, then False (not active)
        result = data.session_reset_time()
        assert result == "No active session"

    def test_very_recent_entry_shows_almost_5h(self, mock_usage_entry):
        """Very recent entry should show close to 5 hours remaining"""
        # Entry 1 minute ago
        entry = mock_usage_entry(hours_ago=1/60)  # 1 minute
        data = SessionData([entry], plan="pro")

        result = data.session_reset_time()
        assert result.startswith("4h")

    def test_session_tracker_accessible(self, mock_usage_entry):
        """session_tracker should be accessible for advanced usage"""
        entries = [mock_usage_entry(hours_ago=1)]
        data = SessionData(entries, plan="pro")

        assert data.session_tracker is not None
        assert len(data.session_tracker.sessions) >= 1
