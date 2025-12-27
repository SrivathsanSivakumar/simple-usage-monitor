### Identify project relating jsonl files and parse them

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from dataclasses import dataclass

# Ref: https://www.claude.com/pricing#api
SONNET_INPUT_TIER_BREAK=200000
SONNET_INPUT_PRICE_LE_200K=3.00
SONNET_INPUT_PRICE_GT_200K=6.00

SONNET_OUTPUT_PRICE_LE_200K=15.00
SONNET_OUTPUT_PRICE_GT_200K=22.50

HAIKU_INPUT_PRICE=1.00
HAIKU_OUTPUT_PRICE=5.00

OPUS_INPUT_PRICE = 5.00 
OPUS_OUTPUT_PRICE = 25.00

def _input_cost_usd(model: str, tokens:int) -> tuple:
    """identifies tier for model and calculates input token pricing

        Args:
            model: model used in session (Sonnet4.5 and Haiku4.5 are supported)
            tokens: input token count

        Returns:
            dollar cost and tier for input tokens
    """
    if "sonnet-4-5" in model:
        if tokens <= SONNET_INPUT_TIER_BREAK:
            tier = "<=200k"  
        else:
            tier = ">200k"

        if tier == "<=200k":
            rate = SONNET_INPUT_PRICE_LE_200K 
        else:
            rate = SONNET_INPUT_PRICE_GT_200K

    elif "haiku-4-5" in model: 
        rate = HAIKU_INPUT_PRICE
        tier = "flat"

    elif "opus-4-5" in model:
        rate = OPUS_INPUT_PRICE
        tier = "flat"

    else:
        return (0.0, "unknown")

    return (tokens/1_000_000)*rate, tier

def _output_cost_usd(model:str, tokens:int) -> tuple:
    """Identifies tier for model and calculates output tokens pricing
    
        Args:
            model: model used in session. (Sonnet4.5 and Haiku4.5 are supported)
            tokens: output token count

        Returns:
            dollar cost and tier for output tokens
    """
    if "sonnet-4-5" in model:
        if tokens <= SONNET_INPUT_TIER_BREAK:
            tier = "<=200k"  
        else:
            tier = ">200k"

        if tier == "<=200k":
            rate = SONNET_OUTPUT_PRICE_LE_200K 
        else:
            rate = SONNET_OUTPUT_PRICE_GT_200K

    elif "haiku-4-5" in model: 
        rate = HAIKU_OUTPUT_PRICE
        tier = "flat"

    elif "opus-4-5" in model:
        rate = OPUS_OUTPUT_PRICE
        tier = "flat"

    else:
        return (0.0, "unknown")

    return (tokens/1_000_000)*rate, tier

@dataclass
class UsageData:
    model: str
    input_tokens: int
    input_tokens_cost: int
    output_tokens: int
    output_tokens_cost: int
    timestamp: datetime

class LogReader:
    """Reads relevant jsonl files and creates a set of valid tokens to use for calculations"""
    def __init__(self):
        # track processed files
        self.processed_entries = set() 
        self.usage_data = []
        self.session_start_time = None

    def get_jsonl_files(self, data_path: Optional[str] = None) -> List[str]:
        """Gets the path of jsonl files relating to the current project
            Args:
                data_path: Path to Claude data directory

            Returns:
                Array of jsonl file paths

            Raises:
                FileNotFoundError: if Claude project directory doesn't exist
        """
        data_path = Path(data_path if data_path else "~/.claude/projects").expanduser()
        
        if not data_path.exists():
            raise FileNotFoundError(
                f"Claude projects directory not found at {data_path}"
            )
        # if path exists read the relevant jsonl files
        return list(data_path.rglob("*.jsonl"))
    

    def parse_json_files(self, hours_back: int = 120) -> List[UsageData]:
        """Parse relevant files only and return a collection of input and output tokens

            Args:
                hours_back: how far back to look for entries (default: 120 hours = 5 days)

            Returns:
                List of objects of data class that contains input and output tokens
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        jsonl_files_path = self.get_jsonl_files()
        for json_file in jsonl_files_path:
            with open(json_file, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    if not line:
                        continue

                    else:
                        data = json.loads(line)
                        message = data.get("message")
                        timestamp = data.get("timestamp")

                        if not timestamp: 
                            continue

                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if timestamp < cutoff_time:
                            continue

                        if isinstance(message, dict):
                            # uniquely identify each request within each message
                            message_id = message.get("id")
                            request_id = data.get("requestId")
                            unique_id = f"{message_id}:{request_id}"

                            if unique_id in self.processed_entries: continue

                            model = message.get("model")
                            usage = message.get("usage")
                            if isinstance(usage, dict):
                                input_tokens = usage.get("input_tokens")
                                output_tokens = usage.get("output_tokens")

                                input_tokens_cost = _input_cost_usd(model, input_tokens)
                                output_tokens_cost = _output_cost_usd(model, output_tokens)
                                user_usage = UsageData(
                                    model=model,
                                    input_tokens=input_tokens,
                                    input_tokens_cost=input_tokens_cost,
                                    output_tokens=output_tokens,
                                    output_tokens_cost=output_tokens_cost,
                                    timestamp=timestamp
                                    )
                                self.usage_data.append(user_usage)
                            self.processed_entries.add(unique_id)

        if self.usage_data:
            if self.session_start_time is None:
                oldest = min(self.usage_data, key=lambda e: e.timestamp)
                self.session_start_time = oldest.timestamp

            session_end_time = self.session_start_time + timedelta(hours=hours_back)
            current_time = datetime.now(timezone.utc)

            # find entries beyond current session
            entries_in_new_session = [e for e in self.usage_data if e.timestamp > session_end_time]

            if entries_in_new_session:
                new_session_earliest = min(entries_in_new_session, key=lambda e: e.timestamp)
                self.usage_data = entries_in_new_session # keep only new session usage data
                self.session_start_time = new_session_earliest.timestamp
            elif current_time > session_end_time:
                # Session expired but no new entries - clear everything
                self.usage_data = []
                self.session_start_time = None

        return self.usage_data
