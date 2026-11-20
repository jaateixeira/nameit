"""Tests for renaming safety and folder traversal in NameIt.py (no network needed)."""
import argparse
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import NameIt  # noqa: E402

SAMPLE_PDF = ROOT / "test-data" / "very-small-doc.pdf"
BIG_PDF = ROOT / "test-data" / "ecis-2025.pdf"


def make_args(**overrides) -> argparse.Namespace:
    base = dict(use_pdf_metadata=False, use_crossref=True, use_layoutlmv3=False,
                recursive=False, dry_run=False, verbose=False, very_verbose=False, silent=False)
    base.update(overrides)
    return argparse.Namespace(**base)


class TestRenamePdfFile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _touch(self, name: str) -> Path:
        path = self.tmp / name
        path.write_bytes(b"%PDF-1.4 x")
        return path

    def test_returns_new_path(self):
        src = self._touch("a.pdf")
        new = NameIt.rename_pdf_file(src, "Author (2020). Title.pdf")
        self.assertEqual(new, self.tmp / "Author (2020). Title.pdf")
        self.assertTrue(new.exists() and not src.exists())

    def test_never_overwrites_existing_file(self):
        existing = self._touch("Author (2020). Title.pdf")
        src = self._touch("a.pdf")
        new = NameIt.rename_pdf_file(src, "Author (2020). Title.pdf")
        self.assertEqual(new.name, "Author (2020). Title (1).pdf")
        self.assertTrue(existing.exists())

    def test_path_separator_in_title_stays_in_same_folder(self):
        src = self._touch("a.pdf")
        new = NameIt.rename_pdf_file(src, "Input/Output: a study.pdf")
        self.assertEqual(new.parent, self.tmp)

    def test_already_named_is_noop(self):
        src = self._touch("Author (2020). Title.pdf")
        self.assertEqual(NameIt.rename_pdf_file(src, "Author (2020). Title.pdf"), src)


class TestIterPdfFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "sub" / "deeper").mkdir(parents=True)
        for rel in ["top.pdf", "notes.txt", "sub/mid.PDF", "sub/deeper/low.pdf"]:
            (self.tmp / rel).write_bytes(b"x")

    def names(self, recursive):
        return sorted(p.name for p in NameIt.iter_pdf_files(self.tmp, recursive))

    def test_non_recursive_only_top_level(self):
        self.assertEqual(self.names(False), ["top.pdf"])

    def test_recursive_finds_nested_pdfs_once(self):
        self.assertEqual(self.names(True), ["low.pdf", "mid.PDF", "top.pdf"])


class TestProcessFolder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "sub").mkdir()
        shutil.copy(BIG_PDF, self.tmp / "one.pdf")
        shutil.copy(BIG_PDF, self.tmp / "sub" / "two.pdf")

    def run_with_fake_crossref(self, args):
        counter = iter(range(1, 100))
        fake = lambda path: f"Fake {next(counter)} (2025). T. J. P"  # noqa: E731
        with mock.patch.object(NameIt, "extract_publication_metadata_from_crossref_using_doi_in_pdf", fake):
            NameIt.process_folder_or_file(self.tmp, args)

    def test_non_recursive_leaves_subfolder_alone(self):
        self.run_with_fake_crossref(make_args(recursive=False))
        self.assertTrue((self.tmp / "sub" / "two.pdf").exists())
        self.assertFalse((self.tmp / "one.pdf").exists())

    def test_recursive_renames_subfolder_files(self):
        self.run_with_fake_crossref(make_args(recursive=True))
        self.assertFalse((self.tmp / "sub" / "two.pdf").exists())
        self.assertEqual(len(list((self.tmp / "sub").glob("*.pdf"))), 1)

    def test_no_method_exits_before_touching_files(self):
        args = make_args(use_crossref=False)
        with self.assertRaises(SystemExit):
            NameIt.process_folder_or_file(self.tmp, args)
        self.assertTrue((self.tmp / "one.pdf").exists())


if __name__ == "__main__":
    unittest.main()
