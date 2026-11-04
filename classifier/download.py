"""Run at image build: fetch the model and OpenAlex's topic list, and write the label table.

Writes to /opt/classifier:
  model/          the model files
  table.json      {model label: {topic, subfield}}
  about.json      {"classifier": "<model id>@<commit>", "topics_fetched": "<date>"}

The build fails if any model label matches no OpenAlex topic, so a mismatch is found before deployment.
"""

import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download
from labels import build_table

MODEL = os.environ.get("CLASSIFIER_MODEL",
                       "OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract")
REVISION = os.environ.get("CLASSIFIER_MODEL_REVISION", "main")
OUT = Path(os.environ.get("CLASSIFIER_DIR", "/opt/classifier"))


def openalex_topics():
    topics, cursor = [], "*"
    while cursor:
        q = urllib.parse.urlencode({"per-page": 200, "cursor": cursor, "select": "id,display_name,subfield"})
        with urllib.request.urlopen(f"https://api.openalex.org/topics?{q}", timeout=60) as res:
            page = json.loads(res.read())
        topics += page["results"]
        cursor = page["meta"].get("next_cursor")
        time.sleep(0.2)
    return topics


def main():
    commit = HfApi().model_info(MODEL, revision=REVISION).sha     # pin the build to one commit of the model
    snapshot_download(MODEL, revision=commit, local_dir=OUT / "model")
    config = json.loads((OUT / "model" / "config.json").read_text())
    labels = list(config["id2label"].values())
    topics = openalex_topics()
    table = build_table(topics, labels)
    (OUT / "table.json").write_text(json.dumps(table, ensure_ascii=False))
    (OUT / "about.json").write_text(json.dumps({"classifier": f"{MODEL}@{commit}",
                                                "topics_fetched": dt.date.today().isoformat(),
                                                "labels": len(labels), "openalex_topics": len(topics)}))
    print(f"{len(labels)} labels mapped to OpenAlex topics; model {MODEL}@{commit}")


if __name__ == "__main__":
    main()
