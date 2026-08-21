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


# --- MARGIN_* settings, with a fallback to the pre-rename MARGINALIA_* names ---

def test_setting_prefers_the_current_margin_prefix(monkeypatch):
    monkeypatch.setenv("MARGIN_ENGINE", "groq")
    monkeypatch.setenv("MARGINALIA_ENGINE", "gemini")
    assert config._setting("ENGINE", "haiku") == "groq"


def test_setting_falls_back_to_the_legacy_prefix(monkeypatch):
    # Someone whose shell profile still exports the old name must not silently
    # get the default instead -- that is how a vault quietly reads as empty.
    monkeypatch.delenv("MARGIN_ENGINE", raising=False)
    monkeypatch.setenv("MARGINALIA_ENGINE", "gemini")
    assert config._setting("ENGINE", "haiku") == "gemini"


def test_setting_returns_the_default_when_neither_is_set(monkeypatch):
    monkeypatch.delenv("MARGIN_ENGINE", raising=False)
    monkeypatch.delenv("MARGINALIA_ENGINE", raising=False)
    assert config._setting("ENGINE", "haiku") == "haiku"


def test_setting_honours_an_explicit_empty_value(monkeypatch):
    # An explicitly empty override is a choice, not "unset".
    monkeypatch.setenv("MARGIN_ENGINE", "")
    assert config._setting("ENGINE", "haiku") == ""


def test_default_vault_prefers_the_new_folder(monkeypatch, tmp_path):
    home = tmp_path
    (home / "MarginNotes").mkdir()
    monkeypatch.setattr(config.Path, "home", staticmethod(lambda: home))
    assert config._default_vault_path() == home / "MarginNotes"


def test_default_vault_keeps_using_a_populated_legacy_folder(monkeypatch, tmp_path):
    # Silently switching to an empty new folder would look exactly like the
    # user's notes had vanished.
    home = tmp_path
    legacy = home / "MarginaliaNotes"
    legacy.mkdir()
    (legacy / "lec1.md").write_text("real notes")
    monkeypatch.setattr(config.Path, "home", staticmethod(lambda: home))
    assert config._default_vault_path() == legacy


def test_default_vault_ignores_an_empty_legacy_folder(monkeypatch, tmp_path):
    home = tmp_path
    (home / "MarginaliaNotes").mkdir()  # exists but holds no notes
    monkeypatch.setattr(config.Path, "home", staticmethod(lambda: home))
    assert config._default_vault_path() == home / "MarginNotes"
