"""HTTP API and dashboard serving. Single-operator local-first demo by design."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import Settings
from .engine import classify
from .llm import LLMError, enhance_with_llm
from .store import Store

WEB_ROOT = Path(__file__).resolve().parent / "web"
SAMPLES = [
    "Срочно! Ошибка 500, сервис недоступен для всех клиентов. Напишите на alice@example.com",
    "Пожалуйста, отправьте счёт на оплату и закрывающие документы.",
    "Подскажите цену для команды из 12 человек. Хотим демо.",
    "Где наш заказ? Доставка задерживается третий день.",
    "Нужен возврат средств по ошибочной оплате.",
    "Здравствуйте! Расскажите подробнее о ваших услугах.",
]


class TicketInput(BaseModel):
    text: str = Field(min_length=5, max_length=8000)
    source: str = Field(default="web", min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    use_llm: bool = False


class RoiInput(BaseModel):
    minutes_saved_per_ticket: float = Field(default=4.0, ge=0, le=240)
    hourly_cost_rub: float = Field(default=900.0, ge=0, le=1_000_000)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = Store(config.db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.init()
        yield

    app = FastAPI(title="AI Process Pilot", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.state.settings = config

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": config.mode, "remote_ready": config.remote_ready}

    @app.get("/api/config")
    def public_config():
        return {
            "mode": config.mode,
            "remote_ready": config.remote_ready,
            "input_usd_per_1m_example": config.input_usd_per_million,
            "output_usd_per_1m_example": config.output_usd_per_million,
            "price_disclaimer": "Пример тарифов, а не актуальные цены поставщиков",
            "privacy_disclaimer": "Маскируются только email и некоторые номера телефонов; это не полная анонимизация",
        }

    @app.post("/api/tickets", status_code=201)
    async def create_ticket(data: TicketInput):
        result = classify(data.text)
        if data.use_llm:
            if not config.remote_ready:
                raise HTTPException(409, "Внешняя модель выключена: настройте PILOT_MODE=remote и LLM-провайдер")
            try:
                result = await enhance_with_llm(result, config)
            except LLMError as exc:
                raise HTTPException(502, str(exc)) from exc
        return store.create(result, data.source)

    @app.get("/api/tickets")
    def tickets(limit: int = 100):
        if not 1 <= limit <= 200:
            raise HTTPException(422, "limit должен быть от 1 до 200")
        return store.list(limit)

    @app.get("/api/tickets/{ticket_id}")
    def ticket(ticket_id: int):
        result = store.get(ticket_id)
        if not result:
            raise HTTPException(404, "Обращение не найдено")
        return result

    @app.patch("/api/tickets/{ticket_id}/status")
    def change_status(ticket_id: int, status: str):
        if status not in ("new", "in_progress", "resolved"):
            raise HTTPException(422, "Допустимый статус: new, in_progress, resolved")
        result = store.update_status(ticket_id, status)
        if not result:
            raise HTTPException(404, "Обращение не найдено")
        return result

    @app.get("/api/stats")
    def stats():
        return store.stats()

    @app.post("/api/roi")
    def roi(input: RoiInput):
        stats = store.stats()
        hours = round(stats["total"] * input.minutes_saved_per_ticket / 60, 2)
        value = round(hours * input.hourly_cost_rub, 2)
        return {
            "tickets": stats["total"],
            "hours_assumption": hours,
            "potential_labor_value_rub": value,
            "api_spend_usd": stats["api_cost_usd"],
            "assumptions": input.model_dump(),
            "disclaimer": "Сценарная оценка, НЕ измеренная экономия. Стоимость API в USD не вычтена из суммы в RUB; затраты на инфраструктуру и контроль не учтены.",
        }

    @app.post("/api/demo/seed")
    def seed_demo():
        if store.stats()["total"]:
            return {"created": 0, "message": "Данные уже есть; существующие обращения не изменены"}
        for sample in SAMPLES:
            store.create(classify(sample), "demo")
        return {"created": len(SAMPLES)}

    @app.get("/")
    def index():
        return FileResponse(WEB_ROOT / "index.html")

    @app.get("/app.css")
    def css():
        return FileResponse(WEB_ROOT / "app.css", media_type="text/css")

    @app.get("/app.js")
    def js():
        return FileResponse(WEB_ROOT / "app.js", media_type="application/javascript")

    return app


app = create_app()
