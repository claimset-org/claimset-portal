"""The classifier service: POST /classify {title, abstract} -> {subfield, topics, classifier}.

Runs OpenAlex's open topic model (title and abstract, Apache-2.0) on the CPU. Reachable only from the portal, on
the compose network.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from labels import classify, model_input
from pydantic import BaseModel
from transformers import pipeline

DIR = Path(os.environ.get("CLASSIFIER_DIR", "/opt/classifier"))
ABOUT = json.loads((DIR / "about.json").read_text())
TABLE = json.loads((DIR / "table.json").read_text())
MODEL = pipeline("text-classification", model=str(DIR / "model"), top_k=10, truncation=True)

app = FastAPI(title="EntryLib classifier", docs_url=None, redoc_url=None)


class Text(BaseModel):
    title: str = ""
    abstract: str = ""


@app.post("/classify")
def classify_text(text: Text):
    scored = [(r["label"], r["score"]) for r in MODEL(model_input(text.title, text.abstract))[0]]
    return {**classify(scored, TABLE), "classifier": ABOUT["classifier"]}


@app.get("/healthz")
def healthz():
    return ABOUT
