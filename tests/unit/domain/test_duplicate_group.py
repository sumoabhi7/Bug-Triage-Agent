import pytest
from pydantic import ValidationError

from bta.domain import DuplicateGroup


def test_duplicate_group_requires_primary_issue_to_be_a_member() -> None:
    group = DuplicateGroup(
        primary_issue_number=42,
        member_issue_numbers=[7, 42],
        similarity_scores={7: 0.86, 42: 1.0},
        threshold_used=0.85,
    )

    assert group.primary_issue_number in group.member_issue_numbers


def test_duplicate_group_rejects_missing_primary_issue_member() -> None:
    with pytest.raises(ValidationError):
        DuplicateGroup(
            primary_issue_number=42,
            member_issue_numbers=[7, 8],
            similarity_scores={7: 0.86, 8: 0.9},
            threshold_used=0.85,
        )
