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
