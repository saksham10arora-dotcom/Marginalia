import itertools
from typing import Callable, TypeVar

T = TypeVar("T")

# Module-level so the starting key rotates across separate calls (not just
# within one call's own attempts) -- otherwise every call would hammer the
# first configured key until IT alone is exhausted, leaving the other three
# untouched instead of spreading load evenly across all four.
_rr_counter = itertools.count()


def call_with_key_rotation(fn: Callable[..., T], api_keys: list[str], *args, **kwargs) -> T:
    """Calls fn(*args, api_key=<key>, **kwargs), trying configured keys in a
    round-robin-rotated order until one succeeds.

    Each key already gets its own retry-with-backoff inside fn (gemini_client
    / finalize's own 429/503 handling) for transient rate limits. By the time
    a RuntimeError bubbles up here, that's already been exhausted for that
    key -- if it's still a 429, backing off further on the SAME key won't
    help a daily quota cap (it won't reset for hours), so this moves to the
    next key immediately instead. Any non-429 error propagates as-is; it's
    not something a different key would fix.
    """
    if not api_keys:
        raise RuntimeError("No Gemini API keys configured")

    start = next(_rr_counter) % len(api_keys)
    rotated = api_keys[start:] + api_keys[:start]

    last_error: RuntimeError | None = None
    for key in rotated:
        try:
            return fn(*args, api_key=key, **kwargs)
        except RuntimeError as e:
            if "429" not in str(e):
                raise
            last_error = e
            continue
    assert last_error is not None
    raise last_error
