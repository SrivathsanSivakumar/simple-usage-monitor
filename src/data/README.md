### Data retrieval logic for claude code

 - `log_reader.py` reads the relevant jsonl files and retrives the relevant fields and returns a dict
 - `cost_calculator.py` calculates the dollar cost of input and output tokens based on Anthropic's pricing table and passes to TerminalHandler to display in terminal 