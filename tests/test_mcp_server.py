import json
from pathlib import Path

from context_diamond.mcp_server import handle_jsonrpc_message


def _request(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    response = handle_jsonrpc_message(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
    )
    assert response is not None
    return response


def test_mcp_initialize_exposes_tools_capability() -> None:
    response = _request("initialize")

    assert response["result"]["serverInfo"]["name"] == "context-diamond"
    assert "tools" in response["result"]["capabilities"]


def test_mcp_tools_list_contains_opencode_tools() -> None:
    response = _request("tools/list")
    tool_names = {tool["name"] for tool in response["result"]["tools"]}

    assert {"compress_text", "compress_file", "benchmark_file"} <= tool_names


def test_mcp_compress_text_tool_returns_markdown() -> None:
    response = _request(
        "tools/call",
        {
            "name": "compress_text",
            "arguments": {
                "text": "Goal: integrate with OpenCode. Decision: expose an MCP server.",
                "budget": 140,
            },
        },
    )

    content = response["result"]["content"][0]
    assert content["mimeType"] == "text/markdown"
    assert "OpenCode Context Capsule" in content["text"]


def test_mcp_compress_file_tool_can_return_json(tmp_path: Path) -> None:
    source = tmp_path / "handoff.md"
    source.write_text("The system must support OpenCode.\nDecision: use MCP.", encoding="utf-8")

    response = _request(
        "tools/call",
        {
            "name": "compress_file",
            "arguments": {"path": str(source), "format": "json", "loss_report": True},
        },
    )

    content = response["result"]["content"][0]
    data = json.loads(content["text"])
    assert content["mimeType"] == "application/json"
    assert data["metadata"]["loss_report"]["kept_count"] > 0


def test_mcp_benchmark_file_returns_table(tmp_path: Path) -> None:
    source = tmp_path / "handoff.md"
    source.write_text("The system must support OpenCode.\nDecision: use MCP.", encoding="utf-8")

    response = _request(
        "tools/call",
        {"name": "benchmark_file", "arguments": {"path": str(source), "budget": 120}},
    )

    assert "| Source | Budget |" in response["result"]["content"][0]["text"]


def test_mcp_unknown_tool_returns_error() -> None:
    response = _request("tools/call", {"name": "missing", "arguments": {}})

    assert response["error"]["code"] == -32000
    assert "unknown tool" in response["error"]["message"]
