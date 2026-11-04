"""Tests of the label mapping; standard library only: python -m unittest discover -s classifier/tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labels import build_table, classify, label_name, model_input, short_id  # noqa: E402

TOPICS = [
    {"id": "https://openalex.org/T10001", "display_name": "Time Series Forecasting",
     "subfield": {"id": "https://openalex.org/subfields/1803"}},
    {"id": "https://openalex.org/T10002", "display_name": "Supply Chain Management",
     "subfield": {"id": "https://openalex.org/subfields/1408"}},
    {"id": "https://openalex.org/T10003", "display_name": "Viral Ecology",
     "subfield": {"id": "https://openalex.org/subfields/2404"}},
]
LABELS = ["0: Time Series Forecasting", "1: Supply Chain Management", "2: Viral Ecology"]


class TestLabels(unittest.TestCase):
    def test_names_and_ids(self):
        self.assertEqual(label_name("1048: Ecology and Evolution of Viruses"), "Ecology and Evolution of Viruses")
        self.assertEqual(short_id("https://openalex.org/T10001"), "openalex:T10001")
        self.assertEqual(short_id("https://openalex.org/subfields/1803"), "openalex:subfields/1803")

    def test_table_and_classify(self):
        table = build_table(TOPICS, LABELS)
        out = classify([("1: Supply Chain Management", 0.6), ("0: Time Series Forecasting", 0.3),
                        ("2: Viral Ecology", 0.05), ("0: Time Series Forecasting", 0.01)], table)
        self.assertEqual(out, {"subfield": "openalex:subfields/1408",
                               "topics": ["openalex:T10002", "openalex:T10001", "openalex:T10003"]})

    def test_unmatched_label_fails_the_build(self):
        with self.assertRaises(ValueError):
            build_table(TOPICS, LABELS + ["3: A Topic OpenAlex Does Not Have"])

    def test_model_input(self):
        self.assertEqual(model_input("T", ""), "<TITLE> T\n<ABSTRACT> NONE")


if __name__ == "__main__":
    unittest.main()
