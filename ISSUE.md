# API Key Protection Enhancement

## Problem Statement

Currently, LLM stores API keys in plaintext in `keys.json` located in the user's configuration directory. While the file is protected with `0o600` permissions (read/write for owner only), this approach has several security limitations:

### Current Implementation

**Storage Location:**
- macOS: `~/Library/Application Support/io.datasette.llm/keys.json`
- Linux: `~/.config/io.datasette.llm/keys.json`
- Custom: Via `LLM_USER_PATH` environment variable

**Storage Format:** Plaintext JSON
```json
{
  "// Note": "This file stores secret API credentials. Do not share!",
  "openai": "sk-...",
  "personal": "your-api-key"
}
```

**Source Files:**
- `llm/__init__.py:386-401` - Key loading and directory management
- `llm/cli.py:1278-1347` - CLI commands for key management
- `llm/models.py:1713-1744` - Key retrieval logic for models

### Security Concerns

1. **No Encryption:** Keys are stored in plaintext, readable by anyone with file access
2. **Backup Risks:** System backups will include plaintext keys
3. **Multi-User Systems:** Not suitable for shared systems despite file permissions
4. **No Key Rotation:** No built-in support for key expiration or rotation policies
5. **No Audit Trail:** No logging of key access or modifications
6. **Memory Exposure:** Keys remain in process memory after use
7. **Limited OS Integration:** Doesn't leverage OS-level credential management

---

## Design Options

### Option 1: Plugin-Based Secret Store System (Recommended)

Leverage the existing plugin architecture to allow multiple secret store backends.

#### Architecture

**New Hook Specification** in `llm/hookspecs.py`:
```python
@hookspec
def register_secret_stores(register):
    """Register alternative secret store backends"""
```

**Base Interface** - Create `llm/secret_stores.py`:
```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class SecretStore(ABC):
    """Base class for secret store implementations"""

    name: str  # Unique identifier for the store

    @abstractmethod
    def get(self, key_alias: str) -> Optional[str]:
        """Retrieve a secret by alias"""

    @abstractmethod
    def set(self, key_alias: str, value: str) -> None:
        """Store a secret"""

    @abstractmethod
    def delete(self, key_alias: str) -> None:
        """Delete a stored secret"""

    @abstractmethod
    def list(self) -> List[str]:
        """List all stored key aliases"""

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the secret store with parameters"""
```

**Configuration** - `llm.user_dir() / "secret-store-config.json`:
```json
{
  "default_store": "vault",
  "stores": {
    "json": {
      "type": "json",
      "enabled": true
    },
    "vault": {
      "type": "vault",
      "enabled": true,
      "config": {
        "url": "https://vault.example.com",
        "path": "secret/llm"
      }
    },
    "gopass": {
      "type": "gopass",
      "enabled": true,
      "config": {
        "path": "llm/keys"
      }
    },
    "keychain": {
      "type": "keychain",
      "enabled": true,
      "config": {
        "service": "llm-cli"
      }
    }
  }
}
```

**CLI Enhancement:**
```bash
# Set key with default store
llm keys set openai

# Set key with specific store
llm keys set openai --store vault

# Get key (checks all enabled stores in priority order)
llm keys get openai

# Configure store
llm keys configure vault --url https://vault.example.com --path secret/llm

# List available stores
llm keys stores
```

#### Example Plugin Implementations

**1. Gopass Backend:**
```python
import subprocess
from llm.secret_stores import SecretStore
import llm

class GopassSecretStore(SecretStore):
    name = "gopass"

    def __init__(self):
        self.path_prefix = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self.path_prefix = config.get("path", "llm/keys")

    def get(self, key_alias: str) -> Optional[str]:
        path = f"{self.path_prefix}/{key_alias}"
        try:
            result = subprocess.run(
                ["gopass", "show", "-o", path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def set(self, key_alias: str, value: str) -> None:
        path = f"{self.path_prefix}/{key_alias}"
        subprocess.run(
            ["gopass", "insert", "-f", path],
            input=value,
            text=True,
            check=True
        )

    def list(self) -> List[str]:
        result = subprocess.run(
            ["gopass", "ls", self.path_prefix],
            capture_output=True,
            text=True
        )
        # Parse gopass output to extract key names
        return self._parse_gopass_list(result.stdout)

@llm.hookimpl
def register_secret_stores(register):
    register(GopassSecretStore())
```

**2. HashiCorp Vault Backend:**
```python
import hvac
from llm.secret_stores import SecretStore
import llm

class VaultSecretStore(SecretStore):
    name = "vault"

    def __init__(self):
        self.client = None
        self.secret_path = ""

    def configure(self, config: Dict[str, Any]) -> None:
        url = config.get("url", os.getenv("VAULT_ADDR"))
        self.secret_path = config.get("path", "secret/llm")
        self.client = hvac.Client(url=url)

    def get(self, key_alias: str) -> Optional[str]:
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path=f"{self.secret_path}/{key_alias}"
            )
            return secret["data"]["data"]["value"]
        except Exception:
            return None

    def set(self, key_alias: str, value: str) -> None:
        self.client.secrets.kv.v2.create_or_update_secret(
            path=f"{self.secret_path}/{key_alias}",
            secret={"value": value}
        )

    def list(self) -> List[str]:
        secrets = self.client.secrets.kv.v2.list_secrets(
            path=self.secret_path
        )
        return secrets["data"]["keys"]

@llm.hookimpl
def register_secret_stores(register):
    register(VaultSecretStore())
```

**3. OS Keychain Backend (Default Plugin):**
```python
import keyring
from llm.secret_stores import SecretStore
import llm

class KeychainSecretStore(SecretStore):
    name = "keychain"

    def __init__(self):
        self.service_name = "llm-cli"

    def configure(self, config: Dict[str, Any]) -> None:
        self.service_name = config.get("service", "llm-cli")

    def get(self, key_alias: str) -> Optional[str]:
        return keyring.get_password(self.service_name, key_alias)

    def set(self, key_alias: str, value: str) -> None:
        keyring.set_password(self.service_name, key_alias, value)

    def delete(self, key_alias: str) -> None:
        keyring.delete_password(self.service_name, key_alias)

    def list(self) -> List[str]:
        # keyring doesn't provide list functionality
        # Fall back to metadata storage
        return self._load_metadata()

@llm.hookimpl
def register_secret_stores(register):
    register(KeychainSecretStore())
```

#### Pros
- **Extensible:** Developers can create plugins for any secret management system
- **Consistent:** Uses existing plugin architecture (proven pattern)
- **Flexible:** Users choose the backend that fits their security requirements
- **Backward Compatible:** Current JSON storage can remain as a default store
- **Community-Driven:** Community can contribute backends without modifying core
- **Multiple Stores:** Users can have different keys in different stores

#### Cons
- **Complexity:** More complex implementation than built-in solutions
- **Plugin Dependencies:** External backends require additional dependencies
- **Configuration:** Users need to configure stores
- **Discovery:** Users need to discover and install plugins

#### Implementation Effort
- **Core Changes:** Moderate (new hook, base class, modified key retrieval)
- **Default Plugins:** 1-2 basic implementations (keychain, encrypted JSON)
- **Documentation:** Significant (plugin API, configuration, examples)
- **Testing:** Moderate (plugin system testing, backend mocking)

---

### Option 2: OS Credential Manager Integration (Built-in)

Use OS-level credential managers via the `keyring` library.

#### Architecture

**Install dependency:**
```bash
pip install keyring
```

**Modify `llm/__init__.py`:**
```python
import keyring

def get_key(key, key_alias=None, default=None):
    # First try explicit key
    if key:
        return key

    # Try keychain first
    if key_alias:
        stored = keyring.get_password("llm-cli", key_alias)
        if stored:
            return stored

    # Fall back to JSON file
    keys = load_keys()
    if key_alias and key_alias in keys:
        return keys[key_alias]

    # Try environment variable
    if key_alias:
        env_var = f"{key_alias.upper()}_API_KEY"
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value

    return default
```

**CLI Enhancement:**
```bash
# Automatically uses keychain
llm keys set openai

# Migrate from JSON to keychain
llm keys migrate --to keychain

# Switch back to JSON
llm keys migrate --to json
```

#### Supported Platforms
- **macOS:** Keychain
- **Windows:** Windows Credential Locker
- **Linux:** Secret Service D-Bus (via libsecret)

#### Pros
- **Simple:** Single dependency, straightforward implementation
- **Native:** Uses OS-level security features
- **User-Friendly:** No configuration required
- **Cross-Platform:** Works on all major operating systems
- **Automatic Encryption:** OS handles encryption at rest

#### Cons
- **Limited Flexibility:** Locked into OS capabilities
- **No Custom Backends:** Can't use Vault, gopass, or other tools
- **Linux Limitations:** Requires D-Bus session, may not work in all environments
- **Headless Systems:** May require additional setup on servers
- **Single Store:** Can't use different backends for different keys

#### Implementation Effort
- **Core Changes:** Small (modify `get_key()`, `load_keys()`, CLI commands)
- **Documentation:** Minimal (explain OS integration)
- **Testing:** Moderate (mock keyring, test fallbacks)

---

### Option 3: Encrypted JSON with Master Password

Keep JSON storage but encrypt it with a master password.

#### Architecture

**Add encryption to `llm/cli.py`:**
```python
from cryptography.fernet import Fernet
import getpass
import hashlib

def _get_encryption_key(password: str) -> bytes:
    """Derive encryption key from password"""
    return base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac('sha256', password.encode(), b'llm-salt', 100000)
    )

def keys_set(key_alias, value=None, password=None):
    # Prompt for master password
    if not password:
        password = getpass.getpass("Master password: ")

    # Load existing keys
    current = load_keys(password)
    current[key_alias] = value

    # Encrypt and save
    encryption_key = _get_encryption_key(password)
    fernet = Fernet(encryption_key)
    encrypted_data = fernet.encrypt(json.dumps(current).encode())

    path = llm.user_dir() / "keys.enc"
    path.write_bytes(encrypted_data)
```

**CLI Usage:**
```bash
# Set master password on first use
llm keys set openai
# Master password: ****
# Confirm password: ****
# Value: sk-...

# Subsequent uses require master password
llm keys get openai
# Master password: ****

# Store master password in environment (optional)
export LLM_MASTER_PASSWORD="secret"
llm keys get openai
```

#### Pros
- **No External Dependencies:** Minimal additional code
- **Backward Compatible:** Easy migration from JSON
- **Encrypted at Rest:** Keys are encrypted on disk
- **Simple:** Users understand password-based encryption

#### Cons
- **Password Management:** Users need to remember/store master password
- **Usability:** Requires password entry for every key access (unless cached)
- **Key Derivation:** Password-based encryption is weaker than key-based
- **Single Point of Failure:** Forget password = lose all keys
- **No OS Integration:** Doesn't leverage OS security features

#### Implementation Effort
- **Core Changes:** Moderate (encryption/decryption, password management)
- **Documentation:** Moderate (password management, recovery)
- **Testing:** Moderate (encryption tests, password handling)

---

### Option 4: Hybrid Approach (Recommended Alternative)

Combine built-in OS credential manager support with plugin system for advanced users.

#### Architecture

**Default Behavior:** Use OS keychain (Option 2) as default
**Advanced Users:** Can install plugins for custom backends (Option 1)

**Configuration** - `llm.user_dir() / "secret-store-config.json`:
```json
{
  "backend": "keychain",  // or "vault", "gopass", "json", etc.
  "config": {
    // Backend-specific configuration
  }
}
```

**Priority Order:**
1. Explicit `--key` parameter
2. Configured secret store backend (keychain, vault, etc.)
3. Legacy `keys.json` file (for backward compatibility)
4. Environment variables

#### Pros
- **Best of Both Worlds:** Simple for basic users, powerful for advanced users
- **Secure by Default:** Uses OS keychain out of the box
- **Extensible:** Plugin system for enterprise/advanced scenarios
- **Gradual Migration:** Users can migrate from JSON → keychain → custom backend

#### Cons
- **Complexity:** Most complex to implement
- **Maintenance:** Need to maintain both built-in and plugin systems

#### Implementation Effort
- **Core Changes:** Significant (keychain + plugin system)
- **Default Plugins:** 1-2 implementations
- **Documentation:** Significant (multiple paths for different users)
- **Testing:** Significant (all backends + interactions)

---

## Recommendations

### Primary Recommendation: Option 4 (Hybrid Approach)

This provides the best user experience across different user segments:

1. **Casual Users:** Automatic OS keychain integration with zero configuration
2. **Enterprise Users:** Can use Vault, AWS Secrets Manager, etc. via plugins
3. **DevOps Users:** Can use gopass, pass, or other CLI tools
4. **Legacy Users:** Existing JSON storage continues to work

### Implementation Phases

**Phase 1: Core Infrastructure**
- Add `SecretStore` base class and plugin hook
- Implement OS keychain as default secret store
- Add migration command from JSON to keychain
- Maintain backward compatibility with JSON storage

**Phase 2: Plugin System**
- Document plugin API
- Create example plugins (gopass, encrypted JSON)
- Add store selection to CLI commands

**Phase 3: Enhanced Features**
- Add audit logging
- Implement key rotation support
- Add configuration validation
- Create comprehensive documentation

### Security Considerations

1. **Key Material Handling:**
   - Clear keys from memory after use where possible
   - Use secure memory handling libraries if available
   - Avoid logging key material

2. **Access Control:**
   - Maintain 0o600 permissions for configuration files
   - Document security implications of each backend
   - Warn users about less secure options

3. **Migration Path:**
   - Provide clear migration documentation
   - Create migration tool: `llm keys migrate --from json --to keychain`
   - Support gradual migration (both systems working simultaneously)

4. **Audit Trail:**
   - Log key access (configurable)
   - Track which backend provided each key
   - Record failed access attempts

---

## Alternative Approaches Considered

### 1. Environment Variables Only
**Rejected because:** Many users have multiple keys and environment variables are often logged/exposed

### 2. Age Encryption (age-encryption.org)
**Rejected because:** Requires key management, less user-friendly than OS keychain

### 3. GPG Encryption
**Rejected because:** Complex setup, requires GPG key management

---

## Questions for Discussion

1. **Default Behavior:** Should we auto-migrate users from JSON to keychain, or require explicit opt-in?

2. **Backward Compatibility:** How long should we maintain support for plaintext JSON storage?

3. **Cross-Platform Consistency:** Should we ensure identical behavior across OS platforms, or optimize for each platform?

4. **Plugin Distribution:** Should secret store plugins be separate packages or included in core?

5. **Configuration UI:** Should we provide an interactive configuration wizard for secret stores?

6. **Key Sharing:** Should we support sharing keys across multiple machines (e.g., via encrypted sync)?

---

## References

- Current key storage: `llm/__init__.py:386-401`, `llm/cli.py:1278-1347`
- Plugin system: `llm/plugins.py`, `llm/hookspecs.py`
- Key retrieval hierarchy: `llm/__init__.py:346-383`
- Test coverage: `tests/test_keys.py`
- Documentation: `docs/setup.md:95-162`
