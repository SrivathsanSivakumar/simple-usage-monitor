### Calculate total usage metrics for session

from typing import List
from data.log_reader import UsageData


class TotalCalculator:
    """Calculates total usage metrics for session and sends it to TerminalHandler"""
    def __init__(self, session_data: List[UsageData]):
        self.session_data = session_data
        self.input_tokens = 0
        self.input_cost = 0
        self.output_tokens = 0
        self.output_cost = 0
    
    def calculate_totals(self) -> tuple:
        """Read relevant metrics from UsageData and add the values to sum totals

            Returns:
                total of input tokens, input tokens cost, output tokens and output tokens cost
        """
        for sdata in self.session_data:
            if sdata.input_tokens_cost and sdata.output_tokens_cost:
                self.input_tokens += sdata.input_tokens
                self.input_cost += sdata.input_tokens_cost[0]
                self.output_tokens += sdata.output_tokens
                self.output_cost += sdata.output_tokens_cost[0]
        # print(self.input_tokens, self.input_cost, self.output_tokens, self.output_cost)
        return self.input_tokens, self.input_cost, self.output_tokens, self.output_cost

        