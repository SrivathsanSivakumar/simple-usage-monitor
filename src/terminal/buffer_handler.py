### handles user input from terminal

class BufferHandler:
    """Handler for cleaning and managing user input"""

    def __init__(self) -> None:
        self.buffer = '' # to log user input

    def handle_enter(self) -> None:
        """Clear the buffer on enter and refresh token count"""
        self.buffer = ""
    
    def handle_backspace(self) -> None:
        """Remove last char from buffer on backspace"""
        if self.buffer:
            self.buffer = self.buffer[:-1]

    def clean_usr_input(self, usr_input) -> str:
        """Takes encoded user input from terminal and cleans it. Removes enter, 
            backspace, arrow keys etc. Preserves new line

            Args:
                usr_input: decoded user input from terminal session

            Returns:
                Cleaned decoded string that contains only the text from user. 
        """
        # BACKSPACE=('KEY_BACKSPACE', '\b', '\x7f')
        # ENTER=('KEY_ENTER', '\r')
        # FOCUS_SEQUENCE = ('\x1b[I', '\x1b[O')

        decoded_inp = usr_input.decode('utf-8')

        match decoded_inp:
            # backspace
            case 'KEY_BACKSPACE' | '\b' | '\x7f': 
                self.handle_backspace()

            # enter
            case 'KEY_ENTER'| '\r':
                self.handle_enter()
            
            # focus sequence
            case '\x1b[I' | '\x1b[O':
                pass

            # filtered user input
            case _:
                self.buffer += decoded_inp

        return self.buffer
    
    def calculate_tokens(self, usr_input):
        """Get user input from claude code and calculate token and price

            Args:
                usr_input: real-time relay of what user types into claude code

            Returns:
                user input back to claude to continue session
        """
        # call to clean user input on each keystroke
        self.clean_usr_input(usr_input)
        return usr_input
