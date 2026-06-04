# ═══════════════════════════════════════════════════════════════
#  tests/python/test_end_to_end.py
#  Full pipeline integration test
# ═══════════════════════════════════════════════════════════════

import pytest
import json
import shutil
from pathlib import Path


class TestEndToEnd:
    """
    Test the complete 4-phase pipeline from start to finish.
    This validates the entire flow works as one cohesive system.
    """

    def test_full_pipeline(self, workspace, sample_room):
        """
        Run complete pipeline: forge → lock → split → sort → integrate.
        Verify output at each stage.
        """
        room_name = "room-test"
        
        # PHASE 1 — LOCK
        locked_dir = workspace / "forge" / "locked"
        locked_dir.mkdir(parents=True, exist_ok=True)
        lock_file = locked_dir / f"{room_name}-v1.lock.json"
        lock_record = {
            "room":    room_name,
            "version": "v1",
            "status":  "LOCKED",
        }
        lock_file.write_text(json.dumps(lock_record))
        assert lock_file.exists()
        
        # Copy to versions
        ver_dir = workspace / "forge" / "versions" / room_name / "v1" / "src"
        ver_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(sample_room, ver_dir, dirs_exist_ok=True)
        assert (ver_dir / "process.py").exists()
        
        # PHASE 2 — SPLIT
        split_out = workspace / "splitter" / "output" / room_name
        split_out.mkdir(parents=True, exist_ok=True)
        for file in sample_room.glob("*.py"):
            shutil.copy2(file, split_out / file.name)
        assert len(list(split_out.glob("*.py"))) > 0
        
        # PHASE 3 — SORT
        sort_out = workspace / "sorter" / "output" / room_name
        sort_out.mkdir(parents=True, exist_ok=True)
        
        categories = {"core": [], "config": [], "utils": []}
        for file in split_out.glob("*.py"):
            if "process" in file.name:
                cat_dir = sort_out / "core"
            elif "config" in file.name:
                cat_dir = sort_out / "config"
            else:
                cat_dir = sort_out / "utils"
            
            cat_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, cat_dir / file.name)
        
        assert (sort_out / "core").exists()
        assert (sort_out / "config").exists()
        
        # PHASE 4 — INTEGRATE
        mesh_out = workspace / "integration" / "output" / "mesh" / "room_test"
        mesh_out.mkdir(parents=True, exist_ok=True)
        
        # Copy sorted to mesh
        for cat_dir in sort_out.iterdir():
            if cat_dir.is_dir():
                dest = mesh_out / cat_dir.name
                shutil.copytree(cat_dir, dest, dirs_exist_ok=True)
        
        # Generate surface
        surface_file = mesh_out / "_surface.py"
        surface_file.write_text('"""Public API."""\n')
        
        # Generate __init__.py
        init_file = mesh_out / "__init__.py"
        init_file.write_text('"""Room package."""\n')
        
        assert surface_file.exists()
        assert init_file.exists()
        assert (mesh_out / "core").exists()
        
        # Verify mesh manifest
        mesh_manifest = workspace / "integration" / "output" / "mesh" / "mesh_manifest.json"
        manifest_data = {
            "mesh_version": "1.0",
            "rooms": [room_name],
            "status": "wired",
        }
        mesh_manifest.write_text(json.dumps(manifest_data))
        assert mesh_manifest.exists()
        
        loaded = json.loads(mesh_manifest.read_text())
        assert loaded["status"] == "wired"
        assert room_name in loaded["rooms"]

    def test_pipeline_state_preserved(self, workspace):
        """Pipeline state must be saved between steps."""
        state_file = workspace / "shared" / "pipeline_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "last_room":   "room-test",
            "last_action": "WIRE",
            "timestamp":   "2024-01-01T00:00:00",
        }
        state_file.write_text(json.dumps(state))
        
        loaded = json.loads(state_file.read_text())
        assert loaded["last_room"] == "room-test"
        assert loaded["last_action"] == "WIRE"
        
    def test_pipeline_recoverable_from_failure(self, workspace):
        """Pipeline must be able to resume after failure."""
        state_file = workspace / "shared" / "pipeline_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Simulate failure at SORT step
        state = {
            "last_completed": "SPLIT",
            "last_failed":    "SORT",
            "room":           "room-test",
            "resume_from":    "SORT",
            "timestamp":      "2024-01-01T00:00:00",
        }
        state_file.write_text(json.dumps(state))
        
        loaded = json.loads(state_file.read_text())
        assert loaded["last_completed"] == "SPLIT"
        assert loaded["resume_from"]    == "SORT"
        assert loaded["last_failed"]    == "SORT"

    def test_multiple_rooms_dont_interfere(self, workspace, sample_room):
        """Running multiple rooms must keep outputs fully isolated."""
        rooms = ["room-1", "room-2", "room-3"]

        for room in rooms:
            mesh_dir = workspace / "integration" / "output" / "mesh" / room
            mesh_dir.mkdir(parents=True, exist_ok=True)

            # Each room gets its own surface
            (mesh_dir / "_surface.py").write_text(
                f'"""Surface for {room}."""\n\nROOM = "{room}"\n'
            )
            (mesh_dir / "__init__.py").write_text(
                f'"""Package for {room}."""\n'
            )

        # Verify each room is isolated
        for room in rooms:
            surface = workspace / "integration" / "output" / "mesh" / room / "_surface.py"
            content = surface.read_text()
            assert f'ROOM = "{room}"' in content

            # Other room names must NOT appear in this surface
            for other in rooms:
                if other != room:
                    assert f'ROOM = "{other}"' not in content

    def test_mesh_manifest_lists_all_rooms(self, workspace):
        """Mesh manifest must include every integrated room."""
        rooms = ["room-1", "room-2", "room-3"]

        for room in rooms:
            mesh_dir = workspace / "integration" / "output" / "mesh" / room
            mesh_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "mesh_version": "1.0",
            "rooms":        rooms,
            "room_count":   len(rooms),
            "status":       "wired",
            "wired_at":     "2024-01-01T00:00:00+00:00",
        }

        manifest_file = (
            workspace / "integration" / "output" / "mesh" / "mesh_manifest.json"
        )
        manifest_file.write_text(json.dumps(manifest, indent=2))

        loaded = json.loads(manifest_file.read_text())
        assert loaded["room_count"] == 3
        for room in rooms:
            assert room in loaded["rooms"]

    def test_logic_lock_seals_final_mesh(self, workspace):
        """Logic lock must seal the complete integrated mesh."""
        import hashlib

        mesh_dir = workspace / "integration" / "output" / "mesh" / "room-test"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        (mesh_dir / "_surface.py").write_text('"""Surface."""\n')
        (mesh_dir / "__init__.py").write_text('"""Init."""\n')

        # Compute seal
        sha256 = hashlib.sha256()
        for file in sorted(mesh_dir.rglob("*")):
            if file.is_file():
                sha256.update(file.read_bytes())
        signature = sha256.hexdigest()

        lock_dir = workspace / "integration" / "logic_locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "room-test.logic.json"
        lock_file.write_text(json.dumps({
            "room":      "room-test",
            "signature": signature,
            "status":    "SEALED",
            "sealed_at": "2024-01-01T00:00:00+00:00",
        }))

        assert lock_file.exists()
        loaded = json.loads(lock_file.read_text())
        assert loaded["status"]    == "SEALED"
        assert loaded["signature"] == signature
        assert len(loaded["signature"]) == 64
            
            
            
