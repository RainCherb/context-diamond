import pytest

from context_diamond import CompressionConfig, ContextDiamondCompressor, compress_text

SOURCE = """
Goal: build a new public tool that compresses LLM context and saves tokens.
The system must be deterministic by default and must not require API keys.
Decision: use a diamond capsule with intent, constraints, decisions, facts, state, and risks.
Currently the prototype lives in `src/context_diamond/compressor.py`.
Open question: should vector embeddings become an optional plugin later?
""" + "\n".join(
    f"Research note {index}: repeated background detail about token waste, handoffs, "
    "conversation drift, and prompt reuse."
    for index in range(18)
)


def test_compress_text_returns_budgeted_capsule() -> None:
    capsule = compress_text(SOURCE, token_budget=180)

    assert capsule.source_tokens > capsule.capsule_tokens
    assert capsule.capsule_tokens <= 180
    assert capsule.sections


def test_sections_keep_constraints_and_decisions() -> None:
    capsule = ContextDiamondCompressor(CompressionConfig(token_budget=260)).compress(SOURCE)
    rendered = capsule.to_markdown()

    assert "Rules And Constraints" in rendered
    assert "must not require API keys" in rendered
    assert "Decisions Already Made" in rendered
    assert "diamond capsule" in rendered


def test_json_output_is_machine_readable() -> None:
    capsule = compress_text(SOURCE, token_budget=220)
    data = capsule.to_dict()

    assert data["strategy"] == "diamond-v1"
    assert data["metadata"]["token_budget"] == 220
    assert isinstance(data["sections"], list)


def test_capsule_does_not_repeat_items_across_sections() -> None:
    capsule = ContextDiamondCompressor(CompressionConfig(token_budget=320)).compress(SOURCE)
    items = [
        item
        for section in capsule.sections
        if section.title not in {"Diamond Pulse", "Entities And Anchors"}
        for item in section.items
    ]

    assert len(items) == len(set(items))


def test_config_rejects_invalid_budget() -> None:
    with pytest.raises(ValueError, match="token_budget"):
        CompressionConfig(token_budget=0)
