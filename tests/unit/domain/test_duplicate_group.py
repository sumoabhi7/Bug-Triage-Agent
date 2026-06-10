from uuid import uuid4

import pytest
from pydantic import ValidationError

from bta.domain import DuplicateGroup


def test_duplicate_group_requires_primary_case_to_be_a_member() -> None:
    primary_id = uuid4()
    member_id = uuid4()

    group = DuplicateGroup(
        primary_case_id=primary_id,
        member_case_ids=[member_id, primary_id],
        similarity_scores={
            str(member_id): 0.86,
            str(primary_id): 1.0,
        },
        threshold_used=0.85,
    )

    assert group.primary_case_id in group.member_case_ids


def test_duplicate_group_rejects_missing_primary_case_member() -> None:
    primary_id = uuid4()

    with pytest.raises(ValidationError):
        DuplicateGroup(
            primary_case_id=primary_id,
            member_case_ids=[uuid4(), uuid4()],
            similarity_scores={},
            threshold_used=0.85,
        )