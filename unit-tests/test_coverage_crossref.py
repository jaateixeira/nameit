"""Crossref helpers and the DOI-in-PDF flow, offline (fetch is mocked, PDFs are generated)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pymupdf

import nameit.crossref as crossref
from nameit.crossref import find_doi_in_text, format_author_names, key_value_table
from nameit.models.exceptions import InvalidCrossrefDataError

GOOD = {"message": {
    "author": [{"given": "Ada", "family": "Lovelace"}], "issued": {"date-parts": [[2019]]},
    "title": ["On engines"], "container-title": ["Journal of Machines"], "publisher": "Elsevier BV"}}


def make_pdf(path, pages):
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_text((50, 100), text, fontsize=11)
    doc.save(path)
    doc.close()


class TestFormatAuthorNames(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(format_author_names([{"family": "A"}]), "A")
        self.assertEqual(format_author_names([{"family": "A"}, {"family": "B"}]), "A and B")
        self.assertEqual(format_author_names([{"family": "A"}, {"family": "B"}, {"family": "C"}]), "A et al.")

    def test_alternative_key_is_accepted(self):
        self.assertEqual(format_author_names([{"surname": "Ng"}]), "Ng")
        self.assertEqual(format_author_names([{"lastName": "Li"}, {"name": "Wu"}]), "Li and Wu")

    def test_bad_input_raises_value_error(self):
        for bad in ([], None, "Smith", ["Smith"], [{"given": "Only"}]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                format_author_names(bad)

    def test_debug_mode_prints_diagnostics_then_raises(self):
        with mock.patch("builtins.print") as printed, self.assertRaises(ValueError):
            format_author_names([{"given": "Only"}], debug=True)
        self.assertTrue(printed.called)


class TestFindDoiInText(unittest.TestCase):
    def test_plain_and_url_dois(self):
        self.assertEqual(find_doi_in_text("see 10.1000/abc.123 here"), "10.1000/abc.123")
        self.assertEqual(find_doi_in_text("at https://doi.org/10.1016/j.x.2020.1 ok"), "10.1016/j.x.2020.1")

    def test_trailing_punctuation_is_dropped(self):
        self.assertEqual(find_doi_in_text("doi 10.1000/abc.def."), "10.1000/abc.def")

    def test_jstor_urls_are_ignored(self):
        self.assertIsNone(find_doi_in_text("https://www.jstor.org/stable/10.2307/1234567"))

    def test_nothing_found(self):
        self.assertIsNone(find_doi_in_text("no identifiers"))


class TestKeyValueTable(unittest.TestCase):
    def test_renders_rows(self):
        table = key_value_table("T", [("a", "1"), ("b", "2")])
        self.assertEqual(table.row_count, 2)


class TestValidateCrossrefRecord(unittest.TestCase):
    def test_good_record(self):
        pub = crossref.validate_crossref_returned_meta_data(GOOD)
        self.assertEqual((pub.authors, pub.year, pub.publication), ("Lovelace", 2019, "Journal of Machines"))

    def test_missing_container_and_publisher_get_placeholders(self):
        record = {"message": {k: v for k, v in GOOD["message"].items() if k not in ("container-title", "publisher")}}
        pub = crossref.validate_crossref_returned_meta_data(record)
        self.assertEqual((pub.publication, pub.publisher), ("Unknown publication", "Unknown publisher"))

    def test_bad_year_and_empty_title_raise(self):
        for field, value in (("issued", {"date-parts": [[1200]]}), ("title", ["  "])):
            record = {"message": {**GOOD["message"], field: value}}
            with self.subTest(field), self.assertRaises(InvalidCrossrefDataError):
                crossref.validate_crossref_returned_meta_data(record)

    def test_not_a_dict(self):
        with self.assertRaises(InvalidCrossrefDataError):
            crossref.validate_crossref_returned_meta_data(None)  # type: ignore[arg-type]


class TestDoiInPdfFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def pdf(self, pages, name="p.pdf"):
        path = os.path.join(self.tmp.name, name)
        make_pdf(path, pages)
        return path

    def run_extract(self, path, fetched=GOOD):
        with mock.patch.object(crossref, "fetch_metadata_by_doi", return_value=fetched) as fetch:
            return crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(path), fetch

    def test_doi_on_first_page_is_looked_up(self):
        pub, fetch = self.run_extract(self.pdf(["Title\nDOI: 10.1000/first.1"]))
        self.assertEqual(pub.authors, "Lovelace")
        self.assertEqual(fetch.call_args[0][0], "10.1000/first.1")

    def test_doi_only_on_last_page_is_found(self):
        pub, fetch = self.run_extract(self.pdf(["a", "b", "c", "Cite: https://doi.org/10.1000/last.9"]))
        self.assertIsNotNone(pub)
        self.assertEqual(fetch.call_args[0][0], "10.1000/last.9")

    def test_no_doi_means_none_and_no_lookup(self):
        pub, fetch = self.run_extract(self.pdf(["nothing to see"]))
        self.assertIsNone(pub)
        fetch.assert_not_called()

    def test_crossref_has_no_record_tries_next_page_then_gives_up(self):
        pub, fetch = self.run_extract(self.pdf(["10.1000/one.1", "10.1000/two.2"]), fetched=None)
        self.assertIsNone(pub)
        self.assertEqual(fetch.call_count, 2)

    def test_unusable_record_on_page_one_falls_through_to_page_two(self):
        bad = {"message": {"author": [{"family": "NoGiven"}], "issued": {"date-parts": [[2019]]}, "title": ["x"]}}
        with mock.patch.object(crossref, "fetch_metadata_by_doi", side_effect=[bad, GOOD]) as fetch:
            pub = crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(
                self.pdf(["10.1000/one.1", "10.1000/two.2"]))
        self.assertEqual(pub.authors, "Lovelace")
        self.assertEqual(fetch.call_count, 2)

    def test_missing_and_corrupt_files_return_none(self):
        self.assertIsNone(crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(
            os.path.join(self.tmp.name, "absent.pdf")))
        broken = Path(self.tmp.name, "broken.pdf")
        broken.write_bytes(b"not a pdf at all")
        self.assertIsNone(crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(str(broken)))

    def test_find_dois_in_pdf_lists_pages(self):
        found = crossref.find_dois_in_pdf(self.pdf(["10.1000/a.1", "x", "10.1000/c.3"]))
        self.assertEqual(found, [(1, "10.1000/a.1"), (3, "10.1000/c.3")])


if __name__ == "__main__":
    unittest.main()
