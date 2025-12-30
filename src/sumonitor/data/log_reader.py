### Identify project relating jsonl files and parse them

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sumonitor.data.pricing import _get_pricing
from dataclasses import dataclass

def _calculate_total_cost(model: str, input_tokens: int, output_tokens: int,
                          cache_write_tokens: int, cache_read_tokens: int) -> float:
    """Apply relevant pricing per token for relevant Claude model

        Args:
            model: Model used for message
            input_tokens: input token usage for message
            output_tokens: output token usage for message
            cache_write_tokens: cached write tokens for message
            cache_read_tokens: cached read tokens for message

        Returns:
            Sum total of dollar cost associated with each token type
    """
    model_pricing = _get_pricing(model)

    # Determine tier based on total input tokens for sonnet
    total_input_tokens = input_tokens + cache_write_tokens + cache_read_tokens

    input_rate = model_pricing.input_base
    output_rate = model_pricing.output_base
    cache_write_rate = model_pricing.cache_write
    cache_read_rate = model_pricing.cache_read

    # Override with tier rates if threshold exceeded
    if model_pricing.tiered and model_pricing.tier_break and total_input_tokens > model_pricing.tier_break:
        input_rate = model_pricing.input_tier
        output_rate = model_pricing.output_tier
        cache_write_rate = model_pricing.cache_write_tier
        cache_read_rate = model_pricing.cache_read_tier

    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate
    cache_write_cost = (cache_write_tokens / 1_000_000) * cache_write_rate
    cache_read_cost = (cache_read_tokens / 1_000_000) * cache_read_rate

    return input_cost + output_cost + cache_write_cost + cache_read_cost

@dataclass
class UsageData:
    model: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    cost: float
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

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

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
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)
                            cache_write_tokens = usage.get("cache_creation_input_tokens", 0)
                            cache_read_tokens = usage.get("cache_read_input_tokens", 0)

                            total_cost = _calculate_total_cost(
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cache_write_tokens=cache_write_tokens,
                                cache_read_tokens=cache_read_tokens,
                            )

                            user_usage = UsageData(
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cache_write_tokens=cache_write_tokens,
                                cache_read_tokens=cache_read_tokens,
                                cost=total_cost,
                                timestamp=timestamp
                                )
                            self.usage_data.append(user_usage)
                        self.processed_entries.add(unique_id)
        return self.usage_data