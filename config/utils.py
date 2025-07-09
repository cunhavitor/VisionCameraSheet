import json

def load_params(json_path):
    with open(json_path, "r") as f:
        return json.load(f)

def center_window(window, width=800, height=600):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.geometry(f"{width}x{height}+{x}+{y}")