from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from time import monotonic

CacheKey = tuple[Hashable, ...]


@dataclass(frozen=True, slots=True)
class _Entry[T]:
    value: T
    expires_at: float


class MemoryCache[T]:
    """Bounded process-local TTL cache with least-recently-used eviction."""

    def __init__(
        self,
        *,
        max_size: int = 256,
        ttl_seconds: float = 300,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[CacheKey, _Entry[T]] = OrderedDict()

    @staticmethod
    def key(
        operation: str,
        content_hash: str,
        model_name: str,
        *parameters: Hashable,
    ) -> CacheKey:
        return (operation, content_hash, model_name, *parameters)

    def get(self, key: CacheKey) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry.value

    def set(self, key: CacheKey, value: T) -> None:
        self._entries[key] = _Entry(value, self._clock() + self._ttl_seconds)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_size:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
