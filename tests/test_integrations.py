from dataclasses import dataclass

from context_diamond import compress_documents, compress_messages, compress_tool_payload


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict[str, str]


def test_compress_messages_accepts_chat_dicts() -> None:
    capsule = compress_messages(
        [
            {"role": "user", "content": "Goal: preserve constraints."},
            {"role": "assistant", "content": "Decision: use deterministic extraction."},
        ],
        token_budget=160,
    )

    assert capsule.title == "Conversation Handoff"
    assert capsule.sections


def test_compress_documents_accepts_duck_typed_documents() -> None:
    capsule = compress_documents(
        [FakeDocument("The system must stay local.", {"source": "spec.md"})],
        token_budget=140,
    )

    assert capsule.title == "Document Context Capsule"
    assert "spec.md" in capsule.to_markdown()


def test_compress_tool_payload_accepts_json_like_payloads() -> None:
    capsule = compress_tool_payload(
        {"status": "failed", "error": "tests/test_cli.py must be updated"},
        token_budget=140,
    )

    assert capsule.title == "Tool Output Capsule"
    assert capsule.sections
