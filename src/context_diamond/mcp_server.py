"""Minimal stdio MCP server for OpenCode and other MCP clients.

The implementation intentionally avoids runtime dependencies. It implements the
small JSON-RPC subset needed for local MCP tool discovery and calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .benchmark import render_markdown, run_benchmark
from .compressor import CompressionConfig, ContextDiamondCompressor
from .profiles import list_tokenizer_profiles

SERVER_INFO = {"name": "context-diamond", "version": "0.7.0"}
JSON_CONTENT = "application/json"
TEXT_CONTENT = "text/markdown"


def main(stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    """Run the line-delimited stdio MCP server."""

    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout

    for line in input_stream:
        if not line.strip():
            continue
        response = handle_jsonrpc_message(line)
        if response is not None:
            output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()

    return 0


def handle_jsonrpc_message(raw: str) -> dict[str, Any] | None:
    """Handle one JSON-RPC request or notification."""

    try:
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("message must be a JSON object")
    except (json.JSONDecodeError, ValueError) as error:
        return _error_response(None, -32700, str(error))

    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = _initialize_result()
        elif method == "tools/list":
            result = {"tools": _tool_definitions()}
        elif method == "tools/call":
            result = _call_tool(params)
        else:
            return _error_response(request_id, -32601, f"unknown method: {method}")
    except Exception as error:  # noqa: BLE001 - MCP should surface tool failures as JSON-RPC errors.
        return _error_response(request_id, -32000, str(error))

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": SERVER_INFO,
        "capabilities": {"tools": {}},
    }


def _tool_definitions() -> list[dict[str, Any]]:
    profiles = list_tokenizer_profiles()
    return [
        {
            "name": "compress_text",
            "description": "Compress raw text into a Context Diamond capsule.",
            "inputSchema": {
                "type": "object",
                "properties": _common_properties()
                | {
                    "text": {
                        "type": "string",
                        "description": "Raw text, chat transcript, logs, or notes to compress.",
                    }
                },
                "required": ["text"],
            },
        },
        {
            "name": "compress_file",
            "description": "Compress a UTF-8 text/markdown file into a context capsule.",
            "inputSchema": {
                "type": "object",
                "properties": _common_properties()
                | {
                    "path": {
                        "type": "string",
                        "description": "Path to a UTF-8 text or markdown file.",
                    }
                },
                "required": ["path"],
            },
        },
        {
            "name": "benchmark_file",
            "description": "Benchmark Context Diamond against head/tail clipping for one file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to a UTF-8 text file."},
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 500,
                        "description": "Target section token budget.",
                    },
                    "profile": {
                        "type": "string",
                        "enum": profiles,
                        "default": "generic",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["path"],
            },
        },
    ]


def _common_properties() -> dict[str, Any]:
    return {
        "budget": {
            "type": "integer",
            "minimum": 1,
            "default": 800,
            "description": "Target section token budget.",
        },
        "title": {
            "type": "string",
            "default": "OpenCode Context Capsule",
            "description": "Capsule title.",
        },
        "format": {
            "type": "string",
            "enum": ["markdown", "json"],
            "default": "markdown",
        },
        "loss_report": {
            "type": "boolean",
            "default": False,
            "description": "Include kept/omitted shard audit data in JSON metadata.",
        },
        "tokenizer_profile": {
            "type": "string",
            "enum": list_tokenizer_profiles(),
            "default": "generic",
        },
    }


def _call_tool(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise TypeError("tools/call params must be an object")

    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        raise TypeError("tool arguments must be an object")

    if name == "compress_text":
        text = _required_string(arguments, "text")
        return _tool_text_result(_render_capsule(text, arguments), _mime_for(arguments))

    if name == "compress_file":
        path = Path(_required_string(arguments, "path"))
        text = path.read_text(encoding="utf-8")
        return _tool_text_result(_render_capsule(text, arguments), _mime_for(arguments))

    if name == "benchmark_file":
        path = Path(_required_string(arguments, "path"))
        budget = _positive_int(arguments.get("budget", 500), "budget")
        profile = str(arguments.get("profile", "generic"))
        output_format = str(arguments.get("format", "markdown"))
        results = run_benchmark([path], budget=budget, profile=profile)
        if output_format == "json":
            rendered = json.dumps(
                [result.to_dict() for result in results],
                ensure_ascii=False,
                indent=2,
            )
            return _tool_text_result(rendered, JSON_CONTENT)
        return _tool_text_result(render_markdown(results), TEXT_CONTENT)

    raise ValueError(f"unknown tool: {name}")


def _render_capsule(text: str, arguments: dict[str, Any]) -> str:
    output_format = str(arguments.get("format", "markdown"))
    config = CompressionConfig(
        token_budget=_positive_int(arguments.get("budget", 800), "budget"),
        title=str(arguments.get("title", "OpenCode Context Capsule")),
        include_loss_report=bool(arguments.get("loss_report", False)),
        tokenizer_profile=str(arguments.get("tokenizer_profile", "generic")),
    )
    capsule = ContextDiamondCompressor(config).compress(text)
    if output_format == "json":
        return capsule.to_json()
    return capsule.to_markdown()


def _required_string(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string")
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def _mime_for(arguments: dict[str, Any]) -> str:
    return JSON_CONTENT if arguments.get("format") == "json" else TEXT_CONTENT


def _tool_text_result(text: str, mime_type: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text, "mimeType": mime_type}]}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
