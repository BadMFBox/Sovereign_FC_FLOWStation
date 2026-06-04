#!/usr/bin/env python3
"""
FlowStation — Phase 1 Lock Tool
Room Zero approval gate.
Once locked, nothing changes without
Room Zero signature.
"""

import json
import hashlib
import datetime
from pathlib import Path

FORGE_PATH = Path("forge")
LOCKED_PATH = FORGE_PATH / "locked"
VERSIONS_PATH = FORGE_PATH / "versions"

def lock_room(room_name: str, version: str) -> dict:
    """
    Lock a room's logic after Room Zero approval.
    Creates a tamper-evident signature.
    """
    version_file = VERSIONS_PATH / room_name / f"{version}.py"
    
    if not version_file.exists():
        raise FileNotFoundError(
            f"Version {version} not found for {room_name}"
        )
    
    # Read the logic
    logic = version_file.read_text()
    
    # Create sovereign signature
    signature = hashlib.sha256(logic.encode()).hexdigest()
    
    # Build lock record
    lock_record = {
        "room": room_name,
        "version": version,
        "locked_at": datetime.datetime.utcnow().isoformat(),
        "signature": signature,
        "approved_by": "room-zero",
        "status": "LOCKED"
    }
    
    # Write locked version
    LOCKED_PATH.mkdir(parents=True, exist_ok=True)
    lock_file = LOCKED_PATH / f"{room_name}.lock.json"
    lock_file.write_text(json.dumps(lock_record, indent=2))
    
    # Copy logic to locked
    locked_logic = LOCKED_PATH / f"{room_name}.py"
    locked_logic.write_text(logic)
    
    print(f"✅ {room_name} LOCKED")
    print(f"   Version  : {version}")
    print(f"   Signature: {signature[:16]}...")
    print(f"   Status   : SOVEREIGN APPROVED")
    
    return lock_record


def verify_lock(room_name: str) -> bool:
    """
    Verify a locked room has not been tampered with.
    """
    lock_file = LOCKED_PATH / f"{room_name}.lock.json"
    locked_logic = LOCKED_PATH / f"{room_name}.py"
    
    if not lock_file.exists():
        print(f"❌ {room_name} — No lock found")
        return False
    
    record = json.loads(lock_file.read_text())
    current_sig = hashlib.sha256(
        locked_logic.read_text().encode()
    ).hexdigest()
    
    if current_sig == record["signature"]:
        print(f"✅ {room_name} — Lock VERIFIED. Sovereign.")
        return True
    else:
        print(f"🚨 {room_name} — LOCK BROKEN. Tampering detected.")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: flow_lock.py [lock|verify] [room] [version]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "lock":
        room = sys.argv[2]
        version = sys.argv[3]
        lock_room(room, version)
    
    elif command == "verify":
        room = sys.argv[2]
        verify_lock(room)
