"""Replay recorded Crossref answers offline and compare the derived names to the golden file.

Fixtures are created on a machine with internet access by tools/record_crossref_fixtures.py.
Without them this test is skipped (it never invents recordings).
"""
import json
import os
import unittest

from nameit.crossref import validate_crossref_returned_meta_data

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "test-data", "crossref")
EXPECTED = os.path.join(FIXTURES, "expected_names.json")


@unittest.skipUnless(os.path.exists(EXPECTED),
                     "no recorded Crossref fixtures; run tools/record_crossref_fixtures.py test-data")
class CrossrefReplay(unittest.TestCase):
    def test_recorded_answers_give_golden_names(self):
        with open(EXPECTED, encoding="utf-8") as fh:
            expected = json.load(fh)
        for doi, name in expected.items():
            with self.subTest(doi):
                path = os.path.join(FIXTURES, doi.replace("/", "_") + ".json")
                with open(path, encoding="utf-8") as fh:
                    meta = json.load(fh)["message"]
                self.assertEqual(str(validate_crossref_returned_meta_data(meta)), name)


if __name__ == "__main__":
    unittest.main()
