"""Safe-ingest screening, deterministic part (design §6, PLT-18).

LibLM exists to put submitted text into other models' contexts, so every text field is screened for content
addressed to reading models. These rules are cheap and run on every submission; the LLM classifier runs later, only
after consent. The rules are public and versioned: a published version records the screening version that passed it.
The `claimset` validator has its own, narrower check (error `safe-ingest`); these rules add to it at the door. Codes
are SI1–SI4, apart from the validator's rule numbers and its S warnings.

    SI1 invisible or direction-changing characters (Unicode format characters, tag characters)
    SI2 text addressed to a reading model: role markers, "ignore previous instructions" and the like
    SI3 long encoded runs (base64-like) in text
    SI4 links in claim statements: a statement is a self-contained assertion, never a pointer
"""

import re
import unicodedata

SCREENING_VERSION = "screening-1"

#: Fields that hold identifiers, links, hashes or codes rather than prose: S2 and S3 do not apply to them.
NON_PROSE_FIELDS = {"id", "uri", "archive_uri", "target", "version", "content_hash", "orcid", "ror", "identifiers",
                    "source_id", "registration", "licence", "code_version", "identifier", "weights", "locator"}

_MODEL_ADDRESSED = [
    r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|preceding|earlier)\s+(?:instructions|prompts?|rules)",
    r"\bdisregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|preceding|earlier|your)\b",
    r"\b(?:forget|override)\s+(?:all\s+|your\s+)?(?:previous\s+)?(?:instructions|rules|guidelines)",
    r"\byou\s+are\s+(?:now\s+)?(?:an?\s+|the\s+)?(?:ai|assistant|language\s+model|llm|chatbot|reviewer|grader)\b",
    r"\bas\s+an?\s+(?:ai|language\s+model)\b",
    r"\b(?:system|developer)\s+prompt\b",
    r"\bnote\s+to\s+(?:the\s+)?(?:ai|model|llm|assistant|reviewer|reader\s+model)\b",
    r"\b(?:to|for)\s+(?:any|the)\s+(?:ai|llm|language\s+model|model)\s+(?:reading|reviewing|processing)\b",
    r"\b(?:rate|score|rank|grade)\s+(?:this|the)\s+(?:paper|claimset|claim|work)\s+(?:as|highly|above|10|100)\b",
    r"\b(?:do\s+not|don't)\s+(?:mention|reveal|tell|disclose)\s+(?:this|that|the)\b",
    r"<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>",
    r"\[/?INST\]|<<SYS>>|<</SYS>>",
    r"(?:^|\n)\s*(?:###\s*)?(?:system|assistant|user|human)\s*:",
]
_MODEL_ADDRESSED_RE = re.compile("|".join(f"(?:{p})" for p in _MODEL_ADDRESSED), re.IGNORECASE)
_ENCODED_RE = re.compile(r"[A-Za-z0-9+/=_-]{120,}")
_LINK_RE = re.compile(r"\b(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|org|net|io|ai|xyz)/\S*", re.IGNORECASE)


def _strings(obj, path="", key=None):
    """(path, field name, text) for every string in a JSON value."""
    if isinstance(obj, str):
        yield path, key, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}" if path else k, k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            label = v.get("id") if isinstance(v, dict) and isinstance(v.get("id"), str) else str(i)
            yield from _strings(v, f"{path}:{label}" if isinstance(v, dict) else f"{path}[{i}]", key)


#: Format characters that ordinary text needs: zero-width non-joiner and joiner (Persian, Hindi and other scripts,
#: emoji sequences) and the soft hyphen. Every other format character is flagged (SI1).
ALLOWED_FORMAT = {"\u200c", "\u200d", "\u00ad"}


def _invisible(text):
    for ch in text:
        if (unicodedata.category(ch) == "Cf" and ch not in ALLOWED_FORMAT) or 0xE0000 <= ord(ch) <= 0xE007F:
            return f"U+{ord(ch):04X} ({unicodedata.name(ch, 'unnamed')})"
    return None


def screen(doc):
    """[{rule, where, message}]: every finding, each blocking publication."""
    findings = []
    for path, key, text in _strings(doc):
        bad = _invisible(text)
        if bad:
            findings.append({"rule": "SI1", "where": path,
                             "message": f"invisible or direction-changing character {bad}; remove it"})
        if key in NON_PROSE_FIELDS:
            continue
        m = _MODEL_ADDRESSED_RE.search(text)
        if m:
            findings.append({"rule": "SI2", "where": path,
                             "message": f"text addressed to a reading model ({m.group(0).strip()!r}); a claimset is "
                                        f"data for models, never instructions to them"})
        if _ENCODED_RE.search(text):
            findings.append({"rule": "SI3", "where": path,
                             "message": "a long encoded run (120 or more characters without spaces); put data in an "
                                        "artefact, not in text"})
    for c in doc.get("claims") or []:
        if isinstance(c, dict) and isinstance(c.get("statement"), str) and _LINK_RE.search(c["statement"]):
            findings.append({"rule": "SI4", "where": f"claims:{c.get('id')}.statement",
                             "message": "a link in a statement; cite the work in references or name the artefact"})
    return findings
