import os
import json

def load_config():
    # Path to config.json inside the config folder
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.json")

    # Read and parse JSON
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()
