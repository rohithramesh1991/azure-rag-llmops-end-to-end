# webapp/metrics.py
from time import perf_counter
from typing import Optional
from prometheus_client import Counter, Histogram

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    labelnames=("provider", "model", "status"),  # status in {"success","error"}
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens",
    labelnames=("provider", "model", "role"),    # role in {"prompt","completion"}
)
LLM_ERRORS = Counter(
    "llm_errors_total",
    "Total LLM request errors",
    labelnames=("provider", "model", "error_type"),
)
LLM_LATENCY = Histogram(
    "llm_request_seconds",
    "LLM request latency in seconds",
    labelnames=("provider", "model"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Total estimated LLM cost in USD",
    labelnames=("provider", "model"),
)

class LLMCallTimer:
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self._t0: Optional[float] = None

    def __enter__(self):
        self._t0 = perf_counter()
        return self

    def record_success(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0):
        LLM_REQUESTS.labels(self.provider, self.model, "success").inc()
        LLM_TOKENS.labels(self.provider, self.model, "prompt").inc(prompt_tokens or 0)
        LLM_TOKENS.labels(self.provider, self.model, "completion").inc(completion_tokens or 0)
        if cost_usd:
            LLM_COST_USD.labels(self.provider, self.model).inc(cost_usd)
        if self._t0 is not None:
            LLM_LATENCY.labels(self.provider, self.model).observe(perf_counter() - self._t0)

    def record_error(self, error_type: str = "exception"):
        LLM_REQUESTS.labels(self.provider, self.model, "error").inc()
        LLM_ERRORS.labels(self.provider, self.model, error_type).inc()
        if self._t0 is not None:
            LLM_LATENCY.labels(self.provider, self.model).observe(perf_counter() - self._t0)

    def __exit__(self, exc_type, exc, tb):
        if self._t0 is not None:
            LLM_LATENCY.labels(self.provider, self.model).observe(perf_counter() - self._t0)
        return False
