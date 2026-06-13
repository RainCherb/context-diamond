"""Tests for batch CLI command."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from context_diamond.cli import _main_batch


def test_batch_compresses_multiple_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = Path(tmpdir) / "a.md"
        p2 = Path(tmpdir) / "b.md"
        p1.write_text("Goal: build a compressor.\nDecision: use Python.")
        p2.write_text("Goal: build a dashboard.\nDecision: use React.")

        out_dir = Path(tmpdir) / "out"
        import io

        stdout = io.StringIO()
        result = _main_batch(
            [str(p1), str(p2), "-o", str(out_dir), "-f", "markdown", "-b", "200"],
            stdout,
        )
        assert result == 0
        assert (out_dir / "a.md").exists()
        assert (out_dir / "b.md").exists()


def test_batch_json_output() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "note.md"
        p.write_text("Goal: test batch.\nDecision: use JSON.")
        out_dir = Path(tmpdir) / "out"
        import io

        stdout = io.StringIO()
        result = _main_batch(
            [str(p), "-o", str(out_dir), "-f", "json", "-b", "200"],
            stdout,
        )
        assert result == 0
        out_path = out_dir / "note.json"
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "sections" in data
