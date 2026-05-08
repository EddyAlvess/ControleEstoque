import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.logging_config import get_logger, setup_logging
from app.routers import (
    auth, categories, movements, operators, ota,
    products, reports, settings as settings_router,
    shifts, users, web,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_DIR)
    Path("app/static/logos").mkdir(parents=True, exist_ok=True)

    from app.database import AsyncSessionLocal
    from app.services.settings_service import settings_cache
    async with AsyncSessionLocal() as db:
        await settings_cache.reload(db)

    yield


app = FastAPI(
    title="InventControl - Controle de Estoque",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(web.router)
app.include_router(users.router)
app.include_router(operators.router)
app.include_router(products.router)
app.include_router(movements.router)
app.include_router(reports.router)
app.include_router(categories.router)
app.include_router(shifts.router)
app.include_router(ota.router)
app.include_router(settings_router.router)


_api_log = get_logger("api")
_err_log = get_logger("errors")


@app.middleware("http")
async def http_logging_middleware(request: Request, call_next):
    request_id = uuid4().hex[:8]
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    status_code = response.status_code

    extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": status_code,
        "duration_ms": duration_ms,
        "ip": request.client.host if request.client else "-",
        "ua": request.headers.get("user-agent", "-")[:120],
    }

    if status_code >= 500:
        _err_log.error("server_error", extra=extra)
    elif request.url.path != "/health":
        _api_log.info("request", extra=extra)

    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=401, content={"detail": "Não autenticado"})
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
