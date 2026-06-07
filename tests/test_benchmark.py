from pathlib import Path

from context_diamond.benchmark import render_markdown, run_benchmark


def test_run_benchmark_compares_signal_recall(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "Goal: save tokens.\n"
        "The system must keep constraints.\n"
        "Decision: use capsules.\n"
        "Open question: how much is lost?\n",
        encoding="utf-8",
    )

    results = run_benchmark([source], budget=120, profile="generic")

    assert len(results) == 1
    assert results[0].diamond_ratio > 0
    assert "constraints" in results[0].diamond_signal_recall


def test_render_markdown_outputs_table(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("Decision: keep markdown output.", encoding="utf-8")
    markdown = render_markdown(run_benchmark([source], budget=100))

    assert "| Source | Budget |" in markdown
    assert "source.md" in markdown


def test_benchmark_uses_readable_source_label_for_absolute_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("Goal: keep output readable.", encoding="utf-8")

    result = run_benchmark([source.resolve()], budget=100)[0]

    assert result.source == "source.md"


def test_default_word_is_not_treated_as_decision_signal(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "The system must run locally by default.\nDecision: keep capsules structured.",
        encoding="utf-8",
    )

    result = run_benchmark([source], budget=140)[0]

    assert result.diamond_signal_recall["decisions"] == 1.0
