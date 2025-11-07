"""Tests for the JsonSecretStore implementation."""

import json
import pytest
import sys
from pathlib import Path
from llm.default_plugins.json_secret_store import JsonSecretStore


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_create_json_secret_store(tmpdir):
    """JsonSecretStore can be instantiated."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)
    assert store.name == "json"
    assert store.keys_path == keys_path


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_uses_default_path(monkeypatch, tmpdir):
    """JsonSecretStore uses default path if none provided."""
    monkeypatch.setenv("LLM_USER_PATH", str(tmpdir))
    store = JsonSecretStore()
    assert store.keys_path == Path(tmpdir) / "keys.json"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_set_and_get(tmpdir):
    """Can set and get keys from JSON store."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("test_key", "test_value")

    assert store.get("test_key") == "test_value"
    assert store.get("nonexistent") is None


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_file_permissions(tmpdir):
    """Keys file has 0o600 permissions."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("test_key", "test_value")

    # Check permissions
    assert oct(keys_path.stat().st_mode)[-3:] == "600"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_file_format(tmpdir):
    """Keys file has correct format with comment."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("test_key", "test_value")

    # Check file contents
    content = json.loads(keys_path.read_text())
    assert "// Note" in content
    assert content["test_key"] == "test_value"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_nonexistent_file(tmpdir):
    """Can handle nonexistent file."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    assert store.get("anything") is None
    assert store.list_keys() == []


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_corrupted_file(tmpdir):
    """Can handle corrupted JSON file."""
    keys_path = Path(tmpdir) / "keys.json"
    keys_path.write_text("not valid json{}")

    store = JsonSecretStore(keys_path)
    assert store.get("anything") is None
    assert store.list_keys() == []


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_atomic_write(tmpdir):
    """Uses atomic write with temp file."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("key1", "value1")
    store.set("key2", "value2")

    # Check that temp file doesn't exist after write
    temp_path = keys_path.with_suffix('.tmp')
    assert not temp_path.exists()

    # Check final file is valid
    content = json.loads(keys_path.read_text())
    assert content["key1"] == "value1"
    assert content["key2"] == "value2"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_comment_preservation(tmpdir):
    """Comment entry is preserved across operations."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("key1", "value1")
    store.set("key2", "value2")

    content = json.loads(keys_path.read_text())
    assert "// Note" in content
    assert content["// Note"] == "This file stores secret API credentials. Do not share!"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_delete(tmpdir):
    """Can delete keys."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("key1", "value1")
    store.set("key2", "value2")

    # Delete existing key
    assert store.delete("key1") is True
    assert store.get("key1") is None
    assert store.get("key2") == "value2"

    # Delete nonexistent key
    assert store.delete("nonexistent") is False


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_list_keys(tmpdir):
    """Can list all keys."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    # Empty store
    assert store.list_keys() == []

    # Add keys
    store.set("key1", "value1")
    store.set("key2", "value2")
    store.set("key3", "value3")

    keys = store.list_keys()
    assert len(keys) == 3
    assert "key1" in keys
    assert "key2" in keys
    assert "key3" in keys


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_multiple_operations(tmpdir):
    """Can perform multiple operations in sequence."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    # Set
    store.set("key1", "value1")
    assert store.get("key1") == "value1"

    # Update
    store.set("key1", "updated_value")
    assert store.get("key1") == "updated_value"

    # Add another
    store.set("key2", "value2")
    assert len(store.list_keys()) == 2

    # Delete
    store.delete("key1")
    assert store.get("key1") is None
    assert len(store.list_keys()) == 1

    # Final state
    assert store.get("key2") == "value2"


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_json_secret_store_filters_comment_from_list(tmpdir):
    """list_keys() doesn't include // Note comment."""
    keys_path = Path(tmpdir) / "keys.json"
    store = JsonSecretStore(keys_path)

    store.set("key1", "value1")

    keys = store.list_keys()
    assert "// Note" not in keys
    assert "key1" in keys


# Tests for plugin registration


def test_json_secret_store_registered_as_plugin():
    """JSON secret store is automatically registered on startup."""
    import llm

    store = llm.get_secret_store('json')
    assert store is not None
    assert store.name == "json"
    assert isinstance(store, JsonSecretStore)


def test_json_secret_store_is_default():
    """JSON secret store is set as default."""
    import llm

    # Get default store
    default_store = llm.get_secret_store()
    assert default_store is not None
    assert default_store.name == "json"
