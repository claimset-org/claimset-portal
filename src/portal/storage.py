"""Packaged files, stored by checksum (claimset spec §2.5): a file kept by several versions is stored once.

For now the store is a folder (`<published>/files/<sha256>`) served by Caddy as downloads; object storage takes
its place later behind the same two methods.
"""

import hashlib
import os
import shutil
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class FileStore:
    def __init__(self, root, base_url):
        self.root = Path(root)
        self.base_url = base_url.rstrip("/")

    def url(self, digest):
        return f"{self.base_url}/files/{digest}"

    def put(self, path):
        """Store a file; returns (sha256 hex digest, permanent URL)."""
        digest = sha256_file(path)
        dest = self.root / "files" / digest
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".tmp")
            shutil.copyfile(path, tmp)
            os.replace(tmp, dest)
        return digest, self.url(digest)
