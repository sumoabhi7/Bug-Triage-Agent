from uuid import uuid4

import pytest

from bta.storage.artifact_store import ArtifactStore


@pytest.mark.asyncio
async def test_artifact_store_writes_immutable_content_and_metadata(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    case_id = uuid4()

    record = await store.write(
        triage_case_id=case_id,
        kind="validation",
        content="exact output\n",
    )
    repeated = await store.write(
        triage_case_id=case_id,
        kind="validation",
        content="exact output\n",
    )

    assert record.relative_path == repeated.relative_path
    assert record.byte_size == len(b"exact output\n")
    assert store.read(record.relative_path) == b"exact output\n"


def test_artifact_store_rejects_paths_outside_root(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError):
        store.read("../secret")
