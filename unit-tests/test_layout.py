"""Layout-based extraction (--layout): golden names on the sample PDFs plus synthetic first pages."""
import os
import tempfile
import unittest
from pathlib import Path

import pymupdf

from nameit.layout import Line, extract_publication_from_layout as extract, find_authors, find_title, find_year
from nameit.models.data_models import Publication

DATA = Path(__file__).resolve().parent.parent / "test-data"

GOLDEN = {
    "1-s2.0-S2444845116300295-main.pdf":
        "Abril and Rodriguez-Cánovas (2016). Marketing mix effects on private labels brand equity. "
        "European Journal of Management and Business Economics. Elsevier.pdf",
    "1-s2.0-S2666389923001873-main.pdf":
        "Schwitzgebel (2023). AI systems must not confuse users about their sentience or moral status. "
        "Patterns. Elsevier.pdf",
    "1-s2.0-S2666764923000085-main.pdf":
        "Cai et al. (2023). Forecasting hourly PM2.5 concentrations based on decomposition-ensemble-reconstruction "
        "framework incorporating deep learning algorithms. Data Science and Management. Elsevier.pdf",
    "s40537-014-0007-7.pdf":  # no embedded metadata at all: only the layout can name it
        "Najafabadi et al. (2015). Deep learning applications and challenges in big data analytics. "
        "Journal of Big Data. Springer.pdf",
    "ecis-2025.pdf":  # one author per line, affiliations in between
        "Teixeira et al. (2025). Towards understanding open and coopetitive platform ecosystems "
        "The case of TensorFlow. Unknown publication. Unknown publisher.pdf",
    "s40008-019-0169-8.pdf":
        "Yeo and Deng (2019). The trade policy effect in international trade case of Pakistan. "
        "Journal of Economic Structures. Springer.pdf",
}


class TestLayoutGolden(unittest.TestCase):
    def test_expected_names(self):
        for pdf, expected in GOLDEN.items():
            with self.subTest(pdf=pdf):
                self.assertEqual(str(extract(str(DATA / pdf))), expected)

    def test_rethinking_paper_without_author_metadata(self):
        name = [f for f in os.listdir(DATA) if f.startswith("Rethinking")][0]
        pub = extract(str(DATA / name))
        self.assertTrue(str(pub).startswith("Bauer et al. (2021). Rethinking societal engagement"))

    def test_nothing_to_find_returns_none(self):
        self.assertIsNone(extract(str(DATA / "very-small-doc.pdf")))
        self.assertIsNone(extract(str(DATA / "does-not-exist.pdf")))


def make_pdf(path, items):
    """items: (y, font size, text) lines on a letter-size page."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    for y, size, text in items:
        page.insert_text((50, y), text, fontsize=size)
    doc.save(path)
    doc.close()


class TestSyntheticPages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def pdf(self, items):
        path = os.path.join(self.tmp.name, "p.pdf")
        make_pdf(path, items)
        return path

    def test_title_authors_year(self):
        path = self.pdf([(80, 20, "A Study of Naming Things"), (110, 12, "Ada Lovelace and Alan Turing"),
                         (130, 9, "University of Nowhere"), (300, 9, "Published 2019 by someone")])
        self.assertEqual(str(extract(path)), "Lovelace and Turing (2019). A Study of Naming Things. "
                                             "Unknown publication. Unknown publisher.pdf")

    def test_wrapped_title_is_joined_and_marks_are_ignored(self):
        path = self.pdf([(80, 20, "A very long title that has"), (104, 20, "to wrap onto a second line"),
                         (140, 12, "Ada Lovelace1, Alan Turing2*, Grace Hopper3"), (300, 9, "© 2020 The Authors")])
        pub = extract(path)
        self.assertEqual(str(pub), "Lovelace et al. (2020). A very long title that has to wrap onto a second line. "
                                   "Unknown publication. Unknown publisher.pdf")

    def test_no_authors_means_no_guess(self):
        self.assertIsNone(extract(self.pdf([(80, 20, "A Title Without Authors"), (300, 9, "© 2020")])))

    def test_year_priority_and_plausibility(self):
        self.assertEqual(find_year("Received 1 May 2015. © 2018 Foo. Printed 2023"), 2018)
        self.assertEqual(find_year("Journal of Big Data (2015) 2:1"), 2015)
        self.assertEqual(find_year("Published 3000", ""), None)
        self.assertEqual(find_year("nothing", "D:20190412001815Z"), 2019)

    def test_running_head_banner_is_not_the_title(self):
        lines = [Line("Journal of Tests 7 (2020) 1-9", 7, 20), Line("Journal of Tests", 14, 60),
                 Line("The real title of the paper", 13, 160), Line("Ada Lovelace", 10, 190)]
        title, end = find_title(lines, 792)
        self.assertEqual(title, "The real title of the paper")
        self.assertEqual(find_authors(lines, end, 792), ["Ada Lovelace"])


class TestHyphenatedSurnames(unittest.TestCase):
    def test_surname_is_kept_whole(self):
        for authors, expected in [("Laine-Kronberg", "Laine-Kronberg"), ("Ann O'Brien", "O'Brien"),
                                  ("Ann Smith and Bo Rodriguez-Cánovas", "Smith and Rodriguez-Cánovas")]:
            with self.subTest(authors):
                pub = Publication(authors=authors, year=2020, title="T", publication="J", publisher="Elsevier")
                self.assertTrue(str(pub).startswith(expected + " (2020)"), str(pub))


if __name__ == "__main__":
    unittest.main()
