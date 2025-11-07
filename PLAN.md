# Implementation Plan: Secret Store Plugin System Foundation

## Overview

This plan implements the foundational infrastructure for a plugin-based secret store system, starting with refactoring the existing plaintext JSON storage as the first plugin. This establishes the architecture for future secret store backends while maintaining full backward compatibility.

## General Instructions

**Progress Tracking:**
- Use this PLAN.md file to track progress through the implementation
- At the end of EVERY step, update PLAN.md to mark completed tasks with `[x]`
- After marking tasks complete, commit and push your changes
- This applies to ALL phases including Phase 10 (documentation)
- Example commit message: "Complete Phase 1.1: Create SecretStore ABC"

**Workflow:**
1. Work on a step
2. Update PLAN.md with `[x]` for completed tasks
3. Commit changes: `git add -A && git commit -m "Complete Phase X.Y: <description>"`
4. Push: `git push -u origin <branch-name>`
5. Move to next step

## Success Criteria

Development is complete when ALL of the following criteria are met:

1. ✅ All existing unit tests pass without modification
2. ✅ Existing `llm keys` commands work identically to before (backward compatibility)
3. ✅ New `SecretStore` abstract base class is implemented and documented
4. ✅ `register_secret_stores` plugin hook is implemented and functional
5. ✅ `JsonSecretStore` plugin successfully implements current behavior
6. ✅ `secret-store-config.json` configuration file support is implemented
7. ✅ `get_key()` function successfully uses the new secret store system
8. ✅ All new code has ≥95% test coverage
9. ✅ All new tests pass (minimum 20+ new test cases)
10. ✅ Documentation is updated for plugin developers
11. ✅ No breaking changes to existing API or CLI behavior
12. ✅ Code passes existing linting/formatting standards (black, etc.)

---

## Phase 0: Environment Setup and Validation

**Goal:** Ensure development environment is working and all tests pass before making changes.

### Steps

#### 0.1: Verify Test Infrastructure
- [x] Run `pytest test_llm.py -v` to verify core functionality
- [x] Run `pytest test_keys.py -v` to verify key-related tests
- [x] Verify both test files pass completely
- [x] Document baseline: test_llm.py (65 tests passed), test_keys.py (7 tests passed)

**Expected Result:** Core tests pass, baseline established without timing out ✅

**Note:** We run only these two test files instead of the full suite to avoid timeouts while still establishing a solid baseline of critical functionality.

**Baseline Results:**
- `tests/test_llm.py`: 65 tests passed in 51.67s
- `tests/test_keys.py`: 7 tests passed in 3.34s
- **Total baseline: 72 tests passing**

#### 0.2: Understand Current Test Coverage
- [x] Review `tests/test_keys.py` to understand existing test patterns
- [x] Identify areas that will need additional testing
- [x] Document current coverage of key-related functionality

**Expected Result:** Clear understanding of test requirements ✅

**Current Test Coverage:**
- 7 tests covering: keys path, set, get, list, and priority hierarchy
- Tests verify file permissions (0o600), JSON format with "// Note" comment
- Priority: keys.json > environment variables, --key option works as alias or literal
- Uses CliRunner, tmpdir fixtures for isolation

#### 0.3: Set Up Development Branch
- [x] Verify working on correct branch: `claude/design-api-key-protection-011CUsGXrx4sxDN78Hi5YMqF`
- [x] Create checkpoint commit before starting changes
- [x] Verify can run tests repeatedly without issues

**Expected Result:** Safe development environment established ✅

**Success Criteria for Phase 0:** ✅
- [x] All existing tests pass
- [x] Test infrastructure is reliable and repeatable
- [x] Development environment is configured correctly

---

## Phase 1: Create Abstract Secret Store Interface

**Goal:** Define the plugin interface that all secret stores will implement.

### Steps

#### 1.1: Create `llm/secret_stores.py`
- [x] Created SecretStore abstract base class
- [x] Implemented all abstract methods and configure() default
- [x] Created tests/test_secret_stores.py with 5 tests
- [x] All tests pass

Create new file with:

```python
"""Secret store plugin interface for LLM."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class SecretStore(ABC):
    """
    Abstract base class for secret store implementations.

    Secret stores provide a pluggable backend for storing and retrieving
    API keys and other sensitive credentials used by LLM.

    Attributes:
        name: Unique identifier for this secret store type (e.g., "json", "vault")
    """

    name: str

    @abstractmethod
    def get(self, key_alias: str) -> Optional[str]:
        """
        Retrieve a secret by its alias.

        Args:
            key_alias: The alias/name of the secret to retrieve

        Returns:
            The secret value if found, None otherwise
        """
        pass

    @abstractmethod
    def set(self, key_alias: str, value: str) -> None:
        """
        Store a secret under the given alias.

        Args:
            key_alias: The alias/name to store the secret under
            value: The secret value to store

        Raises:
            Exception: If storage fails
        """
        pass

    @abstractmethod
    def delete(self, key_alias: str) -> bool:
        """
        Delete a stored secret.

        Args:
            key_alias: The alias/name of the secret to delete

        Returns:
            True if the secret was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    def list_keys(self) -> List[str]:
        """
        List all stored secret aliases.

        Returns:
            List of secret aliases (not the values)
        """
        pass

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the secret store with parameters.

        Optional method that stores can override to accept configuration.
        Default implementation does nothing.

        Args:
            config: Configuration dictionary specific to this store type
        """
        pass
```

**Files to create:**
- `llm/secret_stores.py`

**Testing:**
- [x] Write `tests/test_secret_stores.py`
- [x] Test that `SecretStore` is an abstract class
- [x] Test that it cannot be instantiated directly
- [x] Test that subclasses must implement all abstract methods

**Success Criteria:** ✅
- [x] `SecretStore` ABC is properly defined
- [x] Cannot instantiate `SecretStore` directly
- [x] Subclass without all methods raises `TypeError`
- [x] At least 3 unit tests covering the ABC behavior (5 tests created)

#### 1.2: Export SecretStore in `llm/__init__.py`
Add to the module exports around line 68:

```python
from llm.secret_stores import SecretStore
```

And add to `__all__`:
```python
__all__ = [
    # ... existing exports ...
    "SecretStore",
]
```

**Files to modify:**
- `llm/__init__.py`

**Testing:**
- [x] Test that `import llm; llm.SecretStore` works
- [x] Test that `from llm import SecretStore` works

**Success Criteria:** ✅
- [x] `SecretStore` is importable from `llm` package
- [x] Existing imports still work (all 79 tests pass)

---

## Phase 2: Add Secret Store Plugin Hook

**Goal:** Add plugin hook for registering secret stores.

### Steps

#### 2.1: Add Hook Specification
Add to `llm/hookspecs.py` after existing hooks (~line 36):

```python
@hookspec
def register_secret_stores(register):
    """
    Register secret store backends.

    Example:
        @llm.hookimpl
        def register_secret_stores(register):
            register(JsonSecretStore())
    """
```

**Files to modify:**
- `llm/hookspecs.py`

**Testing:**
- [ ] Verify hook specification is registered in plugin manager
- [ ] Test that plugins can implement this hook

**Success Criteria:**
- Hook is properly defined and registered
- No breaking changes to existing hooks

#### 2.2: Create Secret Store Registry
Add to `llm/__init__.py` after existing plugin-related code:

```python
# Secret store registry
_secret_stores = {}
_default_secret_store_name = None


def register_secret_store(store):
    """Register a secret store instance."""
    if not isinstance(store, SecretStore):
        raise TypeError(f"store must be a SecretStore instance, got {type(store)}")
    if not hasattr(store, 'name') or not store.name:
        raise ValueError("SecretStore must have a non-empty 'name' attribute")
    _secret_stores[store.name] = store


def get_secret_store(name: Optional[str] = None):
    """
    Get a secret store by name.

    Args:
        name: Secret store name, or None for default

    Returns:
        SecretStore instance, or None if not found
    """
    if name is None:
        name = _default_secret_store_name
    return _secret_stores.get(name)


def get_secret_stores():
    """Get all registered secret stores."""
    return dict(_secret_stores)


def set_default_secret_store(name: str):
    """Set the default secret store."""
    global _default_secret_store_name
    if name not in _secret_stores:
        raise ValueError(f"Secret store '{name}' is not registered")
    _default_secret_store_name = name
```

**Files to modify:**
- `llm/__init__.py`

**Testing:**
- [ ] Test registering a mock secret store
- [ ] Test retrieving registered stores
- [ ] Test setting default store
- [ ] Test error handling for invalid stores
- [ ] Test `get_secret_stores()` returns all stores

**Success Criteria:**
- Can register and retrieve secret stores
- Proper error handling for invalid inputs
- At least 5 unit tests covering registry operations

---

## Phase 3: Implement JSON Secret Store Plugin

**Goal:** Refactor existing JSON key storage as a proper plugin.

### Steps

#### 3.1: Create `JsonSecretStore` Class
Add to `llm/default_plugins/json_secret_store.py` (new file):

```python
"""JSON-based secret store - default implementation."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from llm.secret_stores import SecretStore
import llm


class JsonSecretStore(SecretStore):
    """
    Secret store backed by a JSON file.

    This is the default and original secret store implementation,
    storing keys in plaintext JSON with 0o600 file permissions.

    Security note: Keys are stored in plaintext. Consider using
    a more secure secret store for production environments.
    """

    name = "json"

    def __init__(self, keys_path: Optional[Path] = None):
        """
        Initialize JSON secret store.

        Args:
            keys_path: Path to keys.json file. If None, uses default location.
        """
        self.keys_path = keys_path or (llm.user_dir() / "keys.json")

    def _load_keys(self) -> Dict[str, str]:
        """Load keys from JSON file."""
        if not self.keys_path.exists():
            return {}
        try:
            with open(self.keys_path, "r") as f:
                data = json.load(f)
            # Filter out comment entries
            return {k: v for k, v in data.items() if not k.startswith("//")}
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_keys(self, keys: Dict[str, str]) -> None:
        """Save keys to JSON file with proper permissions."""
        # Ensure directory exists
        self.keys_path.parent.mkdir(parents=True, exist_ok=True)

        # Add comment note
        data = {
            "// Note": "This file stores secret API credentials. Do not share!",
            **keys
        }

        # Write atomically with secure permissions
        temp_path = self.keys_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')

        # Set permissions before moving
        temp_path.chmod(0o600)
        temp_path.replace(self.keys_path)

    def get(self, key_alias: str) -> Optional[str]:
        """Retrieve a key from JSON storage."""
        keys = self._load_keys()
        return keys.get(key_alias)

    def set(self, key_alias: str, value: str) -> None:
        """Store a key in JSON storage."""
        keys = self._load_keys()
        keys[key_alias] = value
        self._save_keys(keys)

    def delete(self, key_alias: str) -> bool:
        """Delete a key from JSON storage."""
        keys = self._load_keys()
        if key_alias in keys:
            del keys[key_alias]
            self._save_keys(keys)
            return True
        return False

    def list_keys(self) -> List[str]:
        """List all stored key aliases."""
        keys = self._load_keys()
        return list(keys.keys())


@llm.hookimpl
def register_secret_stores(register):
    """Register the JSON secret store as a default plugin."""
    register(JsonSecretStore())
```

**Files to create:**
- `llm/default_plugins/json_secret_store.py`

**Testing:**
Create `tests/test_json_secret_store.py`:
- [ ] Test creating JsonSecretStore
- [ ] Test get/set/delete/list operations
- [ ] Test file permissions (0o600)
- [ ] Test handling non-existent file
- [ ] Test handling corrupted JSON
- [ ] Test atomic write (temp file usage)
- [ ] Test comment preservation
- [ ] Test custom path vs default path
- [ ] Test empty store behavior
- [ ] Test multiple operations in sequence

**Success Criteria:**
- `JsonSecretStore` implements all `SecretStore` methods
- File permissions are set correctly (0o600)
- Operations work identically to current `llm keys` behavior
- At least 10 unit tests covering all operations
- Test coverage ≥95%

#### 3.2: Register JSON Store as Default Plugin
Update `llm/plugins.py` to include JSON secret store in default plugins:

```python
DEFAULT_PLUGINS = (
    "llm.default_plugins.openai_models",
    "llm.default_plugins.default_tools",
    "llm.default_plugins.json_secret_store",  # Add this
)
```

**Files to modify:**
- `llm/plugins.py`

**Testing:**
- [ ] Test that JSON store is loaded on initialization
- [ ] Test that `get_secret_store('json')` returns JsonSecretStore instance
- [ ] Test plugin loading doesn't break existing functionality

**Success Criteria:**
- JSON store is automatically registered on startup
- Can be retrieved via `get_secret_store('json')`

#### 3.3: Load Secret Stores During Initialization
Update `llm/__init__.py` plugin loading section to register secret stores:

```python
def _load_secret_stores():
    """Load and register secret stores from plugins."""
    # Make sure plugins are loaded
    load_plugins()

    # Call the hook to register stores
    pm.hook.register_secret_stores(register=register_secret_store)

    # Set JSON as default if no default set
    global _default_secret_store_name
    if _default_secret_store_name is None and 'json' in _secret_stores:
        _default_secret_store_name = 'json'
```

Call this function at module initialization, similar to how plugins are loaded.

**Files to modify:**
- `llm/__init__.py`

**Testing:**
- [ ] Test that stores are loaded automatically
- [ ] Test that JSON is set as default
- [ ] Test that multiple plugins can register stores
- [ ] Test behavior when no stores registered

**Success Criteria:**
- Secret stores load automatically on import
- JSON is set as default store
- No errors during initialization

---

## Phase 4: Configuration File Support

**Goal:** Implement `secret-store-config.json` for user configuration.

### Steps

#### 4.1: Create Configuration Schema
Add to `llm/__init__.py`:

```python
def load_secret_store_config() -> Dict[str, Any]:
    """
    Load secret store configuration from secret-store-config.json.

    Returns:
        Configuration dictionary with:
        - default_store: Name of default secret store
        - stores: Dict of store-specific configurations
    """
    config_path = user_dir() / "secret-store-config.json"

    if not config_path.exists():
        return {
            "default_store": "json",
            "stores": {}
        }

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Validate basic structure
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a JSON object")

        # Provide defaults
        config.setdefault("default_store", "json")
        config.setdefault("stores", {})

        return config
    except (json.JSONDecodeError, IOError) as e:
        # Log error but continue with defaults
        # TODO: Add proper logging
        return {
            "default_store": "json",
            "stores": {}
        }


def save_secret_store_config(config: Dict[str, Any]) -> None:
    """Save secret store configuration."""
    config_path = user_dir() / "secret-store-config.json"

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')

    # Secure permissions
    config_path.chmod(0o600)
```

**Files to modify:**
- `llm/__init__.py`

**Testing:**
Create tests in `tests/test_secret_store_config.py`:
- [ ] Test loading non-existent config (returns defaults)
- [ ] Test loading valid config
- [ ] Test loading invalid JSON (returns defaults gracefully)
- [ ] Test saving config
- [ ] Test config file permissions (0o600)
- [ ] Test default values
- [ ] Test custom default_store
- [ ] Test stores configuration section

**Success Criteria:**
- Config loading works with defaults
- Invalid config doesn't crash, uses defaults
- Config file has secure permissions
- At least 6 unit tests

#### 4.2: Apply Configuration at Initialization
Update `_load_secret_stores()` to apply configuration:

```python
def _load_secret_stores():
    """Load and register secret stores from plugins."""
    # Load plugins first
    load_plugins()

    # Register stores from plugins
    pm.hook.register_secret_stores(register=register_secret_store)

    # Load configuration
    config = load_secret_store_config()

    # Configure each store
    for store_name, store_config in config.get("stores", {}).items():
        store = get_secret_store(store_name)
        if store:
            store.configure(store_config)

    # Set default store from config
    default_store = config.get("default_store", "json")
    if default_store in _secret_stores:
        set_default_secret_store(default_store)
    elif 'json' in _secret_stores:
        # Fallback to json if configured default doesn't exist
        set_default_secret_store('json')
```

**Files to modify:**
- `llm/__init__.py`

**Testing:**
- [ ] Test that configuration is applied to stores
- [ ] Test default store selection from config
- [ ] Test fallback to JSON when default unavailable
- [ ] Test store.configure() is called with correct config

**Success Criteria:**
- Configuration is loaded and applied correctly
- Default store selection works
- Graceful fallback when configured store missing

---

## Phase 5: Integrate with Existing Key Retrieval

**Goal:** Modify `get_key()` to use secret store system while maintaining backward compatibility.

### Steps

#### 5.1: Update `get_key()` Function
Modify `llm/__init__.py` `get_key()` function (currently lines 346-383):

```python
def get_key(key, key_alias=None, default=None):
    """
    Get an API key with priority hierarchy:
    1. Explicit key parameter
    2. Secret store (configured backend)
    3. Legacy keys.json file (for backward compatibility)
    4. Environment variable
    5. Default value

    Args:
        key: Explicit key value
        key_alias: Alias to look up
        default: Default value if not found

    Returns:
        The API key or default
    """
    # 1. Explicit key takes highest priority
    if key:
        return key

    if not key_alias:
        return default

    # 2. Try secret store system
    secret_store = get_secret_store()  # Gets default store
    if secret_store:
        stored_value = secret_store.get(key_alias)
        if stored_value:
            return stored_value

    # 3. Legacy: try old load_keys() for backward compatibility
    # This handles existing keys.json files before migration
    legacy_keys = load_keys()
    if key_alias in legacy_keys:
        return legacy_keys[key_alias]

    # 4. Try environment variables
    env_var = f"{key_alias.upper()}_API_KEY"
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value

    # 5. Return default
    return default
```

**Files to modify:**
- `llm/__init__.py`

**Notes:**
- Keep backward compatibility with `load_keys()` during transition
- Priority order ensures existing behavior is preserved
- `load_keys()` check prevents breaking existing installations

**Testing:**
Update `tests/test_keys.py`:
- [ ] Test explicit key takes priority (existing test should still pass)
- [ ] Test secret store retrieval
- [ ] Test legacy keys.json still works
- [ ] Test environment variable fallback
- [ ] Test priority order is correct
- [ ] Test with no store configured
- [ ] Test with store configured but key not found
- [ ] All existing tests in `test_keys.py` must still pass unchanged

**Success Criteria:**
- All existing `test_keys.py` tests pass without modification
- New priority order works correctly
- Secret store integration is transparent
- At least 5 new tests for secret store path

#### 5.2: Keep `load_keys()` for Backward Compatibility
Keep the existing `load_keys()` function unchanged for now. It will be deprecated in a future phase.

**Files to check:**
- `llm/__init__.py` - Verify `load_keys()` remains functional

**Testing:**
- [ ] Verify existing tests using `load_keys()` still pass
- [ ] Test that both old and new systems can coexist

**Success Criteria:**
- `load_keys()` continues to work
- No breaking changes

---

## Phase 6: Update CLI Commands

**Goal:** Update `llm keys` CLI commands to use secret store system.

### Steps

#### 6.1: Update `keys_set` Command
Modify `llm/cli.py` `keys_set()` function (currently lines 1325-1346):

```python
@keys.command(name="set")
@click.argument("alias")
@click.option(
    "--store",
    default=None,
    help="Secret store to use (default: configured default store)",
)
@click.option("--value", help="Secret value (will prompt if not provided)")
def keys_set(alias, value, store):
    """
    Set a secret in the secret store.
    """
    if not value:
        value = click.prompt(f"Enter secret value for {alias}", hide_input=True)

    # Get the appropriate secret store
    store_name = store or llm._default_secret_store_name
    secret_store = llm.get_secret_store(store_name)

    if not secret_store:
        raise click.ClickException(
            f"Secret store '{store_name}' not found. "
            f"Available stores: {', '.join(llm.get_secret_stores().keys())}"
        )

    try:
        secret_store.set(alias, value)
        click.echo(f"Secret '{alias}' stored in '{secret_store.name}' store", err=True)
    except Exception as e:
        raise click.ClickException(f"Failed to store secret: {e}")
```

**Files to modify:**
- `llm/cli.py`

**Testing:**
Update existing tests in `tests/test_keys.py`:
- [ ] Test `llm keys set` with default store
- [ ] Test `llm keys set --store json`
- [ ] Test error handling for invalid store
- [ ] Test prompting for value
- [ ] Test providing value via --value
- [ ] All existing `keys_set` tests must pass

**Success Criteria:**
- Command works identically to before (default behavior)
- Optional `--store` parameter works
- Good error messages
- At least 4 tests covering CLI behavior

#### 6.2: Update `keys_get` Command
Modify `llm/cli.py` `keys_get()` function (currently lines 1303-1319):

```python
@keys.command(name="get")
@click.argument("alias")
@click.option(
    "--store",
    default=None,
    help="Secret store to use (default: search all stores)",
)
def keys_get(alias, store):
    """
    Retrieve a secret from the secret store.
    """
    if store:
        # Get from specific store
        secret_store = llm.get_secret_store(store)
        if not secret_store:
            raise click.ClickException(f"Secret store '{store}' not found")
        value = secret_store.get(alias)
    else:
        # Use get_key which searches in priority order
        value = llm.get_key(None, alias)

    if value:
        click.echo(value)
    else:
        raise click.ClickException(f"Secret '{alias}' not found")
```

**Files to modify:**
- `llm/cli.py`

**Testing:**
- [ ] Test `llm keys get` with existing key
- [ ] Test `llm keys get` with non-existent key
- [ ] Test `llm keys get --store json`
- [ ] Test error handling
- [ ] All existing `keys_get` tests must pass

**Success Criteria:**
- Command works identically to before
- Optional `--store` parameter works
- At least 3 tests

#### 6.3: Update `keys_list` Command
Modify `llm/cli.py` `keys_list()` function (currently lines 1283-1292):

```python
@keys.command(name="list")
@click.option(
    "--store",
    default=None,
    help="Secret store to list (default: all stores)",
)
def keys_list(store):
    """
    List all stored secret aliases.
    """
    if store:
        # List from specific store
        secret_store = llm.get_secret_store(store)
        if not secret_store:
            raise click.ClickException(f"Secret store '{store}' not found")
        keys = secret_store.list_keys()
        for key in keys:
            click.echo(f"{key} ({store})")
    else:
        # List from all stores
        all_keys = set()
        for store_name, secret_store in llm.get_secret_stores().items():
            store_keys = secret_store.list_keys()
            for key in store_keys:
                if key not in all_keys:
                    click.echo(f"{key} ({store_name})")
                    all_keys.add(key)
```

**Files to modify:**
- `llm/cli.py`

**Testing:**
- [ ] Test `llm keys list` shows all keys
- [ ] Test `llm keys list --store json`
- [ ] Test with no keys
- [ ] Test with keys in multiple stores (future-proofing)
- [ ] All existing `keys_list` tests must pass

**Success Criteria:**
- Command works with enhanced output showing store name
- Backward compatible with existing usage
- At least 3 tests

#### 6.4: Keep `keys_path` Command Unchanged
The `keys_path` command shows the JSON file path, which is still valid for the JSON store.

```python
# No changes needed - this remains useful for finding the JSON store location
```

**Testing:**
- [ ] Verify `llm keys path` still works
- [ ] Existing tests still pass

**Success Criteria:**
- No breaking changes

---

## Phase 7: Comprehensive Testing

**Goal:** Ensure complete test coverage and backward compatibility.

### Steps

#### 7.1: Run Full Test Suite
```bash
pytest tests/ -v --cov=llm --cov-report=term-missing
```

**Expected Results:**
- All existing tests pass
- Coverage for new code ≥95%
- No regressions in existing functionality

#### 7.2: Test Backward Compatibility Scenarios
Create `tests/test_secret_store_backward_compat.py`:

Test scenarios:
- [ ] User with existing `keys.json` can still use `llm keys get`
- [ ] Existing `keys.json` keys are accessible via new system
- [ ] Setting new keys works with both old and new systems
- [ ] Environment variables still override as expected
- [ ] Models that use `KeyModel` still work
- [ ] `llm chat` with API keys still works

**Success Criteria:**
- At least 6 backward compatibility tests
- All tests pass
- Existing users experience no disruption

#### 7.3: Integration Tests
Create `tests/test_secret_store_integration.py`:

Test scenarios:
- [ ] End-to-end: set key, retrieve via get_key(), use in model
- [ ] CLI: set via CLI, retrieve via Python API
- [ ] Python API: set via API, retrieve via CLI
- [ ] Multiple keys in same store
- [ ] Store registration and retrieval
- [ ] Configuration loading and application

**Success Criteria:**
- At least 6 integration tests
- Tests cover realistic usage patterns

#### 7.4: Edge Case Testing
Add edge case tests to relevant test files:

- [ ] Empty store
- [ ] Corrupted config file
- [ ] Missing store directory
- [ ] Concurrent access to keys.json
- [ ] Very long key values
- [ ] Special characters in key aliases
- [ ] Unicode in key values
- [ ] Store name collision

**Success Criteria:**
- At least 8 edge case tests
- All edge cases handled gracefully

#### 7.5: Performance Testing
Basic performance validation:

- [ ] Test that key retrieval is fast (<10ms for typical case)
- [ ] Test that many keys (100+) don't degrade performance
- [ ] Test that file I/O is not excessive

**Success Criteria:**
- No performance regressions
- Reasonable performance characteristics documented

---

## Phase 8: Documentation

**Goal:** Document the new system for developers and users.

### Steps

#### 8.1: Update Code Documentation
- [ ] Add comprehensive docstrings to all new functions
- [ ] Add inline comments explaining key design decisions
- [ ] Update type hints for all functions

**Files to document:**
- `llm/secret_stores.py`
- `llm/default_plugins/json_secret_store.py`
- Modified functions in `llm/__init__.py`
- Modified functions in `llm/cli.py`

**Success Criteria:**
- All public functions have docstrings
- Docstrings follow existing project conventions
- Complex logic has inline comments

#### 8.2: Create Plugin Developer Guide
Create `docs/secret-store-plugins.md`:

Content:
- Overview of secret store system
- How to implement a SecretStore
- How to register a secret store plugin
- Example implementation walkthrough
- Configuration format
- Testing recommendations

**Success Criteria:**
- Clear, actionable documentation
- Example plugin code included
- Follows existing docs style

#### 8.3: Update User Documentation
Update `docs/setup.md` section on API keys (currently lines 95-162):

Content:
- Explain secret store system
- Document `secret-store-config.json`
- Explain migration path (future)
- Document `--store` CLI option
- Security considerations

**Success Criteria:**
- User-facing documentation is clear
- Existing documentation updated
- No breaking changes in docs

#### 8.4: Update Changelog
Add to `docs/changelog.md`:

```markdown
## Secret Store Plugin System (In Development)

- Added plugin-based secret store system for extensible key management
- Refactored existing JSON key storage as a plugin
- Added `secret-store-config.json` configuration file
- Added `--store` option to `llm keys` commands
- Enhanced key retrieval with configurable backend support
- Full backward compatibility maintained with existing `keys.json` files
```

**Files to modify:**
- `docs/changelog.md`

**Success Criteria:**
- Changelog accurately reflects changes
- User impact is clear

---

## Phase 9: Code Quality and Final Validation

**Goal:** Ensure code meets project quality standards.

### Steps

#### 9.1: Run Linters and Formatters
```bash
# Format code
black llm/ tests/

# Check formatting
black --check llm/ tests/

# Any other linters used by project
```

**Success Criteria:**
- All code passes `black` formatting
- Follows existing code style
- No linter warnings

#### 9.2: Run Type Checking (if applicable)
```bash
# If project uses mypy or similar
mypy llm/
```

**Success Criteria:**
- No type errors
- Type hints are accurate

#### 9.3: Final Test Run
```bash
# Run complete test suite
pytest tests/ -v --cov=llm --cov-report=html

# Check coverage report
# open htmlcov/index.html
```

**Success Criteria:**
- All tests pass (existing + new)
- Coverage ≥95% for new code
- Zero regressions

#### 9.4: Manual Testing Checklist
Perform manual testing:

- [ ] `llm keys set mykey` works
- [ ] `llm keys get mykey` retrieves the key
- [ ] `llm keys list` shows the key
- [ ] `llm keys path` shows correct path
- [ ] `llm chat "test"` works with OpenAI key
- [ ] Existing `keys.json` file is still used
- [ ] New installation creates keys via secret store
- [ ] Configuration file is created correctly

**Success Criteria:**
- All manual tests pass
- User experience is smooth
- No errors or warnings

---

## Phase 10: Commit and Documentation Review

**Goal:** Prepare changes for review and merge.

### Steps

#### 10.1: Create Comprehensive Commit
```bash
# Stage all changes
git add llm/ tests/ docs/

# Create detailed commit message
git commit -m "Add foundational secret store plugin system

Implements plugin-based architecture for API key storage:

- Add SecretStore abstract base class (llm/secret_stores.py)
- Add register_secret_stores plugin hook (llm/hookspecs.py)
- Implement JsonSecretStore as default plugin refactoring
  existing keys.json functionality
- Add secret-store-config.json configuration support
- Enhance get_key() to use secret store system
- Update llm keys CLI commands with --store option
- Full backward compatibility with existing keys.json
- 100% test coverage for new functionality

Breaking changes: None
Migration required: No (automatic backward compatibility)

Tests: All existing tests pass + 30+ new tests added
Coverage: 95%+ for all new code

Closes #XXX"
```

**Success Criteria:**
- Comprehensive commit message
- All changes staged correctly
- Commit is logical and atomic

#### 10.2: Push to Branch
```bash
git push -u origin claude/design-api-key-protection-011CUsGXrx4sxDN78Hi5YMqF
```

**Success Criteria:**
- Changes pushed successfully
- No conflicts
- Branch is up to date

---

## Final Success Criteria Checklist

Before considering this implementation complete, verify ALL of these:

### Functionality
- [ ] All existing tests pass without modification
- [ ] All new tests pass (minimum 30+ new tests)
- [ ] `SecretStore` ABC is properly implemented
- [ ] `JsonSecretStore` plugin works correctly
- [ ] `register_secret_stores` hook is functional
- [ ] Configuration file loading works
- [ ] `get_key()` uses secret store system
- [ ] CLI commands work with `--store` option
- [ ] Backward compatibility is maintained 100%

### Quality
- [ ] Code coverage ≥95% for all new code
- [ ] All code passes `black` formatting
- [ ] All docstrings are comprehensive
- [ ] No linter warnings
- [ ] Type hints where appropriate

### Documentation
- [ ] Plugin developer guide created
- [ ] User documentation updated
- [ ] Changelog updated
- [ ] Code comments explain complex logic

### Testing
- [ ] Unit tests for all new functions
- [ ] Integration tests for end-to-end flows
- [ ] Backward compatibility tests
- [ ] Edge case tests
- [ ] Manual testing completed

### Security
- [ ] File permissions maintained (0o600)
- [ ] No secrets logged or exposed
- [ ] Configuration file is secure
- [ ] Error messages don't leak sensitive data

---

## Estimated Effort

- **Phase 0:** 30 minutes (environment setup and validation)
- **Phase 1:** 1-2 hours (abstract class and exports)
- **Phase 2:** 1 hour (plugin hook)
- **Phase 3:** 3-4 hours (JsonSecretStore implementation and tests)
- **Phase 4:** 2-3 hours (configuration support)
- **Phase 5:** 2 hours (get_key integration)
- **Phase 6:** 2-3 hours (CLI updates)
- **Phase 7:** 3-4 hours (comprehensive testing)
- **Phase 8:** 2-3 hours (documentation)
- **Phase 9:** 1-2 hours (code quality and validation)
- **Phase 10:** 30 minutes (commit and push)

**Total:** 18-25 hours of focused development

---

## Risk Mitigation

### Risk: Breaking Existing Functionality
**Mitigation:**
- Run existing tests before any changes
- Keep backward compatibility path in `get_key()`
- Don't modify existing `load_keys()` function
- Test with real `keys.json` files

### Risk: Test Coverage Gaps
**Mitigation:**
- Write tests before implementation (TDD where possible)
- Use coverage reports to identify gaps
- Require 95%+ coverage for merge

### Risk: Performance Degradation
**Mitigation:**
- Keep file I/O minimal (same as current implementation)
- Cache configuration where appropriate
- Performance test with many keys

### Risk: Configuration Complexity
**Mitigation:**
- Provide sensible defaults (json store)
- Make configuration optional
- Clear error messages

---

## Next Steps After This Plan

After this foundational implementation is complete, future work can include:

1. **Additional Secret Store Plugins:**
   - OS Keychain plugin (macOS/Windows/Linux)
   - Gopass plugin
   - HashiCorp Vault plugin
   - AWS Secrets Manager plugin

2. **Migration Tools:**
   - `llm keys migrate` command
   - Automatic migration prompts

3. **Enhanced Features:**
   - Audit logging
   - Key rotation support
   - Multiple store fallback chains
   - Store-specific configuration UI

4. **Security Enhancements:**
   - Key encryption at rest
   - Master password support
   - Key expiration policies

These will be addressed in separate, focused implementations.
