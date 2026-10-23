# Архитектура / Architecture

## Overview

```text
Web dashboard / REST clients / MCP-capable coding agents
           |            |            |
           | HTTP       | HTTP       | stdio MCP
           v            v            v
      FastAPI routes                  FastMCP (optional)
             |                         |
             +---- Rule engine --------+
             |      masking + triage    |
             |                         |
             +---- SQLite store -------+
             |
             +---- Optional remote-compatible LLM (explicit opt-in)
                           |
                    action suggestion only
```

### Important design decisions

1. **Useful by default.** The deterministic classifier runs with no model API, no keys and no outside network calls. This is a **rules-based** system, not a trained ML classifier. It is predictable, explainable, and easy to demonstrate.
2. **Human-in-the-loop.** All outcomes are advisory. A person reviews the suggestion; urgent and legal requests are explicitly escalated. The optional LLM does **not** override category, owner or priority.
3. **Opt-in external model.** `PILOT_MODE=remote` plus `PILOT_LLM_BASE_URL` plus `PILOT_LLM_MODEL` are required. The API caller additionally sets `use_llm=true`; neither alone causes inference.
4. **Mask before saving or forwarding.** Common emails and Russian phone numbers are replaced in the rule-engine output; the raw text is not stored by this application. This is **not complete PII detection**, and the regex does not cover every identifier.
5. **Measured vs estimated.** Database counts and reported API tokens are observable. Labor savings come from user-specified **hypothetical** minutes and hourly rate; do not present the amount as achieved ROI.
6. **Agent integration.** The MCP server exposes three tools: `preview_ticket`, `get_work_queue` and `get_process_metrics`. It doesn't expose write/delete tools; the HTTP API handles state changes.
7. **Local HTTP hardening.** Browser mutations are same-origin guarded, `Host` is allowlisted, malformed authority values are rejected, and security decisions use the raw ASGI path. These controls reduce local-demo risk but do not replace production authentication.

### Components

- `api.py`: REST API, schemas, dashboard assets, lifespan database setup.
- `engine.py`: deterministic routing, priority rules, matching explanations and partial PII redaction.
- `llm.py`: optional OpenAI-compatible completion API, strict action-only response handling and consumption-based API cost estimate.
- `store.py`: SQLite persistence and statistics.
- `mcp_server.py`: stdio Model Context Protocol.
- `src/processpilot/web/`: dependency-free dashboard HTML/CSS/JS.

### Known constraints

- Not for direct public internet exposure without auth, user roles, reverse proxy, request-size limits and rate limits.
- No production email, CRM, Telegram or n8n connector. `source` is metadata only; inbound API/CSV adapters can be added later.
- No claims about compliance with Russian personal data legislation. Host locally, assess data flows and obtain the necessary legal/security review.
- No request queues/retries for remote inference. Only per-request processing.
- SQLite is adequate for a single instance / demo. A production multi-worker service may need Postgres and a job queue.
- Cost calculation is a per-request approximation using **user-configured** example rates; provider usage reports may be missing and hosting/hardware are excluded.
- Current demo preserves local ticket records. Manual deletion or database retention policy must be added for real users.
