"""
core/utils.py

Shared utility functions.
"""

import time
from core.constants import BURNER_SLOT_WINDOW


def current_slot() -> int:
    """Current 3-hour slot number."""
    return int(time.time() // BURNER_SLOT_WINDOW)


def slot_expiry(slot: int) -> float:
    """Unix timestamp when the given slot ends."""
    return float((slot + 1) * BURNER_SLOT_WINDOW)


def seconds_until_slot_end() -> float:
    """Seconds remaining in current slot."""
    return slot_expiry(current_slot()) - time.time()
