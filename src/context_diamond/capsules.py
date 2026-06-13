"""Utilities for comparing and merging rendered capsules."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .model import CapsuleSection, ContextCapsule


def load_capsule_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON capsule from disk."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "sections" not in data:
        msg = f"{path} is not a Context Diamond JSON capsule"
        raise ValueError(msg)
    return data


def diff_capsules(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Return section/item additions and removals between two capsule dicts."""

    left_sections = _section_map(left)
    right_sections = _section_map(right)
    section_titles = sorted(set(left_sections) | set(right_sections))
    changes = []

    for title in section_titles:
        left_items = left_sections.get(title, [])
        right_items = right_sections.get(title, [])
        added = _ordered_difference(right_items, left_items)
        removed = _ordered_difference(left_items, right_items)
        if added or removed:
            changes.append({"section": title, "added": added, "removed": removed})

    return {
        "left_title": left.get("title"),
        "right_title": right.get("title"),
        "left_sha256": left.get("source_sha256"),
        "right_sha256": right.get("source_sha256"),
        "changed_sections": changes,
        "added_sections": [title for title in section_titles if title not in left_sections],
        "removed_sections": [title for title in section_titles if title not in right_sections],
    }


def render_capsule_diff(diff: dict[str, Any]) -> str:
    """Render a capsule diff as Markdown."""

    lines = [
        "# Context Diamond Diff",
        "",
        f"- Left: `{diff.get('left_title')}`",
        f"- Right: `{diff.get('right_title')}`",
        "",
    ]
    if not diff["changed_sections"]:
        lines.append("No section item changes.")
        return "\n".join(lines) + "\n"

    for change in diff["changed_sections"]:
        lines.append(f"## {change['section']}")
        for item in change["added"]:
            lines.append(f"- Added: {item}")
        for item in change["removed"]:
            lines.append(f"- Removed: {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def merge_capsules(
    capsules: list[dict[str, Any]],
    *,
    title: str = "Merged Context Diamond Capsule",
    token_budget: int | None = None,
) -> ContextCapsule:
    """Merge JSON capsules, preserving section order and deduplicating items."""

    sections_by_title: OrderedDict[str, list[str]] = OrderedDict()
    for capsule in capsules:
        for section in capsule.get("sections", []):
            title_value = str(section.get("title", "Untitled"))
            items = section.get("items", [])
            if not isinstance(items, list):
                continue
            bucket = sections_by_title.setdefault(title_value, [])
            seen = {_item_key(item) for item in bucket}
            for item in items:
                if not isinstance(item, str):
                    continue
                key = _item_key(item)
                if key not in seen:
                    bucket.append(item)
                    seen.add(key)

    merged_text = "\n\n".join(
        f"{title_value}:\n" + "\n".join(f"- {item}" for item in items)
        for title_value, items in sections_by_title.items()
    )

    if token_budget is not None:
        return ContextDiamondCompressor(
            CompressionConfig(token_budget=token_budget, title=title)
        ).compress(merged_text)

    sections = [
        CapsuleSection(title=title_value, items=items)
        for title_value, items in sections_by_title.items()
        if items
    ]
    source_tokens = sum(int(capsule.get("source_tokens", 0)) for capsule in capsules)
    return ContextCapsule(
        title=title,
        sections=sections,
        source_tokens=source_tokens,
        capsule_tokens=sum(section.token_count for section in sections),
        source_sha256=ContextCapsule.digest_for(merged_text),
        metadata={"merged_capsules": len(capsules)},
    )


def _section_map(capsule: dict[str, Any]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for section in capsule.get("sections", []):
        title = section.get("title")
        items = section.get("items", [])
        if isinstance(title, str) and isinstance(items, list):
            sections[title] = [item for item in items if isinstance(item, str)]
    return sections


def _ordered_difference(left: list[str], right: list[str]) -> list[str]:
    right_keys = {_item_key(item) for item in right}
    return [item for item in left if _item_key(item) not in right_keys]


def _item_key(item: str) -> str:
    return " ".join(item.lower().split())
