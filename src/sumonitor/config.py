import json
import os

class Config:
    """Stores user set values automatically so they dont have to repeat commands 
    everytime they invoke sumonitor"""
    def __init__(self):
        self.path = os.path.expanduser('~/.config/sumonitor/config.json')

    def load_config(self) -> dict:
        """Reads the config file and returns its content as a dict

            Returns:
                dict containing config for the CLI
        """
        try:
            with open(self.path, 'r') as config:
                return json.load(config)
        except (FileNotFoundError, json.JSONDecodeError):
            return {} 

    def save_config(self, config: dict) -> None:
        """Writes config to config file and creates the file if it doesnt exist

            Args:
                config: config dictionary containing values that need to be updated
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as cfg:
            json.dump(config, cfg)