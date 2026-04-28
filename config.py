"""
Handles loading and saving user configuration to ~/.postureGuard/config.json.
"""

import json
import os
from typing import Any, Dict

# Default configuration matching SRD section 7
DEFAULT_CONFIG = {
    "calibration": {
        "nose_y_baseline": 0.42,
        "shoulder_midpoint_y_baseline": 0.61,
        "head_to_shoulder_distance_baseline": 0.19,
        "shoulder_width_baseline": 0.28,
        "head_tilt_baseline_degrees": 1.2
    },
    "thresholds": {
        "nose_drop_threshold": 0.07,
        "slouch_threshold_percent": 15,
        "shoulder_asymmetry_threshold": 0.05,
        "head_tilt_threshold_degrees": 15,
        "bad_checks_to_trigger": 2
    },
    "timers": {
        "bad_posture_lock_delay_seconds": 10,
        "sitting_session_minutes": 30,
        "walk_break_minutes": 5,
        "camera_check_interval_seconds": 2
    },
    "ui": {
        "show_debug_overlay": False
    }
}

CONFIG_DIR = os.path.expanduser("~/.postureGuard")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config() -> Dict[str, Any]:
    """
    Load configuration from ~/.postureGuard/config.json.
    Returns the default config if the file does not exist or is corrupt.
    """
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    """
    Save the provided configuration dictionary to ~/.postureGuard/config.json.
    Creates the ~/.postureGuard directory if it doesn't exist.
    """
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Error saving config to {CONFIG_FILE}: {e}")
