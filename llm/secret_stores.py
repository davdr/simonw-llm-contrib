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
