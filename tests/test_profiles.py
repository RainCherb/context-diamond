import pytest

from context_diamond import estimate_profile_tokens, list_tokenizer_profiles


def test_profile_estimates_are_available() -> None:
    profiles = list_tokenizer_profiles()

    assert "generic" in profiles
    assert "openai" in profiles
    assert estimate_profile_tokens("Use src/app.py now.", "openai") >= 4


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown tokenizer profile"):
        estimate_profile_tokens("hello", "made-up")
