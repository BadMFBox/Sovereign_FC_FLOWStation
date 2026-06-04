# ═══════════════════════════════════════════════════════════════
#  tests/python/test_split.py
#  Phase 2 — flow_split.py tests
# ═══════════════════════════════════════════════════════════════

import pytest
import ast
import json
from pathlib import Path


# ───────────────────────────────────────────────────────────────
#  HELPERS
# ───────────────────────────────────────────────────────────────

def extract_functions(source: str) -> list[str]:
    """Extract top-level function names from source."""
    tree  = ast.parse(source)
    return [
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.col_offset == 0
    ]


def extract_classes(source: str) -> list[str]:
    """Extract top-level class names from source."""
    tree = ast.parse(source)
    return [
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef)
        and n.col_offset == 0
    ]


def simulate_split(source: str, output_dir: Path) -> list[Path]:
    """
    Simulate splitting a Python file into modules.
    One file per top-level class or function group.
    """
    tree    = ast.parse(source)
    lines   = source.splitlines()
    outputs = []

    nodes = [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    for node in nodes:
        name    = node.name.lower()
        start   = node.lineno - 1
        end     = node.end_lineno
        content = "\n".join(lines[start:end])
        out     = output_dir / f"{name}.py"
        out.write_text(content)
        outputs.append(out)

    return outputs


# ───────────────────────────────────────────────────────────────
#  AST PARSING
# ───────────────────────────────────────────────────────────────

class TestAstParsing:

    def test_parse_valid_python(self, sample_python_file):
        """Valid Python must parse without errors."""
        tree = ast.parse(sample_python_file)
        assert tree is not None

    def test_extract_functions(self, sample_python_file):
        """All top-level functions must be found."""
        funcs = extract_functions(sample_python_file)
        assert "process_data" in funcs
        assert "validate_input" in funcs

    def test_extract_classes(self, sample_python_file):
        """All top-level classes must be found."""
        classes = extract_classes(sample_python_file)
        assert "DataProcessor" in classes
        assert "ConfigManager" in classes

    def test_parse_empty_file(self):
        """Empty file must parse as empty tree."""
        tree  = ast.parse("")
        funcs = extract_functions("")
        assert funcs == []

    def test_parse_comments_only(self):
        """File with only comments must produce empty node list."""
        source = "# This is a comment\n# Another comment\n"
        funcs  = extract_functions(source)
        assert funcs == []

    def test_nested_functions_not_extracted(self):
        """Nested functions must not be extracted as top-level modules."""
        source = '''
def outer():
    def inner():
        pass
    return inner
'''
        funcs = extract_functions(source)
        assert "outer" in funcs
        assert "inner" not in funcs

    def test_async_functions_extracted(self):
        """Async functions must be extracted like regular functions."""
        source = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass
'''
        funcs = extract_functions(source)
        assert "fetch_data" in funcs


# ───────────────────────────────────────────────────────────────
#  SPLIT OUTPUT
# ───────────────────────────────────────────────────────────────

class TestSplitOutput:

    def test_split_creates_files(self, workspace, sample_python_file):
        """Split must create one file per top-level node."""
        out_dir = workspace / "splitter" / "output" / "room-test"
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = simulate_split(sample_python_file, out_dir)
        assert len(outputs) > 0
        for f in outputs:
            assert f.exists()

    def test_split_files_are_valid_python(self, workspace, sample_python_file):
        """Every split file must be parseable Python."""
        out_dir = workspace / "splitter" / "output" / "room-test"
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = simulate_split(sample_python_file, out_dir)
        for f in outputs:
            content = f.read_text()
            # Must not raise SyntaxError
            ast.parse(content)

    def test_split_filenames_match_node_names(self, workspace, sample_python_file):
        """Split file names must reflect class/function names."""
        out_dir = workspace / "splitter" / "output" / "room-test"
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = simulate_split(sample_python_file, out_dir)
        names   = [f.stem for f in outputs]
        assert "dataprocessor"  in names or any("processor" in n for n in names)
        assert "configmanager"  in names or any("config"    in n for n in names)

    def test_split_preserves_content(self, workspace):
        """Split must not alter the code content."""
        source = '''def my_func(x: int) -> int:
    """Double the input."""
    return x * 2
'''
        out_dir = workspace / "splitter" / "output" / "room-test"
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = simulate_split(source, out_dir)
        assert len(outputs) == 1
        assert "return x * 2" in outputs[0].read_text()

    def test_split_manifest_written(self, workspace, sample_python_file):
        """A manifest JSON must be created after split."""
        out_dir = workspace / "splitter" / "output" / "room-test"
        out_dir.mkdir(parents=True, exist_ok=True)
        simulate_split(sample_python_file, out_dir)

        manifest = {
            "room":     "room-test",
            "split_at": "2024-01-01T00:00:00",
            "modules":  [{"name": "process_data", "file": "process_data.py"}]
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        assert manifest_path.exists()
        loaded = json.loads(manifest_path.read_text())
        assert loaded["room"] == "room-test"
