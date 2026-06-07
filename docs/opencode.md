# OpenCode Integration

Context Diamond integrates with OpenCode as a local MCP server. OpenCode supports
local MCP servers through the `mcp` object in `opencode.json`, where `type` is
`"local"` and `command` is the process OpenCode starts.

## Install Context Diamond

From GitHub:

```bash
pip install git+https://github.com/RainCherb/context-diamond.git
```

For local development from this checkout:

```bash
pip install -e ".[dev]"
```

Confirm the MCP entrypoint is available:

```bash
context-diamond-mcp
```

It waits on stdin because OpenCode will communicate with it over stdio.

## Add To `opencode.json`

Create or update `opencode.json` in your project:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context_diamond": {
      "type": "local",
      "command": ["context-diamond-mcp"],
      "enabled": true,
      "timeout": 10000
    }
  }
}
```

OpenCode prefixes MCP tools with the server name, so these tools are exposed as:

- `context_diamond_compress_text`
- `context_diamond_compress_file`
- `context_diamond_benchmark_file`

## Use In OpenCode

Example prompts:

```text
Use context_diamond_compress_file on docs/architecture.md with budget 500 and
summarize the resulting capsule before editing.
```

```text
Use context_diamond_benchmark_file on examples/long_handoff.md with budget 320.
Compare the signal recall against head and tail baselines.
```

```text
Compress this handoff with context_diamond_compress_text using budget 600 and
loss_report true, then continue from the capsule.
```

## Tool Arguments

### `compress_text`

- `text` string, required
- `budget` integer, default `800`
- `title` string, default `OpenCode Context Capsule`
- `format` `"markdown"` or `"json"`, default `"markdown"`
- `loss_report` boolean, default `false`
- `tokenizer_profile` one of `generic`, `openai`, `anthropic`, `gemini`, `local-bpe`

### `compress_file`

Same as `compress_text`, but uses `path` instead of `text`.

### `benchmark_file`

- `path` string, required
- `budget` integer, default `500`
- `profile` one of `generic`, `openai`, `anthropic`, `gemini`, `local-bpe`
- `format` `"markdown"` or `"json"`, default `"markdown"`

## Permissions

If you use per-agent tool permissions in OpenCode, enable the server tools with a
glob pattern:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "tools": {
    "context_diamond*": true
  }
}
```

## Notes

- The MCP server is local and does not make network calls.
- `compress_file` reads UTF-8 text files from paths the OpenCode process can
  access.
- `--budget` controls selected capsule sections. Rendered Markdown includes
  headers and metadata lines.
