from context_diamond.tokenizer import estimate_tokens, split_sentences, trim_to_token_budget


def test_estimate_tokens_counts_words_paths_and_punctuation() -> None:
    assert estimate_tokens("Use src/app.py now.") >= 4


def test_split_sentences_preserves_bullets() -> None:
    text = "- First decision.\n- Second decision.\n\nWhat remains open?"
    assert split_sentences(text) == ["First decision.", "Second decision.", "What remains open?"]


def test_trim_to_token_budget_adds_ellipsis() -> None:
    clipped = trim_to_token_budget("alpha beta gamma delta epsilon", 3)
    assert clipped.endswith("...")
