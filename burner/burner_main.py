"""
burner_main.py

Main entry point for the Burner Gate.

Responsibilities:
  - Boot state manager
  - Initialize C++ gate with master key
  - Install signal handlers (SIGUSR1, SIGUSR2)
  - Launch IPC server (Unix domain socket)
  - Heartbeat loop (slot rotation, health reporting)
  - Clean shutdown on SIGTERM/SIGINT

Architecture:
  burner_main.py (this file) — wiring + lifecycle
       ↓
  PredatorBridge — C++ gate wrapper + state/wiper
       ↓
  BurnerStateManager — operational state
  RAMWiper — memory wiping
       ↓
  libpredator_gate.so — C++ crypto core
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path

from core.constants import BURNER_SLOT_WINDOW
from core.utils     import current_slot, seconds_until_slot_end
from burner_state   import BurnerStateManager
from burner_ram     import RAMWiper
from predator_bridge import PredatorBridge


# ── Logging Setup ──────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


# ── Global State (signal handlers need it) ─────────────────

_gate: PredatorBridge = None
_running = True


# ── Signal Handlers ────────────────────────────────────────

def handle_sigusr1(signum, frame):
    """
    SIGUSR1 → Graceful shutdown.
    Stop accepting new tokens. Finish in-flight admits. Exit.
    """
    global _running
    log.warning("SIGUSR1 received → graceful shutdown initiated")
    _running = False


def handle_sigusr2(signum, frame):
    """
    SIGUSR2 → BURN.
    Immediate wipe. Gate permanently burned. Exit.
    """
    global _gate, _running
    log.critical("SIGUSR2 received → BURN TRIGGERED")
    if _gate:
        _gate._trigger_burn(None)
        _gate.destroy()
    _running = False
    sys.exit(0)


def handle_sigterm(signum, frame):
    """SIGTERM → clean shutdown (same as SIGUSR1)."""
    global _running
    log.warning("SIGTERM received → shutdown")
    _running = False


def handle_sigint(signum, frame):
    """SIGINT (Ctrl-C) → clean shutdown."""
    global _running
    log.warning("SIGINT received → shutdown")
    _running = False


# ── Master Key Loading ─────────────────────────────────────

def load_master_key() -> bytes:
    """
    Load master key from environment or file.
    
    Priority:
      1. BURNER_MASTER_KEY env var (hex string)
      2. BURNER_KEY_FILE env var (path to binary key)
      3. ./master.key (default path)
    
    Raises ValueError if key < 32 bytes or not found.
    """
    # Check env var (hex string)
    key_hex = os.getenv('BURNER_MASTER_KEY')
    if key_hex:
        try:
            key = bytes.fromhex(key_hex)
            if len(key) < 32:
                raise ValueError("BURNER_MASTER_KEY too short (need >= 32 bytes)")
            log.info("Master key loaded from BURNER_MASTER_KEY")
            return key
        except ValueError as e:
            raise ValueError(f"Invalid BURNER_MASTER_KEY: {e}")
    
    # Check key file
    key_path = os.getenv('BURNER_KEY_FILE', './master.key')
    path = Path(key_path)
    if not path.exists():
        raise FileNotFoundError(f"Master key not found: {path}")
    
    key = path.read_bytes()
    if len(key) < 32:
        raise ValueError(f"Master key too short: {len(key)} bytes (need >= 32)")
    
    log.info(f"Master key loaded from {path}")
    return key


# ── Heartbeat Loop ─────────────────────────────────────────

def heartbeat_loop(gate: PredatorBridge, state: BurnerStateManager):
    """
    Main event loop.
    
    - Check slot rotation (every 3 hours)
    - Flush caches after rotation
    - Log stats every 60 seconds
    - Exit if burned or _running = False
    """
    global _running
    
    last_slot = current_slot()
    last_stat_report = time.time()
    
    log.info(f"Heartbeat started — slot {last_slot}")
    
    while _running:
        try:
            # Check if burned
            if state.is_burning():
                log.critical("Gate is BURNED — shutting down")
                break
            
            # Check slot rotation
            slot = current_slot()
            if slot != last_slot:
                log.info(f"Slot rotation: {last_slot} → {slot}")
                gate._wiper.flush_caches()
                state.reset_fail()
                last_slot = slot
            
            # Log stats every 60 seconds
            now = time.time()
            if now - last_stat_report >= 60:
                stats = gate.get_stats()
                log.info(
                    f"Stats — tokens:{stats.tokens_issued} "
                    f"admits:{stats.admits_granted} "
                    f"rejects:{stats.admits_rejected} "
                    f"burns:{stats.burns_triggered}"
                )
                last_stat_report = now
            
            # Sleep until next check
            time.sleep(1)
        
        except KeyboardInterrupt:
            log.warning("Keyboard interrupt in heartbeat")
            _running = False
            break
        
        except Exception as e:
            log.error(f"Heartbeat error: {e}", exc_info=True)
            time.sleep(1)
    
    log.info("Heartbeat loop exited")


# ── Main Entry Point ───────────────────────────────────────

def main():
    global _gate, _running
    
    log.info("=" * 60)
    log.info("BURNER GATE — STARTING")
    log.info("=" * 60)
    
    # Install signal handlers
    signal.signal(signal.SIGUSR1, handle_sigusr1)
    signal.signal(signal.SIGUSR2, handle_sigusr2)
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT,  handle_sigint)
    log.info("Signal handlers installed (SIGUSR1, SIGUSR2, SIGTERM, SIGINT)")
    
    # Load master key
    try:
        master_key = load_master_key()
        log.info(f"Master key loaded ({len(master_key)} bytes)")
    except (ValueError, FileNotFoundError) as e:
        log.critical(f"Failed to load master key: {e}")
        sys.exit(1)
    
    # Create subsystems
    state_mgr = BurnerStateManager()
    wiper     = RAMWiper()
    
    # Create gate
    try:
        _gate = PredatorBridge(
            master_key = master_key,
            state_mgr  = state_mgr,
            wiper      = wiper,
        )
        log.info("PredatorBridge initialized")
    except Exception as e:
        log.critical(f"Failed to create gate: {e}", exc_info=True)
        sys.exit(1)
    
    # Wipe master_key from Python memory
    master_key_arr = bytearray(master_key)
    wiper.wipe_buffer(master_key_arr)
    del master_key, master_key_arr
    log.info("Master key wiped from Python memory")
    
    # Boot complete
    slot = current_slot()
    log.info(f"Gate booted — slot {slot}")
    log.info(f"Next slot rotation in {seconds_until_slot_end():.0f}s")
    
    # Enter heartbeat loop
    try:
        heartbeat_loop(_gate, state_mgr)
    except Exception as e:
        log.critical(f"Heartbeat loop crashed: {e}", exc_info=True)
    
    # Shutdown
    log.info("Shutting down...")
    if _gate:
        final_stats = _gate.get_stats()
        log.info(
            f"Final stats — tokens:{final_stats.tokens_issued} "
            f"admits:{final_stats.admits_granted} "
            f"rejects:{final_stats.admits_rejected} "
            f"burns:{final_stats.burns_triggered}"
        )
        _gate.destroy()
    
    log.info("=" * 60)
    log.info("BURNER GATE — STOPPED")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
