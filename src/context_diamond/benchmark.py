"""Deterministic benchmark harness for Context Diamond."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .profiles import estimate_profile_tokens, list_tokenizer_profiles
from .tokenizer import TOKEN_RE

SIGNAL_PATTERNS = {
    "constraints": re.compile(r"\b(must|never|required|do not|cannot|without)\b", re.I),
    "decisions": re.compile(r"\b(decision|decided|chosen|approved|default)\b", re.I),
    "risks": re.compile(r"\b(risk|question|blocked|unknown|unclear)\b", re.I),
    "code": re.compile(r"`[^`]+`|[A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|md|json|toml|yml|yaml)"),
}


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark metrics for a single source and budget."""

    source: str
    budget: int
    profile: str
    source_tokens: int
    diamond_tokens: int
    diamond_ratio: float
    diamond_signal_recall: dict[str, float]
    baseline_head_signal_recall: dict[str, float]
    baseline_tail_signal_recall: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "budget": self.budget,
            "profile": self.profile,
            "source_tokens": self.source_tokens,
            "diamond_tokens": self.diamond_tokens,
            "diamond_ratio": self.diamond_ratio,
            "diamond_signal_recall": self.diamond_signal_recall,
            "baseline_head_signal_recall": self.baseline_head_signal_recall,
            "baseline_tail_signal_recall": self.baseline_tail_signal_recall,
        }


def run_benchmark(
    paths: list[Path],
    *,
    budget: int,
    profile: str = "generic",
) -> list[BenchmarkResult]:
    """Run Context Diamond against simple deterministic baselines."""

    results: list[BenchmarkResult] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        capsule = ContextDiamondCompressor(
            CompressionConfig(token_budget=budget, include_loss_report=True)
        ).compress(source)
        rendered = capsule.to_markdown()
        source_tokens = estimate_profile_tokens(source, profile)
        diamond_tokens = estimate_profile_tokens(rendered, profile)

        results.append(
            BenchmarkResult(
                source=str(path),
                budget=budget,
                profile=profile,
                source_tokens=source_tokens,
                diamond_tokens=diamond_tokens,
                diamond_ratio=round(source_tokens / max(diamond_tokens, 1), 2),
                diamond_signal_recall=_signal_recall(source, rendered),
                baseline_head_signal_recall=_signal_recall(source, _clip_head(source, budget)),
                baseline_tail_signal_recall=_signal_recall(source, _clip_tail(source, budget)),
            )
        )

    return results


def render_markdown(results: list[BenchmarkResult]) -> str:
    """Render benchmark results as a Markdown table."""

    lines = [
        "# Context Diamond Benchmark",
        "",
        "| Source | Budget | Profile | Source tokens | Diamond tokens | Ratio | "
        "Signal recall | Head baseline | Tail baseline |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    Path(result.source).name,
                    str(result.budget),
                    result.profile,
                    str(result.source_tokens),
                    str(result.diamond_tokens),
                    f"{result.diamond_ratio}x",
                    _format_recall(result.diamond_signal_recall),
                    _format_recall(result.baseline_head_signal_recall),
                    _format_recall(result.baseline_tail_signal_recall),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond-bench",
        description="Benchmark Context Diamond against deterministic clipping baselines.",
    )
    parser.add_argument("inputs", nargs="+", help="Input text or markdown files.")
    parser.add_argument("-b", "--budget", type=int, default=500, help="Token budget.")
    parser.add_argument(
        "-p",
        "--profile",
        choices=list_tokenizer_profiles(),
        default="generic",
        help="Tokenizer estimate profile.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    if args.budget <= 0:
        parser.error("budget must be greater than zero")

    results = run_benchmark(
        [Path(path) for path in args.inputs],
        budget=args.budget,
        profile=args.profile,
    )
    if args.format == "json":
        print(json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2))
    else:
        print(render_markdown(results), end="")
    return 0


def _signals(text: str) -> dict[str, set[str]]:
    return {
        name: {match.group(0).lower() for match in pattern.finditer(text)}
        for name, pattern in SIGNAL_PATTERNS.items()
    }


def _signal_recall(source: str, candidate: str) -> dict[str, float]:
    source_signals = _signals(source)
    candidate_signals = _signals(candidate)
    recall: dict[str, float] = {}
    for name, values in source_signals.items():
        if not values:
            recall[name] = 1.0
        else:
            recall[name] = round(len(values & candidate_signals[name]) / len(values), 2)
    return recall


def _clip_head(text: str, budget: int) -> str:
    return " ".join(TOKEN_RE.findall(text)[:budget])


def _clip_tail(text: str, budget: int) -> str:
    return " ".join(TOKEN_RE.findall(text)[-budget:])


def _format_recall(recall: dict[str, float]) -> str:
    return ", ".join(f"{name}:{value:.2f}" for name, value in recall.items())


if __name__ == "__main__":
    raise SystemExit(main())
