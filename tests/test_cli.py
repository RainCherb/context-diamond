import json
import subprocess
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


def test_cli_explain_outputs_score_table(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.md"
    source.write_text("Decision: expose shard explanations.", encoding="utf-8")

    assert main(["explain", str(source)]) == 0
    captured = capsys.readouterr()
    assert "facet" in captured.out
    assert "decisions" in captured.out


def test_cli_repo_outputs_repository_capsule(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text(
        "Goal: test repo command.\nThe system must include git state.",
        encoding="utf-8",
    )

    assert main(["repo", str(tmp_path), "--budget", "420"]) == 0
    captured = capsys.readouterr()
    assert "Repository Context Capsule" in captured.out
    assert "repo command" in captured.out.lower()


def test_cli_diff_and_merge_json_capsules(tmp_path: Path, capsys) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    merged = tmp_path / "merged.json"
    old.write_text(
        json.dumps(
            {
                "title": "Old",
                "source_tokens": 10,
                "source_sha256": "old",
                "sections": [{"title": "Decisions", "items": ["Decision: use CLI."]}],
            }
        ),
        encoding="utf-8",
    )
    new.write_text(
        json.dumps(
            {
                "title": "New",
                "source_tokens": 12,
                "source_sha256": "new",
                "sections": [
                    {
                        "title": "Decisions",
                        "items": ["Decision: use CLI.", "Decision: add diff."],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["diff", str(old), str(new), "--format", "json"]) == 0
    diff_output = capsys.readouterr().out
    assert "Decision: add diff." in diff_output

    assert main(["merge", str(old), str(new), "--format", "json", "--output", str(merged)]) == 0
    data = json.loads(merged.read_text(encoding="utf-8"))
    assert data["metadata"]["merged_capsules"] == 2
    assert "Decision: add diff." in merged.read_text(encoding="utf-8")
