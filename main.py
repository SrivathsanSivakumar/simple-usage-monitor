#!/usr/bin/env python3

### Entry point. init pexpect and transfer control to claude

import shutil, pexpect, os, sys, signal
sys.path.insert(1, os.path.join(sys.path[0], ''))
from data.log_reader import LogReader
from data.total_calculator import TotalCalculator
from terminal_handler import TerminalHandler

def main():
    CLAUDE_BIN = shutil.which('claude')
    if not CLAUDE_BIN:
        print("Error: Claude Code not found. Please install it or point CLAUDE_BIN at correct path")
        
    p = pexpect.spawn(CLAUDE_BIN, encoding='utf-8')
    log_reader = LogReader()
    th = TerminalHandler(log_reader=log_reader, pexpect_obj=p)

    p.setwinsize(*th.get_terminal_size()) # set terminal size on launch
    signal.signal(signal.SIGWINCH, th.on_resize)
    p.interact()

if __name__ == "__main__":
    main()