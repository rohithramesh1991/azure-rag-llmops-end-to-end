# tests/conftest.py
"""
This ensures dummy environment variables are loaded
so Pydantic Settings() doesn't fail during test imports.
No real keys are used.
"""

import os

# Dummy configuration for testing
os.environ.setdefault("OPENAI_API_BASE", "https://example.com/openai")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_VERSION", "2024-06-01")
os.environ.setdefault("CHAT_DEPLOYMENT", "mock-chat")
os.environ.setdefault("EMBEDDING_DEPLOYMENT", "mock-embed")
os.environ.setdefault("SEARCH_SERVICE_NAME", "https://mock.search.windows.net")
os.environ.setdefault("SEARCH_API_KEY", "test-search-key")
os.environ.setdefault("SEARCH_INDEX_NAME", "mock-index")
