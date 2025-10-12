# test/test_core.py
from types import SimpleNamespace
from webapp import main

def test_retrieve_context_returns_first_result(monkeypatch):
    class StubDoc:
        def __init__(self, text: str) -> None:
            self.page_content = text

    class StubVS:
        def similarity_search_with_relevance_scores(self, query: str, k: int = 5):
            # return [(Document, score), ...]
            return [(StubDoc("hello world"), 0.9)]

    # Replace the global vector store with our stub
    monkeypatch.setattr(main, "_vs", StubVS())

    assert main.retrieve_context("x") == "hello world"


def test_llm_answer_extracts_message(monkeypatch):
    # Patch the OpenAI chat call to avoid hitting the network
    def fake_create(**kwargs):
        # shape compatible with main.coerce_content_to_text()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    # Patch the bound method on the already-created client
    monkeypatch.setattr(main._oai.chat.completions, "create", fake_create)

    assert main.llm_answer("q", "c") == "ok"
