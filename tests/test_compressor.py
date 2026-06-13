from dataclasses import replace

import pytest

from context_diamond import (
    CompressionConfig,
    ContextDiamondCompressor,
    EmbeddingReranker,
    Message,
    clear_registered_plugins,
    compress_text,
    register_plugin,
)

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


def test_loss_report_can_be_added_to_metadata() -> None:
    capsule = ContextDiamondCompressor(
        CompressionConfig(token_budget=180, include_loss_report=True)
    ).compress(SOURCE)

    report = capsule.metadata["loss_report"]
    assert report["kept_count"] > 0
    assert "omitted_by_facet" in report
    assert capsule.metadata["tokenizer_profile"] == "generic"


def test_compressor_explain_returns_shard_audit_rows() -> None:
    rows = ContextDiamondCompressor().explain("Решение: использовать MCP.\nНельзя терять правила.")

    assert rows[0]["facet"] == "decisions"
    assert any(row["facet"] == "constraints" for row in rows)


def test_registered_plugin_can_refine_shards() -> None:
    class BoostPlugin:
        name = "boost-test"

        def refine_shards(self, messages, shards):
            return [
                replace(shard, score=shard.score + 1, reasons=(*shard.reasons, "boost"))
                for shard in shards
            ]

    clear_registered_plugins()
    register_plugin(BoostPlugin())
    try:
        capsule = ContextDiamondCompressor().compress("Goal: keep extension hooks.")
    finally:
        clear_registered_plugins()

    assert capsule.metadata["plugins"] == ["boost-test"]
    assert "boost-test" not in capsule.to_markdown()


def test_embedding_reranker_uses_caller_supplied_embeddings() -> None:
    def embed(texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vectors.append([1.0, 0.0] if "Decision" in text or "important" in text else [0.0, 1.0])
        return vectors

    config = CompressionConfig(
        reranker=EmbeddingReranker(embed, query="important Decision", semantic_weight=0.5)
    )
    rows = ContextDiamondCompressor(config).explain(
        [
            Message(role="source", content="Background note."),
            Message(role="source", content="Decision: keep optional embedding reranking."),
        ]
    )

    assert rows[0]["text"].startswith("Decision:")
    assert "embedding-rerank" in rows[0]["reasons"]
