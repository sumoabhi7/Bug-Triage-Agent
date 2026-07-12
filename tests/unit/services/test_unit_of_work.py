from __future__ import annotations

import pytest

from bta.services.unit_of_work import UnitOfWork


class FakeSession:
    def __init__(self) -> None:
        self.began = False
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def begin(self) -> None:
        self.began = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


def test_unit_of_work_commits_on_success() -> None:
    session = FakeSession()
    unit_of_work = UnitOfWork(lambda: session)  # type: ignore[arg-type]

    async def run() -> None:
        async with unit_of_work:
            assert unit_of_work.session is session

    import asyncio

    asyncio.run(run())

    assert session.began is True
    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_unit_of_work_rolls_back_on_failure() -> None:
    session = FakeSession()
    unit_of_work = UnitOfWork(lambda: session)  # type: ignore[arg-type]

    async def run() -> None:
        with pytest.raises(RuntimeError):
            async with unit_of_work:
                raise RuntimeError("boom")

    import asyncio

    asyncio.run(run())

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True
