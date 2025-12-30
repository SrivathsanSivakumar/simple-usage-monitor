### Calculate total usage metrics for session

import datetime
from typing import List
from sumonitor.data.log_reader import UsageData
from sumonitor.data.pricing import _get_plan_limits
from sumonitor.session.session_tracker import SessionTracker
from datetime import datetime, timezone

class SessionData:
    """Calculates total usage data along with session relevant data like time left before reset"""
    def __init__(self, usage_data: List[UsageData], plan: str):
        self.plan_limits = _get_plan_limits(plan)

        self.session_tracker = SessionTracker()
        self.session_tracker.build_sessions(usage_data)
        self.current_session = self.session_tracker.get_current_session()
        
    def total_tokens(self) -> int:
        """Read relevant metrics from UsageData and add the values to sum totals

            Returns:
                total of input tokens and output tokens
        """
        if not self.current_session: return 0.0
        return self.current_session.total_tokens
    
    def session_reset_time(self) -> str:
        """Calculate how much time is left before session resets

            Returns:
                Time left in user readable form
        """

        if self.current_session is None:
            return "No active session"

        current_session_end = self.current_session.end_time
        time_left = current_session_end - datetime.now(timezone.utc)
        total_seconds = int(time_left.total_seconds())
        # convert to human readable format
        if total_seconds < 0:
            return 'Session expired - waiting to start a new conversation'
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
          return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def session_messages(self) -> int:
        """Returns how many messages have been sent in session"""
        if self.current_session is None:
            return 0
        return self.current_session.total_messages
    
    def total_cost(self) -> float:
        """Returns total dollar cost usage"""
        if self.current_session is None:
            return 0.0
        return self.current_session.total_costs
    