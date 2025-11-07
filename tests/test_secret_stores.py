"""Tests for the SecretStore abstract base class."""

import pytest
import llm
from llm.secret_stores import SecretStore


def test_secret_store_is_abstract():
    """SecretStore cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SecretStore()


def test_secret_store_requires_all_methods():
    """Subclass without all abstract methods raises TypeError."""

    class IncompleteStore(SecretStore):
        name = "incomplete"
        # Missing implementations

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteStore()


def test_secret_store_can_be_subclassed():
    """A complete SecretStore implementation can be instantiated."""

    class CompleteStore(SecretStore):
        name = "complete"

        def get(self, key_alias: str):
            return None

        def set(self, key_alias: str, value: str):
            pass

        def delete(self, key_alias: str):
            return False

        def list_keys(self):
            return []

    # Should not raise
    store = CompleteStore()
    assert store.name == "complete"


def test_secret_store_configure_has_default_implementation():
    """The configure method has a default no-op implementation."""

    class MinimalStore(SecretStore):
        name = "minimal"

        def get(self, key_alias: str):
            return None

        def set(self, key_alias: str, value: str):
            pass

        def delete(self, key_alias: str):
            return False

        def list_keys(self):
            return []

    store = MinimalStore()
    # Should not raise - configure has default implementation
    store.configure({"foo": "bar"})


def test_secret_store_subclass_can_override_configure():
    """Subclasses can override the configure method."""

    class ConfigurableStore(SecretStore):
        name = "configurable"

        def __init__(self):
            self.config = {}

        def get(self, key_alias: str):
            return None

        def set(self, key_alias: str, value: str):
            pass

        def delete(self, key_alias: str):
            return False

        def list_keys(self):
            return []

        def configure(self, config):
            self.config = config

    store = ConfigurableStore()
    store.configure({"setting": "value"})
    assert store.config == {"setting": "value"}


def test_secret_store_importable_from_llm():
    """SecretStore can be imported from llm package."""
    # Test that import llm; llm.SecretStore works
    assert hasattr(llm, "SecretStore")
    assert llm.SecretStore is SecretStore


def test_secret_store_in_all():
    """SecretStore is in __all__ exports."""
    assert "SecretStore" in llm.__all__
