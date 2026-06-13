"""Tests for MCP server improvements."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from context_diamond.mcp_server import (
    handle_jsonrpc_message,
    main,
)


def _jsonrpc(method: str, params: dict[str, object] | None = None, id_: int = 1) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})


def test_initialize() -> None:
    response = handle_jsonrpc_message(_jsonrpc("initialize"))
    assert response is not None
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "context-diamond"


def test_tools_list() -> None:
    response = handle_jsonrpc_message(_jsonrpc("tools/list"))
    assert response is not None
    tools = response["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "compress_text" in names
    assert "compress_file" in names
    assert "explain_text" in names
    assert "repo_capsule" in names
    assert "benchmark_file" in names
    assert "batch_compress" in names
    assert "streaming_add" in names
    assert "streaming_get" in names
    assert "streaming_reset" in names
    assert "list_templates" in names
    assert "list_tokenizers" in names
    assert "get_template_info" in names


def test_compress_text() -> None:
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {"name": "compress_text", "arguments": {"text": "Goal: test MCP.", "budget": 100}},
        )
    )
    assert response is not None
    content = response["result"]["content"][0]["text"]
    assert "OpenCode Context Capsule" in content
    assert "Goal" in content


def test_compress_text_with_template() -> None:
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {
                "name": "compress_text",
                "arguments": {"text": "Goal: test template.", "template": "coding", "budget": 100},
            },
        )
    )
    assert response is not None
    content = response["result"]["content"][0]["text"]
    assert "OpenCode Context Capsule" in content
    assert "Goal" in content


def test_explain_text() -> None:
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {
                "name": "explain_text",
                "arguments": {"text": "Goal: test explain.", "format": "json"},
            },
        )
    )
    assert response is not None
    content = json.loads(response["result"]["content"][0]["text"])
    assert isinstance(content, list)
    assert len(content) > 0
    assert "facet" in content[0]


def test_list_templates() -> None:
    response = handle_jsonrpc_message(_jsonrpc("tools/call", {"name": "list_templates"}))
    assert response is not None
    content = json.loads(response["result"]["content"][0]["text"])
    names = {t["name"] for t in content}
    assert "default" in names
    assert "coding" in names
    assert "support" in names
    assert "research" in names
    assert "incident" in names


def test_list_tokenizers() -> None:
    response = handle_jsonrpc_message(_jsonrpc("tools/call", {"name": "list_tokenizers"}))
    assert response is not None
    content = json.loads(response["result"]["content"][0]["text"])
    names = {t["name"] for t in content}
    assert "generic" in names


def test_get_template_info() -> None:
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {"name": "get_template_info", "arguments": {"template": "coding"}},
        )
    )
    assert response is not None
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["name"] == "coding"
    assert "facet_weights" in content


def test_streaming_session() -> None:
    # Reset any previous session
    handle_jsonrpc_message(
        _jsonrpc("tools/call", {"name": "streaming_reset", "arguments": {"session_id": "test_1"}})
    )

    # Add first message
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {
                "name": "streaming_add",
                "arguments": {
                    "session_id": "test_1",
                    "message": "Goal: build a tool.",
                    "budget": 200,
                },
            },
        )
    )
    assert response is not None
    content = response["result"]["content"][0]["text"]
    assert "build a tool" in content

    # Add second message
    response2 = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {
                "name": "streaming_add",
                "arguments": {
                    "session_id": "test_1",
                    "message": "Decision: use Python.",
                    "budget": 200,
                },
            },
        )
    )
    assert response2 is not None
    content2 = response2["result"]["content"][0]["text"]
    assert "Python" in content2

    # Get current capsule
    response3 = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {"name": "streaming_get", "arguments": {"session_id": "test_1"}},
        )
    )
    assert response3 is not None
    content3 = response3["result"]["content"][0]["text"]
    assert "build a tool" in content3
    assert "Python" in content3

    # Reset
    response4 = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {"name": "streaming_reset", "arguments": {"session_id": "test_1"}},
        )
    )
    assert response4 is not None
    status = json.loads(response4["result"]["content"][0]["text"])
    assert status["status"] == "ok"

    # Get after reset should error
    response5 = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {"name": "streaming_get", "arguments": {"session_id": "test_1"}},
        )
    )
    assert response5 is not None
    assert "error" in response5


def test_batch_compress() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = Path(tmpdir) / "a.md"
        p1.write_text("Goal: test batch.\nDecision: use JSON.")
        response = handle_jsonrpc_message(
            _jsonrpc(
                "tools/call",
                {
                    "name": "batch_compress",
                    "arguments": {"paths": [str(p1)], "budget": 200, "format": "json"},
                },
            )
        )
        assert response is not None
        content = json.loads(response["result"]["content"][0]["text"])
        assert len(content) == 1
        assert "source_tokens" in content[0]
        assert "capsule" in content[0]


def test_repo_capsule() -> None:
    response = handle_jsonrpc_message(
        _jsonrpc(
            "tools/call",
            {
                "name": "repo_capsule",
                "arguments": {"path": ".", "budget": 500, "format": "markdown"},
            },
        )
    )
    assert response is not None
    content = response["result"]["content"][0]["text"]
    assert "Repository Context" in content


def test_error_response() -> None:
    response = handle_jsonrpc_message("not json")
    assert response is not None
    assert "error" in response
    assert response["error"]["code"] == -32700


def test_unknown_method() -> None:
    response = handle_jsonrpc_message(_jsonrpc("unknown_method"))
    assert response is not None
    assert "error" in response
    assert response["error"]["code"] == -32601


def test_main_runs_until_eof() -> None:
    import io

    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize"}\n')
    stdout = io.StringIO()
    result = main(stdin, stdout)
    assert result == 0
    output = stdout.getvalue()
    assert "context-diamond" in output
