# 🧠 Azure RAG LLMOps End-to-End

An end-to-end **Retrieval-Augmented Generation (RAG)** application built with **FastAPI**, **LangChain**, and **Azure OpenAI**.  
This project demonstrates how to integrate embeddings, semantic search, and LLM responses into a production-ready app that can later be deployed on Azure.

---

## 🚀 Overview

This project implements a RAG workflow where:
1. Documents are **embedded** using Azure OpenAI’s Embedding API.  
2. Embeddings are **stored and queried** in **Azure Cognitive Search**.  
3. A **FastAPI backend** serves user queries and combines search results with **LLM completions**.  
4. Metrics and health checks are exposed for observability and monitoring.

---

## 🧩 Architecture

User Query → FastAPI → Azure OpenAI (Embedding + Chat)
↘ Azure Cognitive Search (Retrieval)


Key Components:
- **FastAPI** — serves `/ask`, `/healthz`, and `/readyz` endpoints.  
- **Azure OpenAI** — provides embeddings and LLM completions.  
- **LangChain** — integrates embeddings and vector search.  
- **Azure Cognitive Search** — performs similarity search on stored embeddings.  
- **Prometheus metrics** — optional, for monitoring response times and health.

---

## 📁 Project Structure

```azure-rag-llmops-end-to-end/
│
├── webapp/ # Main FastAPI application
│ ├── main.py # Core app logic and routes
│ └── init.py
│
├── ingest/ # (Optional) Data ingestion scripts for embeddings
│
├── data/ # Example CSVs or text data
│
├── test/ # Unit and integration tests (pytest)
│ ├── test_core.py
│ ├── test_health.py
│ └── test_integration.py
│
├── .github/workflows/ # GitHub Actions CI/CD (to be added later)
│
├── Dockerfile # Container image definition
├── pyproject.toml # Dependencies and build configuration
├── quickcheck.py # Quick local testing script
└── README.md
```

