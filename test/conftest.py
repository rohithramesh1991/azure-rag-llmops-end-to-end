"""
Shared test setup:
- Provide dummy environment variables so Pydantic Settings() can load.
- Do NOT stub/mocking anything here (keep tests explicit).
"""

import os

# Minimal, valid-looking values for all required env vars
DEFAULT_ENV = {
    "OPENAI_API_BASE": "https://example.com/openai",   # must look like a URL
    "OPENAI_API_KEY": "test-key",
    "OPENAI_API_VERSION": "2024-06-01",
    "CHAT_DEPLOYMENT": "mock-chat",
    "EMBEDDING_DEPLOYMENT": "mock-embed",
    "SEARCH_SERVICE_NAME": "https://mock.search.windows.net",
    "SEARCH_API_KEY": "mock-search-key",
    "SEARCH_INDEX_NAME": "mock-index",
    # Optional: avoid warming clients during tests if you add such a toggle
    "EAGER_INIT": "false",
}

for k, v in DEFAULT_ENV.items():
    os.environ.setdefault(k, v)

# Some libraries also read these Azure-style env names; set them for safety
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", DEFAULT_ENV["OPENAI_API_BASE"])
os.environ.setdefault("AZURE_OPENAI_API_KEY", DEFAULT_ENV["OPENAI_API_KEY"])