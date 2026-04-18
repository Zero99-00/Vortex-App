import os

def get_asset_path(filename="robot.png"):
    # This is models/logic_units/
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Go UP to models, then DOWN to panels/assets
    full_path = os.path.abspath(os.path.join(base_path, "..", "panels", "assets", filename))
    
    if os.path.exists(full_path):
        return full_path
    
    print(f"⚠️ Asset Warning: Could not find {full_path}")
    return None

import sys
import os

def get_base_path():
    """Gets the absolute path to the root folder, works for Dev and PyInstaller .exe"""
    try:
        # If running as a PyInstaller .exe, it extracts to a temp folder _MEIPASS
        return sys._MEIPASS
    except Exception:
        # If running as a normal Python script, step up from models/panels/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.dirname(current_dir)
        return os.path.dirname(models_dir)

def get_image_path(filename):
    return os.path.join(get_base_path(), "images", filename)