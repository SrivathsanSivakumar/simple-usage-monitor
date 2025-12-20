### Calculate total usage metrics for session

from typing import List
from data.log_reader import UsageData
from session.session_tracker import SessionTracker

class TotalCalculator:
    """Calculates total usage metrics for session and sends it to TerminalHandler"""
    def __init__(self, usage_data: List[UsageData]):
        self.session_tracker = SessionTracker()
        self.session_tracker.build_sessions(usage_data)

    def calculate_totals(self) -> tuple:
        """Read relevant metrics from UsageData and add the values to sum totals

            Returns:
                total of input tokens, input tokens cost, output tokens and output tokens cost
        """
        current_session = self.session_tracker.get_current_session()
        if not current_session: return ((0, 0.0), (0, 0.0), (0, 0.0))
        # print(current_session.total_input_usage, current_session.total_output_usage, current_session.total_tokens)
        return (current_session.total_input_usage, current_session.total_output_usage, current_session.total_tokens)