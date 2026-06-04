#!/usr/bin/env python3
"""
AiZQuad Lab — Phase 1: Flow Lock
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Locks approved room logic with a
SHA-256 signature so it cannot be
modified without detection.

Usage:
  python3 flow_lock.py lock   <room> <version>
  python3 flow_lock.py verify <room>
  python3 flow_lock.py list
  python3 flow_lock.py unlock <room>

FC_FLOW MESH | Sovereign PEU
Founder: Juan Jaime Rivera Zamorano
"""

import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────

ROOT         = Path(".")
FORGE_ACTIVE = ROOT / "forge" / "active"
FORGE_LOCKED = ROOT / "forge" / "locked"
FORGE_VERS   = ROOT / "forge" / "versions"
SPLIT_INPUT  = ROOT / "splitter" / "input"
SHARED       = ROOT / "shared"
STATE_FILE   = SHARED / "pipeline_state.json"

# ─────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_signature(file_path: Path) -> str:
    """Generate SHA-256 signature of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_dir_signature(dir_path: Path) -> str:
    """Generate SHA-256 signature of an entire directory."""
    sha256 = hashlib.sha256()
    files = sorted(dir_path.rglob("*"))
    for file in files:
        if file.is_file():
            sha256.update(str(file.relative_to(dir_path)).encode())
            with open(file, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
    return sha256.hexdigest()


def load_state() -> dict:
    """Load pipeline state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "phase_1_forge": {"status": "initialized", "locked_rooms": []},
        "phase_2_split": {"status": "initialized", "modules_created": 0},
        "phase_3_sort":  {"status": "initialized", "files_sorted": 0},
        "phase_4_integrate": {"status": "initialized", "rooms_integrated": []},
        "engine_cores": {"active": [], "idle": list(range(1, 9))}
    }


def save_state(state: dict) -> None:
    """Save pipeline state."""
    SHARED.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def print_banner():
    print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════╗
║   AiZQuad Lab — Phase 1: Flow Lock       ║
║   [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH   ║
╚═══════════════════════════════════════════╝{RESET}""")


# ─────────────────────────────────────────────
#  LOCK
# ─────────────────────────────────────────────

def cmd_lock(room: str, version: str) -> int:
    """Lock a room's active logic."""
    print_banner()
    print(f"\n{BOLD}🔒 Locking {room} — version {version}{RESET}\n")

    source_dir = FORGE_ACTIVE / room

    # Validate source exists and has content
    if not source_dir.exists():
        print(f"{RED}✗ No active forge found for {room}{RESET}")
        print(f"{DIM}  Run: make forge ROOM={room}{RESET}")
        return 1

    source_files = list(source_dir.rglob("*"))
    logic_files  = [f for f in source_files if f.is_file()]

    if not logic_files:
        print(f"{RED}✗ No files found in {source_dir}{RESET}")
        print(f"{DIM}  Add logic files first{RESET}")
        return 1

    # Check version not already locked
    lock_file = FORGE_LOCKED / f"{room}.lock.json"
    if lock_file.exists():
        existing = json.loads(lock_file.read_text())
        if existing.get("version") == version:
            print(f"{YELLOW}⚠ {room} version {version} already locked{RESET}")
            print(f"{DIM}  Use a new version: make lock ROOM={room} V=v2{RESET}")
            return 1

    # Create destination directories
    FORGE_LOCKED.mkdir(parents=True, exist_ok=True)
    version_dir = FORGE_VERS / room / version
    version_dir.mkdir(parents=True, exist_ok=True)
    SPLIT_INPUT.mkdir(parents=True, exist_ok=True)

    # Copy to versions archive
    dest_dir = version_dir
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)
    print(f"  {GREEN}✓{RESET} Archived to versions/{room}/{version}/")

    # Copy to splitter input
    split_dest = SPLIT_INPUT / room
    if split_dest.exists():
        shutil.rmtree(split_dest)
    shutil.copytree(source_dir, split_dest)
    print(f"  {GREEN}✓{RESET} Copied to splitter/input/{room}/")

    # Generate signature
    signature = get_dir_signature(source_dir)
    print(f"  {GREEN}✓{RESET} Signature generated")

    # Build lock record
    lock_record = {
        "room":       room,
        "version":    version,
        "locked_at":  datetime.now(timezone.utc).isoformat(),
        "signature":  signature,
        "files":      [str(f.relative_to(source_dir)) for f in logic_files],
        "file_count": len(logic_files),
        "status":     "SOVEREIGN_APPROVED"
    }

    # Write lock file
    lock_file.write_text(json.dumps(lock_record, indent=2))
    print(f"  {GREEN}✓{RESET} Lock file written")

    # Update pipeline state
    state = load_state()
    locked = state.get("phase_1_forge", {}).get("locked_rooms", [])
    if room not in locked:
        locked.append(room)
    state["phase_1_forge"] = {
        "status":       "active",
        "locked_rooms": locked
    }
    save_state(state)
    print(f"  {GREEN}✓{RESET} Pipeline state updated")

    # Print summary
    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  LOCK COMPLETE — SOVEREIGN APPROVED      ║
╚═══════════════════════════════════════════╝{RESET}

  Room     : {CYAN}{room}{RESET}
  Version  : {CYAN}{version}{RESET}
  Files    : {len(logic_files)}
  Signature: {DIM}{signature[:32]}...{RESET}
  Status   : {GREEN}🔒 LOCKED{RESET}

  Next step:
  {DIM}make split ROOM={room}{RESET}
""")
    return 0

# Conceptual implementation
class AISession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.memory = {}
    
    def clock_in(self):
        """Load persistent context from secure storage"""
        self.memory = self.load_from_file(f"{self.user_id}_context.json")
        print("AI clocked in with your project context")
    
    def clock_out(self):
        """Save important context, then wipe volatile memory"""
        self.save_to_file(f"{self.user_id}_context.json", self.memory)
        self.memory.clear()  # Clear active session
        print("Session saved and cleared")
    
    def load_from_file(self, filename):
        # Load encrypted local file (stays on YOUR machine)
        pass
    
    def save_to_file(self, filename, data):
        # Save to YOUR local storage only
        pass
class FounderAIWorkspace:
    
    def __init__(self):
        self.ai = AIAssistant()        # Your K9
        self.human = self            # The Officer (YOU)
        self.trust_level = "PROTECTED"
    
    def clock_in(self):
        """Load YOUR context, YOUR way"""
        self.ai.load_local_context()   # No cloud exposure
        self.ai.set_boundaries()       # AI knows its role
        print("AI is briefed and ready to ASSIST")
    
    def ai_suggests(self, task):
        """AI recommends, human decides"""
        suggestion = self.ai.analyze(task)
        return self.human.approve(suggestion)  # YOU have final say
    
    def clock_out(self):
        """Save what matters, protect the rest"""
        self.ai.save_approved_context()
        self.ai.clear_sensitive_data()
        print("Session secured. Trust maintained.")

    
# ─────────────────────────────────────────────
#  VERIFY
# ─────────────────────────────────────────────

def cmd_verify(room: str) -> int:
    """Verify a room lock has not been tampered with."""
    print_banner()
    print(f"\n{BOLD}🔍 Verifying {room} lock integrity{RESET}\n")

    lock_file = FORGE_LOCKED / f"{room}.lock.json"

    if not lock_file.exists():
        print(f"{RED}✗ No lock found for {room}{RESET}")
        print(f"{DIM}  Run: make lock ROOM={room} V=v1{RESET}")
        return 1

    lock_record = json.loads(lock_file.read_text())

    # Check version dir exists
    version     = lock_record.get("version", "v1")
    version_dir = FORGE_VERS / room / version

    if not version_dir.exists():
        print(f"{RED}✗ Version archive missing: {version_dir}{RESET}")
        return 1

    # Recalculate signature
    current_sig  = get_dir_signature(version_dir)
    original_sig = lock_record.get("signature", "")

    if current_sig == original_sig:
        print(f"  {GREEN}✓{RESET} Signature match")
        print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  INTEGRITY VERIFIED — SOVEREIGN          ║
╚═══════════════════════════════════════════╝{RESET}

  Room     : {CYAN}{room}{RESET}
  Version  : {CYAN}{version}{RESET}
  Locked   : {lock_record.get('locked_at', '?')}
  Files    : {lock_record.get('file_count', '?')}
  Signature: {DIM}{original_sig[:32]}...{RESET}
  Status   : {GREEN}✅ UNTAMPERED{RESET}
""")
        return 0
    else:
        print(f"""
{RED}{BOLD}╔═══════════════════════════════════════════╗
║  INTEGRITY FAILED — TAMPERING DETECTED   ║
╚═══════════════════════════════════════════╝{RESET}

  Room     : {CYAN}{room}{RESET}
  Version  : {CYAN}{version}{RESET}
  Expected : {DIM}{original_sig[:32]}...{RESET}
  Got      : {DIM}{current_sig[:32]}...{RESET}
  Status   : {RED}❌ COMPROMISED{RESET}

  The locked version has been modified.
  Re-forge and re-lock if changes are approved.
""")
        return 1


# ─────────────────────────────────────────────
#  LIST
# ─────────────────────────────────────────────

def cmd_list() -> int:
    """List all locked rooms."""
    print_banner()
    print(f"\n{BOLD}📋 Locked Rooms{RESET}\n")

    if not FORGE_LOCKED.exists():
        print(f"  {DIM}No rooms locked yet{RESET}")
        print(f"  {DIM}Run: make forge ROOM=room-0{RESET}")
        return 0

    lock_files = list(FORGE_LOCKED.glob("*.lock.json"))

    if not lock_files:
        print(f"  {DIM}No rooms locked yet{RESET}")
        return 0

    print(f"  {'ROOM':<12} {'VERSION':<10} {'FILES':<8} {'LOCKED AT':<28} SIGNATURE")
    print(f"  {'─'*12} {'─'*10} {'─'*8} {'─'*28} {'─'*16}")

    for lf in sorted(lock_files):
        record = json.loads(lf.read_text())
        room   = record.get("room", lf.stem)
        ver    = record.get("version", "?")
        files  = record.get("file_count", "?")
        locked = record.get("locked_at", "?")[:19].replace("T", " ")
        sig    = record.get("signature", "?")[:16] + "..."
        print(f"  {GREEN}🔒{RESET} {room:<10} {ver:<10} {files:<8} {locked:<28} {DIM}{sig}{RESET}")

    print()
    return 0


# ─────────────────────────────────────────────
#  UNLOCK
# ─────────────────────────────────────────────

def cmd_unlock(room: str) -> int:
    """Remove lock from a room (requires confirmation)."""
    print_banner()
    print(f"\n{YELLOW}{BOLD}⚠ Unlocking {room}{RESET}\n")

    lock_file = FORGE_LOCKED / f"{room}.lock.json"

    if not lock_file.exists():
        print(f"{YELLOW}⚠ {room} is not locked{RESET}")
        return 0

    confirm = input(f"  Type '{room}' to confirm unlock: ").strip()
    if confirm != room:
        print(f"{RED}✗ Aborted — confirmation did not match{RESET}")
        return 1

    lock_file.unlink()

    # Update state
    state = load_state()
    locked = state.get("phase_1_forge", {}).get("locked_rooms", [])
    if room in locked:
        locked.remove(room)
    state["phase_1_forge"]["locked_rooms"] = locked
    save_state(state)

    print(f"  {GREEN}✓{RESET} {room} unlocked")
    print(f"  {DIM}Files preserved in forge/versions/{room}/{RESET}\n")
    return 0


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def usage():
    print(f"""
{CYAN}Usage:{RESET}
  python3 flow_lock.py lock   <room> <version>
  python3 flow_lock.py verify <room>
  python3 flow_lock.py list
  python3 flow_lock.py unlock <room>

{CYAN}Examples:{RESET}
  python3 flow_lock.py lock   room-2 v1
  python3 flow_lock.py verify room-2
  python3 flow_lock.py list
  python3 flow_lock.py unlock room-2
""")


def main() -> int:
    args = sys.argv[1:]

    if not args:
        usage()
        return 0

    command = args[0].lower()

    if command == "lock":
        if len(args) < 3:
            print(f"{RED}✗ Usage: flow_lock.py lock <room> <version>{RESET}")
            return 1
        return cmd_lock(args[1], args[2])

    elif command == "verify":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_lock.py verify <room>{RESET}")
            return 1
        return cmd_verify(args[1])

    elif command == "list":
        return cmd_list()

    elif command == "unlock":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_lock.py unlock <room>{RESET}")
            return 1
        return cmd_unlock(args[1])

    else:
        print(f"{RED}✗ Unknown command: {command}{RESET}")
        usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
