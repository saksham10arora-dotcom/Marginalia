from sidecar import config


def test_load_gemini_api_keys_returns_single_key_when_unnumbered_only(tmp_path, monkeypatch):
    keys_file = tmp_path / "keys.env"
    keys_file.write_text('GEMINI_API_KEY="only-one"\n')
    monkeypatch.setattr(config, "KEYS_PATH", keys_file)
    assert config.load_gemini_api_keys() == ["only-one"]


def test_load_gemini_api_keys_orders_by_numeric_suffix(tmp_path, monkeypatch):
    keys_file = tmp_path / "keys.env"
    keys_file.write_text(
        "GEMINI_API_KEY_3=third\n"
        "GEMINI_API_KEY=first\n"
        "GEMINI_API_KEY_2=second\n"
    )
    monkeypatch.setattr(config, "KEYS_PATH", keys_file)
    assert config.load_gemini_api_keys() == ["first", "second", "third"]


def test_load_gemini_api_keys_skips_commented_lines(tmp_path, monkeypatch):
    keys_file = tmp_path / "keys.env"
    keys_file.write_text(
        "# GEMINI_API_KEY_2=commented-out\n"
        "GEMINI_API_KEY=real\n"
    )
    monkeypatch.setattr(config, "KEYS_PATH", keys_file)
    assert config.load_gemini_api_keys() == ["real"]


def test_load_gemini_api_keys_returns_empty_list_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "KEYS_PATH", tmp_path / "does-not-exist.env")
    assert config.load_gemini_api_keys() == []


def test_load_gemini_api_keys_returns_empty_list_when_none_configured(tmp_path, monkeypatch):
    keys_file = tmp_path / "keys.env"
    keys_file.write_text("OTHER_KEY=x\n")
    monkeypatch.setattr(config, "KEYS_PATH", keys_file)
    assert config.load_gemini_api_keys() == []
