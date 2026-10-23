import math

import pytest

from processpilot.config import Settings
from processpilot.engine import classify, mask_contact_details
from processpilot.llm import LLMError, estimate_cost_usd, validate_base_url
from processpilot.mcp_server import _validated_text


@pytest.mark.parametrize("text,category,owner", [
    ("Хочу узнать стоимость тарифа", "sales", "Продажи"),
    ("Пожалуйста, пришлите счёт на оплату", "billing", "Финансы"),
    ("Ошибка 500, не работает вход", "technical", "Техподдержка"),
    ("Посылка не дошла, доставка задерживается", "delivery", "Операции"),
    ("Привет, можно задать вопрос?", "general", "Первая линия"),
])
def test_classification(text, category, owner):
    item = classify(text)
    assert item.category == category
    assert item.owner == owner
    assert item.reasons
    assert item.handling_mode in ("draft-for-review", "human-review")


def test_normalized_patterns_are_not_double_counted():
    # "счет" and "счёт" are two source spellings of the same normalized token.
    # Billing must not receive two votes and incorrectly tie delivery here.
    x = classify("Нужен счёт, а ещё заказ и доставка задерживаются")
    assert x.category == "delivery"




def test_keyword_matching_avoids_common_substring_false_positives():
    assert classify("Это несрочно, небольшая ошибка").priority == "medium"
    assert classify("Нужна посуда для кухни").priority == "low"
    assert classify("Нужно обсудить border design").category == "general"
    assert classify("We build industrial automation").category == "general"

def test_high_priority_stays_human_review():
    x = classify("СРОЧНО! Критичный сбой, не работает оплата")
    assert x.priority == "high"
    assert x.handling_mode == "human-review"


def test_sensitive_request_escalates_to_human():
    x = classify("По договору обращается юрист")
    assert x.handling_mode == "human-review"
    assert x.priority == "medium"


def test_mask_emails_and_russian_phones():
    text = "Ответьте alex.test+demo@example.org или +7 (999) 123-45-67"
    redacted, found = mask_contact_details(text)
    assert found is True
    assert "alex.test" not in redacted
    assert "999" not in redacted
    assert "[EMAIL]" in redacted
    assert "[PHONE]" in redacted


def test_mask_does_not_claim_to_remove_everything():
    text, detected = mask_contact_details("Меня зовут Анна")
    assert text == "Меня зовут Анна"
    assert not detected


def test_empty_rejected():
    with pytest.raises(ValueError):
        classify("   ")


def test_mcp_preview_input_has_same_bounds_as_http_api():
    assert _validated_text("  Обычный запрос  ") == "Обычный запрос"
    with pytest.raises(ValueError):
        _validated_text("    ")
    with pytest.raises(ValueError):
        _validated_text("x" * 8001)


def test_cost_formula_uses_assumption_not_live_price():
    settings = Settings(input_usd_per_million=0.5, output_usd_per_million=1)
    assert estimate_cost_usd(1_000_000, 1_000_000, settings) == 1.5


def test_url_validator():
    validate_base_url("http://127.0.0.1:11434/v1")
    validate_base_url("https://api.example.com/v1")
    with pytest.raises(LLMError):
        validate_base_url("file:///etc/passwd")
    with pytest.raises(LLMError):
        validate_base_url("http://169.254.169.254/v1")
    with pytest.raises(LLMError):
        validate_base_url("https://alice:secret@example.org/v1")
    with pytest.raises(LLMError):
        validate_base_url("https://api.example.org/v1?token=surprise")
    with pytest.raises(LLMError):
        validate_base_url("https://api.example.org:99999/v1")


def test_non_finite_numeric_environment_values_fall_back(monkeypatch):
    monkeypatch.setenv("PILOT_LLM_TIMEOUT_SECONDS", "nan")
    monkeypatch.setenv("PILOT_INPUT_USD_PER_1M", "inf")
    monkeypatch.setenv("PILOT_OUTPUT_USD_PER_1M", "-5")
    settings = Settings.from_env()
    assert math.isfinite(settings.llm_timeout)
    assert math.isfinite(settings.input_usd_per_million)
    assert settings.llm_timeout == 15.0
    assert settings.input_usd_per_million == 0.25
    assert settings.output_usd_per_million == 0.0
