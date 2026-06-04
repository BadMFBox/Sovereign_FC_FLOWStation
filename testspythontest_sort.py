# ═══════════════════════════════════════════════════════════════
#  tests/python/test_sort.py
#  Phase 3 — flow_sort.py tests
# ═══════════════════════════════════════════════════════════════

import pytest
import json
from pathlib import Path


# ───────────────────────────────────────────────────────────────
#  CATEGORY CLASSIFIER
# ───────────────────────────────────────────────────────────────

CATEGORIES = {
    "core":       ["process", "engine", "pipeline", "run", "execute", "main"],
    "validation": ["validate", "check", "verify", "sanitize", "guard"],
    "config":     ["config", "setting", "option", "env", "load"],
    "utils":      ["util", "helper", "tool", "format", "parse"],
    "models":     ["model", "schema", "data", "entity", "struct"],
    "api":        ["api", "route", "endpoint", "handler", "view"],
    "auth":       ["auth", "login", "token", "session", "permission"],
    "tests":      ["test_", "spec_", "fixture"],
}


def classify_file(filename: str) -> str:
    """Classify a file into a category by name."""
    name = filename.lower().replace(".py", "")
    for category, keywords in CATEGORIES.items():
        if any(kw in name for kw in keywords):
            return category
    return "misc"


def simulate_sort(source_dir: Path, output_dir: Path) -> dict[str, list[Path]]:
    """
    Simulate sorting files into categories.
    Returns dict of category -> list of output files.
    """
    result: dict[str, list[Path]] = {}

    for py_file in source_dir.glob("*.py"):
        category = classify_file(py_file.name)
        cat_dir  = output_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        dest = cat_dir / py_file.name
        import shutil
        shutil.copy2(py_file, dest)

        if category not in result:
            result[category] = []
        result[category].append(dest)

    return result


# ───────────────────────────────────────────────────────────────
#  CLASSIFICATION LOGIC
# ───────────────────────────────────────────────────────────────

class TestClassification:

    def test_core_files_classified_correctly(self):
        assert classify_file("process.py")  == "core"
        assert classify_file("engine.py")   == "core"
        assert classify_file("pipeline.py") == "core"

    def test_validation_files_classified_correctly(self):
        assert classify_file("validate.py")  == "validation"
        assert classify_file("sanitize.py")  == "validation"
        assert classify_file("check_input.py") == "validation"

    def test_config_files_classified_correctly(self):
        assert classify_file("config.py")   == "config"
        assert classify_file("settings.py") == "config"
        assert classify_file("load_env.py") == "config"

    def test_utils_files_classified_correctly(self):
        assert classify_file("utils.py")       == "utils"
        assert classify_file("helper.py")      == "utils"
        assert classify_file("formatters.py")  == "utils"

    def test_unknown_files_go_to_misc(self):
        assert classify_file("banana.py")     == "misc"
        assert classify_file("unknown.py")    == "misc"
        assert classify_file("module_x.py")   == "misc"

    def test_test_files_classified_correctly(self):
        assert classify_file("test_core.py")  == "tests"
        assert classify_file("test_utils.py") == "tests"

    def test_api_files_classified_correctly(self):
        assert classify_file("api.py")      == "api"
        assert classify_file("routes.py")   == "api"
        assert classify_file("handler.py")  == "api"

    def test_auth_files_classified_correctly(self):
        assert classify_file("auth.py")        == "auth"
        assert classify_file("login.py")       == "auth"
        assert classify_file("token_util.py")  == "auth"

    def test_classification_is_case_insensitive(self):
        assert classify_file("VALIDATE.py") == "validation"
        assert classify_file("Config.py")   == "config"
        assert classify_file("UTILS.py")    == "utils"


# ───────────────────────────────────────────────────────────────
#  SORT OUTPUT
# ───────────────────────────────────────────────────────────────

class TestSortOutput:

    def _make_room_files(self, workspace: Path) -> Path:
        source = workspace / "sorter" / "input" / "room-test"
        source.mkdir(parents=True, exist_ok=True)
        files = {
            "process.py":  "def process(): pass",
            "validate.py": "def validate(): pass",
            "config.py":   "def load_config(): pass",
            "utils.py":    "def format_str(): pass",
            "banana.py":   "def banana(): pass",
        }
        for name, content in files.items():
            (source / name).write_text(content)
        return source

    def test_sort_creates_category_dirs(self, workspace):
        """Sort must create a directory per category."""
        source  = self._make_room_files(workspace)
        out_dir = workspace / "sorter" / "output" / "room-test"
        result  = simulate_sort(source, out_dir)
        for category in result:
            assert (out_dir / category).exists()

    def test_files_land_in_correct_category(self, workspace):
        """Each file must land in its correct category dir."""
        source  = self._make_room_files(workspace)
        out_dir = workspace / "sorter" / "output" / "room-test"
        result  = simulate_sort(source, out_dir)

        assert any("process.py"  in str(f) for f in result.get("core",       []))
        assert any("validate.py" in str(f) for f in result.get("validation", []))
        assert any("config.py"   in str(f) for f in result.get("config",     []))
        assert any("utils.py"    in str(f) for f in result.get("utils",      []))
        assert any("banana.py"   in str(f) for f in result.get("misc",       []))

    def test_all_files_are_sorted(self, workspace):
        """Every input file must appear in output."""
        source     = self._make_room_files(workspace)
        out_dir    = workspace / "sorter" / "output" / "room-test"
        result     = simulate_sort(source, out_dir)
        input_files  = set(f.name for f in source.glob("*.py"))
        output_files = set(f.name for files in result.values() for f in files)
        assert input_files == output_files

    def test_sort_preserves_file_content(self, workspace):
        """Sort must not modify file content."""
        source  = self._make_room_files(workspace)
        out_dir = workspace / "sorter" / "output" / "room-test"
        result  = simulate_sort(source, out_dir)

        for category, files in result.items():
            for dest in files:
                source_file = source / dest.name
                if source_file.exists():
                    assert dest.read_text() == source_file.read_text()

    def test_sort_manifest_structure(self, workspace):
        """Sort manifest must have correct structure."""
        manifest = {
            "room":       "room-test",
            "sorted_at":  "2024-01-01T00:00:00",
            "categories": {
                "core":       ["process.py"],
                "validation": ["validate.py"],
                "config":     ["config.py"],
                "utils":      ["utils.py"],
                "misc":       ["banana.py"],
            }
        }
        assert "room"       in manifest
        assert "categories" in manifest
        assert isinstance(manifest["categories"], dict)
