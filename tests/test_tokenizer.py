from context_diamond.tokenizer import estimate_tokens, split_sentences, trim_to_token_budget


def test_estimate_tokens_counts_words_paths_and_punctuation() -> None:
    assert estimate_tokens("Use src/app.py now.") >= 4


def test_split_sentences_preserves_bullets() -> None:
    text = "- First decision.\n- Second decision.\n\nWhat remains open?"
    assert split_sentences(text) == ["First decision.", "Second decision.", "What remains open?"]


def test_trim_to_token_budget_adds_ellipsis() -> None:
    clipped = trim_to_token_budget("alpha beta gamma delta epsilon", 3)
    assert clipped.endswith("...")


def test_split_sentences_skips_markdown_headings() -> None:
    text = "# Transcript\n\nUser: Keep the goal.\nAssistant: Decision: stay deterministic."
    assert split_sentences(text) == [
        "User: Keep the goal.",
        "Assistant: Decision: stay deterministic.",
    ]


def test_split_sentences_keeps_finished_lines_separate() -> None:
    text = "Goal: save tokens.\nThe system must stay deterministic."
    assert split_sentences(text) == [
        "Goal: save tokens.",
        "The system must stay deterministic.",
    ]
