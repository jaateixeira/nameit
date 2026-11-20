"""API tests: planning, applying, undo, collisions. Offline (Crossref is mocked)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nameit import api
from nameit.models.data_models import Publication

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "test-data" / "ecis-2025.pdf"        # > 20 KB, valid pdf
SAMPLE2 = ROOT / "test-data" / "jss_2023092614594425.pdf"


def pub(author="Smith", year=2020, title="A Title"):
    return Publication(authors=author, year=year, title=title, publication="J", publisher="P")


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def fake_extractor(self, publications):
        it = iter(publications)
        return mock.patch.dict(api.EXTRACTORS, {api.METHOD_CROSSREF: lambda path: next(it)})


class TestHelpers(ApiTestCase):
    def test_returns_new_path_and_never_overwrites(self):
        (self.tmp / "Smith (2020). T.pdf").write_bytes(b"old")
        src = self.tmp / "a.pdf"
        src.write_bytes(b"new")
        new = api.rename_pdf_file(src, "Smith (2020). T.pdf")
        self.assertEqual(new.name, "Smith (2020). T (1).pdf")
        self.assertEqual((self.tmp / "Smith (2020). T.pdf").read_bytes(), b"old")

    def test_path_separator_in_title_stays_in_same_folder(self):
        src = self.tmp / "a.pdf"
        src.write_bytes(b"x")
        self.assertEqual(api.rename_pdf_file(src, "Input/Output.pdf").parent, self.tmp)

    def test_iter_pdf_files_recursion(self):
        (self.tmp / "sub").mkdir()
        for rel in ["top.pdf", "notes.txt", "sub/mid.PDF"]:
            (self.tmp / rel).write_bytes(b"x")
        flat = sorted(p.name for p in api.iter_pdf_files(self.tmp, False))
        deep = sorted(p.name for p in api.iter_pdf_files(self.tmp, True))
        self.assertEqual(flat, ["top.pdf"])
        self.assertEqual(deep, ["mid.PDF", "top.pdf"])


class TestPlanAndApply(ApiTestCase):
    def setUp(self):
        super().setUp()
        (self.tmp / "sub").mkdir()
        shutil.copy(SAMPLE, self.tmp / "one.pdf")
        shutil.copy(SAMPLE2, self.tmp / "sub" / "two.pdf")

    def test_plan_changes_nothing_on_disk(self):
        with self.fake_extractor([pub(), pub(title="B")]):
            plans = api.plan_rename(self.tmp, recursive=True)
        self.assertEqual([p.status for p in plans], [api.STATUS_RENAME] * 2)
        self.assertTrue((self.tmp / "one.pdf").exists())
        self.assertTrue((self.tmp / "sub" / "two.pdf").exists())

    def test_same_target_in_one_batch_gets_distinct_names(self):
        shutil.copy(SAMPLE, self.tmp / "three.pdf")
        with self.fake_extractor([pub(), pub(), pub()]):
            plans = api.plan_rename(self.tmp)
        targets = [p.target.name for p in plans]
        self.assertEqual(len(set(targets)), len(targets))

    def test_non_recursive_ignores_subfolders(self):
        with self.fake_extractor([pub()]):
            plans = api.plan_rename(self.tmp, recursive=False)
        self.assertEqual([p.source.name for p in plans], ["one.pdf"])

    def test_missing_metadata_is_skipped_with_reason(self):
        with self.fake_extractor([None]):
            plans = api.plan_rename(self.tmp / "one.pdf")
        self.assertEqual(plans[0].status, api.STATUS_SKIPPED)
        self.assertIn("no metadata", plans[0].reason)

    def test_tiny_file_is_skipped_not_fatal(self):
        (self.tmp / "tiny.pdf").write_bytes(b"%PDF-1.4 tiny")
        with self.fake_extractor([pub(), pub(title="B")]):
            plans = api.plan_rename(self.tmp)
        self.assertIn(api.STATUS_SKIPPED, [p.status for p in plans])

    def test_methods_fall_back_in_order(self):
        calls = []
        def first(path): calls.append("crossref"); return None
        def second(path): calls.append("pdf"); return pub()
        with mock.patch.dict(api.EXTRACTORS, {api.METHOD_CROSSREF: first, api.METHOD_PDF_METADATA: second}):
            plans = api.plan_rename(self.tmp / "one.pdf", methods=("crossref", "pdf-metadata"))
        self.assertEqual(calls, ["crossref", "pdf"])
        self.assertEqual(plans[0].method, "pdf-metadata")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            api.plan_rename(self.tmp, methods=("magic",))

    def test_apply_then_undo_round_trip(self):
        with self.fake_extractor([pub(), pub(title="B")]):
            plans = api.rename_pdf(self.tmp, recursive=True)
        self.assertFalse((self.tmp / "one.pdf").exists())
        logs = list(self.tmp.glob(f"{api.UNDO_LOG_PREFIX}*.json"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(json.loads(logs[0].read_text())), 2)
        restored = api.undo_renames(logs[0])
        self.assertEqual(len(restored), 2)
        self.assertTrue((self.tmp / "one.pdf").exists())
        self.assertTrue((self.tmp / "sub" / "two.pdf").exists())

    def test_undo_log_lands_in_the_given_root_even_if_only_a_subfolder_file_changes(self):
        (self.tmp / "one.pdf").unlink()
        with self.fake_extractor([pub()]):
            api.rename_pdf(self.tmp, recursive=True)
        self.assertEqual(len(list(self.tmp.glob(f"{api.UNDO_LOG_PREFIX}*.json"))), 1)
        self.assertEqual(list((self.tmp / "sub").glob(f"{api.UNDO_LOG_PREFIX}*.json")), [])

    def test_dry_run_writes_nothing(self):
        before = sorted(p.name for p in self.tmp.rglob("*"))
        with self.fake_extractor([pub(), pub(title="B")]):
            api.rename_pdf(self.tmp, recursive=True, dry_run=True)
        self.assertEqual(before, sorted(p.name for p in self.tmp.rglob("*")))


if __name__ == "__main__":
    unittest.main()
