import json

def load_params(json_path):
    with open(json_path, "r") as f:
        return json.load(f)

