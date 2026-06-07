from pathlib import Path

import pytest

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


def test_cli_allows_custom_title(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.md"
    source.write_text("Goal: make a named capsule.", encoding="utf-8")

    assert main([str(source), "--title", "Sprint Handoff"]) == 0
    captured = capsys.readouterr()
    assert "# Sprint Handoff" in captured.out


def test_cli_rejects_non_positive_budget(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("Goal: save tokens.", encoding="utf-8")

    with pytest.raises(SystemExit):
        main([str(source), "--budget", "0"])


def test_cli_reports_invalid_messages_json_shape(tmp_path: Path, capsys) -> None:
    source = tmp_path / "messages.json"
    source.write_text('{"role": "user", "content": "not a list"}', encoding="utf-8")

    with pytest.raises(SystemExit):
        main([str(source), "--messages-json"])

    captured = capsys.readouterr()
    assert "input must be text or a list of messages" in captured.err


def test_cli_can_emit_loss_report_json(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.md"
    source.write_text("Goal: save tokens. Decision: keep audit data.", encoding="utf-8")

    assert main([str(source), "--format", "json", "--loss-report"]) == 0
    captured = capsys.readouterr()
    assert '"loss_report"' in captured.out
    assert '"profile_source_tokens"' in captured.out
    assert '"profile_rendered_tokens"' in captured.out
    assert '"budget_scope": "sections"' in captured.out
