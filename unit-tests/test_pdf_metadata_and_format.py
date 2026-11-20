"""Golden tests for -p mode on the real sample PDFs, and for the filename format."""
import unittest
from pathlib import Path

from nameit.models.data_models import Publication
from nameit.pdf_metadata import extract_publication_from_pdf_metadata as extract

DATA = Path(__file__).resolve().parent.parent / "test-data"

GOLDEN = {
    "1-s2.0-S2666389923001873-main.pdf":
        "Schwitzgebel (2023). AI systems must not confuse users about their sentience or moral status. "
        "Patterns. Unknown publisher.pdf",
    "s40008-019-0169-8.pdf":
        "Yeo (2019). The trade policy effect in international trade case of Pakistan. "
        "Journal of Economic Structures. Unknown publisher.pdf",
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
