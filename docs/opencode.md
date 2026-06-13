# OpenCode Integration

Context Diamond integrates with OpenCode as a local MCP server. OpenCode supports
local MCP servers through the `mcp` object in `opencode.json`, where `type` is
`"local"` and `command` is the process OpenCode starts.

## Install Context Diamond

From GitHub:

```bash
pip install git+https://github.com/RainCherb/context-diamond.git
```

For precise tokenizers, install optional extras:

```bash
pip install "git+https://github.com/RainCherb/context-diamond.git#egg=context-diamond[tiktoken]"
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
      "timeout": 30000
    }
  }
}
```

OpenCode prefixes MCP tools with the server name, so these tools are exposed as:

### Core Tools
- `context_diamond_compress_text`
- `context_diamond_compress_file`
- `context_diamond_explain_text`
- `context_diamond_repo_capsule`
- `context_diamond_benchmark_file`

### Batch & Streaming
- `context_diamond_batch_compress`
- `context_diamond_streaming_add`
- `context_diamond_streaming_get`
- `context_diamond_streaming_reset`

### Discovery
- `context_diamond_list_templates`
- `context_diamond_list_tokenizers`
- `context_diamond_get_template_info`

## Use In OpenCode

### Basic Compression

```text
Use context_diamond_compress_file on docs/architecture.md with budget 500 and
summarize the resulting capsule before editing.
```

```text
Compress this handoff with context_diamond_compress_text using budget 600 and
loss_report true, then continue from the capsule.
```

### Templates

```text
Use context_diamond_compress_text with template "coding" and budget 800
on the current codebase discussion.
```

```text
Show me the available templates using context_diamond_list_templates.
```

### Streaming Sessions

```text
Start a streaming session with session_id "sprint_42" and add:
"Goal: build a login form."
Then add: "Decision: use JWT tokens."
Get the current capsule with context_diamond_streaming_get.
```

```text
Reset the streaming session "sprint_42" when the sprint is done.
```

### Batch Processing

```text
Batch compress all markdown files in the docs folder using
context_diamond_batch_compress with template "support" and budget 400.
```

### Explainability

```text
Use context_diamond_explain_text on this long conversation to see why
specific shards were selected and how they were scored.
```

### Repository Context

```text
Create a repo capsule with context_diamond_repo_capsule on the current
project with budget 1200 and include README.md, pyproject.toml.
```

### Benchmarking

```text
Use context_diamond_benchmark_file on examples/long_handoff.md with budget 320.
Compare the signal recall against head and tail baselines.
```

## Tool Arguments

### `compress_text` / `compress_file`

- `text` / `path` — required
- `budget` — integer, default `800`
- `title` — string, default `OpenCode Context Capsule`
- `format` — `"markdown"` or `"json"`, default `"markdown"`
- `loss_report` — boolean, default `false`
- `tokenizer_profile` — one of `generic`, `openai`, `anthropic`, `gemini`, `local-bpe`
- `template` — one of `default`, `coding`, `support`, `research`, `incident`
- `tokenizer` — one of `generic`, `tiktoken`, `anthropic`, `transformers`

### `explain_text`

- `text` — string, required
- `format` — `"table"` or `"json"`, default `"json"`
- `tokenizer_profile` — one of available profiles

### `repo_capsule`

- `path` — string, default `.`
- `budget` — integer, default `1200`
- `title` — string, default `Repository Context Capsule`
- `include` — list of file paths
- `format` — `"markdown"` or `"json"`, default `"markdown"`

### `benchmark_file`

- `path` — string, required
- `budget` — integer, default `500`
- `profile` — one of available profiles
- `format` — `"markdown"` or `"json"`, default `"markdown"`

### `batch_compress`

- `paths` — list of strings, required
- `budget` — integer, default `800`
- `template` — one of available templates
- `format` — `"markdown"` or `"json"`, default `"markdown"`

### `streaming_add`

- `session_id` — string, required
- `message` — string, required
- `budget` — integer, default `800`
- `template` — one of available templates
- `format` — `"markdown"` or `"json"`, default `"markdown"`

### `streaming_get`

- `session_id` — string, required
- `format` — `"markdown"` or `"json"`, default `"markdown"`

### `streaming_reset`

- `session_id` — string, required

### `list_templates`

No arguments. Returns all templates with descriptions.

### `list_tokenizers`

No arguments. Returns all tokenizers with availability status.

### `get_template_info`

- `template` — string, required

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

- The MCP server is local and does not make network calls by default.
- `compress_file` reads UTF-8 text files from paths the OpenCode process can
  access.
- `--budget` controls selected capsule sections. Rendered Markdown includes
  headers and metadata lines.
- Streaming sessions are stored in memory and are lost when the server restarts.
- Batch operations send progress notifications for long-running tasks.
