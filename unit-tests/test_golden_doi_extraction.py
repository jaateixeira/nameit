"""Golden tests: the DOI NameIt would look up for each sample PDF (offline, no network).

Expected values were produced by running find_dois_in_pdf on the files in test-data/ and
checking the DOI context by eye. Only the FIRST DOI is what NameIt uses; later pages
(e.g. 5, 16, 23, 42) are reference-list DOIs of *other* papers and are asserted only to
document that behaviour.
"""
import os
import unittest

from nameit.crossref import find_dois_in_pdf, find_doi_in_text

DATA = os.path.join(os.path.dirname(__file__), "..", "test-data")

# file -> DOI of the paper itself (first hit); None = no DOI printed in the scanned pages
GOLDEN = {
    "1-s2.0-S2444845116300295-main.pdf": "10.1016/j.redeen.2016.09.003",
    "1-s2.0-S2543925123000025-main.pdf": "10.1016/j.dim.2023.100028",
    "1-s2.0-S2666389923001873-main.pdf": "10.1016/j.patter.2023.100818",
    "1-s2.0-S2666764923000085-main.pdf": "10.1016/j.dsm.2023.02.002",
    "1-s2.0-S2666954423000133-main.pdf": "10.1016/j.digbus.2023.100065",
    "jss_2023092614594425.pdf": "10.4236/jss.2023.119034",
    "s40008-019-0169-8.pdf": "10.1186/s40008-019-0169-8",
    "s40537-014-0007-7.pdf": "10.1186/s40537-014-0007-7",
    "s40991-016-0005-5.pdf": "10.1186/s40991-016-0005-5",
    "ecis-2025.pdf": None,
    "very-small-doc.pdf": None,
}
PREFIX_GOLDEN = {  # long file names: matched by prefix
    "Inflation targeting in high inflation emerging": "10.1080/15140326.2019.1565396",
    "Rethinking societal engagement under the heading": "10.1080/23299460.2021.1909812",
    "Threat analysis model to control IoT network rou": "10.1080/09540091.2022.2149698",
}


def _path(name):
    return os.path.join(DATA, name)


class GoldenDoiExtraction(unittest.TestCase):
    def test_known_files(self):
        for name, expected in GOLDEN.items():
            with self.subTest(name):
                if not os.path.exists(_path(name)):
                    self.skipTest(f"{name} missing")
                found = find_dois_in_pdf(_path(name))
                self.assertEqual(found[0][1] if found else None, expected)

    def test_long_named_files(self):
        files = os.listdir(DATA)
        for prefix, expected in PREFIX_GOLDEN.items():
            with self.subTest(prefix):
                match = [f for f in files if f.startswith(prefix)]
                if not match:
                    self.skipTest(f"{prefix}* missing")
                found = find_dois_in_pdf(_path(match[0]))
                self.assertEqual(found[0][1], expected)

    def test_text_cases(self):
        self.assertEqual(find_doi_in_text("DOI: 10.1000/abc.def."), "10.1000/abc.def")
        self.assertEqual(find_doi_in_text("https://doi.org/10.1016/j.x.2023.1"), "10.1016/j.x.2023.1")
        self.assertIsNone(find_doi_in_text("https://www.jstor.org/stable/10.2307/1234567"))
        self.assertIsNone(find_doi_in_text("no identifier here"))


if __name__ == "__main__":
    unittest.main()
