"""Claimset identifiers (claimset spec §7): the platform's provisional identifier `liblm:<year>.<number>`."""

import re

from claimset.revision import record_folder
from claimset.validate import CLAIMSET_ID_RE

PREFIX = "liblm:"
_KEY_RE = re.compile(r"(\d{4})\.(\d{6,})$")


def make_id(year, number):
    return f"{PREFIX}{year}.{number:06d}"


def allocate(conn, year):
    """The next identifier for `year`. Runs in its own statement, so a number is never handed out twice."""
    row = conn.execute(
        "INSERT INTO id_counters (year, last) VALUES (%s, 1) "
        "ON CONFLICT (year) DO UPDATE SET last = id_counters.last + 1 RETURNING last", (year,)).fetchone()
    return make_id(year, row[0])


def year_number(concept_id):
    """(year, number) of a claimset identifier, DOI or provisional."""
    if not CLAIMSET_ID_RE.match(concept_id or ""):
        raise ValueError(f"not a claimset identifier: {concept_id!r}")
    m = _KEY_RE.search(concept_id)
    return int(m.group(1)), int(m.group(2))


def url_key(concept_id):
    """The part of the portal's URLs that names a claimset: `2026.000001` (/p/2026.000001.json)."""
    year, number = year_number(concept_id)
    return f"{year}.{number:06d}"


def folder(concept_id):
    """The claimset's registry folder (revision spec §2.4)."""
    return record_folder(concept_id)
