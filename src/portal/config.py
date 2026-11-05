"""Settings, read from the environment. Secrets live only in the environment, never in the repository."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    #: PostgreSQL connection string (libpq form or URL).
    database_url: str
    #: The public address of the portal, without a trailing slash: used in links the portal writes.
    base_url: str
    #: Where published static files (JSON, reading views, index) are written; Caddy serves them.
    published_dir: Path
    #: "development" or "production".
    environment: str
    #: The local clone of the registry (revision spec §2.4).
    registry_dir: Path
    #: Pending submissions and uploads in progress. Not public.
    submissions_dir: Path
    #: The classifier service.
    classifier_url: str
    #: The name and address the registry's commits are made under.
    git_name: str
    git_email: str
    #: ORCID: https://sandbox.orcid.org for testing, https://orcid.org in production.
    orcid_base: str = "https://sandbox.orcid.org"
    orcid_client_id: str = ""
    #: Secret: from the environment only.
    orcid_client_secret: str = field(default="", repr=False)
    #: "local": publish straight to the local registry clone (development, tests). "github": publish through pull
    #: requests on the registry repository, as the GitHub App (design §5).
    registry_mode: str = "local"
    github_registry: str = "entrylib/registry"
    github_api: str = "https://api.github.com"
    github_app_id: str = ""
    #: The App's private key: a file path (preferred), or its PEM text. Secret.
    github_app_private_key_file: str = ""
    github_app_private_key: str = field(default="", repr=False)

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            database_url=env.get("DATABASE_URL", "postgresql://portal:portal@localhost:5432/portal"),
            base_url=env.get("PORTAL_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            published_dir=Path(env.get("PORTAL_PUBLISHED_DIR", "./published")),
            environment=env.get("PORTAL_ENV", "development"),
            registry_dir=Path(env.get("PORTAL_REGISTRY_DIR", "./registry")),
            submissions_dir=Path(env.get("PORTAL_SUBMISSIONS_DIR", "./submissions")),
            classifier_url=env.get("PORTAL_CLASSIFIER_URL", "http://localhost:8001"),
            git_name=env.get("PORTAL_GIT_NAME", "EntryLib"),
            git_email=env.get("PORTAL_GIT_EMAIL", "registry@entrylib.org"),
            orcid_base=env.get("ORCID_BASE", "https://sandbox.orcid.org").rstrip("/"),
            orcid_client_id=env.get("ORCID_CLIENT_ID", ""),
            orcid_client_secret=env.get("ORCID_CLIENT_SECRET", ""),
            registry_mode=env.get("PORTAL_REGISTRY_MODE", "local"),
            github_registry=env.get("GITHUB_REGISTRY", "entrylib/registry"),
            github_api=env.get("GITHUB_API", "https://api.github.com").rstrip("/"),
            github_app_id=env.get("GITHUB_APP_ID", ""),
            github_app_private_key_file=env.get("GITHUB_APP_PRIVATE_KEY_FILE", ""),
            github_app_private_key=env.get("GITHUB_APP_PRIVATE_KEY", ""),
        )
