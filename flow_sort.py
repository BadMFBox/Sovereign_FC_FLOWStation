#!/usr/bin/env python3
"""
AiZQuad Lab — Phase 3: Flow Sort
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Takes split modules and organizes them
into a clean, sovereign Unix file structure.

Every file has a place.
Every place has a purpose.
The mesh stays navigable forever.

Usage:
  python3 flow_sort.py sort   <room>
  python3 flow_sort.py status <room>
  python3 flow_sort.py tree   <room>
  python3 flow_sort.py list
  python3 flow_sort.py clean  <room>

FC_FLOW MESH | Sovereign PEU
Founder: Juan Jaime Rivera Zamorano
"""

import sys
import json
import shutil
import re
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────

ROOT          = Path(".")
SPLIT_OUTPUT  = ROOT / "splitter" / "output"
SORT_INPUT    = ROOT / "sorter"   / "input"
SORT_OUTPUT   = ROOT / "sorter"   / "output"
INTEG_INPUT   = ROOT / "integration" / "input"
SHARED        = ROOT / "shared"
STATE_FILE    = SHARED / "pipeline_state.json"

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
BLUE   = "\033[94m"

# ─────────────────────────────────────────────
#  SORT CATEGORIES
#
#  This is the sovereign directory contract.
#  Every module gets ONE home.
#  The structure never changes shape —
#  only the contents grow.
# ─────────────────────────────────────────────

SORT_CATEGORIES = {
    # Core logic — the brain
    "core": {
        "description": "Core logic, algorithms, main processing",
        "patterns": [
            r"^(main|core|engine|processor|handler|controller|manager)",
            r"(algorithm|logic|compute|calculate|process|execute|run)",
        ],
        "extensions": [".py", ".cpp", ".c", ".cc", ".cxx"],
        "priority": 1
    },

    # Data layer — the memory
    "data": {
        "description": "Data models, schemas, structures, types",
        "patterns": [
            r"^(model|schema|struct|type|entity|record|data)",
            r"(model|schema|struct|dataclass|data_class|record)",
        ],
        "extensions": [".py", ".cpp", ".h", ".hpp"],
        "priority": 2
    },

    # IO layer — the senses
    "io": {
        "description": "Input/output, file operations, streams",
        "patterns": [
            r"^(reader|writer|loader|saver|parser|serializer|io)",
            r"(read|write|load|save|parse|serialize|deserialize|stream|file|path)",
        ],
        "extensions": [".py", ".cpp", ".c"],
        "priority": 3
    },

    # Validation — the guard
    "validation": {
        "description": "Validators, sanitizers, checkers",
        "patterns": [
            r"^(valid|check|verify|assert|guard|sanitize|clean)",
            r"(validat|verificat|sanitiz|checker|guard|assert)",
        ],
        "extensions": [".py", ".cpp"],
        "priority": 4
    },

    # Utils — the tools
    "utils": {
        "description": "Utilities, helpers, common functions",
        "patterns": [
            r"^(util|helper|common|shared|tool|misc|format)",
            r"(utility|helper|format|convert|transform|parse|encode|decode)",
        ],
        "extensions": [".py", ".cpp", ".c"],
        "priority": 5
    },

    # Config — the settings
    "config": {
        "description": "Configuration, constants, settings",
        "patterns": [
            r"^(_constants|config|setting|env|constant|param)",
            r"(config|setting|constant|parameter|environ)",
        ],
        "extensions": [".py", ".json", ".yaml", ".toml", ".ini"],
        "priority": 6
    },

    # Interfaces — the contracts
    "interfaces": {
        "description": "Abstract classes, interfaces, protocols",
        "patterns": [
            r"^(interface|abstract|protocol|base|abc|contract)",
            r"(Interface|Abstract|Protocol|Base[A-Z]|ABC)",
        ],
        "extensions": [".py", ".h", ".hpp"],
        "priority": 7
    },

    # Headers — C/C++ headers
    "headers": {
        "description": "C/C++ header files",
        "patterns": [],
        "extensions": [".h", ".hpp"],
        "priority": 8
    },

    # Imports — dependency declarations
    "imports": {
        "description": "Import declarations, dependency maps",
        "patterns": [
            r"^_imports",
        ],
        "extensions": [".py"],
        "priority": 9
    },

    # Tests — the proof
    "tests": {
        "description": "Test files, test cases, fixtures",
        "patterns": [
            r"^(test|spec|fixture|mock|stub|fake)",
            r"(test_|_test|Test[A-Z]|spec_)",
        ],
        "extensions": [".py", ".cpp"],
        "priority": 10
    },

    # Misc — the rest
    "misc": {
        "description": "Uncategorized files",
        "patterns": [],
        "extensions": [],
        "priority": 99
    }
}


# ─────────────────────────────────────────────
#  DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class SortedFile:
    """A file with its assigned category."""
    original_path: Path
    category:      str
    reason:        str
    dest_path:     Path = field(default_factory=lambda: Path("."))


@dataclass
class SortResult:
    """Result of sorting a room."""
    room:         str
    sorted_files: list[SortedFile]
    category_counts: dict[str, int]
    total_files:  int
    sort_at:      str


# ─────────────────────────────────────────────
#  CLASSIFIER
# ─────────────────────────────────────────────

class FileClassifier:
    """
    Classifies a module file into a category
    using name patterns and content scanning.
    """

    def classify(self, file_path: Path) -> tuple[str, str]:
        """
        Returns (category, reason) for a file.
        Uses name first, then content.
        """
        name    = file_path.stem.lower()
        suffix  = file_path.suffix.lower()
        content = ""

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

        # Sort by priority — first match wins
        sorted_cats = sorted(
            SORT_CATEGORIES.items(),
            key=lambda x: x[1]["priority"]
        )

        for cat_name, cat_config in sorted_cats:
            if cat_name == "misc":
                continue

            # Extension-only match for headers
            if cat_name == "headers" and suffix in (".h", ".hpp"):
                return "headers", "C/C++ header extension"

            # Pattern match on filename
            for pattern in cat_config["patterns"]:
                if re.search(pattern, name, re.IGNORECASE):
                    return cat_name, f"name matches /{pattern}/"

            # Content scan for Python class definitions
            if suffix == ".py" and content:
                for pattern in cat_config["patterns"]:
                    if re.search(pattern, content[:500], re.IGNORECASE):
                        return cat_name, f"content matches /{pattern}/"

        # Manifest files always go to config
        if file_path.name == "manifest.json":
            return "config", "manifest file"

        return "misc", "no pattern matched"


# ─────────────────────────────────────────────
#  SORTER
# ─────────────────────────────────────────────

class RoomSorter:
    """Sorts split modules into structured directories."""

    def __init__(self):
        self.classifier = FileClassifier()

    def sort_room(self, room: str, input_dir: Path, output_dir: Path) -> SortResult:
        """Sort all files in a room's split output."""

        # Find all files
        all_files = [f for f in input_dir.rglob("*") if f.is_file()]

        if not all_files:
            return SortResult(
                room             = room,
                sorted_files     = [],
                category_counts  = {},
                total_files      = 0,
                sort_at          = datetime.now(timezone.utc).isoformat()
            )

        sorted_files     = []
        category_counts: dict[str, int] = {}

        for file_path in sorted(all_files):
            category, reason = self.classifier.classify(file_path)

            # Build destination path
            # structure: sorter/output/<room>/<category>/<filename>
            dest_dir  = output_dir / room / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / file_path.name

            # Handle name collisions
            if dest_path.exists():
                stem     = dest_path.stem
                suffix   = dest_path.suffix
                counter  = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter  += 1

            # Copy file
            shutil.copy2(file_path, dest_path)

            sorted_files.append(SortedFile(
                original_path = file_path,
                category      = category,
                reason        = reason,
                dest_path     = dest_path
            ))

            category_counts[category] = category_counts.get(category, 0) + 1

        return SortResult(
            room             = room,
            sorted_files     = sorted_files,
            category_counts  = category_counts,
            total_files      = len(sorted_files),
            sort_at          = datetime.now(timezone.utc).isoformat()
        )


# ─────────────────────────────────────────────
#  MANIFEST WRITER
# ─────────────────────────────────────────────

def write_sort_manifest(result: SortResult, output_dir: Path) -> None:
    """Write sort manifest and category README files."""

    room_out = output_dir / result.room

    # Main sort manifest
    manifest = {
        "room":        result.room,
        "sort_at":     result.sort_at,
        "total_files": result.total_files,
        "categories":  result.category_counts,
        "files": [
            {
                "name":     sf.original_path.name,
                "category": sf.category,
                "reason":   sf.reason,
                "dest":     str(sf.dest_path.relative_to(output_dir))
            }
            for sf in result.sorted_files
        ]
    }

    manifest_path = room_out / "sort_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Write a README in each category directory
    for category, config in SORT_CATEGORIES.items():
        cat_dir = room_out / category
        if cat_dir.exists():
            readme = cat_dir / "README.md"
            readme.write_text(
                f"# {category.upper()}\n\n"
                f"{config['description']}\n\n"
                f"Room: {result.room}\n"
                f"Sorted: {result.sort_at[:10]}\n"
            )


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────

def cmd_sort(room: str) -> int:
    print_banner()
    print(f"\n{BOLD}🗂  Sorting {room} modules{RESET}\n")

    # Validate split output exists
    input_dir = SORT_INPUT / room
    if not input_dir.exists():
        # Try split output directly
        input_dir = SPLIT_OUTPUT / room
        if not input_dir.exists():
            print(f"{RED}✗ No split output found for {room}{RESET}")
            print(f"{DIM}  Run: make split ROOM={room}{RESET}")
            return 1
        print(f"  {DIM}Using splitter/output/{room}/ directly{RESET}")

    # Clean output
    output_dir = SORT_OUTPUT / room
    if output_dir.exists():
        shutil.rmtree(output_dir)

    sorter = RoomSorter()
    result = sorter.sort_room(room, input_dir, SORT_OUTPUT)

    if result.total_files == 0:
        print(f"{YELLOW}⚠ No files found to sort{RESET}")
        return 1

    # Print sort results
    for category, count in sorted(
        result.category_counts.items(),
        key=lambda x: SORT_CATEGORIES.get(x[0], {}).get("priority", 99)
    ):
        cat_desc = SORT_CATEGORIES.get(category, {}).get("description", "")
        bar      = "█" * count
        color    = CYAN if category in ("core", "data") else \
                   GREEN if category in ("validation", "utils") else \
                   BLUE if category == "interfaces" else \
                   DIM
        print(f"  {color}{category:<14}{RESET} "
              f"{GREEN}{bar:<20}{RESET} "
              f"{count} file{'s' if count != 1 else ''}"
              f"  {DIM}{cat_desc}{RESET}")

    # Write manifests and READMEs
    write_sort_manifest(result, SORT_OUTPUT)

    # Copy to integration input
    integ_input = INTEG_INPUT / room
    integ_input.mkdir(parents=True, exist_ok=True)
    if integ_input.exists():
        shutil.rmtree(integ_input)
    shutil.copytree(SORT_OUTPUT / room, integ_input)
    print(f"\n  {GREEN}✓{RESET} Copied to integration/input/{room}/")

    # Update pipeline state
    state = load_state()
    state["phase_3_sort"] = {
        "status":       "active",
        "files_sorted": result.total_files,
        "last_room":    room,
        "categories":   result.category_counts,
        "sort_at":      result.sort_at
    }
    save_state(state)

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  SORT COMPLETE                           ║
╚═══════════════════════════════════════════╝{RESET}

  Room       : {CYAN}{room}{RESET}
  Files      : {GREEN}{result.total_files}{RESET}
  Categories : {len(result.category_counts)}
  Output     : sorter/output/{room}/
  Next step  : {DIM}make integrate ROOM={room}{RESET}
""")
    return 0


def cmd_tree(room: str) -> int:
    """Print the sorted directory tree for a room."""
    print_banner()
    print(f"\n{BOLD}🌲 Directory tree — {room}{RESET}\n")

    output_dir = SORT_OUTPUT / room
    if not output_dir.exists():
        print(f"  {YELLOW}⚠ {room} has not been sorted yet{RESET}")
        print(f"  {DIM}Run: make sort ROOM={room}{RESET}")
        return 0

    def print_tree(path: Path, prefix: str = "  ") -> None:
        entries = sorted(path.iterdir(),
                         key=lambda p: (p.is_file(), p.name))
        for i, entry in enumerate(entries):
            is_last    = i == len(entries) - 1
            connector  = "└── " if is_last else "├── "
            extension  = "    " if is_last else "│   "

            if entry.is_dir():
                cat_config = SORT_CATEGORIES.get(entry.name, {})
                desc       = cat_config.get("description", "")
                print(f"{prefix}{connector}{CYAN}{entry.name}/{RESET}"
                      f"  {DIM}{desc}{RESET}")
                print_tree(entry, prefix + extension)
            else:
                size = entry.stat().st_size
                size_str = f"{size}B" if size < 1024 \
                           else f"{size//1024}KB"
                print(f"{prefix}{connector}{entry.name}"
                      f"  {DIM}{size_str}{RESET}")

    print_tree(output_dir)
    print()
    return 0


def cmd_status(room: str) -> int:
    """Show sort status for a room."""
    print_banner()
    print(f"\n{BOLD}📊 Sort status — {room}{RESET}\n")

    manifest_path = SORT_OUTPUT / room / "sort_manifest.json"
    if not manifest_path.exists():
        print(f"  {YELLOW}⚠ {room} has not been sorted yet{RESET}")
        print(f"  {DIM}Run: make sort ROOM={room}{RESET}")
        return 0

    manifest = json.loads(manifest_path.read_text())
    files    = manifest.get("files", [])

    print(f"  {'FILE':<30} {'CATEGORY':<14} REASON")
    print(f"  {'─'*30} {'─'*14} {'─'*30}")

    for f in files:
        name     = f['name'][:29]
        category = f['category']
        reason   = f['reason'][:35]
        color    = CYAN if category == "core" else \
                   GREEN if category == "utils" else \
                   RESET
        print(f"  {name:<30} {color}{category:<14}{RESET} {DIM}{reason}{RESET}")

    print(f"\n  Total: {GREEN}{len(files)}{RESET} files")
    print(f"  Sorted: {manifest.get('sort_at', '?')[:19]}\n")
    return 0


def cmd_list() -> int:
    """List all sorted rooms."""
    print_banner()
    print(f"\n{BOLD}📋 All Sorted Rooms{RESET}\n")

    if not SORT_OUTPUT.exists():
        print(f"  {DIM}No rooms sorted yet{RESET}")
        return 0

    rooms = [d for d in SORT_OUTPUT.iterdir() if d.is_dir()]
    if not rooms:
        print(f"  {DIM}No rooms sorted yet{RESET}")
        return 0

    for room_dir in sorted(rooms):
        manifest_path = room_dir / "sort_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            total    = manifest.get("total_files", 0)
            cats     = len(manifest.get("categories", {}))
            sort_at  = manifest.get("sort_at", "?")[:10]
            print(f"  {GREEN}🗂{RESET}  {room_dir.name:<12} "
                  f"{total} files  {cats} categories  {DIM}{sort_at}{RESET}")
        else:
            print(f"  {YELLOW}?{RESET}  {room_dir.name:<12} {DIM}no manifest{RESET}")

    print()
    return 0


def cmd_clean(room: str) -> int:
    """Clean sort output for a room."""
    print_banner()
    print(f"\n{YELLOW}🧹 Cleaning sort output — {room}{RESET}\n")

    output_dir = SORT_OUTPUT / room
    if output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"  {GREEN}✓{RESET} Removed sorter/output/{room}/")
    else:
        print(f"  {DIM}Nothing to clean for {room}{RESET}")

    print()
    return 0


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    SHARED.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def print_banner():
    print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════╗
║   AiZQuad Lab — Phase 3: Flow Sort       ║
║   [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH   ║
╚═══════════════════════════════════════════╝{RESET}""")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def usage():
    print(f"""
{CYAN}Usage:{RESET}
  python3 flow_sort.py sort   <room>
  python3 flow_sort.py status <room>
  python3 flow_sort.py tree   <room>
  python3 flow_sort.py list
  python3 flow_sort.py clean  <room>

{CYAN}Examples:{RESET}
  python3 flow_sort.py sort   room-2
  python3 flow_sort.py tree   room-2
  python3 flow_sort.py status room-2
  python3 flow_sort.py list
""")


def main() -> int:
    args = sys.argv[1:]

    if not args:
        usage()
        return 0

    command = args[0].lower()

    if command == "sort":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_sort.py sort <room>{RESET}")
            return 1
        return cmd_sort(args[1])

    elif command == "status":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_sort.py status <room>{RESET}")
            return 1
        return cmd_status(args[1])

    elif command == "tree":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_sort.py tree <room>{RESET}")
            return 1
        return cmd_tree(args[1])

    elif command == "list":
        return cmd_list()

    elif command == "clean":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_sort.py clean <room>{RESET}")
            return 1
        return cmd_clean(args[1])

    else:
        print(f"{RED}✗ Unknown command: {command}{RESET}")
        usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
