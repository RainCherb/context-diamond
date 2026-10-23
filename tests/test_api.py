from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from processpilot.api import create_app
from processpilot.config import Settings
from processpilot.engine import classify
from processpilot.store import Store


def make_client(tmp_path):
    return TestClient(create_app(Settings(db_path=tmp_path / "test.sqlite3")))


def test_health_and_new_ticket(tmp_path):
    with make_client(tmp_path) as client:
        health = client.get("/api/health")
        assert health.json()["status"] == "ok"
        assert health.headers["cache-control"] == "no-store"
        resp = client.post("/api/tickets", json={"text": "Срочно! Отвечайте на me@example.com, ошибка оплаты"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] > 0
        assert "me@example.com" not in body["text"]
        assert body["pii_detected"] is True
        assert body["handling_mode"] == "human-review"
        assert len(body["reasons"]) >= 2
        assert client.get(f"/api/tickets/{body['id']}").json()["id"] == body["id"]
        assert client.get("/api/stats").json()["urgent"] == 1


def test_whitespace_only_and_short_after_trim_are_validation_errors(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/api/tickets", json={"text": "     "}).status_code == 422
        assert client.post("/api/tickets", json={"text": "    x   "}).status_code == 422
        response = client.post("/api/tickets", json={"text": "   Обычный запрос   ", "source": " CRM "})
        assert response.status_code == 201
        assert response.json()["source"] == "crm"


def test_invalid_and_remote_opt_in(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/api/tickets", json={"text": "no"}).status_code == 422
        assert client.post("/api/tickets", json={"text": "Обычный запрос", "use_llm": True}).status_code == 409
        assert client.get("/api/tickets/999").status_code == 404
        assert client.get("/api/tickets?limit=1000").status_code == 422
        assert client.post("/api/roi", json={"minutes_saved_per_ticket": -1}).status_code == 422
        assert client.post(
            "/api/roi",
            content='{"minutes_saved_per_ticket": NaN, "hourly_cost_rub": 900}',
            headers={"Content-Type": "application/json"},
        ).status_code == 422
        assert client.post(
            "/api/roi",
            content='{"minutes_saved_per_ticket": 4, "hourly_cost_rub": Infinity}',
            headers={"Content-Type": "application/json"},
        ).status_code == 422


def test_untrusted_host_is_rejected_to_reduce_dns_rebinding_risk(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/health", headers={"Host": "attacker.example"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid host header"
        malformed = client.get("/api/health", headers={"Host": "testserver/api/health"})
        assert malformed.status_code == 400


def test_cross_origin_browser_mutations_are_rejected(tmp_path):
    with make_client(tmp_path) as client:
        blocked = client.post("/api/demo/seed", headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        allowed = client.post("/api/demo/seed", headers={"Origin": "http://testserver"})
        assert allowed.status_code == 200
        assert allowed.json()["created"] == 6


def test_seed_idempotent_status_and_scenario_roi(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/api/demo/seed").json()["created"] == 6
        assert client.post("/api/demo/seed").json()["created"] == 0
        rows = client.get("/api/tickets").json()
        assert len(rows) == 6
        assert client.patch(f"/api/tickets/{rows[0]['id']}/status?status=resolved").status_code == 200
        assert client.patch(f"/api/tickets/{rows[0]['id']}/status?status=invalid").status_code == 422
        stats = client.get("/api/stats").json()
        assert stats["resolved"] == 1
        roi = client.post("/api/roi", json={"minutes_saved_per_ticket": 6, "hourly_cost_rub": 1000}).json()
        assert roi["tickets"] == 6
        assert roi["hours_assumption"] == 0.6
        assert roi["potential_labor_value_rub"] == 600
        assert "НЕ измеренная" in roi["disclaimer"]


def test_seed_is_atomic_under_concurrent_calls(tmp_path):
    store = Store(tmp_path / "concurrent.sqlite3")
    store.init()
    rows = [classify("Ошибка 500, сервис не работает"), classify("Нужна цена тарифа")]

    def seed():
        return store.seed_if_empty(rows)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: seed(), range(2)))
    assert sorted(results) == [0, 2]
    assert store.stats()["total"] == 2


def test_dashboard_assets_and_security_headers(tmp_path):
    with make_client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Process Pilot" in page.text
        assert "AI-автоматизация" in page.text
        assert page.headers["x-content-type-options"] == "nosniff"
        assert page.headers["x-frame-options"] == "DENY"
        assert "default-src 'self'" in page.headers["content-security-policy"]
        assert "server-status-title" in page.text
        assert client.get("/app.css").status_code == 200
        assert client.get("/app.js").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_no_duplicate_data_accidentally_on_restart(tmp_path):
    s = Settings(db_path=tmp_path / "persist.sqlite3")
    with TestClient(create_app(s)) as client:
        client.post("/api/tickets", json={"text": "Обычный запрос от клиента"})
    with TestClient(create_app(s)) as client:
        assert client.get("/api/stats").json()["total"] == 1
