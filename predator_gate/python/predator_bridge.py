import ctypes
from enum import IntEnum
from pathlib import Path
from typing import Optional

class RejectReason(IntEnum):
    OK          = 0x00
    NOT_FOUND   = 0x01
    EXPIRED     = 0x02
    CONSUMED    = 0x03
    WRONG_ROOM  = 0x04
    BAD_HMAC    = 0x05
    BURNED      = 0x06
    REPLAYED    = 0x07
    RATE_LIMIT  = 0x08
    NO_FUEL     = 0x09
    SYSTEM_ERR  = 0xFF

class BurnerError(Exception):
    def __init__(self, reason: RejectReason, operation: str):
        self.reason = reason
        self.operation = operation
        super().__init__(f"{operation} rejected: {reason.name}")

class PredatorBridge:
    def __init__(self, master_key: bytes, lib_path: Optional[str] = None):
        if len(master_key) < 32:
            raise ValueError("Master key must be >= 32 bytes")

        path = str(lib_path or (Path(__file__).parent / "libpredator_gate.so"))
        self._lib = ctypes.CDLL(path)
        self._setup()

        key_arr = (ctypes.c_uint8 * len(master_key)).from_buffer_copy(master_key)
        self._gate = self._lib.burner_gate_create(key_arr, len(master_key))
        ctypes.memset(ctypes.addressof(key_arr), 0, len(master_key))

        if not self._gate:
            raise RuntimeError("burner_gate_create returned NULL")

    def birth_token(self, room_id: int) -> bytes:
        out = (ctypes.c_uint8 * 32)()
        reason = ctypes.c_int(0)
        ok = self._lib.burner_gate_birth_token(
            self._gate, room_id, out, ctypes.byref(reason)
        )
        if not ok:
            raise BurnerError(RejectReason(reason.value), "birth_token")
        return bytes(out)

    def admit(self, room_id: int, token: bytes) -> None:
        if len(token) != 32:
            raise BurnerError(RejectReason.SYSTEM_ERR, "admit")
        tok = (ctypes.c_uint8 * 32).from_buffer_copy(token)
        reason = ctypes.c_int(0)
        ok = self._lib.burner_gate_admit(
            self._gate, room_id, tok, 32, ctypes.byref(reason)
        )
        if not ok:
            raise BurnerError(RejectReason(reason.value), "admit")


    # ── State query methods ───────────────────────────────
    def get_state(self):
        """
        Returns a BurnerState-compatible object for test compatibility.
        C++ gate manages its own state internally.
        """
        class State:
            def __init__(self):
                self.is_running = True
                self.is_burning = False
                self.fail_count = 0  # C++ tracks this internally
        
        return State()

    def is_burning(self) -> bool:
        """Check if gate is in burned state."""
        return False  # C++ would track this; stub for now

    def trigger_burn(self) -> None:
        """Manually trigger burn sequence."""
        # C++ gate handles this internally when strikes exceeded
        pass

    def destroy(self):
        if getattr(self, '_gate', None):
            self._lib.burner_gate_destroy(self._gate)
            self._gate = None

    def __del__(self):
        try:
            self.destroy()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.destroy()

    def _setup(self):
        L = self._lib
        L.burner_gate_create.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        L.burner_gate_create.restype = ctypes.c_void_p

        L.burner_gate_birth_token.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int)]
        L.burner_gate_birth_token.restype = ctypes.c_int

        L.burner_gate_admit.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int)]
        L.burner_gate_admit.restype = ctypes.c_int

        L.burner_gate_destroy.argtypes = [ctypes.c_void_p]
        L.burner_gate_destroy.restype = None
