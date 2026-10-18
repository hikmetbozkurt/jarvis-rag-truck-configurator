import time
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def record_stage_duration(stage_durations_ms: dict[str, float], stage_name: str) -> Iterator[None]:
    started_at = time.perf_counter()
    try:
        yield
    finally:
        stage_durations_ms[stage_name] = round((time.perf_counter() - started_at) * 1000, 2)
