"""`claimset-portal`: run the portal and its maintenance commands.

    claimset-portal migrate                 apply database migrations
    claimset-portal serve [--port 8000]     run the web app (after migrating)
    claimset-portal publish SUBMISSION      publish a validated submission (package or claimset file) directly,
                                            without consent: for administration and tests, never for authors
    claimset-portal reindex                 rebuild the database index and static files from the registry
"""

import argparse
import json
import sys

from .config import Settings
from .db import migrate


def _context(settings):
    from .classify import HttpClassifier
    from .registry import Registry
    from .storage import FileStore
    registry = Registry(settings.registry_dir, settings.git_name, settings.git_email)
    if not settings.registry_dir.exists():
        registry.init()
    return registry, FileStore(settings.published_dir, settings.base_url), HttpClassifier(settings.classifier_url)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="claimset-portal")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    serve = sub.add_parser("serve", help="apply migrations, then run the web app")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    pub = sub.add_parser("publish", help="publish a submission directly, without consent (administration, tests)")
    pub.add_argument("submission", help="a submission package (BagIt zip or folder) or a claimset file")
    sub.add_parser("reindex", help="rebuild the database index and static files from the registry")
    args = parser.parse_args(argv)
    settings = Settings.from_env()

    applied = migrate(settings.database_url)
    for name in applied:
        print(f"applied {name}")
    if args.command == "migrate":
        if not applied:
            print("database is up to date")
        return 0

    if args.command in ("publish", "reindex"):
        import psycopg

        from .indexer import reindex
        from .publish import PublishError, publish
        registry, store, classifier = _context(settings)
        with psycopg.connect(settings.database_url, autocommit=True) as conn:
            if args.command == "reindex":
                folders = reindex(conn, registry, settings.published_dir, settings.base_url)
                print(f"reindexed {len(folders)} claimset(s)")
                return 0
            try:
                concept, version = publish(args.submission, conn=conn, registry=registry, store=store,
                                           classifier=classifier, published_dir=settings.published_dir,
                                           base_url=settings.base_url)
            except PublishError as exc:
                print(f"NOT PUBLISHED: {exc}", file=sys.stderr)
                for e in exc.errors:
                    print("  " + json.dumps(e, ensure_ascii=False), file=sys.stderr)
                return 1
            print(f"published {concept}@v{version}")
            return 0

    import uvicorn

    from .app import create_app
    uvicorn.run(create_app(settings), host=args.host, port=args.port, proxy_headers=True,
                forwarded_allow_ips="*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
