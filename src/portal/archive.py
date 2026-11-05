"""Software Heritage save requests (design §5.2): the registry, and the author's public repositories that a version
links to, are archived with their history so they survive deletion. Best effort: a failed request is logged and
does not hold publication up.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("portal")

SAVE_API = "https://archive.softwareheritage.org/api/1/origin/save/git/url/{url}/"
#: Public git hosts whose repository root can be read from a link into it.
REPO_ROOT = re.compile(r"^(https://(?:github\.com|gitlab\.com|codeberg\.org)/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)"
                       r"(?:\.git)?(?:/|$)")


def repositories(doc):
    """The repository roots a published file links to through its artefacts."""
    roots = []
    for a in doc.get("artefacts") or []:
        if isinstance(a, dict) and isinstance(a.get("uri"), str):
            m = REPO_ROOT.match(a["uri"])
            if m and m.group(1) not in roots:
                roots.append(m.group(1))
    return roots


def save(url, timeout=20, opener=urllib.request.urlopen):
    """Ask Software Heritage to archive the git repository at `url`. Returns its answer, or None on failure."""
    req = urllib.request.Request(SAVE_API.format(url=urllib.parse.quote(url, safe=":/")), method="POST",
                                 headers={"Accept": "application/json", "User-Agent": "entrylib-portal"})
    try:
        with opener(req, timeout=timeout) as res:
            out = json.loads(res.read() or b"{}")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.warning("Software Heritage save request for %s failed: %s", url, exc)
        return None
    log.info("Software Heritage save request for %s: %s", url, out.get("save_request_status"))
    return out


def archive_version(doc, registry_url, save_fn=save):
    """Save requests for the registry and every repository the version links to."""
    return {url: save_fn(url) for url in [registry_url, *repositories(doc)]}
