"""HTTP API and dashboard serving. Single-operator local-first demo by design."""
from __future__ import annotations

from contextlib import asynccontextmanager
import math
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

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

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RoiInput(BaseModel):
    minutes_saved_per_ticket: float = Field(default=4.0, ge=0, le=240, allow_inf_nan=False)
    hourly_cost_rub: float = Field(default=900.0, ge=0, le=1_000_000, allow_inf_nan=False)


def _origin_matches_host(origin: str, host: str) -> bool:
    """Basic same-origin guard for browser-initiated state-changing requests."""
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and parsed.netloc.lower() == host.lower()




def _host_allowed(host_header: str, allowed_hosts: tuple[str, ...]) -> bool:
    try:
        parsed = urlsplit(f"//{host_header}")
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    # A Host header is authority only. Reject URL metacharacters/path/query tricks
    # rather than letting framework URL reconstruction reinterpret them.
    if (
        not hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        return False
    hostname = hostname.lower()
    for pattern in allowed_hosts:
        if pattern == "*" or hostname == pattern:
            return True
        if pattern.startswith("*.") and hostname.endswith(pattern[1:]):
            return True
    return False


def _json_safe(value):
    """Make validation error details JSON-safe, including NaN/Infinity inputs."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = Store(config.db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.init()
        yield

    app = FastAPI(title="AI Process Pilot", version="1.0.1", lifespan=lifespan)
    app.state.store = store
    app.state.settings = config

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": _json_safe(exc.errors())})

    @app.middleware("http")
    async def harden_local_dashboard(request: Request, call_next):
        # Security decisions use the raw ASGI path, matching router dispatch semantics.
        path = request.scope.get("path", "")
        host = request.headers.get("host", "")
        if not _host_allowed(host, config.allowed_hosts):
            return JSONResponse(status_code=400, content={"detail": "Invalid host header"})

        # No authentication exists in this portfolio demo. Reject browser cross-origin
        # mutations (e.g. a malicious page POSTing to localhost) while keeping CLI/API
        # clients without an Origin header working normally.
        if request.method not in {"GET", "HEAD", "OPTIONS"} and path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and not _origin_matches_host(origin, host):
                return JSONResponse(status_code=403, content={"detail": "Cross-origin mutation is not allowed"})

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if path == "/":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        return response

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
            "privacy_disclaimer": (
                "Маскируются только типовые email и некоторые российские номера телефонов; "
                "это не полная анонимизация"
            ),
        }

    @app.post("/api/tickets", status_code=201)
    async def create_ticket(data: TicketInput):
        result = classify(data.text)
        if data.use_llm:
            if not config.remote_ready:
                raise HTTPException(
                    409,
                    "Внешняя модель выключена: настройте PILOT_MODE=remote и LLM-провайдер",
                )
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
            "disclaimer": (
                "Сценарная оценка, НЕ измеренная экономия. Стоимость API в USD не вычтена "
                "из суммы в RUB; затраты на инфраструктуру и контроль не учтены."
            ),
        }

    @app.post("/api/demo/seed")
    def seed_demo():
        created = store.seed_if_empty((classify(sample) for sample in SAMPLES), "demo")
        if not created:
            return {"created": 0, "message": "Данные уже есть; существующие обращения не изменены"}
        return {"created": created}

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
