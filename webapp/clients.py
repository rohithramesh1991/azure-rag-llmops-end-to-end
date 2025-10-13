
from functools import lru_cache
from webapp.config import settings
from openai import AzureOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch


@lru_cache
def get_oai_client() -> AzureOpenAI:
    # No network call on construction
    return AzureOpenAI(
        api_key=settings.OPENAI_API_KEY,
        api_version=settings.OPENAI_API_VERSION,
        azure_endpoint=str(settings.OPENAI_API_BASE),  # explicit!
    )


@lru_cache
def get_embeddings() -> AzureOpenAIEmbeddings:
    # langchain_openai needs endpoint explicitly (or AZURE_OPENAI_ENDPOINT env)
    return AzureOpenAIEmbeddings(
        model=settings.EMBEDDING_DEPLOYMENT,
        api_key=settings.OPENAI_API_KEY,         #type: ignore[arg-type]
        api_version=settings.OPENAI_API_VERSION,
        azure_endpoint=str(settings.OPENAI_API_BASE),  # explicit!
    )


@lru_cache
def get_vectorstore() -> AzureSearch:
    emb = get_embeddings()
    # AzureSearch may call embed_query("Text") once to detect dims — keep this lazy
    return AzureSearch(
        azure_search_endpoint=str(settings.SEARCH_SERVICE_NAME),
        azure_search_key=settings.SEARCH_API_KEY,
        index_name=settings.SEARCH_INDEX_NAME,
        embedding_function=emb.embed_query,
    )
