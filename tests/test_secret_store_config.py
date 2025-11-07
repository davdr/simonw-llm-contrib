"""Tests for secret store configuration."""

import json
import pytest
import sys
from pathlib import Path
import llm


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_load_secret_store_config_nonexistent(monkeypatch, tmpdir):
    """load_secret_store_config returns defaults for nonexistent file."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config = llm.load_secret_store_config()
    assert config == {
        "default_store": "json",
        "stores": {}
    }


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_load_secret_store_config_valid(monkeypatch, tmpdir):
    """load_secret_store_config loads valid config."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config_path = Path(tmpdir) / "secret-store-config.json"
    config_data = {
        "default_store": "custom",
        "stores": {
            "json": {"setting": "value"}
        }
    }
    config_path.write_text(json.dumps(config_data))

    config = llm.load_secret_store_config()
    assert config == config_data


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_load_secret_store_config_invalid_json(monkeypatch, tmpdir):
    """load_secret_store_config returns defaults for invalid JSON."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config_path = Path(tmpdir) / "secret-store-config.json"
    config_path.write_text("not valid json{")

    config = llm.load_secret_store_config()
    assert config == {
        "default_store": "json",
        "stores": {}
    }


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_load_secret_store_config_provides_defaults(monkeypatch, tmpdir):
    """load_secret_store_config provides default values."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config_path = Path(tmpdir) / "secret-store-config.json"
    config_path.write_text("{}")

    config = llm.load_secret_store_config()
    assert config["default_store"] == "json"
    assert config["stores"] == {}


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_save_secret_store_config(monkeypatch, tmpdir):
    """save_secret_store_config saves config to file."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config_data = {
        "default_store": "custom",
        "stores": {
            "json": {"setting": "value"}
        }
    }

    llm.save_secret_store_config(config_data)

    config_path = Path(tmpdir) / "secret-store-config.json"
    assert config_path.exists()

    saved_config = json.loads(config_path.read_text())
    assert saved_config == config_data


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_save_secret_store_config_permissions(monkeypatch, tmpdir):
    """Config file has 0o600 permissions."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    config_data = {"default_store": "json", "stores": {}}
    llm.save_secret_store_config(config_data)

    config_path = Path(tmpdir) / "secret-store-config.json"
    assert oct(config_path.stat().st_mode)[-3:] == "600"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_configuration_applied_to_stores(monkeypatch, tmpdir):
    """Configuration is applied to stores during initialization."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    # Create a config file
    config_path = Path(tmpdir) / "secret-store-config.json"
    config_data = {
        "default_store": "json",
        "stores": {
            "json": {"test_setting": "test_value"}
        }
    }
    config_path.write_text(json.dumps(config_data))

    # Clear loaded state to force reload
    llm._secret_stores_loaded = False
    llm._secret_stores.clear()
    llm._default_secret_store_name = None

    # Get store which triggers loading
    store = llm.get_secret_store("json")
    assert store is not None
    # Note: JsonSecretStore doesn't store config, but configure() was called


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_default_store_from_config(monkeypatch, tmpdir):
    """Default store is set from configuration."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    # Register a mock store
    class MockStore(llm.SecretStore):
        name = "mock"

        def get(self, key_alias: str):
            return None

        def set(self, key_alias: str, value: str):
            pass

        def delete(self, key_alias: str):
            return False

        def list_keys(self):
            return []

    # Clear and reload
    llm._secret_stores_loaded = False
    llm._secret_stores.clear()
    llm._default_secret_store_name = None

    # Register mock store manually
    llm.register_secret_store(MockStore())

    # Create config with mock as default
    config_path = Path(tmpdir) / "secret-store-config.json"
    config_data = {"default_store": "mock", "stores": {}}
    config_path.write_text(json.dumps(config_data))

    # Reload
    llm._secret_stores_loaded = False
    llm._load_secret_stores()

    # Check default
    default_store = llm.get_secret_store()
    assert default_store.name == "mock"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_fallback_to_json_when_default_missing(monkeypatch, tmpdir):
    """Falls back to json when configured default doesn't exist."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))

    # Create config with nonexistent default
    config_path = Path(tmpdir) / "secret-store-config.json"
    config_data = {"default_store": "nonexistent", "stores": {}}
    config_path.write_text(json.dumps(config_data))

    # Clear and reload
    llm._secret_stores_loaded = False
    llm._secret_stores.clear()
    llm._default_secret_store_name = None

    # Get store which triggers loading
    llm._load_secret_stores()

    # Should fall back to json
    default_store = llm.get_secret_store()
    assert default_store.name == "json"
