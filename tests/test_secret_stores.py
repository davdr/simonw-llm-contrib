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


# Tests for secret store registry


class MockSecretStore(SecretStore):
    """Mock secret store for testing."""

    name = "mock"

    def get(self, key_alias: str):
        return None

    def set(self, key_alias: str, value: str):
        pass

    def delete(self, key_alias: str):
        return False

    def list_keys(self):
        return []


def test_register_secret_store():
    """Can register a secret store."""
    # Clear any existing stores
    llm._secret_stores.clear()

    store = MockSecretStore()
    llm.register_secret_store(store)

    assert "mock" in llm._secret_stores
    assert llm._secret_stores["mock"] is store


def test_register_secret_store_requires_secret_store_instance():
    """register_secret_store requires a SecretStore instance."""
    with pytest.raises(TypeError, match="store must be a SecretStore instance"):
        llm.register_secret_store("not a store")


def test_register_secret_store_requires_name():
    """register_secret_store requires store to have a name."""

    class NoNameStore(SecretStore):
        # Missing name attribute
        def get(self, key_alias: str):
            return None

        def set(self, key_alias: str, value: str):
            pass

        def delete(self, key_alias: str):
            return False

        def list_keys(self):
            return []

    store = NoNameStore()
    with pytest.raises(ValueError, match="must have a non-empty 'name' attribute"):
        llm.register_secret_store(store)


def test_get_secret_store_by_name():
    """Can retrieve a secret store by name."""
    llm._secret_stores.clear()

    store = MockSecretStore()
    llm.register_secret_store(store)

    retrieved = llm.get_secret_store("mock")
    assert retrieved is store


def test_get_secret_store_returns_none_if_not_found():
    """get_secret_store returns None if store not found."""
    llm._secret_stores.clear()

    assert llm.get_secret_store("nonexistent") is None


def test_get_secret_store_returns_default():
    """get_secret_store with no name returns default store."""
    llm._secret_stores.clear()

    store = MockSecretStore()
    llm.register_secret_store(store)
    llm._default_secret_store_name = "mock"

    retrieved = llm.get_secret_store()
    assert retrieved is store


def test_get_secret_stores_returns_all():
    """get_secret_stores returns all registered stores."""
    llm._secret_stores.clear()

    store1 = MockSecretStore()
    store1.name = "store1"
    store2 = MockSecretStore()
    store2.name = "store2"

    llm.register_secret_store(store1)
    llm.register_secret_store(store2)

    stores = llm.get_secret_stores()
    assert len(stores) == 2
    assert stores["store1"] is store1
    assert stores["store2"] is store2


def test_set_default_secret_store():
    """Can set default secret store."""
    llm._secret_stores.clear()
    llm._default_secret_store_name = None

    store = MockSecretStore()
    llm.register_secret_store(store)

    llm.set_default_secret_store("mock")
    assert llm._default_secret_store_name == "mock"


def test_set_default_secret_store_must_exist():
    """set_default_secret_store raises error if store doesn't exist."""
    llm._secret_stores.clear()

    with pytest.raises(ValueError, match="Secret store 'nonexistent' is not registered"):
        llm.set_default_secret_store("nonexistent")
