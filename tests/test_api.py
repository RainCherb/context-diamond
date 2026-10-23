from fastapi.testclient import TestClient

from processpilot.api import create_app
from processpilot.config import Settings


def make_client(tmp_path):
    return TestClient(create_app(Settings(db_path=tmp_path / "test.sqlite3")))


def test_health_and_new_ticket(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/api/health").json()["status"] == "ok"
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


def test_invalid_and_remote_opt_in(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/api/tickets", json={"text": "no"}).status_code == 422
        assert client.post("/api/tickets", json={"text": "Обычный запрос", "use_llm": True}).status_code == 409
        assert client.get("/api/tickets/999").status_code == 404
        assert client.get("/api/tickets?limit=1000").status_code == 422
        assert client.post("/api/roi", json={"minutes_saved_per_ticket": -1}).status_code == 422


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


def test_dashboard_assets(tmp_path):
    with make_client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Process Pilot" in page.text
        assert "AI-автоматизация" in page.text
        assert client.get("/app.css").status_code == 200
        assert client.get("/app.js").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_no_duplicate_data_accidentally_on_restart(tmp_path):
    s = Settings(db_path=tmp_path / "persist.sqlite3")
    with TestClient(create_app(s)) as client:
        client.post("/api/tickets", json={"text": "Обычный запрос от клиента"})
    with TestClient(create_app(s)) as client:
        assert client.get("/api/stats").json()["total"] == 1
