"""Mapping the model's labels to OpenAlex topics and subfields. Pure functions: no model, no network.

The model's labels look like "2543: Mapping Groundwater Potential Zones Using GIS Techniques". The number n is the
topic's ID less 10000: label 2543 is topic T12543. Topics are matched by that ID, not by name: OpenAlex has renamed
most topics since the model was trained (T12543 is now "Groundwater and Watershed Analysis"), while the IDs, and
the clusters they name, stayed. Each topic belongs to exactly one subfield.
"""

import re

_LABEL = re.compile(r"^\s*\d+\s*:\s*(.+?)\s*$")


def label_name(label):
    m = _LABEL.match(label)
    return m.group(1) if m else label.strip()


def short_id(openalex_id):
    """https://openalex.org/T10001 -> openalex:T10001; https://openalex.org/subfields/1803 -> openalex:subfields/1803"""
    return "openalex:" + openalex_id.rsplit("openalex.org/", 1)[-1]


def label_number(label):
    m = re.match(r"^\s*(\d+)\s*:", label)
    if not m:
        raise ValueError(f"model label without a number: {label!r}")
    return int(m.group(1))


def topic_id_of(label):
    """The OpenAlex topic ID a model label names: label n is T(10000 + n)."""
    return f"T{10000 + label_number(label)}"


def build_table(topics, labels):
    """{model label: {"topic", "subfield"}} from OpenAlex topic records ({id, display_name, subfield: {id}}) and the
    model's labels. Raises ValueError naming the labels whose topic OpenAlex does not have."""
    by_id = {t["id"].rsplit("/", 1)[-1]: t for t in topics}
    table, missing = {}, []
    for label in labels:
        topic = by_id.get(topic_id_of(label))
        if topic is None:
            missing.append(label)
        else:
            table[label] = {"topic": short_id(topic["id"]), "subfield": short_id(topic["subfield"]["id"])}
    if missing:
        raise ValueError(f"{len(missing)} label(s) name a topic OpenAlex does not have, e.g. {missing[:3]}")
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
