"""`claimset-portal`: run the portal and its maintenance commands.

    claimset-portal migrate               apply database migrations
    claimset-portal serve [--port 8000]   run the web app (after migrating)
"""

import argparse
import sys

from .config import Settings
from .db import migrate


def main(argv=None):
    parser = argparse.ArgumentParser(prog="claimset-portal")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    serve = sub.add_parser("serve", help="apply migrations, then run the web app")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    settings = Settings.from_env()

    applied = migrate(settings.database_url)
    for name in applied:
        print(f"applied {name}")
    if args.command == "migrate":
        if not applied:
            print("database is up to date")
        return 0

    import uvicorn

    from .app import create_app
    uvicorn.run(create_app(settings), host=args.host, port=args.port, proxy_headers=True,
                forwarded_allow_ips="*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
