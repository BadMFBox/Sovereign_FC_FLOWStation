"""burner_gate.py — Token gate (GateLock)"""
import os
import hmac as _hmac
import hashlib
import threading
from enum import Enum
from core.constants import BURNER_MAX_STRIKES, BURNER_MAX_TOKENS_PER_SLOT
from core.utils import current_slot, slot_expiry


class RejectReason(Enum):
    REPLAY      = "REPLAY"
    WRONG_ROOM  = "WRONG_ROOM"
    SLOT_FULL   = "SLOT_FULL"
    EXPIRED     = "EXPIRED"
    BURNING     = "BURNING"
    STRIKE_BURN = "STRIKE_BURN"


class GateLock:
    def __init__(self, state_mgr, wiper, master_key: bytes = None):
        self._state_mgr  = state_mgr
        self._wiper      = wiper
        self._master_key = bytearray(master_key if master_key else os.urandom(32))
        self._lock       = threading.Lock()
        self._tokens     = {}
        self._strikes    = 0

    def birth_token(self, room_id: int) -> bytes:
        if self._state_mgr.is_burning():
            raise ValueError(RejectReason.BURNING.value)
        slot   = current_slot()
        expiry = slot_expiry(slot)
        nonce  = os.urandom(16)
        msg    = (slot.to_bytes(8, "big") + room_id.to_bytes(4, "big")
                  + nonce + expiry.to_bytes(8, "big"))
        token  = _hmac.new(bytes(self._master_key), msg, hashlib.sha256).digest()
        with self._lock:
            bucket = self._tokens.setdefault(slot, set())
            if len(bucket) >= BURNER_MAX_TOKENS_PER_SLOT:
                raise ValueError(RejectReason.SLOT_FULL.value)
            bucket.add(token)
        return token

    def admit(self, token: bytes, room_id: int) -> bool:
        if self._state_mgr.is_burning():
            return False
        slot = current_slot()
        with self._lock:
            bucket = self._tokens.get(slot, set())
            if token not in bucket:
                self._strikes += 1
                if self._strikes >= BURNER_MAX_STRIKES:
                    self._state_mgr.trigger_burn()
                return False
            bucket.discard(token)
        return True

    def live_token_count(self) -> int:
        slot = current_slot()
        with self._lock:
            return len(self._tokens.get(slot, set()))

    def destroy(self):
        with self._lock:
            self._wiper.wipe_buffer(self._master_key)
            self._tokens.clear()
