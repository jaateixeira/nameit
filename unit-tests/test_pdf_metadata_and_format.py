"""Golden tests for -p mode on the real sample PDFs, and for the filename format."""
import unittest
from pathlib import Path

from nameit.models.data_models import Publication
from nameit.pdf_metadata import (
    CitationLine, RawMetadata, extract_publication_from_pdf_metadata as extract,
    parse_citation_line, publication_from_metadata, publisher_from_doi,
)

DATA = Path(__file__).resolve().parent.parent / "test-data"

GOLDEN = {
    "1-s2.0-S2666389923001873-main.pdf":
        "Schwitzgebel (2023). AI systems must not confuse users about their sentience or moral status. "
        "Patterns. Elsevier.pdf",
    "s40008-019-0169-8.pdf":
        "Yeo (2019). The trade policy effect in international trade case of Pakistan. "
        "Journal of Economic Structures. Springer.pdf",
    "ecis-2025.pdf":
        "Teixeira et al. (2025). Towards understanding open and coopetitive platform ecosystems "
        "The case of TensorFlow. Unknown publication. Unknown publisher.pdf",
}
NO_USABLE_METADATA = ["s40537-014-0007-7.pdf", "very-small-doc.pdf"]


class TestPdfMetadataGolden(unittest.TestCase):
    def test_expected_names(self):
        for pdf, expected in GOLDEN.items():
            with self.subTest(pdf=pdf):
                self.assertEqual(str(extract(str(DATA / pdf))), expected)

    def test_unusable_metadata_returns_none(self):
        for pdf in NO_USABLE_METADATA:
            with self.subTest(pdf=pdf):
                self.assertIsNone(extract(str(DATA / pdf)))

    def test_missing_or_corrupt_file_returns_none(self):
        self.assertIsNone(extract(str(DATA / "does-not-exist.pdf")))


class TestCitationLine(unittest.TestCase):
    def test_elsevier_style(self):
        self.assertEqual(
            parse_citation_line("Patterns, 4 (2023) 100818. doi:10.1016/j.patter.2023.100818"),
            CitationLine("Patterns", 2023, "10.1016/j.patter.2023.100818"))

    def test_year_after_comma_and_spaced_doi(self):
        self.assertEqual(parse_citation_line("Connection Science, 2022. doi: 10.1080/09540091.2022.2149698"),
                         CitationLine("Connection Science", 2022, "10.1080/09540091.2022.2149698"))

    def test_url_style(self):
        c = parse_citation_line("Journal of Economic Structures, https://doi.org/10.1186/s40008-019-0169-8")
        self.assertEqual((c.journal, c.doi), ("Journal of Economic Structures", "10.1186/s40008-019-0169-8"))

    def test_abstract_is_not_a_citation_line(self):
        abstract = "Business ethics are moral strategies, 2020 goals. " + "word " * 60
        self.assertEqual(parse_citation_line(abstract), CitationLine())
        self.assertEqual(parse_citation_line(""), CitationLine())


class TestPublicationFromMetadata(unittest.TestCase):
    def raw(self, **kw):
        base = dict(title="A real title", author="Ann Smith", subject="", keywords="", creation_date="D:20210101000000Z")
        base.update(kw)
        return RawMetadata(**base)

    def test_year_falls_back_to_creation_date(self):
        self.assertIn("(2021)", str(publication_from_metadata(self.raw())))

    def test_citation_year_wins_over_creation_date(self):
        pub = publication_from_metadata(self.raw(subject="J Tests, 3 (2019) 1-9. doi:10.1016/x.1"))
        self.assertIn("(2019)", str(pub))
        self.assertTrue(str(pub).endswith("J Tests. Elsevier.pdf"))

    def test_keywords_are_not_used_in_the_name(self):
        self.assertNotIn("topicword", str(publication_from_metadata(self.raw(keywords="topicword"))))

    def test_missing_pieces_give_none(self):
        self.assertIsNone(publication_from_metadata(self.raw(title="Document1")))
        self.assertIsNone(publication_from_metadata(self.raw(author="")))
        self.assertIsNone(publication_from_metadata(self.raw(creation_date="")))

    def test_publisher_prefixes(self):
        self.assertEqual(publisher_from_doi("10.1016/j.x"), "Elsevier")
        self.assertIsNone(publisher_from_doi("10.9999/unknown"))
        self.assertIsNone(publisher_from_doi(None))


class TestAuthorFormat(unittest.TestCase):
    def name(self, authors):
        return str(Publication(authors=authors, year=2020, title="T", publication="J", publisher="Elsevier"))

    def test_one_author(self):
        self.assertTrue(self.name("Smith").startswith("Smith (2020)."))

    def test_two_authors_both_kept(self):
        self.assertTrue(self.name("Smith and Jones").startswith("Smith and Jones (2020)."))

    def test_more_than_two_authors_et_al(self):
        self.assertTrue(self.name("Smith et al.").startswith("Smith et al. (2020)."))
        self.assertTrue(self.name("Smith, Jones, Lee").startswith("Smith et al. (2020)."))


if __name__ == "__main__":
    unittest.main()
