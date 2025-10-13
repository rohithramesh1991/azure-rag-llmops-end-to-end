# webapp/config.py
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Azure AI Foundry
    OPENAI_API_BASE: AnyHttpUrl
    OPENAI_API_KEY: str
    OPENAI_API_VERSION: str = "2024-06-01"

    # Deployments
    CHAT_DEPLOYMENT: str
    EMBEDDING_DEPLOYMENT: str

    # Azure AI Search
    SEARCH_SERVICE_NAME: AnyHttpUrl
    SEARCH_API_KEY: str
    SEARCH_INDEX_NAME: str

    # App toggles
    LLM_TIMEOUT: float = 30.0
    TOP_K: int = 5
    EAGER_INIT: bool = False  # if True, warm clients at startup

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()        # pyright: ignore[reportCallIssue]
