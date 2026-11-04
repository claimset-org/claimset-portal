"""Tests of the label mapping; standard library only: python -m unittest discover -s classifier/tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labels import build_table, classify, label_name, model_input, short_id, topic_id_of  # noqa: E402

TOPICS = [
    {"id": "https://openalex.org/T10001", "display_name": "Time Series Forecasting",
     "subfield": {"id": "https://openalex.org/subfields/1803"}},
    {"id": "https://openalex.org/T10002", "display_name": "Supply Chain Management",
     "subfield": {"id": "https://openalex.org/subfields/1408"}},
    {"id": "https://openalex.org/T10003", "display_name": "Viral Ecology",
     "subfield": {"id": "https://openalex.org/subfields/2404"}},
]
# Labels carry the names the model was trained with; OpenAlex may have renamed the topics since.
LABELS = ["1: Forecasting Economic Time Series", "2: Supply Chain Management", "3: Viral Ecology"]


class TestLabels(unittest.TestCase):
    def test_names_and_ids(self):
        self.assertEqual(label_name("1048: Ecology and Evolution of Viruses"), "Ecology and Evolution of Viruses")
        self.assertEqual(short_id("https://openalex.org/T10001"), "openalex:T10001")
        self.assertEqual(short_id("https://openalex.org/subfields/1803"), "openalex:subfields/1803")

    def test_table_and_classify(self):
        table = build_table(TOPICS, LABELS)
        out = classify([("2: Supply Chain Management", 0.6), ("1: Forecasting Economic Time Series", 0.3),
                        ("3: Viral Ecology", 0.05), ("1: Forecasting Economic Time Series", 0.01)], table)
        self.assertEqual(out, {"subfield": "openalex:subfields/1408",
                               "topics": ["openalex:T10002", "openalex:T10001", "openalex:T10003"]})

    def test_labels_match_topics_by_id_not_by_name(self):
        self.assertEqual(topic_id_of("2543: Mapping Groundwater Potential Zones Using GIS Techniques"), "T12543")
        table = build_table(TOPICS, LABELS)
        self.assertEqual(table["1: Forecasting Economic Time Series"]["topic"], "openalex:T10001")   # renamed

    def test_a_label_whose_topic_is_missing_fails_the_build(self):
        with self.assertRaises(ValueError):
            build_table(TOPICS, LABELS + ["9: A Topic OpenAlex Does Not Have"])

    def test_model_input(self):
        self.assertEqual(model_input("T", ""), "<TITLE> T\n<ABSTRACT> NONE")


if __name__ == "__main__":
    unittest.main()
