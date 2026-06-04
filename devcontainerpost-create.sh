#!/bin/bash
set -e

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   AiZQuad Lab - Post-Create Setup        ║"
echo "║   [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH   ║"
echo "║   [ 4 ]  ◈  [ 3 ]                       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# Install build essentials
echo "🔧 Installing build essentials..."
sudo apt-get install -y -qq \
    build-essential \
    gcc \
    g++ \
    cmake \
    make \
    git \
    curl \
    wget \
    nano \
    vim \
    gdb \
    lldb \
    valgrind \
    clang \
    clang-format \
    clang-tidy \
    tree \
    htop \
    jq

# Install Python dev tools
echo "🐍 Installing Python development tools..."
python3 -m pip install --upgrade pip setuptools wheel --quiet
python3 -m pip install --quiet \
    pytest \
    pytest-cov \
    pytest-asyncio \
    black \
    ruff \
    mypy \
    ipython \
    jupyter \
    rich

# Create AiZQuad Lab directory structure
echo "🏗️  Creating AiZQuad Lab structure..."

# Lab configuration
mkdir -p .lab/{ai-room,human-room}
mkdir -p .lab/ai-room/{suggestions,drafts}
mkdir -p .lab/human-room/{approved,rejected}

# Pipeline phases
mkdir -p forge/{active,versions,locked}
mkdir -p splitter/{input,output}
mkdir -p sorter/{headers,sources}

# Integration rooms
mkdir -p integration/{room-0,room-1,room-2,room-3,room-4,room-5,sovereign-arch-core}
for room in integration/room-{0..5}; do
    mkdir -p $room/{src,include,tests}
done

# 8 Core Engine
mkdir -p engine/core-{1..8}

# Shared workspace
mkdir -p shared

# Tools
mkdir -p tools

# Create initial session files
echo "📝 Creating session files..."

# Human room notes
cat > .lab/human-room/notes.md << 'EOF'
# Your Lab Notes

Session started: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Today's Goals
- 

## Decisions Made
- 

## Next Steps
- 

EOF

# AI room notes
cat > .lab/ai-room/notes.md << 'EOF'
# AI Lab Notes

Session started: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Suggestions Pending
- 

## Work In Progress
- 

## Completed
- 

EOF

# Chat log
cat > shared/chat_log.md << 'EOF'
# AiZQuad Lab — Session Log

**Started:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

---

EOF

# Decisions log
cat > shared/decisions.md << 'EOF'
# AiZQuad Lab — Decision Log

Track all major decisions made during the session.

---

EOF

# Pipeline state
cat > shared/pipeline_state.json << 'EOF'
{
  "session_id": "",
  "started_at": "",
  "phase_1_forge": {
    "status": "initialized",
    "locked_rooms": []
  },
  "phase_2_split": {
    "status": "initialized",
    "modules_created": 0
  },
  "phase_3_sort": {
    "status": "initialized",
    "files_sorted": 0
  },
  "phase_4_integrate": {
    "status": "initialized",
    "rooms_integrated": []
  },
  "engine_cores": {
    "active": [],
    "idle": [1, 2, 3, 4, 5, 6, 7, 8]
  }
}
EOF

# Lab config
cat > .lab/config.json << 'EOF'
{
  "lab_name": "AiZQuad Lab",
  "project": "Sovereign PEU",
  "version": "0.1.0",
  "mode": "collaborative",
  "ai_enabled": true,
  "auto_sync": true,
  "session_log": "shared/chat_log.md",
  "pipeline_phases": [
    "forge",
    "split",
    "sort",
    "integrate"
  ],
  "rooms": [
    "room-0",
    "room-1",
    "room-2",
    "room-3",
    "room-4",
    "room-5"
  ],
  "engine_cores": 8
}
EOF

# Install lab status tool
echo "📊 Installing lab status tool..."
cat > tools/lab_status.py << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
AiZQuad Lab — Live Status Dashboard
See everything. Both rooms. Full pipeline.
FC_FLOW MESH | Sovereign PEU
"""

import json
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
    
    state_file = LAB_ROOT / "shared" / "pipeline_state.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
        active = state.get("engine_cores", {}).get("active", [])
    else:
        active = []

    bar = ""
    for core in range(1, 9):
        if core in active:
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
        lines = [l for l in human_notes.read_text().strip().split("\n") if l.strip() and not l.startswith("#")]
        last = lines[-1] if lines else "empty"
        print(f"    Last: {DIM}{last[:50]}{RESET}")
    else:
        print(f"    {DIM}No notes yet{RESET}")

    print(f"  {CYAN}AI ROOM{RESET}")
    if ai_notes.exists():
        lines = [l for l in ai_notes.read_text().strip().split("\n") if l.strip() and not l.startswith("#")]
        last = lines[-1] if lines else "empty"
        print(f"    Last: {DIM}{last[:50]}{RESET}")
    else:
        print(f"    {DIM}No notes yet{RESET}")

    if chat_log.exists():
        size = chat_log.stat().st_size
        lines = len(chat_log.read_text().split("\n"))
        print(f"  {CYAN}CHAT LOG{RESET}  {DIM}{lines} lines ({size} bytes){RESET}")

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
PYTHON_EOF

chmod +x tools/lab_status.py

# Create .clang-format for C++ formatting
cat > .clang-format << 'EOF'
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
AllowShortFunctionsOnASingleLine: None
AlwaysBreakAfterReturnType: None
BreakBeforeBraces: Attach
EOF

# Git configuration
echo "🔗 Configuring git..."
git config --global init.defaultBranch main
git config --global core.editor "code --wait"
git config --global pull.rebase false

# Make tools executable
chmod +x tools/*.py 2>/dev/null || true

echo ""
echo "✅ AiZQuad Lab setup complete!"
echo ""
echo "📋 Available Commands:"
echo "   make help          - Show all commands"
echo "   make lab-status    - View full lab status"
echo "   make forge         - Start Phase 1 (Forge)"
echo "   make build         - Build all C++ modules"
echo "   make test          - Run tests"
echo ""
echo "🤖 AI Collaboration:"
echo "   GitHub Copilot Chat - Ctrl+Shift+I (or Cmd+Shift+I)"
echo "   Terminal            - Ctrl+\` (backtick)"
echo ""
echo "📦 The lab is ready. Let's build sovereign systems."
echo ""


#chmod +x .devcontainer/post-create.sh
