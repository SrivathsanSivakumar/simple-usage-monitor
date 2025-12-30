"""Shared pytest fixtures and configuration for all tests"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock

from sumonitor.data.log_reader import UsageData, LogReader
from sumonitor.session.session_tracker import SessionTracker, Session
from sumonitor.data.pricing import PlanLimits, ModelPricing


@pytest.fixture
def mock_usage_entry():
    """Factory fixture for creating UsageData entries with configurable parameters

    Example:
        entry = mock_usage_entry(hours_ago=2, input_tokens=500, cost=0.025)
    """
    def _create(hours_ago=0,
                input_tokens=100,
                output_tokens=50,
                cache_write=0,
                cache_read=0,
                cost=0.015,
                model="claude-sonnet-4-5-20250929"):
        timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return UsageData(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write,
            cache_read_tokens=cache_read,
            cost=cost,
            timestamp=timestamp
        )
    return _create


@pytest.fixture
def temp_jsonl_dir(tmp_path):
    """Create temporary directory structure mimicking Claude projects directory

    Returns:
        Path to temporary projects directory
    """
    projects_dir = tmp_path / ".claude" / "projects" / "test-project"
    projects_dir.mkdir(parents=True)
    return projects_dir


@pytest.fixture
def mock_pexpect():
    """Mock pexpect subprocess for terminal handler tests

    Returns:
        MagicMock with typical pexpect attributes
    """
    mock = MagicMock()
    mock.closed = False
    mock.setwinsize = Mock()
    return mock


@pytest.fixture
def pro_plan_limits():
    """PRO plan limits for testing

    Returns:
        PlanLimits instance for Pro plan
    """
    return PlanLimits(tokens=19_000, cost=18.00, messages=250)


@pytest.fixture
def max5_plan_limits():
    """MAX5 plan limits for testing

    Returns:
        PlanLimits instance for Max5 plan
    """
    return PlanLimits(tokens=88_000, cost=35.00, messages=1000)


@pytest.fixture
def max20_plan_limits():
    """MAX20 plan limits for testing

    Returns:
        PlanLimits instance for Max20 plan
    """
    return PlanLimits(tokens=220_000, cost=140.00, messages=2000)


@pytest.fixture
def log_reader():
    """Create fresh LogReader instance for each test

    Returns:
        LogReader instance with clean state
    """
    return LogReader()


@pytest.fixture
def session_tracker():
    """Create fresh SessionTracker instance for each test

    Returns:
        SessionTracker instance with empty sessions list
    """
    return SessionTracker()
