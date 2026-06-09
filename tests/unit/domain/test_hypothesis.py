import pytest
from pydantic import ValidationError

from bta.domain import RootCauseHypothesis


def test_root_cause_hypothesis_is_ranked_and_grounded() -> None:
    hypothesis = RootCauseHypothesis(
        rank=1,
        hypothesis="Missing key handling raises KeyError instead of using a default.",
        category="config-error",
        confidence=0.91,
        evidence_references=["file:app.py:10-14", "trace:0"],
        affected_files=["app.py"],
        affected_lines=[("app.py", 10, 14)],
        model_used="qwen2.5-coder:7b",
    )

    assert hypothesis.rank == 1
    assert hypothesis.confidence == 0.91
    assert hypothesis.affected_lines == [("app.py", 10, 14)]


def test_root_cause_hypothesis_rejects_invalid_scores_and_lines() -> None:
    with pytest.raises(ValidationError):
        RootCauseHypothesis(
            rank=0,
            hypothesis="bad",
            category="config-error",
            confidence=0.5,
            model_used="qwen2.5-coder:7b",
        )

    with pytest.raises(ValidationError):
        RootCauseHypothesis(
            rank=1,
            hypothesis="bad",
            category="config-error",
            confidence=-0.1,
            model_used="qwen2.5-coder:7b",
        )

    with pytest.raises(ValidationError):
        RootCauseHypothesis(
            rank=1,
            hypothesis="bad",
            category="config-error",
            confidence=0.5,
            affected_lines=[("app.py", 20, 10)],
            model_used="qwen2.5-coder:7b",
        )
