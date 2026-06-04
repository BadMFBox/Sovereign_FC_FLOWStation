class LogicLock:
    """
    Locks approved logic with SHA-256 signature.
    Generates surface definitions for AI access.
    Enforces explicit approval for reads.
    Detects unauthorized modifications.
    Logs all access attempts.
    """
    
    def lock(self, room: str, surface_def: dict):
        """Lock room logic and define surface."""
        
    def verify(self, room: str) -> bool:
        """Verify signature hasn't been tampered with."""
        
    def request_access(self, room: str, requester: str) -> bool:
        """AI requests access. User approves or denies."""
        
    def generate_surface(self, room: str) -> Path:
        """Generate _surface.py for AI interaction."""
        
    def audit_log(self, room: str, action: str, requester: str):
        """Log all access attempts."""

class AIAccessControl:
    """
    Manages AI permissions at room level.
    Explicit approval required.
    Surface-only or full access.
    Revocable at any time.
    """
    
    def grant_surface_access(self, room: str):
        """AI can read surface only."""
        
    def grant_read_access(self, room: str):
        """AI can read locked internals (rare)."""
        
    def revoke_access(self, room: str):
        """Remove all AI access to room."""
        
    def check_permission(self, room: str, file: str) -> bool:
        """Check if AI can access a specific file."""
#!/usr/bin/env python3
"""
AiZQuad Lab — Phase 4: Flow Integrate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Merges versions, locks logic, generates
surfaces, wires the sovereign mesh.

PIN-protected workstation lock.
AI access controlled by user approval.
Zero Trust of puppet masters.
Full trust of the team.

Usage:
  python3 flow_integrate.py unlock
  python3 flow_integrate.py lock
  python3 flow_integrate.py build     <room>
  python3 flow_integrate.py merge     <room>
  python3 flow_integrate.py seal      <room>
  python3 flow_integrate.py surface   <room>
  python3 flow_integrate.py wire      <room>
  python3 flow_integrate.py verify    <room>
  python3 flow_integrate.py access    <room> <grant|deny|revoke>
  python3 flow_integrate.py audit     <room>
  python3 flow_integrate.py status
  python3 flow_integrate.py list

FC_FLOW MESH | Sovereign PEU
Founder: Juan Jaime Rivera Zamorano
"""

import sys
import json
import hashlib
import shutil
import re
import os
import getpass
import hmac
import time
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────

ROOT         = Path(".")
FORGE_VERS   = ROOT / "forge"       / "versions"
SORT_OUTPUT  = ROOT / "sorter"      / "output"
INTEG_ROOT   = ROOT / "integration"
INTEG_INPUT  = INTEG_ROOT / "input"
INTEG_MERGE  = INTEG_ROOT / "merge"
INTEG_LOCKS  = INTEG_ROOT / "logic_locks"
INTEG_OUTPUT = INTEG_ROOT / "output" / "mesh"
SHARED       = ROOT / "shared"
STATE_FILE   = SHARED / "pipeline_state.json"
SESSION_FILE = SHARED / ".session"
PIN_FILE     = SHARED / ".pin"
AUDIT_FILE   = SHARED / "audit.log"

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
MAGENTA= "\033[95m"


# ─────────────────────────────────────────────
#  AUDIT LOGGER
# ─────────────────────────────────────────────

def audit(action: str, room: str = "system", detail: str = "") -> None:
    """Write every significant action to the audit log."""
    SHARED.mkdir(parents=True, exist_ok=True)
    ts      = datetime.now(timezone.utc).isoformat()
    entry   = {
        "ts":     ts,
        "action": action,
        "room":   room,
        "detail": detail
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─────────────────────────────────────────────
#  PIN / SESSION MANAGER
# ─────────────────────────────────────────────

class SessionManager:
    """
    Manages workstation lock/unlock via 6-digit PIN.
    When locked — nothing runs.
    When unlocked — user is in control.
    Session expires after 4 hours of inactivity.
    """

    SESSION_TTL = 4 * 60 * 60  # 4 hours in seconds

    def _hash_pin(self, pin: str) -> str:
        """Hash a PIN using PBKDF2."""
        salt = b"aizquad_sovereign_salt_v1"
        key  = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode(),
            salt,
            iterations=260_000
        )
        return key.hex()

    def setup_pin(self) -> bool:
        """First-time PIN setup."""
        print(f"\n{CYAN}{BOLD}  First time setup — Set your workstation PIN{RESET}")
        print(f"  {DIM}6 digits. You will need this every session.{RESET}\n")

        while True:
            pin = getpass.getpass("  Set PIN (6 digits): ").strip()
            if not pin.isdigit() or len(pin) != 6:
                print(f"  {RED}✗ PIN must be exactly 6 digits{RESET}")
                continue

            confirm = getpass.getpass("  Confirm PIN: ").strip()
            if pin != confirm:
                print(f"  {RED}✗ PINs do not match. Try again.{RESET}")
                continue

            SHARED.mkdir(parents=True, exist_ok=True)
            PIN_FILE.write_text(self._hash_pin(pin))
            audit("PIN_SETUP", detail="PIN configured for first time")
            print(f"\n  {GREEN}✓ PIN set. Workstation secured.{RESET}")
            return True

    def unlock(self) -> bool:
        """Unlock workstation with PIN."""
        if not PIN_FILE.exists():
            return self.setup_pin() and self._create_session()

        print(f"\n{CYAN}{BOLD}  AiZQuad Workstation — Locked{RESET}")
        print(f"  {DIM}Enter your 6-digit PIN to continue{RESET}\n")

        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                pin = getpass.getpass("  PIN: ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n  {RED}✗ Aborted{RESET}")
                audit("UNLOCK_ABORTED")
                return False

            stored = PIN_FILE.read_text().strip()

            if hmac.compare_digest(self._hash_pin(pin), stored):
                self._create_session()
                audit("UNLOCK_SUCCESS")
                print(f"\n  {GREEN}✓ Workstation unlocked{RESET}\n")
                return True
            else:
                attempts += 1
                remaining = max_attempts - attempts
                audit("UNLOCK_FAILED", detail=f"attempt {attempts}")
                if remaining > 0:
                    print(f"  {RED}✗ Wrong PIN. {remaining} attempts left.{RESET}")
                else:
                    print(f"\n  {RED}✗ Too many failed attempts.{RESET}")
                    print(f"  {RED}  Workstation is locked.{RESET}\n")
                    audit("UNLOCK_BLOCKED", detail="max attempts reached")
                    return False

        return False

    def _create_session(self) -> bool:
        """Write session token to disk."""
        session = {
            "created_at": time.time(),
            "expires_at": time.time() + self.SESSION_TTL,
            "active":     True
        }
        SHARED.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(session))
        return True

    def is_unlocked(self) -> bool:
        """Check if there is a valid active session."""
        if not SESSION_FILE.exists():
            return False
        try:
            session = json.loads(SESSION_FILE.read_text())
            if not session.get("active", False):
                return False
            if time.time() > session.get("expires_at", 0):
                self.lock(silent=True)
                return False
            return True
        except Exception:
            return False

    def lock(self, silent: bool = False) -> None:
        """Lock the workstation. Wipe session."""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        audit("WORKSTATION_LOCKED")
        if not silent:
            print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════╗
║   AiZQuad Workstation — LOCKED           ║
║                                          ║
║   Session closed.                        ║
║   All operations suspended.              ║
║   Logic locks remain sealed.             ║
║                                          ║
║   Run: python3 flow_integrate.py unlock  ║
╚═══════════════════════════════════════════╝{RESET}
""")

    def require_session(self) -> bool:
        """
        Gate for all commands.
        If locked → print lock screen and exit.
        """
        if self.is_unlocked():
            return True

        print(f"""
{RED}{BOLD}╔═══════════════════════════════════════════╗
║   WORKSTATION LOCKED                     ║
║                                          ║
║   No operations available.              ║
║   Unlock first:                          ║
║                                          ║
║   python3 flow_integrate.py unlock       ║
╚═══════════════════════════════════════════╝{RESET}
""")
        audit("ACCESS_DENIED", detail="workstation locked")
        return False

    def refresh(self) -> None:
        """Refresh session TTL on activity."""
        if SESSION_FILE.exists():
            try:
                session = json.loads(SESSION_FILE.read_text())
                session["expires_at"] = time.time() + self.SESSION_TTL
                SESSION_FILE.write_text(json.dumps(session))
            except Exception:
                pass


# ─────────────────────────────────────────────
#  AI ACCESS CONTROL
# ─────────────────────────────────────────────

class AIAccessControl:
    """
    Manages AI permissions per room.
    Explicit user approval required.
    Surface-only or full read access.
    Revocable at any time.
    Puppet masters get nothing.
    """

    ACCESS_FILE = SHARED / "ai_access.json"

    def _load(self) -> dict:
        if self.ACCESS_FILE.exists():
            return json.loads(self.ACCESS_FILE.read_text())
        return {}

    def _save(self, data: dict) -> None:
        SHARED.mkdir(parents=True, exist_ok=True)
        self.ACCESS_FILE.write_text(json.dumps(data, indent=2))

    def grant(self, room: str, level: str = "surface") -> None:
        """
        Grant AI access to a room.
        level: 'surface' (API only) or 'read' (full read)
        """
        data = self._load()
        data[room] = {
            "level":      level,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "active":     True
        }
        self._save(data)
        audit("AI_ACCESS_GRANTED", room=room, detail=f"level={level}")
        print(f"  {GREEN}✓ AI granted {level} access to {room}{RESET}")

    def revoke(self, room: str) -> None:
        """Remove all AI access to a room."""
        data = self._load()
        if room in data:
            data[room]["active"] = False
            data[room]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        self._save(data)
        audit("AI_ACCESS_REVOKED", room=room)
        print(f"  {GREEN}✓ AI access revoked for {room}{RESET}")

    def check(self, room: str, file_path: str = "") -> tuple[bool, str]:
        """
        Check if AI can access a room/file.
        Returns (allowed, level).
        """
        data = self._load()
        record = data.get(room)
        if not record or not record.get("active", False):
            audit("AI_ACCESS_DENIED", room=room,
                  detail=f"no permission for {file_path}")
            return False, "none"
        level = record.get("level", "surface")
        audit("AI_ACCESS_CHECKED", room=room, detail=f"level={level}")
        return True, level

    def status(self, room: str) -> str:
        """Get current AI access level for a room."""
        data   = self._load()
        record = data.get(room, {})
        if not record or not record.get("active", False):
            return "none"
        return record.get("level", "surface")

    def interactive_grant(self, room: str) -> None:
        """Prompt user to approve AI access level."""
        print(f"\n{YELLOW}{BOLD}  AI Access Request — {room}{RESET}")
        print(f"""
  {DIM}What level of access should AI have?{RESET}

  {CYAN}[1]{RESET} Surface only   — AI sees function signatures,
                    type hints, and docstrings.
                    Cannot see implementation.
                    {GREEN}Recommended.{RESET}

  {CYAN}[2]{RESET} Full read       — AI sees everything in the room.
                    Use for deep review sessions.
                    {YELLOW}Use with caution.{RESET}

  {CYAN}[3]{RESET} Deny            — AI gets nothing.
""")
        choice = input("  Your choice [1/2/3]: ").strip()

        if choice == "1":
            self.grant(room, "surface")
        elif choice == "2":
            confirm = input(
                f"  {YELLOW}Full read grants AI access to locked internals.\n"
                f"  Type '{room}' to confirm: {RESET}"
            ).strip()
            if confirm == room:
                self.grant(room, "read")
            else:
                print(f"  {RED}✗ Aborted{RESET}")
        elif choice == "3":
            self.revoke(room)
        else:
            print(f"  {RED}✗ Invalid choice{RESET}")


# ─────────────────────────────────────────────
#  MERGE ENGINE
# ─────────────────────────────────────────────

class MergeEngine:
    """
    Merges multiple versions of a room
    into one clean, best-of output.
    
    Scoring per file:
      - Line count      (more complete wins)
      - Docstring count (more documented wins)
      - Most recent     (newer wins on tie)
    """

    def _score_file(self, path: Path) -> int:
        """Score a file by completeness."""
        try:
            content    = path.read_text(encoding="utf-8", errors="replace")
            lines      = len(content.splitlines())
            docstrings = content.count('"""') // 2
            comments   = content.count('#')
            return lines + (docstrings * 10) + (comments * 2)
        except Exception:
            return 0

    def merge_room(self, room: str, output_dir: Path) -> dict:
        """
        Find all versions of a room,
        pick the best file for each module,
        write merged output.
        """
        versions_dir = FORGE_VERS / room
        if not versions_dir.exists():
            return {"status": "no_versions", "files": 0}

        versions = sorted(versions_dir.iterdir())
        if not versions:
            return {"status": "no_versions", "files": 0}

        # Collect all files across all versions
        # key = relative filename, value = list of (version, path, score)
        file_candidates: dict[str, list[tuple[str, Path, int]]] = {}

        for version_dir in versions:
            if not version_dir.is_dir():
                continue
            for file_path in version_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = str(file_path.relative_to(version_dir))
                score = self._score_file(file_path)
                if rel not in file_candidates:
                    file_candidates[rel] = []
                file_candidates[rel].append((version_dir.name, file_path, score))

        if not file_candidates:
            return {"status": "no_files", "files": 0}

        # Pick best version of each file
        output_dir.mkdir(parents=True, exist_ok=True)
        merged_count = 0
        merge_log    = []

        for rel_path, candidates in file_candidates.items():
            # Sort by score descending, then version descending (most recent)
            best = sorted(candidates, key=lambda x: (x[2], x[0]), reverse=True)[0]
            best_version, best_path, best_score = best

            dest = output_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_path, dest)
            merged_count += 1

            merge_log.append({
                "file":     rel_path,
                "chosen":   best_version,
                "score":    best_score,
                "options":  [c[0] for c in candidates]
            })

        # Write merge manifest
        manifest = {
            "room":        room,
            "merged_at":   datetime.now(timezone.utc).isoformat(),
            "versions":    [v.name for v in versions],
            "files":       merged_count,
            "merge_log":   merge_log
        }
        (output_dir / "merge_manifest.json").write_text(
            json.dumps(manifest, indent=2)
        )

        return {"status": "ok", "files": merged_count, "log": merge_log}


# ─────────────────────────────────────────────
#  LOGIC LOCK
# ─────────────────────────────────────────────

class LogicLock:
    """
    Seals merged logic with SHA-256 signature.
    Defines the public surface (what AI sees).
    Private internals stay hidden.
    Tampering is detectable.
    """

    def _hash_dir(self, dir_path: Path) -> str:
        sha256 = hashlib.sha256()
        for file in sorted(dir_path.rglob("*")):
            if file.is_file() and file.name != "logic_lock.json":
                sha256.update(str(file.relative_to(dir_path)).encode())
                with open(file, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def _extract_surface(self, dir_path: Path) -> dict:
        """
        Extract public surface from Python files.
        Surface = function signatures + docstrings.
        Implementation stays locked.
        """
        surface: dict[str, list] = {}

        for py_file in dir_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                import ast
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree    = ast.parse(content)
                entries = []

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.col_offset == 0:
                            # Get argument names
                            args = [a.arg for a in node.args.args]

                            # Get return annotation
                            returns = ""
                            if node.returns:
                                try:
                                    returns = ast.unparse(node.returns)
                                except Exception:
                                    returns = "?"

                            # Get docstring
                            doc = ""
                            try:
                                first = node.body[0]
                                if isinstance(first, ast.Expr) and \
                                   isinstance(first.value, ast.Constant):
                                    doc = str(first.value.value).strip()[:120]
                            except Exception:
                                pass

                            entries.append({
                                "name":    node.name,
                                "args":    args,
                                "returns": returns,
                                "doc":     doc,
                                "line":    node.lineno
                            })

                    elif isinstance(node, ast.ClassDef):
                        if node.col_offset == 0:
                            doc = ""
                            try:
                                first = node.body[0]
                                if isinstance(first, ast.Expr) and \
                                   isinstance(first.value, ast.Constant):
                                    doc = str(first.value.value).strip()[:120]
                            except Exception:
                                pass

                            entries.append({
                                "name":    node.name,
                                "kind":    "class",
                                "doc":     doc,
                                "line":    node.lineno
                            })

                if entries:
                    rel = str(py_file.relative_to(dir_path))
                    surface[rel] = entries

            except Exception:
                continue

        return surface

    def seal(self, room: str, source_dir: Path) -> dict:
        """Seal a room's logic and generate surface."""
        INTEG_LOCKS.mkdir(parents=True, exist_ok=True)

        signature = self._hash_dir(source_dir)
        surface   = self._extract_surface(source_dir)

        lock_record = {
            "room":      room,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
            "signature": signature,
            "surface":   surface,
            "status":    "SEALED",
            "version":   "1.0"
        }

        lock_path = INTEG_LOCKS / f"{room}.logic.json"
        lock_path.write_text(json.dumps(lock_record, indent=2))
        audit("LOGIC_SEALED", room=room,
              detail=f"sig={signature[:16]}")

        return lock_record

    def verify(self, room: str, source_dir: Path) -> tuple[bool, str]:
        """Verify a room seal has not been broken."""
        lock_path = INTEG_LOCKS / f"{room}.logic.json"
        if not lock_path.exists():
            return False, "no lock found"

        lock_record   = json.loads(lock_path.read_text())
        original_sig  = lock_record.get("signature", "")
        current_sig   = self._hash_dir(source_dir)

        if hmac.compare_digest(current_sig, original_sig):
            audit("LOGIC_VERIFIED", room=room, detail="ok")
            return True, "ok"
        else:
            audit("LOGIC_TAMPERED", room=room,
                  detail=f"expected={original_sig[:16]} got={current_sig[:16]}")
            return False, f"signature mismatch"

    def get_surface(self, room: str) -> Optional[dict]:
        """Get the public surface definition for AI."""
        lock_path = INTEG_LOCKS / f"{room}.logic.json"
        if not lock_path.exists():
            return None
        return json.loads(lock_path.read_text()).get("surface", {})


# ─────────────────────────────────────────────
#  SURFACE GENERATOR
# ─────────────────────────────────────────────

class SurfaceGenerator:
    """
    Generates _surface.py files.
    This is what AI teammates see.
    No internals. No implementation.
    Just the contract.
    """

    def generate(self, room: str, surface: dict, output_dir: Path) -> Path:
        """Generate _surface.py from logic lock surface definition."""
        room_safe = room.replace("-", "_")
        lines     = [
            f'"""',
            f'AiZQuad Lab — {room.upper()} — Public Surface',
            f'{"━" * 48}',
            f'This is what AI sees.',
            f'Implementation is locked.',
            f'Modify only with user approval.',
            f'"""',
            f'',
            f'# Surface auto-generated from logic lock',
            f'# DO NOT EDIT MANUALLY',
            f'# Re-run: make integrate surface ROOM={room}',
            f'',
            f'from typing import Any, Optional',
            f'',
            f'',
            f'SURFACE_VERSION = "1.0"',
            f'ROOM            = "{room}"',
            f'',
        ]

        for file_rel, entries in surface.items():
            lines.append(f"# ── {file_rel} ──")
            for entry in entries:
                name    = entry.get("name", "?")
                args    = entry.get("args", [])
                returns = entry.get("returns", "Any")
                doc     = entry.get("doc", "")
                kind    = entry.get("kind", "function")

                if kind == "class":
                    lines.append(f"class {name}:")
                    if doc:
                        lines.append(f'    """{doc}"""')
                    lines.append(f"    ...")
                    lines.append(f"")
                else:
                    args_str = ", ".join(args) if args else ""
                    ret_str  = f" -> {returns}" if returns else ""
                    lines.append(f"def {name}({args_str}){ret_str}:")
                    if doc:
                        lines.append(f'    """{doc}"""')
                    lines.append(f"    ...")
                    lines.append(f"")

        content    = "\n".join(lines)
        output_dir.mkdir(parents=True, exist_ok=True)
        dest       = output_dir / "_surface.py"
        dest.write_text(content, encoding="utf-8")
        return dest


# ─────────────────────────────────────────────
#  INIT GENERATOR
# ─────────────────────────────────────────────

class InitGenerator:
    """
    Generates clean __init__.py files.
    Explicit imports only. No star imports.
    Exposes surface. Hides internals.
    """

    def generate_for_dir(self, dir_path: Path, room: str) -> Path:
        """Generate __init__.py for a category directory."""
        py_files = [
            f for f in dir_path.glob("*.py")
            if f.name not in ("__init__.py", "_surface.py")
            and not f.name.startswith("test_")
        ]

        imports = []
        for py_file in sorted(py_files):
            module_name = py_file.stem
            imports.append(f"from .{module_name} import *  "
                           f"# noqa: F401,F403")

        content = f'''"""
AiZQuad Lab — {room.upper()} — {dir_path.name}
Auto-generated __init__.py
Room: {room}
"""
'''
        if imports:
            content += "\n" + "\n".join(imports) + "\n"

        init_path = dir_path / "__init__.py"
        init_path.write_text(content, encoding="utf-8")
        return init_path

    def generate_room_init(
        self,
        room_dir: Path,
        room: str,
        surface: Optional[dict]
    ) -> Path:
        """Generate top-level __init__.py for a room package."""
        room_safe    = room.replace("-", "_")
        category_dirs = [
            d for d in room_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            and d.name != "_locked"
        ]

        lines = [
            f'"""',
            f'AiZQuad Lab — {room.upper()} Room Package',
            f'Sovereign mesh entry point.',
            f'AI sees the surface. Logic stays locked.',
            f'"""',
            f'',
            f'from . import _surface  # noqa: F401',
            f''
        ]

        for cat_dir in sorted(category_dirs):
            lines.append(f"from . import {cat_dir.name}  # noqa: F401")

        lines.append("")
        lines.append(f'ROOM = "{room}"')
        lines.append("")
        lines.append("def get_surface():")
        lines.append(f'    """Return the approved public surface for {room}."""')
        lines.append("    return _surface")
        lines.append("")

        content   = "\n".join(lines)
        init_path = room_dir / "__init__.py"
        init_path.write_text(content, encoding="utf-8")
        return init_path

    def generate_mesh_init(
        self,
        mesh_dir: Path,
        rooms: list[str]
    ) -> Path:
        """Generate master mesh __init__.py."""
        lines = [
            '"""',
            'AiZQuad Lab — FC_FLOW MESH',
            'Master sovereign entry point.',
            'All rooms. All surfaces. One mesh.',
            '"""',
            '',
        ]

        for room in sorted(rooms):
            room_safe = room.replace("-", "_")
            lines.append(f"from . import {room_safe}  # noqa: F401")

        lines += [
            "",
            "MESH_VERSION = \"1.0\"",
            "",
            "def get_room(name: str):",
            '    """Get a room package by name."""',
            "    import importlib",
            "    safe = name.replace('-', '_')",
            "    return importlib.import_module(f'.{safe}', package=__name__)",
            ""
        ]

        content   = "\n".join(lines)
        init_path = mesh_dir / "__init__.py"
        init_path.write_text(content, encoding="utf-8")
        return init_path


# ─────────────────────────────────────────────
#  DEPENDENCY GRAPH (continued)
# ─────────────────────────────────────────────

class DependencyGraph:
    """
    Builds a directed dependency graph
    from split manifests.
    Topological sort ensures safe wire order.
    Cycle detection prevents broken mesh.
    """

    def build(self, room: str) -> dict[str, list[str]]:
        """Build dependency graph from manifest."""
        graph: dict[str, list[str]] = {}

        for manifest_path in INTEG_INPUT.rglob("manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text())
                for mod in manifest.get("modules", []):
                    name = mod.get("name", "")
                    deps = mod.get("depends_on", [])
                    graph[name] = deps
            except Exception:
                continue

        return graph

    def topological_sort(
        self,
        graph: dict[str, list[str]]
    ) -> tuple[list[str], list[str]]:
        """
        Kahn's algorithm for topological sort.
        Returns (sorted_order, cycle_nodes).
        """
        in_degree: dict[str, int] = {n: 0 for n in graph}
        for node, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1

        # Start with nodes that have no dependencies
        queue  = [n for n, d in in_degree.items() if d == 0]
        order  = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for dep in graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        # If not all nodes were processed, there's a cycle
        cycle_nodes = [n for n in graph if n not in order]
        return order, cycle_nodes

    def detect_cycles(
        self,
        graph: dict[str, list[str]]
    ) -> list[list[str]]:
        """Find all cycles in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in graph.get(node, []):
                if dep not in visited:
                    dfs(dep, path[:])
                elif dep in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    cycles.append(cycle)

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles


# ─────────────────────────────────────────────
#  MESH WIRER
# ─────────────────────────────────────────────

class MeshWirer:
    """
    Wires all rooms together into the final mesh.
    Handles room-to-room connections.
    Creates master entry point.
    Generates integration manifest.
    """

    def __init__(self):
        self.init_gen = InitGenerator()
        self.dep_graph = DependencyGraph()

    def wire_room(
        self,
        room: str,
        source_dir: Path,
        output_dir: Path,
        surface: Optional[dict]
    ) -> dict:
        """Wire a single room into the mesh."""
        room_safe = room.replace("-", "_")
        room_out  = output_dir / room_safe

        # Copy sorted files to mesh output
        if room_out.exists():
            shutil.rmtree(room_out)
        shutil.copytree(source_dir, room_out)

        # Generate __init__.py for each category
        category_dirs = [
            d for d in room_out.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        inits = []
        for cat_dir in category_dirs:
            init = self.init_gen.generate_for_dir(cat_dir, room)
            inits.append(str(init.relative_to(output_dir)))

        # Generate surface file
        if surface:
            surf_gen = SurfaceGenerator()
            surf_file = surf_gen.generate(room, surface, room_out)
            inits.append(str(surf_file.relative_to(output_dir)))

        # Generate room package init
        room_init = self.init_gen.generate_room_init(room_out, room, surface)
        inits.append(str(room_init.relative_to(output_dir)))

        return {
            "room":       room,
            "room_safe":  room_safe,
            "inits":      inits,
            "categories": [d.name for d in category_dirs]
        }

    def wire_mesh(
        self,
        rooms: list[str],
        mesh_dir: Path
    ) -> dict:
        """Wire all rooms into master mesh."""
        mesh_dir.mkdir(parents=True, exist_ok=True)

        # Generate master init
        master_init = self.init_gen.generate_mesh_init(mesh_dir, rooms)

        # Build inter-room dependency graph
        full_graph: dict[str, list[str]] = {}
        for room in rooms:
            room_graph = self.dep_graph.build(room)
            full_graph.update(room_graph)

        # Check for cycles
        order, cycle_nodes = self.dep_graph.topological_sort(full_graph)
        cycles = self.dep_graph.detect_cycles(full_graph)

        manifest = {
            "mesh_version":     "1.0",
            "wired_at":         datetime.now(timezone.utc).isoformat(),
            "rooms":            rooms,
            "dependency_order": order,
            "cycle_detected":   len(cycles) > 0,
            "cycles":           cycles,
            "status":           "wired"
        }

        manifest_path = mesh_dir / "mesh_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest


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
║  AiZQuad Lab — Phase 4: Flow Integrate   ║
║  [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH    ║
╚═══════════════════════════════════════════╝{RESET}""")


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────

def cmd_unlock(session: SessionManager) -> int:
    """Unlock workstation with PIN."""
    if session.unlock():
        return 0
    return 1


def cmd_lock(session: SessionManager) -> int:
    """Lock workstation immediately."""
    session.lock()
    return 0


def cmd_merge(room: str, session: SessionManager) -> int:
    """Merge all versions of a room."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}🔀 Merging versions — {room}{RESET}\n")

    merger     = MergeEngine()
    output_dir = INTEG_MERGE / room

    result = merger.merge_room(room, output_dir)

    if result["status"] != "ok":
        print(f"{RED}✗ Merge failed: {result['status']}{RESET}")
        return 1

    files = result["files"]
    log   = result.get("log", [])

    print(f"  {GREEN}✓ Merged {files} files{RESET}\n")

    # Show merge decisions
    for entry in log[:10]:  # Show first 10
        file_name = entry["file"]
        chosen    = entry["chosen"]
        print(f"  {file_name:<30} {DIM}← {chosen}{RESET}")

    if len(log) > 10:
        print(f"  {DIM}... and {len(log) - 10} more{RESET}")

    audit("MERGE_COMPLETE", room=room, detail=f"{files} files")
    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  MERGE COMPLETE                          ║
╚═══════════════════════════════════════════╝{RESET}

  Room   : {CYAN}{room}{RESET}
  Files  : {files}
  Output : integration/merge/{room}/
  Next   : {DIM}make integrate seal ROOM={room}{RESET}
""")
    return 0


def cmd_seal(room: str, session: SessionManager) -> int:
    """Seal merged logic with signature."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}🔒 Sealing logic — {room}{RESET}\n")

    source_dir = INTEG_MERGE / room
    if not source_dir.exists():
        print(f"{RED}✗ No merged output found{RESET}")
        print(f"{DIM}  Run: make integrate merge ROOM={room}{RESET}")
        return 1

    locker = LogicLock()
    record = locker.seal(room, source_dir)

    sig     = record["signature"]
    surface = record["surface"]

    print(f"  {GREEN}✓ Logic sealed{RESET}")
    print(f"  {GREEN}✓ Signature: {DIM}{sig[:32]}...{RESET}")
    print(f"  {GREEN}✓ Surface extracted: {len(surface)} files{RESET}")

    audit("SEAL_COMPLETE", room=room, detail=f"sig={sig[:16]}")

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  LOGIC SEALED — SOVEREIGN APPROVED       ║
╚═══════════════════════════════════════════╝{RESET}

  Room      : {CYAN}{room}{RESET}
  Signature : {DIM}{sig[:32]}...{RESET}
  Status    : {GREEN}🔒 SEALED{RESET}
  Lock file : integration/logic_locks/{room}.logic.json
  Next      : {DIM}make integrate surface ROOM={room}{RESET}
""")
    return 0


def cmd_surface(room: str, session: SessionManager) -> int:
    """Generate AI surface file."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}📄 Generating surface — {room}{RESET}\n")

    locker  = LogicLock()
    surface = locker.get_surface(room)

    if not surface:
        print(f"{RED}✗ No logic lock found{RESET}")
        print(f"{DIM}  Run: make integrate seal ROOM={room}{RESET}")
        return 1

    room_safe  = room.replace("-", "_")
    output_dir = INTEG_OUTPUT / room_safe
    surf_gen   = SurfaceGenerator()
    surf_file  = surf_gen.generate(room, surface, output_dir)

    print(f"  {GREEN}✓ Surface generated{RESET}")
    print(f"  {DIM}{surf_file.relative_to(ROOT)}{RESET}")

    audit("SURFACE_GENERATED", room=room)

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  SURFACE GENERATED                       ║
╚═══════════════════════════════════════════╝{RESET}

  Room    : {CYAN}{room}{RESET}
  File    : {surf_file.name}
  Entries : {sum(len(v) for v in surface.values())}
  Next    : {DIM}make integrate wire ROOM={room}{RESET}
""")
    return 0


def cmd_wire(room: str, session: SessionManager) -> int:
    """Wire room into the mesh."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}🔌 Wiring into mesh — {room}{RESET}\n")

    # Get sorted source
    source_dir = INTEG_INPUT / room
    if not source_dir.exists():
        source_dir = SORT_OUTPUT / room
    if not source_dir.exists():
        print(f"{RED}✗ No sorted output found{RESET}")
        print(f"{DIM}  Run: make sort ROOM={room}{RESET}")
        return 1

    # Get surface
    locker  = LogicLock()
    surface = locker.get_surface(room)

    # Wire it
    wirer  = MeshWirer()
    result = wirer.wire_room(room, source_dir, INTEG_OUTPUT, surface)

    inits = result["inits"]
    cats  = result["categories"]

    print(f"  {GREEN}✓ Room wired into mesh{RESET}")
    print(f"  {GREEN}✓ Generated {len(inits)} __init__.py files{RESET}")
    print(f"  {GREEN}✓ Categories: {', '.join(cats)}{RESET}")

    # Wire full mesh
    all_rooms = [
        d.name for d in INTEG_OUTPUT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    mesh_manifest = wirer.wire_mesh(all_rooms, INTEG_OUTPUT)

    if mesh_manifest.get("cycle_detected"):
        cycles = mesh_manifest.get("cycles", [])
        print(f"\n  {YELLOW}⚠ Circular dependencies detected:{RESET}")
        for cycle in cycles[:3]:
            print(f"    {' → '.join(cycle)}")

    audit("WIRE_COMPLETE", room=room, detail=f"cats={len(cats)}")

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  WIRE COMPLETE                           ║
╚═══════════════════════════════════════════╝{RESET}

  Room       : {CYAN}{room}{RESET}
  Categories : {len(cats)}
  Mesh rooms : {len(all_rooms)}
  Output     : integration/output/mesh/
  Next       : {DIM}make build{RESET}
""")
    return 0


def cmd_verify(room: str, session: SessionManager) -> int:
    """Verify logic lock integrity."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}🔍 Verifying logic lock — {room}{RESET}\n")

    source_dir = INTEG_MERGE / room
    if not source_dir.exists():
        print(f"{RED}✗ No merged source found{RESET}")
        return 1

    locker        = LogicLock()
    valid, reason = locker.verify(room, source_dir)

    if valid:
        print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  INTEGRITY VERIFIED — SOVEREIGN          ║
╚═══════════════════════════════════════════╝{RESET}

  Room   : {CYAN}{room}{RESET}
  Status : {GREEN}✅ UNTAMPERED{RESET}
""")
        return 0
    else:
        print(f"""
{RED}{BOLD}╔═══════════════════════════════════════════╗
║  INTEGRITY FAILED — TAMPERING DETECTED   ║
╚═══════════════════════════════════════════╝{RESET}

  Room   : {CYAN}{room}{RESET}
  Reason : {reason}
  Status : {RED}❌ COMPROMISED{RESET}

  The sealed logic has been modified.
  Re-seal if changes are approved.
""")
        return 1


def cmd_access(room: str, action: str, session: SessionManager) -> int:
    """Manage AI access to a room."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()

    ai_control = AIAccessControl()

    if action == "grant":
        ai_control.interactive_grant(room)
    elif action == "deny":
        ai_control.revoke(room)
        print(f"\n  {GREEN}✓ AI access denied for {room}{RESET}\n")
    elif action == "revoke":
        ai_control.revoke(room)
        print(f"\n  {GREEN}✓ AI access revoked for {room}{RESET}\n")
    else:
        print(f"{RED}✗ Unknown action: {action}{RESET}")
        print(f"{DIM}  Use: grant, deny, or revoke{RESET}")
        return 1

    return 0


def cmd_audit(room: str, session: SessionManager) -> int:
    """Show audit log for a room."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}📋 Audit log — {room}{RESET}\n")

    if not AUDIT_FILE.exists():
        print(f"  {DIM}No audit entries yet{RESET}\n")
        return 0

    entries = []
    with open(AUDIT_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("room") == room or room == "all":
                    entries.append(entry)
            except Exception:
                continue

    if not entries:
        print(f"  {DIM}No entries for {room}{RESET}\n")
        return 0

    print(f"  {'TIMESTAMP':<20} {'ACTION':<22} DETAIL")
    print(f"  {'─'*20} {'─'*22} {'─'*30}")

    for entry in entries[-50:]:  # Last 50
        ts     = entry["ts"][:19].replace("T", " ")
        action = entry["action"]
        detail = entry.get("detail", "")[:35]
        print(f"  {ts} {action:<22} {DIM}{detail}{RESET}")

    print(f"\n  Total: {len(entries)} entries\n")
    return 0


def cmd_build(room: str, session: SessionManager) -> int:
    """Run full integration pipeline for a room."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}🏗  Full integration — {room}{RESET}\n")

    steps = [
        ("merge",   cmd_merge),
        ("seal",    cmd_seal),
        ("surface", cmd_surface),
        ("wire",    cmd_wire),
    ]

    for step_name, step_func in steps:
        print(f"  {CYAN}▶{RESET} Running: {step_name}")
        result = step_func(room, session)
        if result != 0:
            print(f"\n{RED}✗ Pipeline failed at step: {step_name}{RESET}\n")
            return 1
        print()

    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  INTEGRATION COMPLETE                    ║
╚═══════════════════════════════════════════╝{RESET}

  Room   : {CYAN}{room}{RESET}
  Status : {GREEN}✅ WIRED INTO MESH{RESET}
  Output : integration/output/mesh/{room.replace('-', '_')}/
""")
    return 0


def cmd_status(session: SessionManager) -> int:
    """Show integration status."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}📊 Integration Status{RESET}\n")

    # Locked rooms
    if INTEG_LOCKS.exists():
        locks = list(INTEG_LOCKS.glob("*.logic.json"))
        if locks:
            print(f"  {CYAN}{BOLD}Logic Locks{RESET}")
            for lock_file in sorted(locks):
                room = lock_file.stem.replace(".logic", "")
                try:
                    record = json.loads(lock_file.read_text())
                    sig    = record.get("signature", "?")[:16]
                    sealed = record.get("sealed_at", "?")[:10]
                    print(f"    🔒 {room:<15} {DIM}{sig}... {sealed}{RESET}")
                except Exception:
                    print(f"    ❌ {room:<15} {DIM}corrupted{RESET}")
            print()

    # AI Access
    ai_control = AIAccessControl()
    access_data = ai_control._load()
    if access_data:
        print(f"  {CYAN}{BOLD}AI Access{RESET}")
        for room, record in sorted(access_data.items()):
            if record.get("active"):
                level = record.get("level", "?")
                color = GREEN if level == "surface" else YELLOW
                print(f"    {color}✓{RESET} {room:<15} {level}")
            else:
                print(f"    {DIM}✗{RESET} {room:<15} {DIM}revoked{RESET}")
        print()

    # Wired rooms
    if INTEG_OUTPUT.exists():
        rooms = [d for d in INTEG_OUTPUT.iterdir() 
                 if d.is_dir() and not d.name.startswith(".")]
        if rooms:
            print(f"  {CYAN}{BOLD}Wired Rooms{RESET}")
            for room_dir in sorted(rooms):
                init = room_dir / "__init__.py"
                if init.exists():
                    print(f"    🔌 {room_dir.name}")
            print()

    # Session info
    if session.is_unlocked():
        try:
            sess = json.loads(SESSION_FILE.read_text())
            created = datetime.fromtimestamp(sess["created_at"])
            expires = datetime.fromtimestamp(sess["expires_at"])
            now     = datetime.now()
            remaining = expires - now
            hours = int(remaining.total_seconds() // 3600)
            mins  = int((remaining.total_seconds() % 3600) // 60)
            
            print(f"  {CYAN}{BOLD}Session{RESET}")
            print(f"    Status : {GREEN}ACTIVE{RESET}")
            print(f"    Time   : {hours}h {mins}m remaining")
        except Exception:
            pass

    print()
    return 0


def cmd_list(session: SessionManager) -> int:
    """List all integrated rooms."""
    if not session.require_session():
        return 1

    session.refresh()
    print_banner()
    print(f"\n{BOLD}📋 All Integrated Rooms{RESET}\n")

    if not INTEG_OUTPUT.exists():
        print(f"  {DIM}No rooms integrated yet{RESET}\n")
        return 0

    rooms = [d for d in INTEG_OUTPUT.iterdir() 
             if d.is_dir() and not d.name.startswith(".")]

    if not rooms:
        print(f"  {DIM}No rooms integrated yet{RESET}\n")
        return 0

    for room_dir in sorted(rooms):
        room = room_dir.name.replace("_", "-")
        
        # Check lock status
        lock_file = INTEG_LOCKS / f"{room}.logic.json"
        lock_status = "🔒" if lock_file.exists() else "🔓"
        
        # Check AI access
        ai_control = AIAccessControl()
        ai_level   = ai_control.status(room)
        ai_status  = f"{GREEN}AI:surface{RESET}" if ai_level == "surface" \
                     else f"{YELLOW}AI:read{RESET}" if ai_level == "read" \
                     else f"{DIM}AI:none{RESET}"
        
        # Count categories
        cats = [d for d in room_dir.iterdir() 
                if d.is_dir() and not d.name.startswith("_")]
        
        print(f"  {lock_status} {room:<15} {len(cats)} cats  {ai_status}")

    print()
    return 0


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def usage():
    print(f"""
{CYAN}Usage:{RESET}
  python3 flow_integrate.py unlock
  python3 flow_integrate.py lock
  python3 flow_integrate.py build     <room>
  python3 flow_integrate.py merge     <room>
  python3 flow_integrate.py seal      <room>
  python3 flow_integrate.py surface   <room>
  python3 flow_integrate.py wire      <room>
  python3 flow_integrate.py verify    <room>
  python3 flow_integrate.py access    <room> <grant|deny|revoke>
  python3 flow_integrate.py audit     <room>
  python3 flow_integrate.py status
  python3 flow_integrate.py list

{CYAN}Examples:{RESET}
  # First time
  python3 flow_integrate.py unlock

  # Full pipeline
  python3 flow_integrate.py build room-2

  # Step by step
  python3 flow_integrate.py merge   room-2
  python3 flow_integrate.py seal    room-2
  python3 flow_integrate.py surface room-2
  python3 flow_integrate.py wire    room-2

  # AI Access
  python3 flow_integrate.py access room-2 grant
  python3 flow_integrate.py access room-2 revoke

  # Verify integrity
  python3 flow_integrate.py verify room-2

  # Lock when done
  python3 flow_integrate.py lock
""")


def main() -> int:
    args    = sys.argv[1:]
    session = SessionManager()

    if not args:
        usage()
        return 0

    command = args[0].lower()

    # unlock and lock don't require existing session
    if command == "unlock":
        return cmd_unlock(session)

    elif command == "lock":
        return cmd_lock(session)

    # All other commands require session
    elif command == "build":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py build <room>{RESET}")
            return 1
        return cmd_build(args[1], session)

    elif command == "merge":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py merge <room>{RESET}")
            return 1
        return cmd_merge(args[1], session)

    elif command == "seal":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py seal <room>{RESET}")
            return 1
        return cmd_seal(args[1], session)

    elif command == "surface":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py surface <room>{RESET}")
            return 1
        return cmd_surface(args[1], session)

    elif command == "wire":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py wire <room>{RESET}")
            return 1
        return cmd_wire(args[1], session)

    elif command == "verify":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py verify <room>{RESET}")
            return 1
        return cmd_verify(args[1], session)

    elif command == "access":
        if len(args) < 3:
            print(f"{RED}✗ Usage: flow_integrate.py access <room> <grant|deny|revoke>{RESET}")
            return 1
        return cmd_access(args[1], args[2], session)

    elif command == "audit":
        if len(args) < 2:
            print(f"{RED}✗ Usage: flow_integrate.py audit <room>{RESET}")
            return 1
        return cmd_audit(args[1], session)

    elif command == "status":
        return cmd_status(session)

    elif command == "list":
        return cmd_list(session)

    else:
        print(f"{RED}✗ Unknown command: {command}{RESET}")
        usage()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Interrupted{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}✗ Fatal error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    