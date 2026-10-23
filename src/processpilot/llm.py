"""Optional LLM-assisted rewrite using an OpenAI-compatible chat endpoint."""
from __future__ import annotations

import ipaddress
import json
from dataclasses import replace
from urllib.parse import urlsplit

import httpx

from .config import Settings
from .engine import Analysis


class LLMError(Exception):
    pass


def validate_base_url(url: str) -> None:
    """Reject unsafe or ambiguous URL forms.

    The URL is controlled by the deployer rather than HTTP clients, so private and
    loopback endpoints remain allowed for local/self-hosted models. Production still
    needs network-level egress controls.
    """
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
    ):
        raise LLMError("Неверный или небезопасный адрес LLM API")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise LLMError("Некорректный порт LLM API") from exc
    if parsed.path not in ("", "/", "/v1", "/v1/"):
        raise LLMError("PILOT_LLM_BASE_URL должен указывать на корень API (например /v1)")
    # URL comes from the deployer, not from HTTP clients. Block common cloud metadata targets.
    if parsed.hostname in ("metadata.google.internal", "169.254.169.254"):
        raise LLMError("Адрес metadata-сервиса запрещён")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
        if addr.is_link_local or addr.is_multicast or addr.is_unspecified:
            raise LLMError("Небезопасный сетевой адрес")
    except ValueError:
        pass


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int, settings: Settings) -> float:
    return round(
        (
            prompt_tokens * settings.input_usd_per_million
            + completion_tokens * settings.output_usd_per_million
        )
        / 1_000_000,
        8,
    )


async def enhance_with_llm(analysis: Analysis, settings: Settings) -> Analysis:
    """Preserve deterministic routing; use LLM only for a short action suggestion.

    This prevents an LLM from assigning ownership or downgrading urgency.
    """
    if not settings.remote_ready:
        return analysis
    validate_base_url(settings.llm_base_url)
    prompt = (
        "Ты ассистент маршрутизации деловых обращений. Подготовь одно короткое безопасное "
        "действие для оператора на русском языке (до 220 символов). Не обещай выполнить работу, "
        "не принимай правовых или финансовых решений. Верни только JSON вида "
        '{"action":"..."}. Сведения могли быть замаскированы.\n'
        f"Категория: {analysis.category_label}\nПриоритет: {analysis.priority}\n"
        f"Обращение: {analysis.masked_text[:4000]}"
    )
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    # Explicitly opt-in, and disable redirects/proxy inheritance to reduce accidental egress.
    async with httpx.AsyncClient(
        timeout=settings.llm_timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        try:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
            raw = body["choices"][0]["message"]["content"]
            obj = json.loads(raw)
            action = obj.get("action", "")
            if not isinstance(action, str):
                raise LLMError("Некорректный ответ модели")
            action = action.strip()
            if not (4 <= len(action) <= 220):
                raise LLMError("Некорректный ответ модели")
            usage = body.get("usage") or {}
            in_tokens = max(0, int(usage.get("prompt_tokens") or 0))
            out_tokens = max(0, int(usage.get("completion_tokens") or 0))
            return replace(
                analysis,
                action=action,
                provider_used=f"compatible:{settings.llm_model}",
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                api_cost_usd=estimate_cost_usd(in_tokens, out_tokens, settings),
                reasons=analysis.reasons
                + ["Предложение действия подготовлено LLM; требуется проверка оператором"],
            )
        except LLMError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("LLM недоступна или вернула неподдерживаемый ответ") from exc
