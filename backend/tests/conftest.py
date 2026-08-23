import os

import pytest

# Langfuse credentials leak in from the developer shell (~/.zshrc); without
# this, mocked test runs export fake traces into the real Langfuse project.
os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
os.environ.pop("LANGFUSE_SECRET_KEY", None)


@pytest.fixture(autouse=True)
def _no_langfuse_env(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
