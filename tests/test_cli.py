from pathlib import Path

from context_diamond.cli import main


def test_cli_writes_markdown(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    output = tmp_path / "capsule.md"
    source.write_text("Goal: save tokens. Decision: keep deterministic output.", encoding="utf-8")

    assert main([str(source), "--budget", "120", "--output", str(output)]) == 0
    assert "Context Diamond Capsule" in output.read_text(encoding="utf-8")


def test_cli_prints_json(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.md"
    source.write_text("Open question: what should happen next?", encoding="utf-8")

    assert main([str(source), "--format", "json", "--budget", "100"]) == 0
    captured = capsys.readouterr()
    assert '"strategy": "diamond-v1"' in captured.out
