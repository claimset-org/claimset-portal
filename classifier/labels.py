"""Mapping the model's labels to OpenAlex topics and subfields. Pure functions: no model, no network.

The model's labels look like "1048: Ecology and Evolution of Viruses in Ecosystems". They are matched to OpenAlex
topics by name, since the number in a label need not be the topic's ID. Each topic belongs to exactly one subfield.
"""

import re

_LABEL = re.compile(r"^\s*\d+\s*:\s*(.+?)\s*$")


def label_name(label):
    m = _LABEL.match(label)
    return m.group(1) if m else label.strip()


def short_id(openalex_id):
    """https://openalex.org/T10001 -> openalex:T10001; https://openalex.org/subfields/1803 -> openalex:subfields/1803"""
    return "openalex:" + openalex_id.rsplit("openalex.org/", 1)[-1]


def build_table(topics, labels):
    """{model label: {"topic", "subfield"}} from OpenAlex topic records ({id, display_name, subfield: {id}}) and the
    model's labels. Raises ValueError naming the labels that match no topic, or match more than one."""
    by_name = {}
    for t in topics:
        by_name.setdefault(t["display_name"].strip().casefold(), []).append(t)
    table, missing, ambiguous = {}, [], []
    for label in labels:
        found = by_name.get(label_name(label).casefold(), [])
        if not found:
            missing.append(label)
        elif len(found) > 1:
            ambiguous.append(label)
        else:
            table[label] = {"topic": short_id(found[0]["id"]), "subfield": short_id(found[0]["subfield"]["id"])}
    if missing or ambiguous:
        raise ValueError(f"{len(missing)} label(s) match no OpenAlex topic, e.g. {missing[:3]}; "
                         f"{len(ambiguous)} match several, e.g. {ambiguous[:3]}")
    return table


def classify(scored, table, max_topics=3):
    """{subfield, topics} from the model's [(label, score)], best first: up to three topics, and the subfield of
    the best one."""
    topics = [table[label]["topic"] for label, _ in scored[:max_topics]]
    if not topics:
        raise ValueError("the model returned no labels")
    return {"subfield": table[scored[0][0]]["subfield"], "topics": topics}


def model_input(title, abstract):
    """The model's input format: "<TITLE> {title}\\n<ABSTRACT> {abstract}", NONE for a missing part."""
    return f"<TITLE> {title.strip() or 'NONE'}\n<ABSTRACT> {abstract.strip() or 'NONE'}"
