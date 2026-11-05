"""Publication (design §4.2 steps 6–7, §5): from a validated submission to a version in the registry.

    publish(source, ...) -> (concept id, version)

`source` is a submission package (a BagIt zip or folder, claimset spec §2.5) or a claimset file. Consent and the
registry pull request come in later steps; this is the part they all end in:

1. validate the submission with the `claimset` package (rules of every file, submission rules, rules 70 and 77);
2. the claimset is classified; then a new claimset gets the next `entrylib:` identifier (only once the classifier
   has answered, so an outage uses up no numbers), while a correction names an existing one (claimset spec §9);
3. packaged files are stored by checksum and their relative `uri` replaced with the permanent URL;
4. the platform's fields are added: identifier, version, date, status, classification, verifiability, and for a
   correction previous_version, changes and the status notice;
5. the result is validated as a published file; it must pass;
6. the version is written to the registry (claimset.json, lab.jsonl, validation.json), committed and tagged;
7. the version is indexed: database rows and static files.
"""

import copy
import datetime as dt
import json
import tempfile
import zipfile
from pathlib import Path

import claimset
from claimset.revision import raw_patch
from claimset.validate import (
    is_relative_uri,
    local_targets,
    validate,
    validate_path,
)

from . import ids
from .indexer import index_version
from .registry import dump


class PublishError(Exception):
    """The submission cannot be published; `errors` holds the validator's errors (rule, where, message)."""

    def __init__(self, message, errors=()):
        super().__init__(message)
        self.errors = list(errors)


def _bag_root(path, tmp):
    """The folder holding bagit.txt and data/, unpacking a zip into tmp (rule 77 has already checked it)."""
    p = Path(path)
    if p.is_file() and zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            z.extractall(tmp)
        p = Path(tmp)
        inner = [d for d in p.iterdir() if d.is_dir()]
        if not (p / "bagit.txt").exists() and len(inner) == 1:
            p = inner[0]
    return p


def load_submission(source, tmp):
    """(document, payload folder or None) of a submission, after it has passed validation."""
    p = Path(source)
    if p.is_dir() or (p.is_file() and zipfile.is_zipfile(p)):
        root = _bag_root(p, tmp)
        files = sorted((root / "data").glob("*.claimset.json")) or sorted((root / "data").glob("*.json"))
        return json.loads(files[0].read_text(encoding="utf-8")), root / "data"
    return json.loads(p.read_text(encoding="utf-8")), None


def _errors(rep):
    return [{"rule": e["rule"], "where": e["where"], "message": e["message"]} for e in rep.errors]


def publish(source, *, conn, registry, store, classifier, published_dir, base_url, today=None):
    """Publish a submission. Returns (concept id, version). Raises PublishError if it cannot be published."""
    today = today or dt.date.today()
    rep = validate_path(str(source))
    if rep is None:
        raise PublishError(f"cannot read {source}")
    if rep.errors:
        raise PublishError(f"the submission is not valid: {len(rep.errors)} error(s)", _errors(rep))
    with tempfile.TemporaryDirectory() as tmp:
        doc, payload = load_submission(source, tmp)
        if local_targets(doc):
            raise PublishError("references to unpublished papers of the author's repository (id_type "
                               "claimset_local) cannot be published yet; publish the cited paper first and cite "
                               "it by its identifier")
        paper = doc["paper"]

        # 2. identifier and version
        if "id" in paper:
            concept = paper["id"]
            row = conn.execute("SELECT folder, current_version FROM papers WHERE concept_id = %s",
                               (concept,)).fetchone()
            if row is None:
                raise PublishError(f"a correction names {concept}, which is not published here")
            folder, previous_n = row
            previous = registry.read(folder, previous_n)
            version = previous_n + 1
        else:
            concept = folder = previous = None
            version = 1

        # Classify before a new identifier is given out: the classifier is the step most likely to be unavailable,
        # and a number given out is never given again.
        cls = classifier(doc)
        if concept is None:
            concept = ids.allocate(conn, today.year)
            folder = ids.folder(concept)

        # 3. packaged files
        published = copy.deepcopy(doc)
        lab_copy = None
        for a in published.get("artefacts") or []:
            if isinstance(a, dict) and is_relative_uri(a.get("uri")):
                f = payload / a["uri"]
                digest, url = store.put(f)
                if a.get("kind") == "lab_record" and lab_copy is None:
                    lab_copy = f.read_text(encoding="utf-8")
                a["uri"] = url
                a["version"] = f"sha256:{digest}"

        # 4. platform fields
        p = published["paper"]
        p["id"] = concept
        p["version"] = version
        p["date"] = today.isoformat()
        p["classification"] = {**(p.get("classification") or {}), "subfield": cls.subfield,
                               "topics": list(cls.topics)}
        for c in published.get("claims") or []:
            computed = rep.computed.get(c.get("id")) if isinstance(c, dict) else None
            if computed:
                c["verifiability"] = computed["verifiability"]
                c["verifiability_flags"] = computed["verifiability_flags"]
        if previous is None:
            p["status"] = "active"
        else:
            reason = p.get("correction_reason", "")
            p["status"] = "corrected"
            p["previous_version"] = f"{concept}@v{version - 1}"
            p["status_notice"] = {"date": today.isoformat(), "reason_code": "correction", "statement": reason,
                                  "issued_by": "platform"}
            changes = [{**op, "reason": reason} for op, _ in raw_patch(previous, published)]
            if not changes:
                raise PublishError("the correction changes nothing in the claimset")
            p["changes"] = changes

        # 5. the published file must be valid
        check = validate(published, published=True)
        if check.errors:
            raise PublishError("the published file would not be valid; this is a fault of the portal",
                               _errors(check))

        # 6. registry
        validation = {"validator": f"claimset {claimset.__version__}", "spec": claimset.SPEC_VERSION,
                      "submission": {"errors": [], "warnings": [{"rule": w["rule"], "where": w["where"],
                                                                 "message": w["message"]} for w in rep.warnings]},
                      "classifier": cls.classifier}
        files = {"claimset.json": dump(published), "validation.json": dump(validation)}
        if lab_copy is not None:
            files["lab.jsonl"] = lab_copy
        registry.write_version(folder, version, files, f"Publish {concept}@v{version}")

    # 7. index
    index_version(conn, registry, folder, version, published_dir, base_url)
    return concept, version
