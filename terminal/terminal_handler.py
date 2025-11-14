### Manages the terminal and fetches user input to pass to backend

### Consider starting a new thread to write the overlay separately

import os, sys, fcntl, termios, struct
sys.path.insert(1, os.path.join(sys.path[0], ''))
from terminal.buffer_handler import BufferHandler
from tokens.token_cost_estimator import count_tokens, input_cost_usd;
import threading, time

CLAUDE_BIN = os.getenv('CLAUDE_BIN', '/opt/homebrew/bin/claude')

class TerminalHandler:
    """Handler for managing terminal and drawing overlays"""
    
    def __init__(self, buffer_handler: BufferHandler, pexpect_obj) -> None:
        self.in_alt_screen = False # to know when to draw in terminal        
        self.buffer_handler = buffer_handler
        self.p = pexpect_obj

        self.overlay_thread = threading.Thread(target=self.draw_overlay, daemon=True)
        self.overlay_thread.start()
        self.overlay_thread.join()

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
        """Pass user input to backend and get token and dollar cost

            Returns:
                Formatted string that contains (Model | Token cost | $ cost)
        """
        usr_input = self.buffer_handler.buffer
        if usr_input:
            tokens = count_tokens(usr_input)
            dollar_cost, tier = input_cost_usd(tokens)
            return f"Tokens: {tokens} | Cost: ${dollar_cost:.6f} | Tier: {tier}"
        return "Type to start..."
        
    def draw_overlay(self):
        # can you just get the final string here? for now use a hardcoded string and deal with it later
        text = self.get_overlay_data()

        # get terminal dimensions to get to last row
        rows, cols = self.get_terminal_size()

        if text:
            text = text[:cols]

            # cursor manipulation and adding text
            overlay_bytes = (
                # b'\x1b[0J' +
                '\x1b[s'            # save cursor position
                f'\x1b[{rows}B' +   # move to last row
                '\x1b[2K' +         # clear the entire line
                text +              # write the text onto the line
                '\x1b[u'            # move cursor to saved position
            )
            sys.stdout.write(overlay_bytes)
            sys.stdout.flush()

        threading.Timer(0.2, self.draw_overlay).start()


    def overlay(self, buffer_handler: BufferHandler, data) -> bytes:
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

        # in alt screen
        if '\x1b[I'.encode('utf-8') in data:
            self.in_alt_screen = True

        # in our screen
        if '\x1b[O'.encode('utf-8') in data:
            self.in_alt_screen = False

        return data