#!/usr/bin/env python3
"""
AiZQuad Lab — Phase 2: Flow Split
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Takes locked room logic and splits it
into clean, individual modules.

Divide and conquer.
Each module does ONE thing.
Each module is easy to expand.
Each module is easy to upgrade.

Usage:
  python3 flow_split.py split  <room>
  python3 flow_split.py status <room>
  python3 flow_split.py list
  python3 flow_split.py clean  <room>

FC_FLOW MESH | Sovereign PEU
Founder: Juan Jaime Rivera Zamorano
"""

import sys
import json
import ast
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────

ROOT         = Path(".")
FORGE_LOCKED = ROOT / "forge" / "locked"
SPLIT_INPUT  = ROOT / "splitter" / "input"
SPLIT_OUTPUT = ROOT / "splitter" / "output"
SORT_INPUT   = ROOT / "sorter"   / "input"
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
#  DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class Module:
    """A single extracted module."""
    name:        str
    kind:        str           # function | class | constant | imports
    source:      str
    origin_file: str
    line_start:  int
    line_end:    int
    depends_on:  list[str] = field(default_factory=list)
    docstring:   str        = ""


@dataclass
class SplitResult:
    """Result of splitting a room."""
    room:        str
    modules:     list[Module]
    imports:     list[str]
    constants:   list[Module]
    total_lines: int
    source_file: str


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
║   AiZQuad Lab — Phase 2: Flow Split      ║
║   [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH   ║
╚═══════════════════════════════════════════╝{RESET}""")


def get_docstring(node) -> str:
    """Extract docstring from AST node."""
    try:
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            return str(first.value.value).strip()
    except (IndexError, AttributeError):
        pass
    return ""


def get_dependencies(source: str, all_names: list[str]) -> list[str]:
    """Find which other modules this source depends on."""
    deps = []
    for name in all_names:
        # Check if name is referenced in source (but not as its own definition)
        pattern = r'\b' + re.escape(name) + r'\b'
        if re.search(pattern, source):
            deps.append(name)
    return deps


def make_module_header(module: Module, room: str) -> str:
    """Generate the file header for a module."""
    return f'''"""
AiZQuad Lab — {room.upper()} — {module.name}
{'━' * 48}
Type    : {module.kind}
Origin  : {module.origin_file}
Lines   : {module.line_start} → {module.line_end}
Room    : {room}

FC_FLOW MESH | Sovereign PEU
"""
'''


# ─────────────────────────────────────────────
#  PYTHON SPLITTER
# ─────────────────────────────────────────────

class PythonSplitter:
    """Splits Python files into individual modules."""

    def split_file(self, file_path: Path, room: str) -> SplitResult:
        source_code  = file_path.read_text(encoding="utf-8")
        lines        = source_code.splitlines()
        total_lines  = len(lines)

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            print(f"  {RED}✗ Syntax error in {file_path.name}: {e}{RESET}")
            return SplitResult(
                room        = room,
                modules     = [],
                imports     = [],
                constants   = [],
                total_lines = total_lines,
                source_file = str(file_path)
            )

        modules   = []
        imports   = []
        constants = []

        for node in ast.walk(tree):

            # Extract top-level functions
            if isinstance(node, ast.FunctionDef) and \
               isinstance(getattr(node, 'col_offset', 99), int) and \
               node.col_offset == 0:

                start  = node.lineno - 1
                end    = node.end_lineno
                source = "\n".join(lines[start:end])

                modules.append(Module(
                    name        = node.name,
                    kind        = "function",
                    source      = source,
                    origin_file = file_path.name,
                    line_start  = node.lineno,
                    line_end    = end,
                    docstring   = get_docstring(node)
                ))

            # Extract top-level classes
            elif isinstance(node, ast.ClassDef) and \
                 getattr(node, 'col_offset', 99) == 0:

                start  = node.lineno - 1
                end    = node.end_lineno
                source = "\n".join(lines[start:end])

                modules.append(Module(
                    name        = node.name,
                    kind        = "class",
                    source      = source,
                    origin_file = file_path.name,
                    line_start  = node.lineno,
                    line_end    = end,
                    docstring   = get_docstring(node)
                ))

        # Extract imports (top of file)
        import_lines = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if node.lineno <= 30:  # Top of file imports only
                    start = node.lineno - 1
                    end   = node.end_lineno
                    import_lines.append("\n".join(lines[start:end]))

        imports = list(dict.fromkeys(import_lines))  # Deduplicate

        # Extract top-level constants (ALL_CAPS = ...)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if name.isupper() and len(name) > 1:
                            start  = node.lineno - 1
                            end    = node.end_lineno
                            source = "\n".join(lines[start:end])
                            constants.append(Module(
                                name        = name,
                                kind        = "constant",
                                source      = source,
                                origin_file = file_path.name,
                                line_start  = node.lineno,
                                line_end    = end
                            ))

        # Resolve dependencies between modules
        all_names = [m.name for m in modules]
        for module in modules:
            deps = get_dependencies(module.source, all_names)
            deps = [d for d in deps if d != module.name]
            module.depends_on = deps

        return SplitResult(
            room        = room,
            modules     = modules,
            imports     = imports,
            constants   = constants,
            total_lines = total_lines,
            source_file = str(file_path)
        )


# ─────────────────────────────────────────────
#  GENERIC SPLITTER (C++, etc.)
# ─────────────────────────────────────────────

class GenericSplitter:
    """
    Splits non-Python files by detecting
    function/class boundaries using regex.
    Handles C, C++, JavaScript, etc.
    """

    # C/C++ function pattern
    CPP_FUNC = re.compile(
        r'^(?:[\w:*&<>\[\]]+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{',
        re.MULTILINE
    )

    def split_file(self, file_path: Path, room: str) -> SplitResult:
        source_code = file_path.read_text(encoding="utf-8", errors="replace")
        lines       = source_code.splitlines()

        modules = []
        suffix  = file_path.suffix.lower()

        if suffix in ('.cpp', '.c', '.cc', '.cxx', '.h', '.hpp'):
            modules = self._split_cpp(source_code, lines, file_path.name)

        return SplitResult(
            room        = room,
            modules     = modules,
            imports     = [],
            constants   = [],
            total_lines = len(lines),
            source_file = str(file_path)
        )

    def _split_cpp(
        self,
        source: str,
        lines: list[str],
        filename: str
    ) -> list[Module]:
        """Split C/C++ by finding function definitions."""
        modules = []
        matches = list(self.CPP_FUNC.finditer(source))

        for i, match in enumerate(matches):
            func_name = match.group(1)

            # Skip common keywords that look like functions
            if func_name in ('if', 'for', 'while', 'switch', 'catch'):
                continue

            start_pos = match.start()
            end_pos   = matches[i + 1].start() if i + 1 < len(matches) \
                        else len(source)

            func_source = source[start_pos:end_pos].strip()
            start_line  = source[:start_pos].count('\n') + 1
            end_line    = start_line + func_source.count('\n')

            modules.append(Module(
                name        = func_name,
                kind        = "function",
                source      = func_source,
                origin_file = filename,
                line_start  = start_line,
                line_end    = end_line
            ))

        return modules


# ─────────────────────────────────────────────
#  FILE WRITER
# ─────────────────────────────────────────────

class ModuleWriter:
    """Writes split modules to output directory."""

    def write(
        self,
        result: SplitResult,
        output_dir: Path
    ) -> list[Path]:
        """Write all modules to disk. Returns list of written files."""
        written   = []
        room      = result.room
        room_dir  = output_dir / room
        room_dir.mkdir(parents=True, exist_ok=True)

        # Write imports module
        if result.imports:
            imports_file = room_dir / "_imports.py"
            content = make_module_header(
                Module(
                    name        = "_imports",
                    kind        = "imports",
                    source      = "",
                    origin_file = result.source_file,
                    line_start  = 0,
                    line_end    = 0
                ),
                room
            )
            content += "\n".join(result.imports) + "\n"
            imports_file.write_text(content, encoding="utf-8")
            written.append(imports_file)
            print(f"    {GREEN}✓{RESET} _imports.py")

        # Write constants module
        if result.constants:
            consts_file = room_dir / "_constants.py"
            content = make_module_header(
                Module(
                    name        = "_constants",
                    kind        = "constants",
                    source      = "",
                    origin_file = result.source_file,
                    line_start  = 0,
                    line_end    = 0
                ),
                room
            )
            for const in result.constants:
                content += f"\n# {const.name}\n{const.source}\n"
            consts_file.write_text(content, encoding="utf-8")
            written.append(consts_file)
            print(f"    {GREEN}✓{RESET} _constants.py")

        # Write each function/class as its own file
        for module in result.modules:
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', module.name)
            ext       = ".py" if module.kind in ("function", "class") else ".cpp"
            mod_file  = room_dir / f"{safe_name}{ext}"

            content = make_module_header(module, room)

            # Add imports for Python modules
            if ext == ".py" and result.imports:
                content += "\n".join(result.imports) + "\n\n"

            # Add docstring if available
            if module.docstring:
                content += f'# {module.docstring}\n\n'

            # Add dependencies comment
            if module.depends_on:
                deps_str = ", ".join(module.depends_on)
                content += f"# Depends on: {deps_str}\n\n"

            content += module.source + "\n"
            mod_file.write_text(content, encoding="utf-8")
            written.append(mod_file)

            dep_str = f" {DIM}← needs: {', '.join(module.depends_on)}{RESET}" \
                      if module.depends_on else ""
            print(f"    {GREEN}✓{RESET} {mod_file.name}{dep_str}")

        # Write manifest
        manifest = {
            "room":         room,
            "source_file":  result.source_file,
            "split_at":     datetime.now(timezone.utc).isoformat(),
            "total_lines":  result.total_lines,
            "modules":      [
                {
                    "name":       m.name,
                    "kind":       m.kind,
                    "file":       f"{re.sub(r'[^a-zA-Z0-9_]', '_', m.name)}.py",
                    "lines":      f"{m.line_start}→{m.line_end}",
                    "depends_on": m.depends_on,
                    "docstring":  m.docstring
                }
                for m in result.modules
            ],
            "imports_file":   "_imports.py" if result.imports else None,
            "constants_file": "_constants.py" if result.constants else None,
            "file_count":     len(written)
        }

        manifest_file = room_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        written.append(manifest_file)
        print(f"    {GREEN}✓{RESET} manifest.json")

        return written


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────

def cmd_split(room: str) -> int:
    print_banner()
    print(f"\n{BOLD}✂️  Splitting {room} into modules{RESET}\n")

    # Validate lock exists
    lock_file = FORGE_LOCKED / f"{room}.lock.json"
    if not lock_file.exists():
        print(f"{RED}✗ {room} is not locked{RESET}")
        print(f"{DIM}  Run: make lock ROOM={room} V=v1{RESET}")
        return 1

    # Validate input exists
    input_dir = SPLIT_INPUT / room
    if not input_dir.exists():
        print(f"{RED}✗ No input found at {input_dir}{RESET}")
        print(f"{DIM}  Re-lock to refresh input: make lock ROOM={room} V=v1{RESET}")
        return 1

    # Find all source files
    source_files = sorted(input_dir.rglob("*"))
    source_files = [f for f in source_files if f.is_file() and
                    f.suffix in ('.py', '.cpp', '.c', '.h', '.hpp', '.cc')]

    if not source_files:
        print(f"{RED}✗ No supported source files found in {input_dir}{RESET}")
        print(f"{DIM}  Supported: .py .cpp .c .h .hpp .cc{RESET}")
        return 1

    # Clean output directory
    output_dir = SPLIT_OUTPUT / room
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Also prep sorter input
    sort_input_dir = SORT_INPUT / room if (ROOT / "sorter").exists() \
                     else None

    py_splitter      = PythonSplitter()
    generic_splitter = GenericSplitter()
    writer           = ModuleWriter()

    total_modules = 0

    for source_file in source_files:
        print(f"\n  {CYAN}Processing:{RESET} {source_file.name}")

        # Choose splitter
        if source_file.suffix == '.py':
            result = py_splitter.split_file(source_file, room)
        else:
            result = generic_splitter.split_file(source_file, room)

        if not result.modules and not result.imports:
            print(f"    {YELLOW}⚠ No modules found{RESET}")
            print(f"    {DIM}File will be passed through whole{RESET}")

            # Pass through as-is
            passthrough_dir = output_dir / room
            passthrough_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, passthrough_dir / source_file.name)
            continue

        # Write modules
        written = writer.write(result, output_dir)
        total_modules += len(result.modules)

        print(f"\n    {DIM}─── {source_file.name} → "
              f"{len(result.modules)} modules ───{RESET}")

    # Copy to sorter input
    sorter_input = ROOT / "sorter" / "input"
    sorter_input.mkdir(parents=True, exist_ok=True)
    sort_dest = sorter_input / room
    if sort_dest.exists():
        shutil.rmtree(sort_dest)
    shutil.copytree(output_dir / room if (output_dir / room).exists()
                    else output_dir, sort_dest)
    print(f"\n  {GREEN}✓{RESET} Copied to sorter/input/{room}/")

    # Update pipeline state
    state = load_state()
    state["phase_2_split"] = {
        "status":         "active",
        "modules_created": total_modules,
        "last_room":      room,
        "split_at":       datetime.now(timezone.utc).isoformat()
    }
    save_state(state)

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  SPLIT COMPLETE                          ║
╚═══════════════════════════════════════════╝{RESET}

  Room       : {CYAN}{room}{RESET}
  Files      : {len(source_files)}
  Modules    : {GREEN}{total_modules}{RESET}
  Output     : splitter/output/{room}/
  Next step  : {DIM}make sort ROOM={room}{RESET}
""")
    return 0


def cmd_status(room: str) -> int:
    print_banner()
    print(f"\n{BOLD}📊 Split status for {room}{RESET}\n")

    output_dir = SPLIT_OUTPUT / room
    if not output_dir.exists():
        print(f"  {YELLOW}⚠ {room} has not been split yet{RESET}")
        print(f"  {DIM}Run: make split ROOM={room}{RESET}")
        return 0

    manifest_file = output_dir / "manifest.json"
    if not manifest_file.exists():
        print(f"  {YELLOW}⚠ No manifest found{RESET}")
        return 0

    manifest = json.loads(manifest_file.read_text())
    modules  = manifest.get("modules", [])

    print(f"  {'NAME':<25} {'KIND':<12} {'LINES':<12} DEPENDS ON")
    print(f"  {'─'*25} {'─'*12} {'─'*12} {'─'*20}")

    for mod in modules:
        name = mod['name']
        kind = mod['kind']
        lines = mod.get('lines', '?')
        deps  = ', '.join(mod.get('depends_on', [])) or '—'
        kind_color = CYAN if kind == 'class' else GREEN
        print(f"  {name:<25} "
              f"{kind_color}{kind:<12}{RESET} "
              f"{lines:<12} {DIM}{deps}{RESET}")

    print(f"\n  Total modules: {GREEN}{len(modules)}{RESET}")
    print(f"  Split at     : {manifest.get('split_at', '?')[:19]}\n")
    return 0


def cmd_list() -> int:
    print_banner()
    print(f"\n{BOLD}📋 All Split Rooms{RESET}\n")

    if not SPLIT_OUTPUT.exists():
        print(f"  {DIM}No rooms split yet{RESET}")
        return 0

    rooms = [d for d in SPLIT_OUTPUT.iterdir() if d.is_dir()]

    if not rooms:
        print(f"  {DIM}No rooms split yet{RESET}")
        return 0

    for room_dir in sorted(rooms):
        manifest_file = room_dir / "manifest.json"
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text())
            count    = len(manifest.get("modules", []))
            split_at = manifest.get("split_at", "?")[:10]
            print(f"  {GREEN}✂{RESET}  {room_dir.name:<12} "
                  f"{count} modules  {DIM}{split_at}{RESET}")
        else:
            print(f"  {YELLOW}?{RESET}  {room_dir.name:<12} {DIM}no manifest{RESET}")

    print()
    return 0


def cmd_clean(room: str) -> int:
    print_banner()
    print(f"\n{YELLOW}🧹 Cleaning split output for {room}{RESET}\n")

    output_dir = SPLIT_OUTPUT / room
    if output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"  {GREEN}✓{RESET} Removed splitter/output/{room}/")
    else:
        print(f"  {DIM}Nothing to clean for {room}{RESET}")

    print()
    return 0


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def usage():
    print(f"""
{CYAN}Usage:{RESET}
  python3 flow_split.py split  <room>
  python3 flow_split.py status <room>
  python3 flow_split.py list
  python3 flow_split.py clean  <room>

{CYAN}Examples:{RESET}
  python3 flow_split.py split  room-2
  python3 flow_split.py status room-2
  python3 flow_split.py list
  python3 flow_split.py clean  room-2
""")


def main() -> int:
    args = sys.argv[1:]

    if not args:
        usage()
        return 0

    command = args[0].lower()

    if command == "split":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_split.py split <room>{RESET}")
            return 1
        return cmd_split(args[1])

    elif command == "status":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_split.py status <room>{RESET}")
            return 1
        return cmd_status(args[1])

    elif command == "list":
        return cmd_list()

    elif command == "clean":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_split.py clean <room>{RESET}")
            return 1
        return cmd_clean(args[1])

    else:
        print(f"{RED}✗ Unknown command: {command}{RESET}")
        usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
