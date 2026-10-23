import asyncio
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from processpilot.api import create_app
from processpilot.config import Settings
from processpilot.engine import classify
from processpilot.llm import LLMError, enhance_with_llm


@contextmanager
def fake_llm_server(response_payload: dict, status: int = 200):
    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers.get("content-length", "0"))
            captured["path"] = self.path
            captured["body"] = self.rfile.read(size).decode("utf-8")
            raw = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], captured
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_real_http_llm_roundtrip_masks_pii_and_accounts_usage():
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"action": "  Проверить заявку и связаться с клиентом.  "},
                        ensure_ascii=False,
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 20},
    }
    with fake_llm_server(payload) as (port, captured):
        analysis = classify(
            "Ответьте me@example.com или +7 (999) 123-45-67: нужна цена тарифа"
        )
        settings = Settings(
            mode="remote",
            llm_base_url=f"http://127.0.0.1:{port}/v1",
            llm_model="test-model",
            input_usd_per_million=0.5,
            output_usd_per_million=1.0,
        )
        result = asyncio.run(enhance_with_llm(analysis, settings))

    assert captured["path"] == "/v1/chat/completions"
    assert "me@example.com" not in captured["body"]
    assert "999" not in captured["body"]
    assert "[EMAIL]" in captured["body"]
    assert "[PHONE]" in captured["body"]
    assert result.action == "Проверить заявку и связаться с клиентом."
    assert result.input_tokens == 120
    assert result.output_tokens == 20
    assert result.api_cost_usd == 0.00008


def test_llm_rejects_empty_action_after_trimming():
    payload = {
        "choices": [{"message": {"content": json.dumps({"action": "     "})}}],
        "usage": {},
    }
    with fake_llm_server(payload) as (port, _):
        settings = Settings(
            mode="remote",
            llm_base_url=f"http://127.0.0.1:{port}/v1",
            llm_model="test-model",
        )
        with pytest.raises(LLMError):
            asyncio.run(enhance_with_llm(classify("Нужна цена тарифа"), settings))


def test_invalid_remote_configuration_fails_without_persisting_ticket(tmp_path):
    settings = Settings(
        mode="remote",
        db_path=tmp_path / "bad-remote.sqlite3",
        llm_base_url="https://api.example.org/v1?unexpected=query",
        llm_model="test-model",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/tickets",
            json={"text": "Нужна цена тарифа", "use_llm": True},
        )
        assert response.status_code == 502
        assert client.get("/api/stats").json()["total"] == 0
