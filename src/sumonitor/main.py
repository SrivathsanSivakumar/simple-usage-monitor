#!/usr/bin/env python3

### Entry point. init pexpect and transfer control to claude

import shutil, pexpect, signal, argparse
from .data.log_reader import LogReader
from .session.session_data import SessionData
from .terminal.terminal_handler import TerminalHandler

def get_args_parser():
    parser = argparse.ArgumentParser(
        prog='sumonitor',
        description='Real-time token and cost monitoring for Claude Code CLI')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
    parser.add_argument('--path', default=shutil.which('claude'), type=str,
                        help='Path to Claude Code installation (default: auto-detect with which)')
    parser.add_argument('--plan', default='pro', type=str, choices=['pro', 'max5', 'max20'],
                        help='Claude plan type (default: pro)')
    return parser

def main():
    parser = get_args_parser()
    args = parser.parse_args()
    
    p = pexpect.spawn(args.path, encoding='utf-8')
    log_reader = LogReader()
    th = TerminalHandler(log_reader=log_reader, pexpect_obj=p, plan=args.plan)

    p.setwinsize(*th.get_terminal_size()) # set terminal size on launch
    signal.signal(signal.SIGWINCH, th.on_resize)
    p.interact()

if __name__ == "__main__":
    main()