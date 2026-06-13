from context_diamond.extractors import create_shards, detect_facet
from context_diamond.model import Message


def test_final_requirement_is_a_constraint() -> None:
    assert detect_facet("Final requirement: do not overclaim the project.") == "constraints"


def test_decision_label_is_not_stripped_as_speaker() -> None:
    assert (
        detect_facet("Decision: use a diamond capsule with intent, constraints, and decisions.")
        == "decisions"
    )


def test_user_constraint_scores_above_noise_log() -> None:
    shards = create_shards(
        [
            Message(role="source", content="User: The system must keep constraints."),
            Message(role="source", content="Noise log 18: constraints were mentioned again."),
        ]
    )

    user_shard = next(shard for shard in shards if shard.text.startswith("User:"))
    noise_shard = next(shard for shard in shards if shard.text.startswith("Noise log"))
    assert user_shard.score > noise_shard.score
    assert noise_shard.facet == "noise"


def test_because_does_not_trigger_decision_keyword() -> None:
    shard = create_shards(
        [
            Message(
                role="source",
                content=(
                    "Tool: ruff initially failed because new modules had unsorted imports "
                    "and ran `python -m ruff check .`."
                ),
            )
        ]
    )[0]

    assert shard.facet == "state"
