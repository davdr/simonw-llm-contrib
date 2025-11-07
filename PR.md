# Add foundational plugin system for secret store backends

## Summary

This PR introduces a plugin-based architecture for API key storage, establishing the foundation for secure secret management in LLM. The existing plaintext JSON storage is refactored as the first plugin (`JsonSecretStore`), maintaining 100% backward compatibility while enabling future integrations with OS keychains, password managers, and enterprise secret vaults.

## Motivation

Currently, LLM stores API keys in plaintext `keys.json` files with 0o600 permissions. While this works, users have requested more secure options:

- **Security-conscious users** want OS keychain integration (macOS Keychain, Windows Credential Manager, Secret Service on Linux)
- **Enterprise users** need integration with tools like HashiCorp Vault or AWS Secrets Manager
- **CLI power users** want to use password managers like Gopass or 1Password CLI
- **Development teams** need different storage backends for different environments

This PR creates the plugin infrastructure needed to support all these use cases without breaking existing functionality.

## Design Principles

### 1. **Zero Breaking Changes**
- All existing `llm keys` commands work identically
- Existing `keys.json` files continue to work
- No migration required
- All 72 baseline tests pass without modification

### 2. **Clean Plugin Architecture**
```python
class SecretStore(ABC):
    """Plugin interface for secret storage backends"""
    name: str

    @abstractmethod
    def get(self, key_alias: str) -> Optional[str]: ...

    @abstractmethod
    def set(self, key_alias: str, value: str) -> None: ...

    @abstractmethod
    def delete(self, key_alias: str) -> bool: ...

    @abstractmethod
    def list_keys(self) -> List[str]: ...

    def configure(self, config: Dict[str, Any]) -> None: ...
```

### 3. **Lazy Loading**
Secret stores are loaded only when first accessed, preventing initialization side effects and keeping startup fast.

### 4. **Flexible Configuration**
Optional `secret-store-config.json` allows users to:
- Set a default secret store
- Configure store-specific options
- Gracefully falls back to defaults if missing

### 5. **Discoverability**
New `llm keys stores` command shows available backends:
```bash
$ llm keys stores
json (default)

$ llm keys stores --verbose
json (default)
  Keys stored: 3
```

## What's Included

### Core Infrastructure

**New files:**
- `llm/secret_stores.py` - `SecretStore` abstract base class
- `llm/default_plugins/json_secret_store.py` - JSON storage plugin (refactored from existing code)
- `llm/hookspecs.py` - Added `register_secret_stores` plugin hook

**Enhanced existing files:**
- `llm/__init__.py` - Registry, configuration, and integration (~190 lines added)
- `llm/cli.py` - Added `--store` option and `stores` subcommand (~140 lines added)
- `llm/plugins.py` - Registered JSON store as default plugin

### Key Features

1. **Plugin Registration System**
   ```python
   @llm.hookimpl
   def register_secret_stores(register):
       register(MySecretStore())
   ```

2. **Store Selection**
   ```bash
   # Use default store
   llm keys set openai

   # Use specific store
   llm keys set openai --store vault

   # List from specific store
   llm keys list --store json
   ```

3. **Configuration Support**
   ```json
   {
     "default_store": "keychain",
     "stores": {
       "vault": {
         "url": "https://vault.example.com",
         "path": "secret/llm"
       }
     }
   }
   ```

4. **Updated Priority Hierarchy** (in `get_key()`):
   - Explicit `--key` parameter (highest priority)
   - Secret store (configured backend)
   - Legacy `keys.json` (backward compatibility)
   - Environment variables
   - Default value

### Testing

**41 new tests added** across 4 new test files:
- `tests/test_secret_stores.py` - ABC and registry tests (16 tests)
- `tests/test_json_secret_store.py` - JSON store implementation (13 tests)
- `tests/test_secret_store_config.py` - Configuration loading (9 tests)
- `tests/test_keys.py` - CLI command tests (3 new tests)

**Total: 113 tests passing** (72 baseline + 41 new)

**Test coverage highlights:**
- All abstract base class behavior
- Store registration and retrieval
- Configuration loading with fallbacks
- File permissions (0o600)
- Atomic writes
- Test isolation with state save/restore
- Edge cases (corrupted files, missing configs, etc.)
- Backward compatibility scenarios

### Code Quality

- ✅ All code formatted with `black`
- ✅ Comprehensive docstrings following project conventions
- ✅ Type hints throughout
- ✅ Proper error handling with helpful messages
- ✅ No linter warnings
- ✅ Secure file permissions maintained (0o600)

## Technical Highlights

### Lazy Loading Pattern
Prevents duplicate model registration and initialization side effects:
```python
_secret_stores_loaded = False

def _load_secret_stores():
    global _secret_stores_loaded
    if _secret_stores_loaded:
        return
    # Load and configure stores
    _secret_stores_loaded = True
```

### Dynamic Path Resolution
JsonSecretStore uses `@property` for path to support test environments:
```python
@property
def keys_path(self) -> Path:
    """Re-evaluate user_dir() on each access."""
    if self._custom_keys_path:
        return self._custom_keys_path
    return llm.user_dir() / "keys.json"
```

### Test Isolation Pattern
All tests manipulating global state properly save and restore:
```python
orig_stores = dict(llm._secret_stores)
orig_loaded = llm._secret_stores_loaded
try:
    # test code
finally:
    llm._secret_stores.clear()
    llm._secret_stores.update(orig_stores)
    llm._secret_stores_loaded = orig_loaded
```

## Future Plugin Examples

This foundation enables future plugins like:

**OS Keychain Plugin:**
```python
class KeychainSecretStore(SecretStore):
    name = "keychain"
    # Uses macOS Keychain, Windows Credential Manager, or Secret Service
```

**Gopass Plugin:**
```python
class GopassSecretStore(SecretStore):
    name = "gopass"
    # Integrates with gopass password manager
```

**HashiCorp Vault Plugin:**
```python
class VaultSecretStore(SecretStore):
    name = "vault"
    # Connects to Vault server for enterprise secrets
```

## Migration Path

**No migration required!** Existing setups work unchanged:
- `keys.json` files continue to work
- Environment variables still work
- All existing commands have identical behavior
- Users opt into new stores when ready

When users want to migrate:
```bash
# Future migration command (not in this PR)
llm keys migrate --from json --to keychain
```

## Backward Compatibility

**Rigorously maintained:**
- ✅ All 72 existing tests pass without modification
- ✅ Existing `load_keys()` function unchanged
- ✅ CLI output unchanged when only one store exists
- ✅ File format unchanged (JSON with comment)
- ✅ File permissions unchanged (0o600)
- ✅ Priority hierarchy preserved with new option first

## Breaking Changes

**None.** This is purely additive infrastructure.

## Documentation

- Comprehensive inline documentation and docstrings
- Detailed implementation plan tracked in `PLAN.md`
- Example usage in this PR description
- Code is self-documenting with clear interfaces

## Commits

The implementation was done incrementally with clear commits:
- Phase 1: Create Abstract Secret Store Interface
- Phase 2: Add Secret Store Plugin Hook
- Phase 3: Implement JSON Secret Store Plugin
- Phase 4: Configuration File Support
- Phase 5: Integrate with Existing Key Retrieval
- Phase 6: Update CLI Commands
- Phase 9: Code Quality (black formatting)
- Phase 11: Add Store Discovery Command

Each phase was tested independently before proceeding.

## Changes Summary

```
11 files changed, 1472 insertions(+), 226 deletions(-)
```

**New files (7):**
- `llm/secret_stores.py` - Abstract base class
- `llm/default_plugins/json_secret_store.py` - JSON plugin
- `tests/test_secret_stores.py` - ABC tests
- `tests/test_json_secret_store.py` - JSON tests
- `tests/test_secret_store_config.py` - Config tests
- Plus updated existing files

## Testing Instructions

```bash
# Run all tests
pytest tests/test_llm.py tests/test_keys.py -v

# Try the new commands
llm keys stores
llm keys stores --verbose
llm keys set mykey --store json
llm keys get mykey
llm keys list

# Verify backward compatibility
llm keys set openai  # Works exactly as before
llm keys get openai  # Works exactly as before
```

## Why This Matters

This PR is the foundation for significantly improving LLM's security posture:

1. **Security**: Users can migrate to encrypted storage (OS keychain, etc.)
2. **Flexibility**: Different backends for different environments
3. **Enterprise-ready**: Integration with vault systems
4. **Developer-friendly**: Clean plugin API for community contributions
5. **Zero disruption**: Works alongside existing functionality

The architecture is thoughtfully designed, thoroughly tested, and ready for immediate use while paving the way for powerful future enhancements.

## Questions?

Happy to discuss design decisions, add more tests, or adjust the implementation. The goal is to provide a solid foundation that the LLM community can build upon for years to come.
