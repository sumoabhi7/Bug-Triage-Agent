from bta.storage.cache import MemoryCache


def test_memory_cache_expires_and_evicts_least_recently_used_entry() -> None:
    now = 0.0

    def clock() -> float:
        return now

    cache = MemoryCache[str](max_size=2, ttl_seconds=10, clock=clock)
    first = cache.key("embed", "hash-1", "model")
    second = cache.key("embed", "hash-2", "model")
    third = cache.key("embed", "hash-3", "model")

    cache.set(first, "first")
    cache.set(second, "second")
    assert cache.get(first) == "first"

    cache.set(third, "third")
    assert cache.get(second) is None
    assert cache.get(first) == "first"

    now = 11
    assert cache.get(first) is None


def test_memory_cache_keys_isolate_parameters() -> None:
    first = MemoryCache.key("search", "hash", "model", "owner/repo")
    second = MemoryCache.key("search", "hash", "model", "other/repo")

    assert first != second
