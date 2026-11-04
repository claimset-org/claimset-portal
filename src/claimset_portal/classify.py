"""Classification (claimset spec §3.1, PLT-24): the OpenAlex subfield and 1–3 topics of a claimset.

The classifier service (`classifier/`) runs OpenAlex's open topic model on the claimset's title and principal
claims, the claimset's abstract by design, with its keywords as a hint. The portal talks to it over HTTP.
"""

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    subfield: str          # openalex:subfields/1702
    topics: tuple          # (openalex:T10001, ...), 1 to 3
    classifier: str        # which model and version assigned them


def classifier_input(doc):
    """What the classifier reads: the title, and as the abstract the principal claims with the keywords."""
    paper = doc.get("paper") or {}
    claims = {c.get("id"): c for c in doc.get("claims") or [] if isinstance(c, dict)}
    principal = [claims[c].get("statement", "") for c in paper.get("contributions") or [] if c in claims]
    keywords = (paper.get("classification") or {}).get("keywords") or []
    text = " ".join(principal)
    if keywords:
        text += " Keywords: " + "; ".join(keywords) + "."
    return {"title": paper.get("title", ""), "abstract": text}


class ClassifierError(Exception):
    pass


class HttpClassifier:
    """The classifier service: POST /classify {title, abstract} -> {subfield, topics, classifier}."""

    def __init__(self, url, timeout=30):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def __call__(self, doc):
        body = json.dumps(classifier_input(doc)).encode()
        req = urllib.request.Request(f"{self.url}/classify", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                out = json.loads(res.read())
        except OSError as exc:
            raise ClassifierError(f"classifier unavailable: {exc}") from exc
        topics = tuple(out.get("topics") or ())[:3]
        if not out.get("subfield") or not topics:
            raise ClassifierError(f"classifier returned no subfield or topics: {out}")
        return Classification(out["subfield"], topics, out.get("classifier", "unknown"))
