"""Repository-aware context collection."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .compressor import CompressionConfig, ContextDiamondCompressor
from .model import ContextCapsule
from .tokenizer import estimate_tokens, trim_to_token_budget

DEFAULT_REPO_FILES = (
    "README.md",
    "pyproject.toml",
    "package.json",
    "CHANGELOG.md",
    "docs/architecture.md",
)


def build_repo_context(
    root: str | Path,
    *,
    include: list[str] | None = None,
    max_file_tokens: int = 500,
) -> str:
    """Build a deterministic text context from repository state and files."""

    repo_root = Path(root).resolve()
    if not repo_root.exists():
        msg = f"repository path does not exist: {repo_root}"
        raise FileNotFoundError(msg)

    included = include or list(DEFAULT_REPO_FILES)
    modified_paths = _git_lines(repo_root, "diff", "--name-only")
    untracked_paths = [
        line[3:] for line in _git_lines(repo_root, "status", "--short") if line.startswith("?? ")
    ]
    for path in [*modified_paths, *untracked_paths]:
        if path not in included:
            included.append(path)

    sections = [
        "# Repository Context",
        "",
        "## Git State",
        f"- Branch: {_git_one(repo_root, 'branch', '--show-current') or 'unknown'}",
        "- Status:",
        _indent_block("\n".join(_git_lines(repo_root, "status", "--short")) or "clean"),
        "- Diff stat:",
        _indent_block("\n".join(_git_lines(repo_root, "diff", "--stat")) or "none"),
        "",
        "## Files",
    ]

    for relative in included:
        path = (repo_root / relative).resolve()
        if not _is_within(path, repo_root) or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        sections.extend(
            [
                "",
                f"### {relative}",
                trim_to_token_budget(content, max_file_tokens)
                if estimate_tokens(content) > max_file_tokens
                else content.strip(),
            ]
        )

    return "\n".join(sections).strip() + "\n"


def compress_repo(
    root: str | Path,
    *,
    token_budget: int = 1200,
    title: str = "Repository Context Capsule",
    include: list[str] | None = None,
    max_file_tokens: int = 500,
) -> ContextCapsule:
    """Compress repository context into a Context Diamond capsule."""

    source = build_repo_context(root, include=include, max_file_tokens=max_file_tokens)
    return ContextDiamondCompressor(
        CompressionConfig(token_budget=token_budget, title=title)
    ).compress(source)


def _git_lines(root: Path, *args: str) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _git_one(root: Path, *args: str) -> str:
    lines = _git_lines(root, *args)
    return lines[0] if lines else ""


def _indent_block(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
