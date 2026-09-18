import pytest

from castor.config.settings import settings


@pytest.fixture(autouse=True)
def no_langfuse(monkeypatch):
    """Keep tests from sending spans to Langfuse."""
    monkeypatch.setattr(settings, "langfuse_secret_key", None)
    monkeypatch.setattr(settings, "langfuse_public_key", None)
