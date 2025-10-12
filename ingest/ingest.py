from __future__ import annotations

import os
import time
import math
import argparse
from dotenv import load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch


def require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest CSV data into Azure AI Search.")
    parser.add_argument("--csv", default="Data/wine-ratings.csv", help="Path to the CSV file")
    parser.add_argument("--index", default=None, help="Azure Search index name (defaults to env var)")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size for splitting text")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Overlap between chunks")
    parser.add_argument("--batch", type=int, default=64, help="Upload batch size")
    parser.add_argument("--dry-run", action="store_true", help="Only test embeddings, don’t upload")
    args = parser.parse_args()

    # ---- Load required environment variables ----
    OPENAI_API_BASE = require("OPENAI_API_BASE")  # must end with /openai
    OPENAI_API_KEY = require("OPENAI_API_KEY")
    OPENAI_API_VERSION = require("OPENAI_API_VERSION")
    EMBEDDING_DEPLOYMENT = require("EMBEDDING_DEPLOYMENT")

    SEARCH_SERVICE_NAME = require("SEARCH_SERVICE_NAME")
    SEARCH_API_KEY = require("SEARCH_API_KEY")
    SEARCH_INDEX_NAME = args.index or require("SEARCH_INDEX_NAME")

    # ---- Load CSV ----
    print(f"Loading data from {args.csv} ...")
    loader = CSVLoader(file_path=args.csv, encoding="utf-8")
    docs = loader.load()
    print(f"Loaded {len(docs)} rows from CSV")

    # ---- Split text (chunk long descriptions) ----
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        separators=["\n\n", "\n", ". ", "? ", "! "],
    )
    split_docs = text_splitter.split_documents(docs)
    print(f"Split into {len(split_docs)} text chunks")

    # ---- Initialize Embeddings ----
    embeddings = AzureOpenAIEmbeddings(
        model=EMBEDDING_DEPLOYMENT,
        api_key=OPENAI_API_KEY,  #type: ignore[arg-type]
        api_version=OPENAI_API_VERSION,
        azure_endpoint=OPENAI_API_BASE,
    )

    if args.dry_run:
        test_vec = embeddings.embed_query("This is a dry-run test.")
        print(f"Dry-run: embedding length = {len(test_vec)} (should be 1536 for ada-002)")
        return

    # ---- Initialize AzureSearch VectorStore ----
    vector_store = AzureSearch(
        azure_search_endpoint=SEARCH_SERVICE_NAME,
        azure_search_key=SEARCH_API_KEY,
        index_name=SEARCH_INDEX_NAME,
        embedding_function=embeddings.embed_query
    )

    # ---- Upload documents in batches ----
    total = len(split_docs)
    batch_size = args.batch
    print(f"Ingesting {total} chunks into index '{SEARCH_INDEX_NAME}' (batch={batch_size}) ...")
    t0 = time.time()

    for i in range(0, total, batch_size):
        batch = split_docs[i:i + batch_size]
        vector_store.add_documents(batch)
        pct = math.floor((i + len(batch)) * 100 / total)
        print(f"   → Uploaded {i + len(batch)}/{total} ({pct}%)")

    print(f"Done! Uploaded {total} chunks in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
