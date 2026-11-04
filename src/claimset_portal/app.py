"""The web application: one FastAPI app serving the API, consent pages, search and (later) the MCP server.

Published files (`/p/...`, `/index.jsonl`, `/llms.txt`) are static and served by Caddy from the published
directory; the app does not serve them in production.
"""

from contextlib import asynccontextmanager
from importlib import resources

import claimset
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from . import __version__
from .config import Settings
from .db import make_pool


def create_app(settings=None, pool=None):
    """The app. `pool` may be given (tests); otherwise one is made from the settings and opened on startup."""
    settings = settings or Settings.from_env()
    own_pool = pool is None
    pool = pool or make_pool(settings.database_url, min_size=1, max_size=10)

    @asynccontextmanager
    async def lifespan(app):
        if own_pool:
            pool.open()
        try:
            yield
        finally:
            if own_pool:
                pool.close()

    app = FastAPI(title="LibLM", version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.settings = settings
    app.state.pool = pool

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        """Liveness and readiness: the app runs and the database answers."""
        body = {"portal": __version__, "claimset": claimset.__version__, "spec": claimset.SPEC_VERSION}
        try:
            with pool.connection(timeout=2) as conn:
                conn.execute("SELECT 1")
            body["database"] = "ok"
            return body
        except Exception as exc:  # noqa: BLE001 - any failure means not ready
            body["database"] = f"unavailable: {type(exc).__name__}"
            return JSONResponse(body, status_code=503)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return (resources.files("claimset_portal") / "static" / "index.html").read_text(encoding="utf-8")

    return app
