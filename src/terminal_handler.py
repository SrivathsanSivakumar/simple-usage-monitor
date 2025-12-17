### Manages the terminal and displays usage data for current session

import os, sys, fcntl, termios, struct
import time

from data.log_reader import LogReader
sys.path.insert(1, os.path.join(sys.path[0], ''))
import threading
from data.total_calculator import TotalCalculator

class TerminalHandler:
    """Handler for managing terminal and drawing overlays"""
    
    def __init__(self, log_reader: LogReader, pexpect_obj) -> None:
        self.in_alt_screen = False # to know when to draw in terminal        
        self.p = pexpect_obj
        self.log_reader = log_reader
        self.overlay_thread = threading.Thread(target=self.draw_overlay, daemon=True)
        self.overlay_thread.start()

    def get_terminal_size(self) -> int:
        """Get terminal size

            Returns: 
                rows, columns -- terminal dimensions
        """
        s = struct.pack("HHHH", 0, 0, 0, 0)
        a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s))
        rows, cols = a[0], a[1]
        return rows, cols

    def on_resize(self, sig, _) -> None:
        """Fetch new terminal size on resize
        
            Args:
                sig: signal for change (SIGWINCH)
        """
        global p
        if not self.p.closed:
            self.p.setwinsize(*self.get_terminal_size())

    def get_overlay_data(self) -> str:
        """Fetch total usage metrics for the current session

            Returns:
                Formatted string that contains (Model | Input tokens, cost | Output tokens, cost)
        """
        usage_data = self.log_reader.parse_json_files()
        total_calculator = TotalCalculator(usage_data=usage_data)
        usage_data = total_calculator.calculate_totals()
        if usage_data:
            input_tokens, input_cost = usage_data[0][0], usage_data[0][1]
            output_tokens, output_cost = usage_data[1][0], usage_data[1][1]
            total_tokens, total_cost = usage_data[2][0], usage_data[2][1]
            return (
                f"In: {input_tokens} tokens, ${input_cost:.6f} | " +
                f"Out: {output_tokens} tokens, ${output_cost:.6f} | " +
                f"Total: {total_tokens} tokens, ${total_cost:.6f}"
            )
        return ""
        
    def draw_overlay(self):
        """Filter that adds overlay to the bottom of terminal

            Returns:
                Text in bottom line of terminal describing costs of the current input
        """
        ### ANSI CODES:
        ### ESC is \x1b in hex. So ESC 7 will be \x1b7 to save cursor position.
        ### ESC[#B to move cursor down # lines
        ### ESC 7 save cursor position
        ### ESC 8 mvoe cursor to last saved position
        ### ref https://stackoverflow.com/questions/11023929/using-the-alternate-screen-in-a-bash-script
        ### ref https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797

        while not self.p.closed:
            text = self.get_overlay_data()

            # get terminal dimensions to get to last row
            rows, cols = self.get_terminal_size()

            if text:
                text = text[:cols]

                # cursor manipulation and adding text
                overlay_bytes = (
                    # b'\x1b[0J' +
                    '\x1b[s'             # save cursor position
                    f'\x1b[{rows};1H' +  # move to last row
                    '\x1b[K' +           # clear the entire line
                    text +               # write the text onto the line
                    '\x1b[u'             # move cursor to saved position
                )
                sys.stdout.write(overlay_bytes)
                sys.stdout.flush()

            time.sleep(0.75)