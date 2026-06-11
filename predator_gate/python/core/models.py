"""
core/models.py

Immutable data models.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BurnerState:
    is_running:   bool
    is_burning:   bool
    current_slot: int
    fail_count:   int
    last_burn_at: float
    booted_at:    float


@dataclass(frozen=True)
class WipeStats:
    total_wipes:       int
    total_bytes_wiped: int
    cache_flushes:     int
    failed_wipes:      int
    last_wipe_at:      float


@dataclass(frozen=True)
class TokenInfo:
    room_id:    int
    slot:       int
    created_at: float
    consumed:   bool = False
    burned:     bool = False


@dataclass(frozen=True)
class GateStats:
    tokens_issued:   int
    admits_granted:  int
    admits_rejected: int
    burns_triggered: int
    wipe_stats:      Optional[WipeStats] = None
