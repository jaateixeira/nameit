"""Output levels (-s / default / -v / -vv) and Crossref failure handling. Offline: Crossref is mocked."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nameit import cli
import nameit.crossref as crossref
from nameit.models.exceptions import InvalidCrossrefDataError
from nameit.utils.unified_console import console
from nameit.utils.verbosity import NORMAL, SILENT, VERBOSE, VERY_VERBOSE, configure_output, get_verbosity, set_verbosity

DATA = Path(__file__).resolve().parent.parent / "test-data"
PDF_WITH_DOI = DATA / "s40537-014-0007-7.pdf"   # DOI 10.1186/s40537-014-0007-7 on page 1

GOOD = {"message": {
    "author": [{"given": "Gregorio", "family": "Robles"}, {"given": "Jose", "family": "Teixeira"},
               {"given": "Jesus", "family": "Gonzalez-Barahona"}],
    "issued": {"date-parts": [[2015]]},
    "title": ["Lessons learned"], "container-title": ["J Internet Serv Appl"], "publisher": "Springer"}}
AUTHOR_WITHOUT_GIVEN_NAME = {"message": {
    "author": [{"family": "OnlyFamily"}], "issued": {"date-parts": [[2015]]}, "title": ["x"]}}
NO_AUTHORS = {"message": {"issued": {"date-parts": [[2015]]}, "title": ["x"]}}


class CrossrefFailureHandling(unittest.TestCase):
    def test_bad_authors_raise_instead_of_exiting_the_process(self):
        with self.assertRaises(InvalidCrossrefDataError):
            crossref.validate_crossref_returned_meta_data(AUTHOR_WITHOUT_GIVEN_NAME)

    def test_missing_fields_raise_invalid_data_error(self):
        with self.assertRaises(InvalidCrossrefDataError):
            crossref.validate_crossref_returned_meta_data(NO_AUTHORS)

    def test_unusable_record_means_none_not_a_crash(self):
        with mock.patch.object(crossref, "fetch_metadata_by_doi", return_value=AUTHOR_WITHOUT_GIVEN_NAME):
            self.assertIsNone(crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(str(PDF_WITH_DOI)))

    def test_good_record_gives_expected_name(self):
        with mock.patch.object(crossref, "fetch_metadata_by_doi", return_value=GOOD):
            pub = crossref.extract_publication_metadata_from_crossref_using_doi_in_pdf(str(PDF_WITH_DOI))
        self.assertTrue(str(pub).startswith("Robles et al. (2015). Lessons learned."))

    def test_error_message_keeps_a_plain_string_intact(self):
        self.assertIn("No 'message' in response.", str(InvalidCrossrefDataError("No 'message' in response.")))


class OutputLevels(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(PDF_WITH_DOI, self.tmp / "paper.pdf")
        self.addCleanup(set_verbosity, NORMAL)

    def run_cli(self, *flags, payload=GOOD):
        with mock.patch.object(cli, "is_there_internet_access", return_value=True), \
             mock.patch.object(crossref, "fetch_metadata_by_doi", return_value=payload), \
             console.capture() as capture:
            code = cli.main([*flags, str(self.tmp)])
        return code, capture.get()

    def test_flags_map_to_levels(self):
        self.assertEqual(configure_output(), NORMAL)
        self.assertEqual(configure_output(verbose=True), VERBOSE)
        self.assertEqual(configure_output(very_verbose=True), VERY_VERBOSE)
        self.assertEqual(configure_output(silent=True), SILENT)
        self.assertEqual(get_verbosity(), SILENT)

    def test_default_shows_table_and_summary_but_no_steps(self):
        code, out = self.run_cli("-d")
        self.assertEqual(code, 0)
        self.assertIn("Robles et al. (2015)", out)
        self.assertIn("Would rename 1 file(s)", out)
        self.assertNotIn("looking for a DOI", out)
        self.assertNotIn("RAW Crossref metadata", out)

    def test_verbose_adds_one_line_per_step(self):
        _, out = self.run_cli("-d", "-v")
        self.assertIn("looking for a DOI", out)
        self.assertIn("Found DOI 10.1186/s40537-014-0007-7", out)
        self.assertIn("Crossref returned metadata", out)
        self.assertNotIn("RAW Crossref metadata", out)

    def test_very_verbose_adds_rich_metadata_tables(self):
        _, out = self.run_cli("-d", "-vv")
        self.assertIn("RAW Crossref metadata", out)
        self.assertIn("Validated Crossref metadata", out)
        self.assertIn("Checking page 1", out)

    def test_silent_prints_no_table_or_summary(self):
        code, out = self.run_cli("-d", "-s")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_unusable_crossref_record_is_skipped_and_reported(self):
        code, out = self.run_cli("-c", "-d", "-v", payload=AUTHOR_WITHOUT_GIVEN_NAME)
        self.assertEqual(code, 1)                      # nothing could be renamed
        self.assertIn("not usable", out)
        self.assertIn("skipped: no metadata found", out)
        self.assertTrue((self.tmp / "paper.pdf").exists())


if __name__ == "__main__":
    unittest.main()
