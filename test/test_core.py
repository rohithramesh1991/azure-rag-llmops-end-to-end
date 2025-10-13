from types import SimpleNamespace
from webapp.services import rag

def test_retrieve_context_returns_first_result(monkeypatch):
    class StubDoc:
        def __init__(self, text: str):
            self.page_content = text

    class StubVS:
        def similarity_search_with_relevance_scores(self, query: str, k: int = 5):
            return [(StubDoc("hello world"), 0.9)]

    # IMPORTANT: patch the symbol used inside rag.py
    monkeypatch.setattr(rag, "get_vectorstore", lambda: StubVS())

    result = rag.retrieve("some query")
    assert result == "hello world"


def test_llm_answer_extracts_message(monkeypatch):
    def fake_create(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    class StubCompletions:
        def create(self, **kwargs):
            return fake_create(**kwargs)

    class StubChat:
        completions = StubCompletions()

    class StubOAI:
        chat = StubChat()

    # IMPORTANT: patch the symbol used inside rag.py
    monkeypatch.setattr(rag, "get_oai_client", lambda: StubOAI())

    result = rag.answer("question", "context")
    assert result == "ok"
