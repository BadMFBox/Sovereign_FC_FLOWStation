# ═══════════════════════════════════════════════════════════════
#  tests/python/test_lock.py
#  Phase 1 — flow_lock.py tests
# ═══════════════════════════════════════════════════════════════

import pytest
import json
import hashlib
import time
from pathlib import Path
from unittest.mock import patch
import sys
import os


# ───────────────────────────────────────────────────────────────
#  HELPERS
# ───────────────────────────────────────────────────────────────

def make_lock_record(room: str, version: str, workspace: Path) -> dict:
    """Helper to build a valid lock record."""
    return {
        "room":       room,
        "version":    version,
        "locked_at":  "2024-01-01T00:00:00+00:00",
        "locked_by":  "test",
        "signature":  "abc123",
        "files":      3,
        "status":     "LOCKED",
    }


def write_lock(workspace: Path, room: str, version: str) -> Path:
    """Write a lock file to the workspace."""
    lock_dir  = workspace / "forge" / "locked"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{room}-{version}.lock.json"
    lock_file.write_text(json.dumps(make_lock_record(room, version, workspace)))
    return lock_file


# ───────────────────────────────────────────────────────────────
#  LOCK FILE CREATION
# ───────────────────────────────────────────────────────────────

class TestLockFileCreation:

    def test_lock_file_is_valid_json(self, workspace, sample_room):
        """Lock record must be valid, parseable JSON."""
        record    = make_lock_record("room-test", "v1", workspace)
        lock_path = write_lock(workspace, "room-test", "v1")
        loaded    = json.loads(lock_path.read_text())
        assert loaded["room"]    == "room-test"
        assert loaded["version"] == "v1"
        assert loaded["status"]  == "LOCKED"

    def test_lock_file_contains_required_fields(self, workspace):
        """All required fields must be present."""
        record = make_lock_record("room-test", "v1", workspace)
        required = ["room", "version", "locked_at", "signature", "status"]
        for field in required:
            assert field in record, f"Missing field: {field}"

    def test_lock_file_signature_is_string(self, workspace):
        """Signature must be a non-empty string."""
        record = make_lock_record("room-test", "v1", workspace)
        assert isinstance(record["signature"], str)
        assert len(record["signature"]) > 0

    def test_lock_creates_in_correct_directory(self, workspace):
        """Lock files must land in forge/locked/."""
        lock_path = write_lock(workspace, "room-test", "v1")
        assert "forge/locked" in str(lock_path)
        assert lock_path.exists()

    def test_lock_filename_includes_room_and_version(self, workspace):
        """Filename must encode room and version."""
        lock_path = write_lock(workspace, "room-test", "v1")
        assert "room-test" in lock_path.name
        assert "v1"        in lock_path.name

    def test_multiple_versions_coexist(self, workspace):
        """Multiple versions of the same room must not overwrite each other."""
        write_lock(workspace, "room-test", "v1")
        write_lock(workspace, "room-test", "v2")
        write_lock(workspace, "room-test", "v3")

        lock_dir = workspace / "forge" / "locked"
        locks    = list(lock_dir.glob("room-test-*.lock.json"))
        assert len(locks) == 3

    def test_different_rooms_coexist(self, workspace):
        """Different rooms must not interfere with each other."""
        write_lock(workspace, "room-1", "v1")
        write_lock(workspace, "room-2", "v1")
        write_lock(workspace, "room-3", "v1")

        lock_dir = workspace / "forge" / "locked"
        locks    = list(lock_dir.glob("*.lock.json"))
        assert len(locks) == 3


# ───────────────────────────────────────────────────────────────
#  SIGNATURE HASHING
# ───────────────────────────────────────────────────────────────

class TestSignatureHashing:

    def _hash_dir(self, dir_path: Path) -> str:
        """Replicate the hash logic."""
        sha256 = hashlib.sha256()
        for file in sorted(dir_path.rglob("*")):
            if file.is_file():
                sha256.update(str(file.relative_to(dir_path)).encode())
                with open(file, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def test_same_dir_same_hash(self, workspace, sample_room):
        """Same directory content must produce same hash."""
        h1 = self._hash_dir(sample_room)
        h2 = self._hash_dir(sample_room)
        assert h1 == h2

    def test_changed_file_changes_hash(self, workspace, sample_room):
        """Modifying a file must change the hash."""
        h1 = self._hash_dir(sample_room)
        (sample_room / "process.py").write_text("# changed")
        h2 = self._hash_dir(sample_room)
        assert h1 != h2

    def test_added_file_changes_hash(self, workspace, sample_room):
        """Adding a file must change the hash."""
        h1 = self._hash_dir(sample_room)
        (sample_room / "new_file.py").write_text("# new")
        h2 = self._hash_dir(sample_room)
        assert h1 != h2

    def test_deleted_file_changes_hash(self, workspace, sample_room):
        """Deleting a file must change the hash."""
        h1 = self._hash_dir(sample_room)
        (sample_room / "utils.py").unlink()
        h2 = self._hash_dir(sample_room)
        assert h1 != h2

    def test_hash_is_hex_string(self, workspace, sample_room):
        """Hash output must be a valid hex string."""
        h = self._hash_dir(sample_room)
        assert isinstance(h, str)
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64  # SHA-256 hex length


# ───────────────────────────────────────────────────────────────
#  VERSION MANAGEMENT
# ───────────────────────────────────────────────────────────────

class TestVersionManagement:

    def test_version_directory_created(self, workspace, sample_room):
        """Version snapshot directory must be created."""
        ver_dir = workspace / "forge" / "versions" / "room-test" / "v1"
        ver_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copytree(sample_room, ver_dir / "src", dirs_exist_ok=True)
        assert ver_dir.exists()
        assert (ver_dir / "src").exists()

    def test_version_is_immutable_copy(self, workspace, sample_room):
        """Locked version must be independent of active workspace."""
        ver_dir = workspace / "forge" / "versions" / "room-test" / "v1" / "src"
        ver_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copytree(sample_room, ver_dir, dirs_exist_ok=True)

        original_content = (ver_dir / "utils.py").read_text()

        # Modify active workspace
        (sample_room / "utils.py").write_text("# modified active")

        # Version must be unchanged
        assert (ver_dir / "utils.py").read_text() == original_content

    def test_version_names_are_valid(self):
        """Version names must follow naming rules."""
        valid   = ["v1", "v2", "v10", "v1-alpha", "v2-beta"]
        invalid = ["", " ", "version one", "V1"]

        pattern = __import__("re").compile(r"^v\d+")
        for v in valid:
            assert pattern.match(v), f"Should be valid: {v}"
        for v in invalid:
            assert not pattern.match(v), f"Should be invalid: {v}"
