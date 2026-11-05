"""The registry: a git repository holding the published record (revision spec §2.4).

    <folder>/v1/claimset.json  v1/lab.jsonl  v1/validation.json
    <folder>/v2/claimset.json  ...

Only the platform writes to it, one commit per published version, tagged `<folder>-v<n>`. This module works on a
local clone; pushing to the hosted registry happens elsewhere.
"""

import json
import os
import re
import subprocess
from pathlib import Path

VERSION_DIR = re.compile(r"^v([1-9]\d*)$")


class RegistryError(Exception):
    pass


def dump(obj):
    """How the registry writes JSON: stable, readable, UTF-8."""
    return json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


class Registry:
    def __init__(self, path, author_name="EntryLib", author_email="registry@entrylib.org"):
        self.path = Path(path)
        self.env = {**os.environ, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email,
                    "GIT_COMMITTER_NAME": author_name, "GIT_COMMITTER_EMAIL": author_email}

    def git(self, *args):
        res = subprocess.run(["git", "-C", str(self.path), *args], env=self.env, capture_output=True, text=True)
        if res.returncode != 0:
            raise RegistryError(f"git {' '.join(args)}: {res.stderr.strip()}")
        return res.stdout

    def init(self):
        """Create an empty registry (for tests and a first setup)."""
        self.path.mkdir(parents=True, exist_ok=True)
        if not (self.path / ".git").exists():
            self.git("init", "-q", "-b", "main")
        return self

    def version_dir(self, folder, n):
        return self.path / folder / f"v{n}"

    def versions(self, folder):
        """The version numbers present for a claimset, in order."""
        d = self.path / folder
        if not d.is_dir():
            return []
        return sorted(int(m.group(1)) for p in d.iterdir() if p.is_dir() and (m := VERSION_DIR.match(p.name)))

    def folders(self):
        """Every claimset folder in the registry."""
        return sorted(p.name for p in self.path.iterdir()
                      if p.is_dir() and not p.name.startswith(".") and self.versions(p.name))

    def read(self, folder, n, name="claimset.json"):
        return json.loads((self.version_dir(folder, n) / name).read_text(encoding="utf-8"))

    def write_version(self, folder, n, files, message):
        """Write one version's documents ({name: text}) and commit them with the tag `<folder>-v<n>`.
        A version that exists is never overwritten."""
        d = self.version_dir(folder, n)
        if d.exists():
            raise RegistryError(f"{folder}/v{n} exists; published versions are never rewritten")
        d.mkdir(parents=True)
        for name, text in files.items():
            (d / name).write_text(text, encoding="utf-8")
        self.git("add", "--", f"{folder}/v{n}")
        self.git("commit", "-q", "-m", message)
        self.git("tag", f"{folder}-v{n}")
        return d
