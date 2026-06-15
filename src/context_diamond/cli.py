"""Command line interface for Context Diamond."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .capsules import diff_capsules, load_capsule_json, merge_capsules, render_capsule_diff
from .compressor import CompressionConfig, ContextDiamondCompressor
from .profiles import list_tokenizer_profiles
from .repo import compress_repo
from .templates import get_template, list_templates
from .tokenizers import list_tokenizers

COMMANDS = {"compress", "explain", "repo", "diff", "merge", "batch"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context-diamond",
        description="Create a deterministic context capsule for LLM workflows.",
    )
    parser.add_argument(
        "input",
        help="Path to a text/markdown file, a JSON message list, or '-' for stdin.",
    )
    parser.add_argument(
        "-b",
        "--budget",
        type=_positive_int,
        default=800,
        help="Target capsule token budget. Default: 800.",
    )
    parser.add_argument(
        "-t",
        "--title",
        default="Context Diamond Capsule",
        help="Capsule title. Default: Context Diamond Capsule.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write the capsule to a file instead of stdout.",
    )
    parser.add_argument(
        "--messages-json",
        action="store_true",
        help="Interpret input as a JSON array of objects with role/content fields.",
    )
    parser.add_argument(
        "--no-rehydration-prompt",
        action="store_true",
        help="Do not append the rehydration prompt section.",
    )
    parser.add_argument(
        "--loss-report",
        action="store_true",
        help="Include kept/omitted shard audit data in JSON metadata.",
    )
    parser.add_argument(
        "--tokenizer-profile",
        choices=list_tokenizer_profiles(),
        default="generic",
        help="Tokenizer estimate profile for metadata. Default: generic.",
    )
    parser.add_argument(
        "--template",
        choices=list_templates(),
        default="default",
        help="Domain-specific capsule template. Default: default.",
    )
    parser.add_argument(
        "--tokenizer",
        choices=list_tokenizers(),
        default="generic",
        help="Precise tokenizer to use (optional extras may be required). Default: generic.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Adaptive compression for a target LLM model. "
            "Examples: gpt-4o, claude-3-sonnet, gemini-1.5-pro. "
            "Overrides --budget with the model's context window."
        ),
    )
    parser.add_argument(
        "--cascade",
        action="store_true",
        help="Use multi-level cascade compression (3 levels by default).",
    )
    parser.add_argument(
        "--cascade-levels",
        type=_positive_int,
        default=3,
        help="Number of cascade levels (used with --cascade). Default: 3.",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    command = args_list.pop(0) if args_list and args_list[0] in COMMANDS else "compress"
    if command == "compress":
        return _main_compress(args_list, stdout)
    if command == "explain":
        return _main_explain(args_list, stdout)
    if command == "repo":
        return _main_repo(args_list, stdout)
    if command == "diff":
        return _main_diff(args_list, stdout)
    if command == "merge":
        return _main_merge(args_list, stdout)
    if command == "batch":
        return _main_batch(args_list, stdout)
    raise AssertionError(f"unhandled command: {command}")


def _main_compress(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = stdout or sys.stdout

    try:
        raw = _read_input(args.input)
        source = json.loads(raw) if args.messages_json else raw

        capsule: Any
        compressor: Any
        if args.cascade:
            from .cascade import CascadeCompressor

            levels = _build_cascade_levels(
                start_budget=args.budget,
                levels_count=args.cascade_levels,
                include_rehydration_prompt=not args.no_rehydration_prompt,
            )
            compressor = CascadeCompressor(levels=levels)
            capsule = compressor.compress(source)
            rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()
        elif args.model:
            from .adaptive import AdaptiveCompressor

            adaptive = AdaptiveCompressor()
            result = adaptive.compress(
                source,
                model_name=args.model,
                title=args.title,
                include_rehydration_prompt=not args.no_rehydration_prompt,
                include_loss_report=args.loss_report,
                tokenizer_profile=args.tokenizer_profile,
            )
            if args.format == "json":
                rendered = (
                    result.capsule.to_json()
                    if result.capsule
                    else json.dumps({"text": result.text})
                )
            else:
                rendered = result.text
        else:
            template = get_template(args.template)
            config_kwargs = template.to_config_kwargs(token_budget=args.budget)
            config_kwargs["title"] = args.title
            config_kwargs["include_rehydration_prompt"] = not args.no_rehydration_prompt
            config_kwargs["include_loss_report"] = args.loss_report
            config_kwargs["tokenizer_profile"] = args.tokenizer_profile
            config = CompressionConfig(**config_kwargs)

            compressor = ContextDiamondCompressor(config)
            capsule = compressor.compress(source)
            rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        parser.error(str(error))

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        stream.write(rendered)

    return 0


def _main_explain(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond explain",
        description="Explain shard facets, scores, tokens, and scoring reasons.",
    )
    parser.add_argument("input", help="Path to text/markdown, JSON messages, or '-' for stdin.")
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format. Default: table.",
    )
    parser.add_argument(
        "--messages-json",
        action="store_true",
        help="Interpret input as a JSON array of objects with role/content fields.",
    )
    parser.add_argument(
        "--tokenizer-profile",
        choices=list_tokenizer_profiles(),
        default="generic",
        help="Tokenizer estimate profile for config compatibility. Default: generic.",
    )
    args = parser.parse_args(argv)

    try:
        raw = _read_input(args.input)
        source = json.loads(raw) if args.messages_json else raw
        compressor = ContextDiamondCompressor(
            CompressionConfig(tokenizer_profile=args.tokenizer_profile)
        )
        rows = compressor.explain(source)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        parser.error(str(error))

    rendered = (
        json.dumps(rows, ensure_ascii=False, indent=2) if args.format == "json" else _table(rows)
    )
    (stdout or sys.stdout).write(rendered)
    return 0


def _main_repo(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond repo",
        description="Create a capsule from repository state and selected files.",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Repository path. Default: current dir."
    )
    parser.add_argument("-b", "--budget", type=_positive_int, default=1200, help="Token budget.")
    parser.add_argument(
        "-t", "--title", default="Repository Context Capsule", help="Capsule title."
    )
    parser.add_argument("-f", "--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("-o", "--output", help="Write capsule to a file instead of stdout.")
    parser.add_argument(
        "--include",
        nargs="*",
        help="Repository-relative files to include before changed/untracked files.",
    )
    parser.add_argument(
        "--max-file-tokens",
        type=_positive_int,
        default=500,
        help="Maximum source tokens read from each included file.",
    )
    args = parser.parse_args(argv)

    try:
        capsule = compress_repo(
            args.path,
            token_budget=args.budget,
            title=args.title,
            include=args.include,
            max_file_tokens=args.max_file_tokens,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()
    _write_output(rendered, args.output, stdout)
    return 0


def _main_diff(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond diff",
        description="Compare two JSON capsules section by section.",
    )
    parser.add_argument("left", help="Old JSON capsule.")
    parser.add_argument("right", help="New JSON capsule.")
    parser.add_argument("-f", "--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    try:
        diff = diff_capsules(load_capsule_json(args.left), load_capsule_json(args.right))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    rendered = (
        json.dumps(diff, ensure_ascii=False, indent=2)
        if args.format == "json"
        else render_capsule_diff(diff)
    )
    (stdout or sys.stdout).write(rendered)
    return 0


def _main_merge(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond merge",
        description="Merge multiple JSON capsules and deduplicate section items.",
    )
    parser.add_argument("inputs", nargs="+", help="JSON capsules to merge.")
    parser.add_argument("-t", "--title", default="Merged Context Diamond Capsule")
    parser.add_argument("-b", "--budget", type=_positive_int, help="Optional merged token budget.")
    parser.add_argument("-f", "--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("-o", "--output", help="Write merged capsule to a file instead of stdout.")
    args = parser.parse_args(argv)

    try:
        capsule = merge_capsules(
            [load_capsule_json(path) for path in args.inputs],
            title=args.title,
            token_budget=args.budget,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()
    _write_output(rendered, args.output, stdout)
    return 0


def _main_batch(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-diamond batch",
        description="Batch-process multiple files into capsules.",
    )
    parser.add_argument(
        "inputs", nargs="+", help="Input text or markdown files (glob patterns supported)."
    )
    parser.add_argument(
        "-b", "--budget", type=_positive_int, default=800, help="Token budget per file."
    )
    parser.add_argument(
        "-t", "--title", default="Context Diamond Capsule", help="Base capsule title."
    )
    parser.add_argument("-f", "--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "-o", "--output-dir", default=".", help="Output directory for generated capsules."
    )
    parser.add_argument(
        "--template", choices=list_templates(), default="default", help="Capsule template."
    )
    parser.add_argument(
        "--messages-json", action="store_true", help="Interpret inputs as JSON message lists."
    )
    parser.add_argument(
        "--loss-report", action="store_true", help="Include loss report in JSON metadata."
    )
    args = parser.parse_args(argv)

    from glob import glob as stdlib_glob

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = get_template(args.template)
    config_kwargs = template.to_config_kwargs(token_budget=args.budget)
    config_kwargs["title"] = args.title
    config_kwargs["include_loss_report"] = args.loss_report
    config = CompressionConfig(**config_kwargs)
    compressor = ContextDiamondCompressor(config)

    expanded_paths: list[str] = []
    unmatched_patterns: list[str] = []
    for pattern in args.inputs:
        # Treat inputs that look like literal file paths (no glob metacharacters)
        # as-is so users can point at files that happen to contain *, ?, etc.
        has_glob_chars = any(ch in pattern for ch in "*?[")
        matches = stdlib_glob(pattern, recursive=True) if has_glob_chars else []
        if matches:
            expanded_paths.extend(matches)
        elif has_glob_chars and not Path(pattern).is_file():
            unmatched_patterns.append(pattern)
        else:
            expanded_paths.append(pattern)

    written: list[str] = []
    for path_str in expanded_paths:
        path = Path(path_str)
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            source = json.loads(raw) if args.messages_json else raw
            capsule = compressor.compress(source)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue

        suffix = ".json" if args.format == "json" else ".md"
        out_name = path.stem + suffix
        out_path = output_dir / out_name
        rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()
        out_path.write_text(rendered, encoding="utf-8")
        written.append(out_path.as_posix())

    stream = stdout or sys.stdout
    stream.write(f"Batch processed {len(written)} file(s):\n")
    for w in written:
        stream.write(f"  {w}\n")
    for pattern in unmatched_patterns:
        stream.write(f"  warning: no files matched pattern {pattern!r}\n")
    return 0


def _build_cascade_levels(
    *,
    start_budget: int,
    levels_count: int,
    include_rehydration_prompt: bool,
) -> list[Any]:
    """Build cascade levels derived from the user's budget and level count.

    Each subsequent level halves the budget of the previous one and focuses on
    the facets that matter most under tight space (constraints, decisions,
    state). Unlike the previous hardcoded ``[800, 400, 200]`` list, this honours
    ``--budget`` and produces exactly ``levels_count`` levels.
    """

    from .cascade import CascadeLevel

    if levels_count < 1:
        levels_count = 1

    levels: list[Any] = []
    budget = max(start_budget, 64)
    for index in range(levels_count):
        weights = {
            "pulse": 0.12,
            "goal": 0.14,
            "constraints": 0.16,
            "decisions": 0.16,
            "facts": 0.11,
            "state": 0.15,
            "open_loops": 0.12,
            "glossary": 0.04,
        }
        max_items = 6
        rehydration = include_rehydration_prompt and index == 0
        if index > 0:
            # Tighter levels drop fluff and prioritise hard signal.
            weights = {
                "pulse": 0.00,
                "goal": 0.00,
                "constraints": 0.50,
                "decisions": 0.40,
                "facts": 0.00,
                "state": 0.10,
                "open_loops": 0.00,
                "glossary": 0.00,
            }
            max_items = max(2, 6 - index * 2)
        levels.append(
            CascadeLevel(
                token_budget=max(budget, 32),
                facet_weights=weights,
                max_items_per_facet=max_items,
                include_rehydration_prompt=rehydration,
            )
        )
        budget = max(budget // 2, 32)
    return levels


def _read_input(input_path: str) -> str:
    if input_path == "-":
        return sys.stdin.read()
    return Path(input_path).read_text(encoding="utf-8")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        msg = "must be greater than zero"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def _write_output(rendered: str, output: str | None, stdout: TextIO | None) -> None:
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    else:
        (stdout or sys.stdout).write(rendered)


def _table(rows: list[dict[str, Any]]) -> str:
    lines = ["index score facet        tokens reasons              text"]
    for row in rows:
        reasons = ",".join(row["reasons"]) or "-"
        text = " ".join(str(row["text"]).split())
        if len(text) > 86:
            text = text[:83] + "..."
        lines.append(
            f"{row['index']:>5} {row['score']:>5.2f} {row['facet']:<12} "
            f"{row['tokens']:>6} {reasons:<20} {text}"
        )
    return "\n".join(lines) + "\n"
