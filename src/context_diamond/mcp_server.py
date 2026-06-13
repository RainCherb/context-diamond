"""Enhanced stdio MCP server for OpenCode and other MCP clients.

Implements the JSON-RPC subset for local MCP tool discovery, calls, and
resources. The server stays dependency-free while exposing all v0.7.0
features: templates, streaming sessions, batch processing, precise
tokenizers, and explainability.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .benchmark import render_markdown, run_benchmark
from .compressor import CompressionConfig, ContextDiamondCompressor
from .profiles import list_tokenizer_profiles
from .repo import compress_repo
from .streaming import StreamingCompressor
from .templates import get_template, list_templates
from .tokenizers import get_tokenizer, list_tokenizers

SERVER_INFO = {"name": "context-diamond", "version": "0.7.0"}
JSON_CONTENT = "application/json"
TEXT_CONTENT = "text/markdown"

#: In-memory streaming sessions by session_id.
_STREAMING_SESSIONS: dict[str, StreamingCompressor] = {}


def main(stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    """Run the line-delimited stdio MCP server."""

    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout

    for line in input_stream:
        if not line.strip():
            continue
        response = handle_jsonrpc_message(line, output_stream)
        if response is not None:
            output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()

    return 0


def handle_jsonrpc_message(
    raw: str, output_stream: TextIO | None = None
) -> dict[str, Any] | None:
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
            result = _call_tool(params, output_stream)
        else:
            return _error_response(request_id, -32601, f"unknown method: {method}")
    except Exception as error:  # noqa: BLE001
        return _error_response(request_id, -32000, str(error))

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": SERVER_INFO,
        "capabilities": {
            "tools": {},
            "resources": {},
        },
    }


def _tool_definitions() -> list[dict[str, Any]]:
    profiles = list_tokenizer_profiles()
    templates = list_templates()
    return [
        {
            "name": "compress_text",
            "description": (
                "Compress raw text into a Context Diamond capsule. "
                "Supports templates, precise tokenizers, and loss reports."
            ),
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
            "description": (
                "Compress a UTF-8 text/markdown file into a context capsule. "
                "Supports templates, precise tokenizers, and loss reports."
            ),
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
            "name": "explain_text",
            "description": (
                "Explain shard-level facets, scores, tokens, and reasons for a text. "
                "Useful for debugging why certain content was selected."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Raw text to analyze.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["table", "json"],
                        "default": "json",
                        "description": "Output format for explanation.",
                    },
                    "tokenizer_profile": {
                        "type": "string",
                        "enum": profiles,
                        "default": "generic",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "repo_capsule",
            "description": (
                "Create a capsule from repository state and selected files. "
                "Captures branch, git state, and chosen files."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository path. Default: current directory.",
                        "default": ".",
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1200,
                        "description": "Token budget.",
                    },
                    "title": {
                        "type": "string",
                        "default": "Repository Context Capsule",
                        "description": "Capsule title.",
                    },
                    "include": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to include before changed/untracked files.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": [],
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
        {
            "name": "batch_compress",
            "description": (
                "Batch-process multiple files into capsules. "
                "Each input file produces one output capsule."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to process.",
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 800,
                    },
                    "template": {
                        "type": "string",
                        "enum": templates,
                        "default": "default",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["paths"],
            },
        },
        {
            "name": "streaming_add",
            "description": (
                "Add a message to a streaming compressor session. "
                "Creates a new session if session_id does not exist."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier.",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message text to add.",
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 800,
                    },
                    "template": {
                        "type": "string",
                        "enum": templates,
                        "default": "default",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["session_id", "message"],
            },
        },
        {
            "name": "streaming_get",
            "description": "Get the current capsule from a streaming session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "streaming_reset",
            "description": "Reset (clear) a streaming session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier.",
                    },
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "list_templates",
            "description": "List available domain-specific capsule templates.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "list_tokenizers",
            "description": (
                "List available tokenizers, including optional extras. "
                "Use 'generic' if no extras are installed."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_template_info",
            "description": "Get detailed information about a specific template.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "enum": templates,
                        "description": "Template name.",
                    }
                },
                "required": ["template"],
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
        "template": {
            "type": "string",
            "enum": list_templates(),
            "default": "default",
            "description": "Domain-specific capsule template preset.",
        },
        "tokenizer": {
            "type": "string",
            "enum": list_tokenizers(),
            "default": "generic",
            "description": "Precise tokenizer to use (optional extras may be required).",
        },
    }


def _call_tool(params: Any, output_stream: TextIO | None = None) -> dict[str, Any]:
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

    if name == "explain_text":
        text = _required_string(arguments, "text")
        return _tool_text_result(_explain_text(text, arguments), _mime_for(arguments))

    if name == "repo_capsule":
        return _tool_text_result(_repo_capsule(arguments), _mime_for(arguments))

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

    if name == "batch_compress":
        return _batch_compress(arguments, output_stream)

    if name == "streaming_add":
        return _streaming_add(arguments)

    if name == "streaming_get":
        return _streaming_get(arguments)

    if name == "streaming_reset":
        return _streaming_reset(arguments)

    if name == "list_templates":
        return _tool_text_result(
            json.dumps(
                [
                    {
                        "name": t,
                        "description": get_template(t).description,
                        "title": get_template(t).title,
                    }
                    for t in list_templates()
                ],
                ensure_ascii=False,
                indent=2,
            ),
            JSON_CONTENT,
        )

    if name == "list_tokenizers":
        return _tool_text_result(
            json.dumps(
                [
                    {
                        "name": t,
                        "available": _is_tokenizer_available(t),
                    }
                    for t in list_tokenizers()
                ],
                ensure_ascii=False,
                indent=2,
            ),
            JSON_CONTENT,
        )

    if name == "get_template_info":
        template_name = _required_string(arguments, "template")
        template = get_template(template_name)
        return _tool_text_result(
            json.dumps(
                {
                    "name": template.name,
                    "description": template.description,
                    "title": template.title,
                    "max_items_per_facet": template.max_items_per_facet,
                    "facet_weights": template.facet_weights,
                    "included_facets": template.included_facets,
                },
                ensure_ascii=False,
                indent=2,
            ),
            JSON_CONTENT,
        )

    raise ValueError(f"unknown tool: {name}")


def _render_capsule(text: str, arguments: dict[str, Any]) -> str:
    output_format = str(arguments.get("format", "markdown"))
    template_name = str(arguments.get("template", "default"))
    template = get_template(template_name)
    config_kwargs = template.to_config_kwargs(
        token_budget=_positive_int(arguments.get("budget", 800), "budget")
    )
    config_kwargs["title"] = str(arguments.get("title", "OpenCode Context Capsule"))
    config_kwargs["include_loss_report"] = bool(arguments.get("loss_report", False))
    config_kwargs["tokenizer_profile"] = str(arguments.get("tokenizer_profile", "generic"))
    config = CompressionConfig(**config_kwargs)
    capsule = ContextDiamondCompressor(config).compress(text)
    if output_format == "json":
        return capsule.to_json()
    return capsule.to_markdown()


def _explain_text(text: str, arguments: dict[str, Any]) -> str:
    output_format = str(arguments.get("format", "json"))
    compressor = ContextDiamondCompressor(
        CompressionConfig(
            tokenizer_profile=str(arguments.get("tokenizer_profile", "generic"))
        )
    )
    rows = compressor.explain(text)
    if output_format == "table":
        lines = ["index score facet        tokens reasons              text"]
        for row in rows:
            reasons = ",".join(row["reasons"]) or "-"
            row_text = " ".join(str(row["text"]).split())
            if len(row_text) > 86:
                row_text = row_text[:83] + "..."
            lines.append(
                f"{row['index']:>5} {row['score']:>5.2f} {row['facet']:<12} "
                f"{row['tokens']:>6} {reasons:<20} {row_text}"
            )
        return "\n".join(lines) + "\n"
    return json.dumps(rows, ensure_ascii=False, indent=2)


def _repo_capsule(arguments: dict[str, Any]) -> str:
    output_format = str(arguments.get("format", "markdown"))
    path = str(arguments.get("path", "."))
    budget = _positive_int(arguments.get("budget", 1200), "budget")
    title = str(arguments.get("title", "Repository Context Capsule"))
    include = arguments.get("include")
    if include is not None and not isinstance(include, list):
        raise TypeError("include must be a list of strings")
    capsule = compress_repo(
        path,
        token_budget=budget,
        title=title,
        include=include if isinstance(include, list) else None,
    )
    if output_format == "json":
        return capsule.to_json()
    return capsule.to_markdown()


def _batch_compress(
    arguments: dict[str, Any], output_stream: TextIO | None = None
) -> dict[str, Any]:
    paths = arguments.get("paths")
    if not isinstance(paths, list):
        raise TypeError("paths must be a list of strings")
    budget = _positive_int(arguments.get("budget", 800), "budget")
    template_name = str(arguments.get("template", "default"))
    output_format = str(arguments.get("format", "markdown"))

    template = get_template(template_name)
    config_kwargs = template.to_config_kwargs(token_budget=budget)
    config = CompressionConfig(**config_kwargs)
    compressor = ContextDiamondCompressor(config)

    results: list[dict[str, Any]] = []
    for index, path_str in enumerate(paths, 1):
        path = Path(path_str)
        if not path.is_file():
            results.append({"path": path_str, "error": "file not found"})
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            capsule = compressor.compress(raw)
            results.append(
                {
                    "path": path_str,
                    "source_tokens": capsule.source_tokens,
                    "capsule_tokens": capsule.capsule_tokens,
                    "compression_ratio": capsule.compression_ratio,
                    "capsule": (
                        capsule.to_dict() if output_format == "json" else capsule.to_markdown()
                    ),
                }
            )
        except (OSError, ValueError, TypeError) as error:
            results.append({"path": path_str, "error": str(error)})

        if output_stream is not None:
            _send_progress(output_stream, "batch_compress", index, len(paths))

    return _tool_text_result(
        json.dumps(results, ensure_ascii=False, indent=2),
        JSON_CONTENT,
    )


def _streaming_add(arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = _required_string(arguments, "session_id")
    message = _required_string(arguments, "message")
    budget = _positive_int(arguments.get("budget", 800), "budget")
    template_name = str(arguments.get("template", "default"))
    output_format = str(arguments.get("format", "markdown"))

    if session_id not in _STREAMING_SESSIONS:
        template = get_template(template_name)
        config_kwargs = template.to_config_kwargs(token_budget=budget)
        _STREAMING_SESSIONS[session_id] = StreamingCompressor(CompressionConfig(**config_kwargs))

    streamer = _STREAMING_SESSIONS[session_id]
    capsule = streamer.add_message(message)
    return _tool_text_result(
        capsule.to_json() if output_format == "json" else capsule.to_markdown(),
        _mime_for(arguments),
    )


def _streaming_get(arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = _required_string(arguments, "session_id")
    output_format = str(arguments.get("format", "markdown"))

    if session_id not in _STREAMING_SESSIONS:
        raise ValueError(f"streaming session {session_id!r} not found")

    capsule = _STREAMING_SESSIONS[session_id].current_capsule
    if capsule is None:
        return _tool_text_result("No messages in session yet.", TEXT_CONTENT)

    return _tool_text_result(
        capsule.to_json() if output_format == "json" else capsule.to_markdown(),
        _mime_for(arguments),
    )


def _streaming_reset(arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = _required_string(arguments, "session_id")
    if session_id in _STREAMING_SESSIONS:
        del _STREAMING_SESSIONS[session_id]
    return _tool_text_result(
        json.dumps({"status": "ok", "session_id": session_id}, ensure_ascii=False),
        JSON_CONTENT,
    )


def _send_progress(output_stream: TextIO, operation: str, current: int, total: int) -> None:
    """Send a JSON-RPC notification with progress info."""
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/progress",
        "params": {
            "operation": operation,
            "current": current,
            "total": total,
            "percentage": round(current / max(total, 1) * 100, 1),
        },
    }
    output_stream.write(json.dumps(notification, ensure_ascii=False) + "\n")
    output_stream.flush()


def _is_tokenizer_available(name: str) -> bool:
    """Check whether a tokenizer is importable."""
    if name == "generic":
        return True
    try:
        get_tokenizer(name)
        return True
    except ImportError:
        return False


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
