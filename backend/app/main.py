from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, movements, operators, ota, products, reports, users, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SorvPel - Controle de Estoque",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.include_router(auth.router)
app.include_router(web.router)
app.include_router(users.router)
app.include_router(operators.router)
app.include_router(products.router)
app.include_router(movements.router)
app.include_router(reports.router)
app.include_router(ota.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "Não autenticado"})
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
