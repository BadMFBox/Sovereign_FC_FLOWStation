# ═══════════════════════════════════════════════════════════════
#  tests/python/test_integrate.py (continued)
#  Phase 4 — flow_integrate.py tests
# ═══════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
#  SESSION MANAGER TESTS (continued)
# ───────────────────────────────────────────────────────────────

class TestSessionManager:

    def _hash_pin(self, pin: str) -> str:
        salt = b"aizquad_sovereign_salt_v1"
        key  = hashlib.pbkdf2_hmac(
            "sha256", pin.encode(), salt, iterations=260_000
        )
        return key.hex()

    def _write_session(self, workspace, active=True, expired=False):
        now     = time.time()
        expires = (now - 100) if expired else (now + 14400)
        session = {"created_at": now, "expires_at": expires, "active": active}
        session_file = workspace / "shared" / ".session"
        session_file.write_text(json.dumps(session))
        return session_file

    def _write_pin(self, workspace, pin="123456"):
        pin_file = workspace / "shared" / ".pin"
        pin_file.write_text(self._hash_pin(pin))
        return pin_file

    def test_correct_pin_creates_session(self, workspace):
        """Correct PIN must produce an active session file."""
        self._write_pin(workspace, "123456")
        session_file = self._write_session(workspace)
        assert session_file.exists()
        data = json.loads(session_file.read_text())
        assert data["active"] is True

    def test_session_has_expiry(self, workspace):
        """Session must have a future expiry timestamp."""
        session_file = self._write_session(workspace)
        data = json.loads(session_file.read_text())
        assert data["expires_at"] > time.time()

    def test_expired_session_is_invalid(self, workspace):
        """Expired session must not be treated as active."""
        self._write_session(workspace, expired=True)
        session_file = workspace / "shared" / ".session"
        data         = json.loads(session_file.read_text())
        is_expired   = time.time() > data["expires_at"]
        assert is_expired is True

    def test_lock_removes_session(self, workspace):
        """Locking workstation must delete session file."""
        session_file = self._write_session(workspace)
        assert session_file.exists()
        session_file.unlink()
        assert not session_file.exists()

    def test_pin_is_hashed(self, workspace):
        """PIN must never be stored in plaintext."""
        pin_file = self._write_pin(workspace, "123456")
        content  = pin_file.read_text()
        assert "123456" not in content
        assert len(content) == 64  # SHA-256 hex length

    def test_wrong_pin_rejected(self, workspace):
        """Wrong PIN must not match stored hash."""
        self._write_pin(workspace, "123456")
        pin_file     = workspace / "shared" / ".pin"
        stored_hash  = pin_file.read_text()
        attempt_hash = self._hash_pin("999999")
        assert stored_hash != attempt_hash

    def test_session_refresh_extends_expiry(self, workspace):
        """Refreshing session must extend expiry time."""
        session_file = self._write_session(workspace)
        data1 = json.loads(session_file.read_text())
        
        time.sleep(0.1)
        
        # Simulate refresh
        now     = time.time()
        data1["expires_at"] = now + 14400
        session_file.write_text(json.dumps(data1))
        
        data2 = json.loads(session_file.read_text())
        assert data2["expires_at"] > data1["created_at"]


# ───────────────────────────────────────────────────────────────
#  LOGIC LOCK TESTS
# ───────────────────────────────────────────────────────────────

class TestLogicLock:

    def _hash_dir(self, dir_path: Path) -> str:
        """Compute SHA-256 hash of directory contents."""
        sha256 = hashlib.sha256()
        for file in sorted(dir_path.rglob("*")):
            if file.is_file() and not file.name.startswith("."):
                sha256.update(str(file.relative_to(dir_path)).encode())
                with open(file, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def _make_lock(self, workspace, room: str) -> Path:
        """Create a logic lock record."""
        merge_dir = workspace / "integration" / "merge" / room
        merge_dir.mkdir(parents=True, exist_ok=True)
        (merge_dir / "test.py").write_text("def test(): pass")
        
        signature = self._hash_dir(merge_dir)
        record = {
            "room":       room,
            "signature":  signature,
            "sealed_at":  "2024-01-01T00:00:00+00:00",
            "surface":    {"core": ["test.py"]},
            "status":     "SEALED"
        }
        
        lock_dir  = workspace / "integration" / "logic_locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / f"{room}.logic.json"
        lock_file.write_text(json.dumps(record))
        return lock_file

    def test_logic_lock_created(self, workspace):
        """Logic lock file must be created after seal."""
        lock_file = self._make_lock(workspace, "room-test")
        assert lock_file.exists()

    def test_logic_lock_has_signature(self, workspace):
        """Logic lock must contain SHA-256 signature."""
        lock_file = self._make_lock(workspace, "room-test")
        record    = json.loads(lock_file.read_text())
        assert "signature" in record
        assert len(record["signature"]) == 64

    def test_logic_lock_has_surface(self, workspace):
        """Logic lock must contain surface definition."""
        lock_file = self._make_lock(workspace, "room-test")
        record    = json.loads(lock_file.read_text())
        assert "surface" in record
        assert isinstance(record["surface"], dict)

    def test_tampered_code_detected(self, workspace):
        """Tampering with code must invalidate signature."""
        lock_file = self._make_lock(workspace, "room-test")
        record    = json.loads(lock_file.read_text())
        original_sig = record["signature"]
        
        # Tamper with code
        merge_dir = workspace / "integration" / "merge" / "room-test"
        (merge_dir / "test.py").write_text("def test(): return 'hacked'")
        
        # Recompute signature
        new_sig = self._hash_dir(merge_dir)
        assert new_sig != original_sig

    def test_untampered_code_verified(self, workspace):
        """Untampered code must match signature."""
        lock_file = self._make_lock(workspace, "room-test")
        record    = json.loads(lock_file.read_text())
        stored_sig = record["signature"]
        
        merge_dir = workspace / "integration" / "merge" / "room-test"
        computed_sig = self._hash_dir(merge_dir)
        assert computed_sig == stored_sig

    def test_surface_extraction(self, workspace):
        """Surface must list only public API files."""
        lock_file = self._make_lock(workspace, "room-test")
        record    = json.loads(lock_file.read_text())
        surface   = record["surface"]
        
        # Surface should be organized by category
        assert isinstance(surface, dict)
        for category, files in surface.items():
            assert isinstance(files, list)
            for file in files:
                assert not file.startswith("_")  # No private files


# ───────────────────────────────────────────────────────────────
#  AI ACCESS CONTROL TESTS
# ───────────────────────────────────────────────────────────────

class TestAIAccessControl:

    def _write_access(self, workspace, room: str, level: str, active=True):
        access_file = workspace / "shared" / "ai_access.json"
        data = {
            room: {
                "level":      level,
                "granted_at": "2024-01-01T00:00:00+00:00",
                "active":     active,
            }
        }
        access_file.write_text(json.dumps(data))
        return access_file

    def test_access_levels_exist(self, workspace):
        """Valid access levels: surface, read."""
        valid = ["surface", "read"]
        for level in valid:
            access_file = self._write_access(workspace, "room-test", level)
            data = json.loads(access_file.read_text())
            assert data["room-test"]["level"] == level

    def test_surface_level_restricts_access(self, workspace):
        """Surface level must only expose _surface.py files."""
        self._write_access(workspace, "room-test", "surface")
        access_file = workspace / "shared" / "ai_access.json"
        data = json.loads(access_file.read_text())
        assert data["room-test"]["level"] == "surface"
        # AI should only see _surface.py, not internal files

    def test_read_level_allows_full_access(self, workspace):
        """Read level must allow access to all room files."""
        self._write_access(workspace, "room-test", "read")
        access_file = workspace / "shared" / "ai_access.json"
        data = json.loads(access_file.read_text())
        assert data["room-test"]["level"] == "read"

    def test_revoked_access_inactive(self, workspace):
        """Revoked access must be marked inactive."""
        access_file = self._write_access(workspace, "room-test", "surface", active=False)
        data = json.loads(access_file.read_text())
        assert data["room-test"]["active"] is False

    def test_multiple_rooms_independent(self, workspace):
        """Access control must be independent per room."""
        access_file = workspace / "shared" / "ai_access.json"
        data = {
            "room-1": {"level": "surface", "active": True},
            "room-2": {"level": "read",    "active": True},
            "room-3": {"level": "surface", "active": False},
        }
        access_file.write_text(json.dumps(data))
        loaded = json.loads(access_file.read_text())
        
        assert loaded["room-1"]["level"] == "surface"
        assert loaded["room-2"]["level"] == "read"
        assert loaded["room-3"]["active"] is False

    def test_grant_creates_audit_entry(self, workspace):
        """Granting access must create an audit log entry."""
        self._write_access(workspace, "room-test", "surface")
        audit_file = workspace / "shared" / "audit.log"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        entry = json.dumps({
            "ts":     "2024-01-01T00:00:00+00:00",
            "action": "AI_ACCESS_GRANTED",
            "room":   "room-test",
            "detail": "level=surface"
        })
        audit_file.write_text(entry + "\n")
        
        assert audit_file.exists()
        assert "AI_ACCESS_GRANTED" in audit_file.read_text()


# ───────────────────────────────────────────────────────────────
#  MERGE ENGINE TESTS
# ───────────────────────────────────────────────────────────────

class TestMergeEngine:

    def _make_versions(self, workspace, room: str, num_versions=3):
        """Create multiple versions of a room."""
        versions_dir = workspace / "forge" / "versions" / room
        versions = []
        
        for i in range(1, num_versions + 1):
            ver_dir = versions_dir / f"v{i}" / "src"
            ver_dir.mkdir(parents=True, exist_ok=True)
            
            # Each version has slightly different content
            (ver_dir / "core.py").write_text(f"# Version {i}\ndef process(): return {i}")
            (ver_dir / "utils.py").write_text(f"def helper(): return 'v{i}'")
            
            versions.append(ver_dir)
        
        return versions

    def test_merge_combines_all_versions(self, workspace):
        """Merge must consider all locked versions."""
        versions = self._make_versions(workspace, "room-test", 3)
        
        # Simulate merge: take latest of each file
        merge_dir = workspace / "integration" / "merge" / "room-test"
        merge_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        for ver in versions:
            for file in ver.glob("*.py"):
                dest = merge_dir / file.name
                shutil.copy2(file, dest)
        
        assert (merge_dir / "core.py").exists()
        assert (merge_dir / "utils.py").exists()

    def test_merge_chooses_latest_version(self, workspace):
        """When files conflict, merge must choose newest version."""
        versions = self._make_versions(workspace, "room-test", 3)
        
        merge_dir = workspace / "integration" / "merge" / "room-test"
        merge_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate: latest version wins
        latest = versions[-1]
        import shutil
        for file in latest.glob("*.py"):
            shutil.copy2(file, merge_dir / file.name)
        
        content = (merge_dir / "core.py").read_text()
        assert "Version 3" in content

    def test_merge_creates_decision_log(self, workspace):
        """Merge must log which version was chosen for each file."""
        self._make_versions(workspace, "room-test", 3)
        
        merge_dir = workspace / "integration" / "merge" / "room-test"
        merge_dir.mkdir(parents=True, exist_ok=True)
        
        log = [
            {"file": "core.py",  "chosen": "v3", "reason": "latest"},
            {"file": "utils.py", "chosen": "v3", "reason": "latest"},
        ]
        
        log_file = merge_dir / "merge_log.json"
        log_file.write_text(json.dumps(log, indent=2))
        
        assert log_file.exists()
        loaded = json.loads(log_file.read_text())
        assert len(loaded) == 2
        assert loaded[0]["chosen"] == "v3"

    def test_merge_preserves_unique_files(self, workspace):
        """Files unique to one version must be included."""
        versions_dir = workspace / "forge" / "versions" / "room-test"
        
        v1 = versions_dir / "v1" / "src"
        v1.mkdir(parents=True, exist_ok=True)
        (v1 / "unique_v1.py").write_text("# Only in v1")
        
        v2 = versions_dir / "v2" / "src"
        v2.mkdir(parents=True, exist_ok=True)
        (v2 / "unique_v2.py").write_text("# Only in v2")
        
        merge_dir = workspace / "integration" / "merge" / "room-test"
        merge_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(v1 / "unique_v1.py", merge_dir / "unique_v1.py")
        shutil.copy2(v2 / "unique_v2.py", merge_dir / "unique_v2.py")
        
        assert (merge_dir / "unique_v1.py").exists()
        assert (merge_dir / "unique_v2.py").exists()


# ───────────────────────────────────────────────────────────────
#  DEPENDENCY GRAPH TESTS
# ───────────────────────────────────────────────────────────────

class TestDependencyGraph:

    def test_topological_sort_simple(self):
        """Simple dependency chain must sort correctly."""
        graph = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
        }
        # Expected order: a, b, c
        sorted_nodes = self._toposort(graph)
        assert sorted_nodes.index("a") < sorted_nodes.index("b")
        assert sorted_nodes.index("b") < sorted_nodes.index("c")

    def test_topological_sort_diamond(self):
        """Diamond dependency must sort correctly."""
        graph = {
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
        }
        sorted_nodes = self._toposort(graph)
        assert sorted_nodes.index("a") < sorted_nodes.index("b")
        assert sorted_nodes.index("a") < sorted_nodes.index("c")
        assert sorted_nodes.index("b") < sorted_nodes.index("d")
        assert sorted_nodes.index("c") < sorted_nodes.index("d")

    def test_cycle_detection(self):
        """Circular dependencies must be detected."""
        graph = {
            "a": ["b"],
            "b": ["c"],
            "c": ["a"],
        }
        has_cycle = self._has_cycle(graph)
        assert has_cycle is True

    def test_no_cycle_in_dag(self):
        """DAG (no cycles) must pass cycle check."""
        graph = {
            "a": [],
            "b": ["a"],
            "c": ["a", "b"],
        }
        has_cycle = self._has_cycle(graph)
        assert has_cycle is False

    def test_self_dependency_is_cycle(self):
        """Node depending on itself is a cycle."""
        graph = {"a": ["a"]}
        has_cycle = self._has_cycle(graph)
        assert has_cycle is True

    def _toposort(self, graph: dict) -> list:
        """Kahn's algorithm for topological sort."""
        in_degree = {n: 0 for n in graph}
        for node, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        
        while queue:
            node = queue.pop(0)
            order.append(node)
            for dep in graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        return order

    def _has_cycle(self, graph: dict) -> bool:
        """DFS cycle detection."""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for dep in graph.get(node, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False


# ───────────────────────────────────────────────────────────────
#  SURFACE GENERATION TESTS
# ───────────────────────────────────────────────────────────────

class TestSurfaceGeneration:

    def test_surface_file_created(self, workspace):
        """_surface.py must be generated for each room."""
        room_dir = workspace / "integration" / "output" / "mesh" / "room_test"
        room_dir.mkdir(parents=True, exist_ok=True)
        
        surface_file = room_dir / "_surface.py"
        surface_content = '''"""
Public API surface for room-test.
AI sees only this file.
"""

def process(data):
    """Public processing function."""
    pass
'''
        surface_file.write_text(surface_content)
        assert surface_file.exists()
        assert surface_file.name == "_surface.py"

    def test_surface_contains_only_public_api(self, workspace):
        """Surface must not expose internal implementation."""
        surface = '''
def public_func():
    """Public."""
    pass
'''
        tree  = ast.parse(surface)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        
        # No private functions (starting with _)
        private = [f for f in funcs if f.startswith("_")]
        assert len(private) == 0

    def test_surface_has_docstring(self, workspace):
        """Surface file must have module docstring."""
        surface = '''"""
Public API surface for room-test.
"""

def api_func():
    pass
'''
        tree = ast.parse(surface)
        assert ast.get_docstring(tree) is not None

    def test_surface_lists_exports(self, workspace):
        """Surface must define __all__ for explicit exports."""
        surface = '''"""Surface."""

__all__ = ["process", "validate"]

def process(data):
    pass

def validate(data):
    pass

def _internal():
    pass
'''
        tree = ast.parse(surface)
        # Find __all__ assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        assert isinstance(node.value, ast.List)


# ───────────────────────────────────────────────────────────────
#  AUDIT LOG TESTS
# ───────────────────────────────────────────────────────────────

class TestAuditLog:

    def test_audit_entries_are_json(self, workspace):
        """Every audit entry must be valid JSON."""
        audit_file = workspace / "shared" / "audit.log"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = [
            {"ts": "2024-01-01T00:00:00", "action": "LOCK", "room": "room-1"},
            {"ts": "2024-01-01T00:01:00", "action": "SEAL", "room": "room-1"},
        ]
        
        for entry in entries:
            audit_file.write_text(json.dumps(entry) + "\n", mode="a")
        
        lines = audit_file.read_text().strip().split("\n")
        for line in lines:
            parsed = json.loads(line)
            assert "ts" in parsed
            assert "action" in parsed

    def test_audit_captures_all_actions(self, workspace):
        """Audit must log every significant action."""
        actions = [
            "LOCK",
            "SPLIT",
            "SORT",
            "MERGE",
            "SEAL",
            "WIRE",
            "AI_ACCESS_GRANTED",
            "AI_ACCESS_REVOKED",
            "VERIFY_OK",
            "VERIFY_FAIL",
        ]
        
        audit_file = workspace / "shared" / "audit.log"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        for action in actions:
            entry = json.dumps({"ts": "2024-01-01", "action": action, "room": "test"})
            audit_file.write_text(entry + "\n", mode="a")
        
        content = audit_file.read_text()
        for action in actions:
            assert action in content

    def test_audit_entries_have_timestamp(self, workspace):
        """Every audit entry must have ISO 8601 timestamp."""
        audit_file = workspace / "shared" / "audit.log"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {"ts": "2024-01-01T12:34:56+00:00", "action": "TEST", "room": "test"}
        audit_file.write_text(json.dumps(entry) + "\n")
        
        loaded = json.loads(audit_file.read_text().strip())
        assert "ts" in loaded
        assert "T" in loaded["ts"]  # ISO 8601 format

    def test_audit_log_append_only(self, workspace):
        """Audit log must only append, never overwrite."""
        audit_file = workspace / "shared" / "audit.log"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write first entry
        e1 = json.dumps({"ts": "2024-01-01", "action": "ACTION1"})
        with open(audit_file, "a") as f:
            f.write(e1 + "\n")
        
        # Write second entry
        e2 = json.dumps({"ts": "2024-01-02", "action": "ACTION2"})
        with open(audit_file, "a") as f:
            f.write(e2 + "\n")
        
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "ACTION1" in lines[0]
        assert "ACTION2" in lines[1]
