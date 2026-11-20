"""CLI tests (offline)."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nameit import api, cli

SAMPLE = Path(__file__).resolve().parent.parent / "test-data" / "ecis-2025.pdf"


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")

    def test_crossref_is_the_default_method(self):
        with mock.patch.object(cli, "is_there_internet_access", return_value=True):
            args = cli.parse_and_validate_arguments([str(self.tmp)])
        self.assertTrue(args.use_crossref)

    def test_layoutlm_is_rejected_clearly(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.parse_and_validate_arguments(["-l", str(self.tmp)])
        self.assertEqual(ctx.exception.code, 2)

    def test_no_internet_without_fallback_exits(self):
        with mock.patch.object(cli, "is_there_internet_access", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                cli.parse_and_validate_arguments(["-c", str(self.tmp)])
        self.assertEqual(ctx.exception.code, 1)

    def test_no_internet_falls_back_to_pdf_metadata(self):
        with mock.patch.object(cli, "is_there_internet_access", return_value=False):
            args = cli.parse_and_validate_arguments(["-c", "-p", str(self.tmp)])
        self.assertFalse(args.use_crossref)
        self.assertTrue(args.use_pdf_metadata)

    def test_path_required_unless_undo(self):
        with self.assertRaises(SystemExit):
            cli.parse_and_validate_arguments(["-p"])

    def test_dry_run_with_pdf_metadata_renames_nothing(self):
        code = cli.main(["-p", "-d", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "paper.pdf").exists())

    def test_rename_then_undo_via_cli(self):
        self.assertEqual(cli.main(["-p", str(self.tmp)]), 0)
        self.assertFalse((self.tmp / "paper.pdf").exists())
        (log,) = self.tmp.glob(f"{api.UNDO_LOG_PREFIX}*.json")
        self.assertEqual(cli.main(["--undo", str(log)]), 0)
        self.assertTrue((self.tmp / "paper.pdf").exists())

    def test_exit_code_1_when_nothing_could_be_done(self):
        (self.tmp / "paper.pdf").unlink()
        shutil.copy(SAMPLE.parent / "s40537-014-0007-7.pdf", self.tmp / "nometa.pdf")
        self.assertEqual(cli.main(["-p", str(self.tmp)]), 1)


if __name__ == "__main__":
    unittest.main()
