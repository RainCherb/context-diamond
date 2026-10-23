"""Deterministic, explainable offline triage and conservative PII masking."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+7|8)[\s(\-]*(?:\d[\s)\-]*){10}(?!\w)")

CATEGORIES = {
    "billing": {
        "label": "Платежи и документы",
        "patterns": ("оплат", "счет", "счёт", "возврат", "чек", "invoice", "refund", "payment"),
        "owner": "Финансы",
        "action": "Проверить транзакцию и подготовить ответ по оплате.",
    },
    "technical": {
        "label": "Техническая поддержка",
        "patterns": ("ошибк", "не работает", "сбой", "баг", "сломал", "не открывает", "error", "bug", "crash", "500"),
        "owner": "Техподдержка",
        "action": "Уточнить шаги воспроизведения и передать техническому специалисту.",
    },
    "sales": {
        "label": "Продажи",
        "patterns": ("тариф", "купить", "стоимость", "цена", "демо", "коммерческ", "pricing", "quote", "trial"),
        "owner": "Продажи",
        "action": "Уточнить потребность и предложить подходящий тариф или демонстрацию.",
    },
    "delivery": {
        "label": "Доставка и заказы",
        "patterns": ("достав", "заказ", "посылк", "курьер", "shipping", "delivery", "order"),
        "owner": "Операции",
        "action": "Проверить статус заказа и срок исполнения.",
    },
}
URGENT_TERMS = ("срочно", "немедленно", "критич", "утечк", "недоступ", "все клиенты", "urgent", "outage", "security", "взлом")
ESCALATE_TERMS = ("юрист", "суд", "персональн", "паспорт", "штраф", "договор", "lawyer", "legal", "gdpr")


@dataclass(frozen=True)
class Analysis:
    category: str
    category_label: str
    priority: str
    owner: str
    action: str
    reasons: list[str]
    handling_mode: str
    masked_text: str
    pii_detected: bool
    estimated_minutes_saved: int
    provider_used: str = "offline-rules"
    input_tokens: int = 0
    output_tokens: int = 0
    api_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def mask_contact_details(text: str) -> tuple[str, bool]:
    """Masks common email/phone patterns; NOT comprehensive anonymization."""
    masked = _EMAIL_RE.sub("[EMAIL]", text)
    masked = _PHONE_RE.sub("[PHONE]", masked)
    return masked, masked != text


def _category_signal_matches(text: str, signal: str) -> bool:
    """Use word boundaries for English keywords, stems/substrings for Russian rules."""
    if signal.isascii() and re.fullmatch(r"[a-z0-9]+", signal):
        return re.search(rf"(?<![a-z0-9_]){re.escape(signal)}(?![a-z0-9_])", text) is not None
    return signal in text


def _risk_term_matches(text: str, term: str) -> bool:
    """Match a risk term from the start of a word to avoid `несрочно`/`посуда` false positives."""
    if " " in term:
        return term in text
    if term.isascii():
        return re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", text) is not None
    return re.search(rf"(?<!\w){re.escape(term)}", text, flags=re.UNICODE) is not None


def classify(text: str) -> Analysis:
    if not text.strip():
        raise ValueError("Текст обращения не должен быть пустым")
    masked, pii = mask_contact_details(text.strip())
    lower = masked.casefold().replace("ё", "е")
    scores: dict[str, int] = {}
    reasons: list[str] = []
    for category, data in CATEGORIES.items():
        # Normalize and deduplicate patterns: e.g. "счет" and "счёт" become the
        # same token after ё→е normalization and must count only once.
        normalized_patterns = {p.casefold().replace("ё", "е") for p in data["patterns"]}
        hits = [pattern for pattern in normalized_patterns if _category_signal_matches(lower, pattern)]
        if hits:
            scores[category] = len(hits)
    key = max(scores, key=lambda k: scores[k]) if scores else "general"
    if key == "general":
        label, owner, action = ("Общее обращение", "Первая линия", "Изучить запрос и определить следующий шаг.")
        reasons.append("Не найдены выраженные признаки профильной категории")
    else:
        category = CATEGORIES[key]
        label, owner, action = category["label"], category["owner"], category["action"]
        reasons.append(f"Совпадение с тематикой «{label}» ({scores[key]} признака/ов)")

    is_urgent = any(_risk_term_matches(lower, term) for term in URGENT_TERMS)
    requires_human = any(_risk_term_matches(lower, term) for term in ESCALATE_TERMS)
    priority = "high" if is_urgent else "medium" if requires_human or key == "technical" else "low"
    if is_urgent:
        reasons.append("Обнаружен признак срочности — требуется оперативная проверка")
    if requires_human:
        reasons.append("Потенциально чувствительный запрос — решение принимает человек")
    if pii:
        reasons.append("Похожие на телефон/email данные замаскированы перед хранением")
    # Triage is advisory. Even 'auto-draft' must be reviewed by a person.
    handling = "human-review" if priority == "high" or requires_human else "draft-for-review"
    return Analysis(
        category=key,
        category_label=label,
        priority=priority,
        owner=owner,
        action=action,
        reasons=reasons,
        handling_mode=handling,
        masked_text=masked,
        pii_detected=pii,
        estimated_minutes_saved=4 if key != "general" else 2,
    )
