import itertools

import pytest

from sidecar import key_rotation
from sidecar.key_rotation import call_with_key_rotation


@pytest.fixture(autouse=True)
def reset_rotation_counter(monkeypatch):
    # _rr_counter is module-level global state that persists across the whole
    # test session so separate calls actually rotate in production -- reset
    # it here so each test starts deterministically at key index 0 regardless
    # of how many prior tests (in this file or elsewhere) already called
    # call_with_key_rotation.
    monkeypatch.setattr(key_rotation, "_rr_counter", itertools.count())


def test_call_with_key_rotation_uses_first_key_on_success():
    calls = []

    def fn(x, api_key):
        calls.append((x, api_key))
        return f"ok:{api_key}"

    result = call_with_key_rotation(fn, ["key-a", "key-b"], "arg")
    assert result == "ok:key-a"
    assert calls == [("arg", "key-a")]


def test_call_with_key_rotation_falls_through_on_429():
    calls = []

    def fn(api_key):
        calls.append(api_key)
        if api_key == "key-a":
            raise RuntimeError("Gemini API returned HTTP 429: quota exceeded")
        return f"ok:{api_key}"

    result = call_with_key_rotation(fn, ["key-a", "key-b", "key-c"])
    assert result == "ok:key-b"
    assert calls == ["key-a", "key-b"]


def test_call_with_key_rotation_raises_last_error_when_all_keys_exhausted():
    def fn(api_key):
        raise RuntimeError(f"Gemini API returned HTTP 429: quota exceeded for {api_key}")

    with pytest.raises(RuntimeError, match="key-c"):
        call_with_key_rotation(fn, ["key-a", "key-b", "key-c"])


def test_call_with_key_rotation_does_not_rotate_on_non_429_error():
    calls = []

    def fn(api_key):
        calls.append(api_key)
        raise RuntimeError("Gemini API returned HTTP 400: bad request")

    with pytest.raises(RuntimeError, match="bad request"):
        call_with_key_rotation(fn, ["key-a", "key-b"])
    assert calls == ["key-a"]  # never tried key-b -- a 400 isn't fixed by a different key


def test_call_with_key_rotation_raises_when_no_keys_configured():
    with pytest.raises(RuntimeError, match="No Gemini API keys configured"):
        call_with_key_rotation(lambda api_key: "unused", [])


def test_call_with_key_rotation_starting_key_rotates_across_separate_calls():
    def fn(api_key):
        return api_key

    keys = ["key-a", "key-b", "key-c"]
    # Call it more times than there are keys and confirm every key gets used
    # as the starting (first-tried) key at least once, not just key-a always.
    results = [call_with_key_rotation(fn, keys) for _ in range(6)]
    assert set(results) == {"key-a", "key-b", "key-c"}
