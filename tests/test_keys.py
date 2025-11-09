from click.testing import CliRunner
import json
from llm.cli import cli
import pathlib
import pytest
import sys


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
@pytest.mark.parametrize("env", ({}, {"LLM_USER_PATH": "/tmp/llm-keys-test"}))
def test_keys_in_user_path(monkeypatch, env, user_path):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "path"])
    assert result.exit_code == 0
    if env:
        expected = env["LLM_USER_PATH"] + "/keys.json"
    else:
        expected = user_path + "/keys.json"
    assert result.output.strip() == expected


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_keys_set(monkeypatch, tmpdir):
    user_path = tmpdir / "user/keys"
    monkeypatch.setenv("LLM_USER_PATH", str(user_path))
    keys_path = user_path / "keys.json"
    assert not keys_path.exists()
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "set", "openai"], input="foo")
    assert result.exit_code == 0
    assert keys_path.exists()
    # Should be chmod 600
    assert oct(keys_path.stat().mode)[-3:] == "600"
    content = keys_path.read_text("utf-8")
    assert json.loads(content) == {
        "// Note": "This file stores secret API credentials. Do not share!",
        "openai": "foo",
    }


@pytest.mark.xfail(sys.platform == "win32", reason="Expected to fail on Windows")
def test_keys_get(monkeypatch, tmpdir):
    user_path = tmpdir / "user/keys"
    monkeypatch.setenv("LLM_USER_PATH", str(user_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "set", "openai"], input="fx")
    assert result.exit_code == 0
    result2 = runner.invoke(cli, ["keys", "get", "openai"])
    assert result2.exit_code == 0
    assert result2.output.strip() == "fx"


@pytest.mark.parametrize("args", (["keys", "list"], ["keys"]))
def test_keys_list(monkeypatch, tmpdir, args):
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "set", "openai"], input="foo")
    assert result.exit_code == 0
    result2 = runner.invoke(cli, args)
    assert result2.exit_code == 0
    assert result2.output.strip() == "openai"


@pytest.mark.httpx_mock(
    assert_all_requests_were_expected=False, can_send_already_matched_responses=True
)
def test_uses_correct_key(mocked_openai_chat, monkeypatch, tmpdir):
    user_dir = tmpdir / "user-dir"
    pathlib.Path(user_dir).mkdir()
    keys_path = user_dir / "keys.json"
    KEYS = {
        "openai": "from-keys-file",
        "other": "other-key",
    }
    keys_path.write_text(json.dumps(KEYS), "utf-8")
    monkeypatch.setenv("LLM_USER_PATH", str(user_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")

    def assert_key(key):
        request = mocked_openai_chat.get_requests()[-1]
        assert request.headers["Authorization"] == "Bearer {}".format(key)

    runner = CliRunner()

    # Called without --key uses stored key
    result = runner.invoke(cli, ["hello", "--no-stream"], catch_exceptions=False)
    assert result.exit_code == 0
    assert_key("from-keys-file")

    # Called without --key and without keys.json uses environment variable
    keys_path.write_text("{}", "utf-8")
    result2 = runner.invoke(cli, ["hello", "--no-stream"], catch_exceptions=False)
    assert result2.exit_code == 0
    assert_key("from-env")
    keys_path.write_text(json.dumps(KEYS), "utf-8")

    # Called with --key name-in-keys.json uses that value
    result3 = runner.invoke(
        cli, ["hello", "--key", "other", "--no-stream"], catch_exceptions=False
    )
    assert result3.exit_code == 0
    assert_key("other-key")

    # Called with --key something-else uses exactly that
    result4 = runner.invoke(
        cli, ["hello", "--key", "custom-key", "--no-stream"], catch_exceptions=False
    )
    assert result4.exit_code == 0
    assert_key("custom-key")


def test_keys_stores_basic(monkeypatch, tmpdir):
    """Test that llm keys stores lists available stores"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores"])
    assert result.exit_code == 0
    assert "json (default)" in result.output


def test_keys_stores_verbose(monkeypatch, tmpdir):
    """Test that llm keys stores --verbose shows key counts"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # First check with no keys
    result = runner.invoke(cli, ["keys", "stores", "--verbose"])
    assert result.exit_code == 0
    assert "json (default)" in result.output
    assert "Keys stored: 0" in result.output

    # Add a key and check again
    runner.invoke(cli, ["keys", "set", "test"], input="value")
    result = runner.invoke(cli, ["keys", "stores", "--verbose"])
    assert result.exit_code == 0
    assert "json (default)" in result.output
    assert "Keys stored: 1" in result.output


def test_keys_stores_ordering(monkeypatch, tmpdir):
    """Test that stores are listed in alphabetical order"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores"])
    assert result.exit_code == 0
    # With only json store, should see json (default)
    lines = result.output.strip().split("\n")
    assert lines[0] == "json (default)"


def test_keys_stores_default_show(monkeypatch, tmpdir):
    """Test showing the default store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores", "default"])
    assert result.exit_code == 0
    assert result.output.strip() == "json"


def test_keys_stores_default_set(monkeypatch, tmpdir):
    """Test setting the default store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores", "default", "json"])
    assert result.exit_code == 0
    assert "Default store set to 'json'" in result.output

    # Verify it persists
    result2 = runner.invoke(cli, ["keys", "stores", "default"])
    assert result2.exit_code == 0
    assert result2.output.strip() == "json"


def test_keys_stores_default_set_invalid(monkeypatch, tmpdir):
    """Test error when setting invalid store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores", "default", "invalid"])
    assert result.exit_code != 0
    assert "Store 'invalid' not found" in result.output
    assert "Available stores: json" in result.output


def test_keys_stores_options_list_empty(monkeypatch, tmpdir):
    """Test listing options when none configured"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores", "options"])
    assert result.exit_code == 0
    assert "No store options configured" in result.output


def test_keys_stores_options_set_and_list(monkeypatch, tmpdir):
    """Test setting and listing options"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set an option
    result = runner.invoke(
        cli, ["keys", "stores", "options", "set", "json", "key1", "value1"]
    )
    assert result.exit_code == 0
    assert "Set key1=value1 for store 'json'" in result.output

    # List options
    result2 = runner.invoke(cli, ["keys", "stores", "options"])
    assert result2.exit_code == 0
    assert "json:" in result2.output
    assert "key1: value1" in result2.output


def test_keys_stores_options_show(monkeypatch, tmpdir):
    """Test showing options for a specific store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set some options
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key1", "value1"])
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key2", "value2"])

    # Show options for json store
    result = runner.invoke(cli, ["keys", "stores", "options", "show", "json"])
    assert result.exit_code == 0
    assert "key1: value1" in result.output
    assert "key2: value2" in result.output


def test_keys_stores_options_show_empty(monkeypatch, tmpdir):
    """Test showing options when none configured for store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["keys", "stores", "options", "show", "json"])
    assert result.exit_code == 0
    assert "No options configured for store 'json'" in result.output


def test_keys_stores_options_set_invalid_store(monkeypatch, tmpdir):
    """Test error when setting option for invalid store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["keys", "stores", "options", "set", "invalid", "key", "value"]
    )
    assert result.exit_code != 0
    assert "Store 'invalid' not found" in result.output


def test_keys_stores_options_clear_all(monkeypatch, tmpdir):
    """Test clearing all options for a store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set some options
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key1", "value1"])
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key2", "value2"])

    # Clear all options
    result = runner.invoke(cli, ["keys", "stores", "options", "clear", "json"])
    assert result.exit_code == 0
    assert "Cleared all options for store 'json'" in result.output

    # Verify they're gone
    result2 = runner.invoke(cli, ["keys", "stores", "options"])
    assert result2.exit_code == 0
    assert "No store options configured" in result2.output


def test_keys_stores_options_clear_key(monkeypatch, tmpdir):
    """Test clearing a specific option"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set some options
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key1", "value1"])
    runner.invoke(cli, ["keys", "stores", "options", "set", "json", "key2", "value2"])

    # Clear one key
    result = runner.invoke(
        cli, ["keys", "stores", "options", "clear", "json", "--key", "key1"]
    )
    assert result.exit_code == 0
    assert "Cleared key1 for store 'json'" in result.output

    # Verify key1 is gone but key2 remains
    result2 = runner.invoke(cli, ["keys", "stores", "options", "show", "json"])
    assert result2.exit_code == 0
    assert "key1" not in result2.output
    assert "key2: value2" in result2.output


def test_keys_stores_backward_compatibility(monkeypatch, tmpdir):
    """Test that llm keys stores still works as before"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Test basic command
    result = runner.invoke(cli, ["keys", "stores"])
    assert result.exit_code == 0
    assert "json (default)" in result.output

    # Test with --verbose
    result2 = runner.invoke(cli, ["keys", "stores", "--verbose"])
    assert result2.exit_code == 0
    assert "json (default)" in result2.output
    assert "Keys stored:" in result2.output

    # Test explicit list
    result3 = runner.invoke(cli, ["keys", "stores", "list"])
    assert result3.exit_code == 0
    assert "json (default)" in result3.output


def test_keys_delete_basic(monkeypatch, tmpdir):
    """Test deleting a key from default store with --yes flag"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set a key first
    runner.invoke(cli, ["keys", "set", "test-key"], input="test-value")

    # Verify it exists
    result = runner.invoke(cli, ["keys", "get", "test-key"])
    assert result.exit_code == 0
    assert "test-value" in result.output

    # Delete it with --yes flag
    result = runner.invoke(cli, ["keys", "delete", "test-key", "--yes"])
    assert result.exit_code == 0
    assert "deleted from store 'json'" in result.output

    # Verify it's gone
    result = runner.invoke(cli, ["keys", "get", "test-key"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_keys_delete_with_store(monkeypatch, tmpdir):
    """Test deleting a key from specific store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set a key
    runner.invoke(
        cli, ["keys", "set", "test-key", "--store", "json"], input="test-value"
    )

    # Delete from specific store
    result = runner.invoke(
        cli, ["keys", "delete", "test-key", "--store", "json", "--yes"]
    )
    assert result.exit_code == 0
    assert "deleted from store 'json'" in result.output


def test_keys_delete_nonexistent(monkeypatch, tmpdir):
    """Test error when deleting non-existent key"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["keys", "delete", "nonexistent", "--yes"])
    assert result.exit_code != 0
    assert "not found in store" in result.output


def test_keys_delete_invalid_store(monkeypatch, tmpdir):
    """Test error when specifying invalid store"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    result = runner.invoke(
        cli, ["keys", "delete", "somekey", "--store", "invalid", "--yes"]
    )
    assert result.exit_code != 0
    assert "not found" in result.output
    assert "Available stores" in result.output


def test_keys_delete_verify_removed(monkeypatch, tmpdir):
    """Test that key is actually removed from storage"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set a key
    runner.invoke(cli, ["keys", "set", "test-key"], input="test-value")

    # Delete it
    runner.invoke(cli, ["keys", "delete", "test-key", "--yes"])

    # Verify it doesn't appear in list
    result = runner.invoke(cli, ["keys", "list"])
    assert result.exit_code == 0
    assert "test-key" not in result.output


def test_keys_delete_other_keys_remain(monkeypatch, tmpdir):
    """Test that deleting one key doesn't affect others"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set multiple keys
    runner.invoke(cli, ["keys", "set", "key1"], input="value1")
    runner.invoke(cli, ["keys", "set", "key2"], input="value2")
    runner.invoke(cli, ["keys", "set", "key3"], input="value3")

    # Delete one key
    runner.invoke(cli, ["keys", "delete", "key2", "--yes"])

    # Verify the other keys still exist
    result = runner.invoke(cli, ["keys", "list"])
    assert result.exit_code == 0
    assert "key1" in result.output
    assert "key2" not in result.output
    assert "key3" in result.output


def test_keys_delete_confirmation_cancelled(monkeypatch, tmpdir):
    """Test that deletion is cancelled when user says no"""
    user_path = str(tmpdir / "user/keys")
    monkeypatch.setenv("LLM_USER_PATH", user_path)
    runner = CliRunner()

    # Set a key
    runner.invoke(cli, ["keys", "set", "test-key"], input="test-value")

    # Try to delete without --yes, answer 'n' to confirmation
    result = runner.invoke(cli, ["keys", "delete", "test-key"], input="n\n")
    assert result.exit_code == 0
    assert "Cancelled" in result.output

    # Verify key still exists
    result = runner.invoke(cli, ["keys", "get", "test-key"])
    assert result.exit_code == 0
    assert "test-value" in result.output
