import claimset
from fastapi.testclient import TestClient

from claimset_portal import __version__
from claimset_portal.app import create_app
from claimset_portal.config import Settings
from claimset_portal.db import make_pool


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"portal": __version__, "claimset": claimset.__version__, "spec": claimset.SPEC_VERSION,
                        "database": "ok"}


def test_healthz_reports_an_unreachable_database():
    url = "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1"
    pool = make_pool(url, min_size=0, max_size=1)
    pool.open()
    try:
        with TestClient(create_app(Settings.from_env({"DATABASE_URL": url}), pool=pool)) as c:
            r = c.get("/healthz")
        assert r.status_code == 503
        assert r.json()["database"].startswith("unavailable")
    finally:
        pool.close()


def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "EntryLib" in r.text and "/llms.txt" in r.text


def test_api_docs(client):
    assert client.get("/api/openapi.json").status_code == 200
