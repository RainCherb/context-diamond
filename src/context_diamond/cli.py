"""Command line interface for Context Diamond."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from .compressor import CompressionConfig, ContextDiamondCompressor


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
        type=int,
        default=800,
        help="Target capsule token budget. Default: 800.",
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
    return parser


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = stdout or sys.stdout

    raw = _read_input(args.input)
    source = json.loads(raw) if args.messages_json else raw

    compressor = ContextDiamondCompressor(
        CompressionConfig(
            token_budget=args.budget,
            include_rehydration_prompt=not args.no_rehydration_prompt,
        )
    )
    capsule = compressor.compress(source)
    rendered = capsule.to_json() if args.format == "json" else capsule.to_markdown()

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        stream.write(rendered)

    return 0


def _read_input(input_path: str) -> str:
    if input_path == "-":
        return sys.stdin.read()
    return Path(input_path).read_text(encoding="utf-8")
