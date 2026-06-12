import os
import gc
import mmap
import threading
import time
from core.constants import BURNER_WIPE_PASSES, DROP_CACHES_PATH
from core.models import WipeStats

class RAMWiper:
    def __init__(self):
        self._lock = threading.Lock()
        self._s = {
            "total_wipes": 0,
            "total_bytes_wiped": 0,
            "cache_flushes": 0,
            "failed_wipes": 0,
            "last_wipe_at": 0.0
        }

    def wipe_buffer(self, buf):
        try:
            size = len(buf)
            if size == 0:
                return True
            if isinstance(buf, bytearray):
                for p in range(BURNER_WIPE_PASSES):
                    if p == BURNER_WIPE_PASSES - 1:
                        for i in range(size):
                            buf[i] = 0
                    else:
                        rnd = os.urandom(size)
                        for i in range(size):
                            buf[i] = rnd[i]
            elif isinstance(buf, memoryview):
                if buf.readonly:
                    return False
                for p in range(BURNER_WIPE_PASSES):
                    buf[:] = bytes(size) if p == BURNER_WIPE_PASSES - 1 else os.urandom(size)
            elif isinstance(buf, mmap.mmap):
                for p in range(BURNER_WIPE_PASSES):
                    buf.seek(0)
                    buf.write(bytes(size) if p == BURNER_WIPE_PASSES - 1 else os.urandom(size))
                buf.flush()
            else:
                return False
            with self._lock:
                self._s["total_wipes"] += 1
                self._s["total_bytes_wiped"] += size
                self._s["last_wipe_at"] = time.monotonic()
            return True
        except Exception:
            with self._lock:
                self._s["failed_wipes"] += 1
            return False

    def wipe_object(self, obj):
        try:
            if isinstance(obj, dict):
                for v in list(obj.values()):
                    if isinstance(v, bytearray):
                        self.wipe_buffer(v)
                obj.clear()
                return True
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, bytearray):
                        self.wipe_buffer(item)
                    obj[i] = None
                obj.clear()
                return True
            elif hasattr(obj, "__dict__"):
                for k, v in list(obj.__dict__.items()):
                    if isinstance(v, bytearray):
                        self.wipe_buffer(v)
                    obj.__dict__[k] = None
                return True
            return False
        except Exception:
            return False

    def flush_caches(self):
        try:
            for gen in range(3):
                gc.collect(gen)
            try:
                os.sync()
            except Exception:
                pass
            try:
                with open(DROP_CACHES_PATH, "w") as f:
                    f.write("3\n")
            except Exception:
                pass
            with self._lock:
                self._s["cache_flushes"] += 1
            return True
        except Exception:
            return False

    def burn_all(self):
        for _ in range(5):
            gc.collect()
        self.flush_caches()

    def get_stats(self):
        with self._lock:
            return WipeStats(**self._s)

    def reset_stats(self):
        with self._lock:
            for k in self._s:
                self._s[k] = 0 if k != "last_wipe_at" else 0.0
