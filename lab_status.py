#!/usr/bin/env python3
"""
AiZQuad Lab — Live Status Dashboard
See everything. Both rooms. Full pipeline.
FC_FLOW MESH | Sovereign PEU
"""

import json
import os
from pathlib import Path
from datetime import datetime

LAB_ROOT = Path(".")

# ANSI colors
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
DIM     = "\033[2m"

def print_header():
    print(f"""
{CYAN}{BOLD}
╔═══════════════════════════════════════════╗
║           AIZQUAD LAB STATUS             ║
║  [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH    ║
║  [ 4 ]  ◈  [ 3 ]  Sovereign PEU         ║
╚═══════════════════════════════════════════╝
{RESET}""")

def check_phase(phase_path: Path, phase_name: str):
    """Check status of a pipeline phase."""
    if not phase_path.exists():
        print(f"  {RED}✗{RESET} {phase_name:<20} {DIM}not initialized{RESET}")
        return

    items = list(phase_path.rglob("*"))
    files = [i for i in items if i.is_file()]
    print(f"  {GREEN}✓{RESET} {phase_name:<20} {len(files)} files")

def check_rooms():
    """Check status of all integration rooms."""
    rooms = {
        "room-0": "Sovereign",
        "room-1": "CypheReign",
        "room-2": "Lawgic",
        "room-3": "Retribution",
        "room-4": "Sniper",
        "room-5": "The Forge"
    }

    print(f"\n{BOLD}  MESH ROOMS{RESET}")
    for folder, name in rooms.items():
        room_path = LAB_ROOT / "integration" / folder
        locked_path = LAB_ROOT / "forge" / "locked" / f"{folder}.lock.json"

        status = f"{RED}◯ empty{RESET}"
        if room_path.exists():
            files = list(room_path.rglob("*.cpp"))
            if files:
                status = f"{GREEN}● {len(files)} modules{RESET}"
            else:
                status = f"{YELLOW}◌ initialized{RESET}"

        lock_status = ""
        if locked_path.exists():
            lock_status = f" {CYAN}🔒 LOCKED{RESET}"

        print(f"    {folder} {DIM}|{RESET} {name:<15} {status}{lock_status}")

def check_engine():
    """Check 8 core engine status."""
    print(f"\n{BOLD}  8 CORE ENGINE{RESET}")
    cores = list(range(1, 9))
    active = []

    for core in cores:
        core_path = LAB_ROOT / "engine" / f"core-{core}"
        if core_path.exists():
            files = list(core_path.rglob("*"))
            if [f for f in files if f.is_file()]:
                active.append(str(core))

    bar = ""
    for core in cores:
        if str(core) in active:
            bar += f"{GREEN}[{core}]{RESET}"
        else:
            bar += f"{DIM}[{core}]{RESET}"

    print(f"    {bar}")

def check_lab_rooms():
    """Check human and AI room status."""
    print(f"\n{BOLD}  LAB ROOMS{RESET}")

    human_notes = LAB_ROOT / ".lab" / "human-room" / "notes.md"
    ai_notes    = LAB_ROOT / ".lab" / "ai-room" / "notes.md"
    chat_log    = LAB_ROOT / "shared" / "chat_log.md"

    print(f"  {CYAN}YOUR ROOM{RESET}")
    if human_notes.exists():
        lines = human_notes.read_text().strip().split("\n")
        last = lines[-1] if lines else "empty"
        print(f"    Last note: {DIM}{last[:50]}{RESET}")
    else:
        print(f"    {DIM}No notes yet{RESET}")

    print(f"  {CYAN}AI ROOM{RESET}")
    if ai_notes.exists():
        lines = ai_notes.read_text().strip().split("\n")
        last = lines[-1] if lines else "empty"
        print(f"    Last note: {DIM}{last[:50]}{RESET}")
    else:
        print(f"    {DIM}No notes yet{RESET}")

    if chat_log.exists():
        size = chat_log.stat().st_size
        print(f"  {CYAN}CHAT LOG{RESET}  {DIM}{size} bytes{RESET}")

def main():
    print_header()

    print(f"{BOLD}  PIPELINE PHASES{RESET}")
    check_phase(LAB_ROOT / "forge",       "Phase 1 — Forge")
    check_phase(LAB_ROOT / "splitter",    "Phase 2 — Split")
    check_phase(LAB_ROOT / "sorter",      "Phase 3 — Sort")
    check_phase(LAB_ROOT / "integration", "Phase 4 — Integrate")

    check_rooms()
    check_engine()
    check_lab_rooms()

    print(f"\n{DIM}  Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"\n{CYAN}  The mesh holds. Sovereign. Always.{RESET}\n")

if __name__ == "__main__":
    main()
