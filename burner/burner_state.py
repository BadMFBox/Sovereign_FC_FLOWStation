import time
import threading
from core.models import BurnerState
from core.utils import current_slot, slot_expiry

class BurnerStateManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_running = False
        self._is_burning = False
        self._fail_count = 0
        self._last_burn = 0.0
        self._booted_at = 0.0

    def boot(self):
        with self._lock:
            if self._is_running:
                raise RuntimeError("Already running")
            self._is_running = True
            self._booted_at = time.time()

    def shutdown(self):
        with self._lock:
            self._is_running = False

    def get_state(self):
        with self._lock:
            return BurnerState(
                is_running=self._is_running,
                is_burning=self._is_burning,
                current_slot=current_slot(),
                fail_count=self._fail_count,
                last_burn_at=self._last_burn,
                booted_at=self._booted_at
            )

    def is_running(self):
        with self._lock:
            return self._is_running

    def is_burning(self):
        with self._lock:
            return self._is_burning

    def get_current_slot(self):
        return current_slot()

    def get_slot_expiry(self):
        return slot_expiry(current_slot())

    def increment_fail(self):
        with self._lock:
            self._fail_count += 1
            return self._fail_count

    def reset_fail(self):
        with self._lock:
            self._fail_count = 0

    def trigger_burn(self):
        with self._lock:
            self._is_burning = True
            self._last_burn = time.time()
