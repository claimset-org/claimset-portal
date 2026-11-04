"""The web application: one FastAPI app serving the API, consent pages, search and (later) the MCP server.

Published files (`/p/...`, `/index.jsonl`, `/llms.txt`, `/files/...`) are static and served by Caddy from the
published directory; the app does not serve them in production.
"""

import asyncio
import contextlib
import ipaddress
import logging
import tempfile
from contextlib import asynccontextmanager
from importlib import resources
from pathlib import Path

import claimset
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from . import __version__, submissions
from .config import Settings
from .db import make_pool

log = logging.getLogger("claimset_portal")

#: How often pending submissions past their consent window are deleted.
EXPIRY_INTERVAL_SECONDS = 600


class UploadTooLarge(Exception):
    pass


async def _save_body(request, directory):
    """Stream the request body to a temporary file, refusing more than MAX_UPLOAD_BYTES."""
    directory.mkdir(parents=True, exist_ok=True)
    fh = tempfile.NamedTemporaryFile(dir=directory, prefix="upload-", delete=False)
    size = 0
    try:
        async for chunk in request.stream():
            size += len(chunk)
            if size > submissions.MAX_UPLOAD_BYTES:
                raise UploadTooLarge
            fh.write(chunk)
    except BaseException:
        fh.close()
        Path(fh.name).unlink(missing_ok=True)
        raise
    fh.close()
    return Path(fh.name), size


def _error(status, message, errors=(), warnings=()):
    return JSONResponse({"error": message, "errors": list(errors), "warnings": list(warnings)}, status_code=status)


def create_app(settings=None, pool=None, run_expiry=True):
    """The app. `pool` may be given (tests); otherwise one is made from the settings and opened on startup."""
    settings = settings or Settings.from_env()
    own_pool = pool is None
    pool = pool or make_pool(settings.database_url, min_size=1, max_size=10)
    uploads = settings.submissions_dir / "incoming"

    def expire_now():
        with pool.connection() as conn:
            return submissions.expire(conn, settings.submissions_dir)

    async def expiry_loop():
        while True:
            try:
                expired = await run_in_threadpool(expire_now)
                if expired:
                    log.info("expired %d submission(s)", len(expired))
            except Exception:  # noqa: BLE001 - keep the loop alive; the next round retries
                log.exception("expiring submissions failed")
            await asyncio.sleep(EXPIRY_INTERVAL_SECONDS)

    @asynccontextmanager
    async def lifespan(app):
        if own_pool:
            pool.open()
        task = asyncio.create_task(expiry_loop()) if run_expiry else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
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

    @app.post("/api/validate", tags=["submissions"])
    async def validate(request: Request):
        """Check a claimset file (JSON) or a submission package (BagIt zip), sent as the request body, exactly as a
        submission is checked. Nothing is kept. Always 200: `valid` says whether it would be accepted."""
        try:
            path, _ = await _save_body(request, uploads)
        except UploadTooLarge:
            return _error(413, f"larger than {submissions.MAX_UPLOAD_BYTES} bytes")
        try:
            result = await run_in_threadpool(submissions.check, path)
        finally:
            path.unlink(missing_ok=True)
        return result.as_json()

    @app.post("/api/submissions", status_code=201, tags=["submissions"])
    async def submit(request: Request):
        """Submit a claimset file (JSON) or a submission package (BagIt zip, `claimset package`) as the request body:
        `curl --data-binary @paper.zip -H 'Content-Type: application/zip' <portal>/api/submissions`.

        A valid submission is held for 48 hours. The response gives one consent link per guarantor: pass each to
        its guarantor, who signs in with ORCID and confirms. The links are shown only in this response. Once every
        guarantor has confirmed, the claimset is published."""
        try:
            path, _ = await _save_body(request, uploads)
        except UploadTooLarge:
            return _error(413, f"larger than {submissions.MAX_UPLOAD_BYTES} bytes")
        client = request.client.host if request.client else None
        try:
            client = str(ipaddress.ip_address(client)) if client else None
        except ValueError:                                  # not an address (the test client): no per-address cap
            client = None

        def work():
            with pool.connection() as conn:
                return submissions.receive(conn, path, submissions_dir=settings.submissions_dir,
                                           base_url=settings.base_url, client_ip=client)
        try:
            return await run_in_threadpool(work)
        except submissions.SubmissionError as exc:
            return _error(exc.status, str(exc), exc.errors, exc.warnings)
        finally:
            path.unlink(missing_ok=True)

    @app.get("/api/submissions/{sub_id}", tags=["submissions"])
    def submission_status(sub_id: str):
        """The state of a submission: pending, confirmed, published (with its identifier), refused or expired."""
        with pool.connection() as conn:
            out = submissions.status(conn, sub_id, settings.base_url)
        if out is None:
            return _error(404, "no such submission (submissions are forgotten 14 days after they close)")
        return out

    return app
