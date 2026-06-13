"""Tests for the template engine."""

from __future__ import annotations

import pytest

from context_diamond.templates import (
    CODING,
    DEFAULT,
    INCIDENT,
    RESEARCH,
    SUPPORT,
    CapsuleTemplate,
    get_template,
    list_templates,
    register_template,
)


def test_list_templates() -> None:
    names = list_templates()
    assert "default" in names
    assert "coding" in names
    assert "support" in names
    assert "research" in names
    assert "incident" in names


def test_get_template_default() -> None:
    template = get_template("default")
    assert template.name == "default"
    assert template.description == "General-purpose balanced template."


def test_get_template_unknown() -> None:
    with pytest.raises(ValueError, match="unknown template"):
        get_template("nonexistent")


def test_default_template_weights() -> None:
    assert DEFAULT.facet_weights["constraints"] == 0.16
    assert DEFAULT.facet_weights["decisions"] == 0.16


def test_coding_template_prioritizes_state() -> None:
    assert CODING.facet_weights["state"] > DEFAULT.facet_weights["state"]


def test_support_template_prioritizes_constraints() -> None:
    assert SUPPORT.facet_weights["constraints"] > DEFAULT.facet_weights["constraints"]


def test_research_template_prioritizes_facts() -> None:
    assert RESEARCH.facet_weights["facts"] > DEFAULT.facet_weights["facts"]


def test_incident_template_prioritizes_state() -> None:
    assert INCIDENT.facet_weights["state"] > DEFAULT.facet_weights["state"]


def test_template_to_config_kwargs() -> None:
    kwargs = CODING.to_config_kwargs(token_budget=500)
    assert kwargs["token_budget"] == 500
    assert kwargs["title"] == "Coding Context Capsule"
    assert kwargs["max_items_per_facet"] == 8


def test_register_template() -> None:
    custom = CapsuleTemplate(name="custom", description="My custom template.")
    register_template("custom", custom)
    assert get_template("custom") == custom
