from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
import uuid
import logging

from webapp.config import settings

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag-api")

# -----------------------------------------------------------------------------
# Create FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="RAG LLMOps API", version="1.0.0")

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
@app.middleware("http")
async def add_request_id_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled_error request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(status_code=500, content={"error": "internal_error", "request_id": request_id})
    response.headers["x-request-id"] = request_id
    log.info("%s %s -> %s request_id=%s", request.method, request.url.path, response.status_code, request_id)
    return response

# -----------------------------------------------------------------------------
# Routes from api.py
# -----------------------------------------------------------------------------
from webapp.api import router as api_router
app.include_router(api_router)

@app.get("/")
def root():
    return RedirectResponse(url="/docs", status_code=301)

# -----------------------------------------------------------------------------
# Prometheus /metrics endpoint
# -----------------------------------------------------------------------------
Instrumentator().instrument(app).expose(app)

# -----------------------------------------------------------------------------
# Entry point for Uvicorn / Gunicorn
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp.main:app", host="0.0.0.0", port=8000, reload=True)
