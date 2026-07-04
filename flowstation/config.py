"""flowstation.config

Holds configuration constants and helpers loaded from environment or local JSON.
This is a minimal stub to organize constants referenced by FlowStation-v1.1.0-FC_FLOW.py.

TODO: add any additional constants or runtime overrides you need.
"""
from typing import Dict
import os

# Network defaults mirrored from FlowStation-v1.1.0-FC_FLOW.py
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WS_PORT = int(os.getenv("WS_PORT", "8081"))

# Feature toggles / mode defaults
DEV_MODE = os.getenv("FLOWSTATION_DEV", "0") == "1"

# Example default ROOMs mapping (keeps behaviour non-breaking)
DEFAULT_ROOMS = {
    "room_0": "SovereignFuel",
    "room_1": "LoginLock",
    "room_2": "EvoFuse",
    "room_3": "PassPatrol",
    "room_4": "FlowControl",
    "room_5": "AiZquad",
}


def load_local_config(path: str) -> Dict:
    """Load optional JSON config (placeholder).

    Returns an empty dict if file missing.
    """
    import json
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
