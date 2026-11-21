"""Several paths and glob patterns, in the API and on the command line. Offline."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nameit import api, cli
from nameit.models.data_models import Publication
from nameit.models.exceptions import InvalidNameItPath

DATA = Path(__file__).resolve().parent.parent / "test-data"
BIG = DATA / "ecis-2025.pdf"          # valid, > 20 KB


def pub(title="T"):
    return Publication(authors="Smith", year=2020, title=title, publication="J", publisher="P")


class WildcardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "sub").mkdir()
        for rel in ["2023-a.pdf", "2024-a.pdf", "2024-b.PDF", "2024-notes.txt", "sub/2024-c.pdf", "sub/other.pdf"]:
            shutil.copy(BIG, self.tmp / rel) if rel.lower().endswith(".pdf") else (self.tmp / rel).write_text("x")

    def names(self, inputs, recursive=False):
        return sorted(str(p.relative_to(self.tmp)) for p, _ in api.collect_pdf_files(inputs, recursive))

    def pattern(self, text):
        return str(self.tmp / text)


class TestCollect(WildcardCase):
    def test_star_matches_only_pdfs_silently_dropping_other_files(self):
        self.assertEqual(self.names(self.pattern("2024*")), ["2024-a.pdf", "2024-b.PDF"])

    def test_question_mark_and_brackets(self):
        self.assertEqual(self.names(self.pattern("202?-a.pdf")), ["2023-a.pdf", "2024-a.pdf"])
        self.assertEqual(self.names(self.pattern("2023-[ab].pdf")), ["2023-a.pdf"])

    def test_double_star_reaches_subfolders(self):
        self.assertEqual(self.names(self.pattern("**/2024-*.pdf")), ["2024-a.pdf", "sub/2024-c.pdf"])

    def test_several_inputs_are_merged_in_order_without_duplicates(self):
        got = self.names([self.pattern("2023-a.pdf"), self.pattern("2023*"), str(self.tmp / "sub")])
        self.assertEqual(got, ["2023-a.pdf", "sub/2024-c.pdf", "sub/other.pdf"])

    def test_pattern_with_no_match_is_an_error(self):
        with self.assertRaises(InvalidNameItPath) as ctx:
            api.collect_pdf_files(self.pattern("nothing*.pdf"))
        self.assertIn("no file matches", ctx.exception.reason)

    def test_missing_literal_path_is_an_error(self):
        with self.assertRaises(InvalidNameItPath):
            api.collect_pdf_files(self.pattern("missing.pdf"))

    def test_existing_file_with_brackets_is_taken_literally(self):
        weird = self.tmp / "paper[1].pdf"
        shutil.copy(BIG, weird)
        self.assertEqual(self.names(self.pattern("paper[1].pdf")), ["paper[1].pdf"])

    def test_explicit_non_pdf_is_kept_so_it_can_be_reported(self):
        self.assertEqual(self.names(self.pattern("2024-notes.txt")), ["2024-notes.txt"])

    def test_input_folder_is_the_common_parent(self):
        self.assertEqual(api.input_folder(self.pattern("sub/*.pdf")), (self.tmp / "sub").resolve())
        self.assertEqual(api.input_folder([self.pattern("2023-a.pdf"), self.pattern("sub/other.pdf")]),
                         self.tmp.resolve())


class TestPlanWithPatterns(WildcardCase):
    def fake(self):
        counter = iter(range(1, 99))
        return mock.patch.dict(api.EXTRACTORS, {api.METHOD_CROSSREF: lambda p: pub(f"Title {next(counter)}")})

    def test_plan_for_a_pattern_only_covers_matches(self):
        with self.fake():
            plans = api.plan_rename(self.pattern("2024*"))
        self.assertEqual(sorted(p.source.name for p in plans), ["2024-a.pdf", "2024-b.PDF"])
        self.assertTrue((self.tmp / "2023-a.pdf").exists())

    def test_explicit_non_pdf_is_skipped_with_reason(self):
        with self.fake():
            plans = api.plan_rename([self.pattern("2024-notes.txt"), self.pattern("2023-a.pdf")])
        self.assertEqual([p.status for p in plans], [api.STATUS_SKIPPED, api.STATUS_RENAME])
        self.assertEqual(plans[0].reason, "not a pdf file")

    def test_rename_with_pattern_writes_undo_log_in_common_folder(self):
        with self.fake():
            api.rename_pdf(self.pattern("sub/*.pdf"))
        self.assertEqual(len(list((self.tmp / "sub").glob(f"{api.UNDO_LOG_PREFIX}*.json"))), 1)


class TestCliPatterns(WildcardCase):
    def run_cli(self, *argv):
        with mock.patch.dict(api.EXTRACTORS, {api.METHOD_CROSSREF: lambda p: pub(Path(p).stem)}), \
             mock.patch.object(cli, "is_there_internet_access", return_value=True):
            return cli.main(list(argv))

    def test_quoted_pattern_is_expanded_by_nameit(self):
        self.assertEqual(self.run_cli("-d", self.pattern("2024*")), 0)
        self.assertTrue((self.tmp / "2024-a.pdf").exists())

    def test_shell_expanded_list_of_files_works(self):          # what `nameit papers/2024*.pdf` sends
        self.run_cli(self.pattern("2024-a.pdf"), self.pattern("2023-a.pdf"))
        self.assertFalse((self.tmp / "2024-a.pdf").exists())
        self.assertFalse((self.tmp / "2023-a.pdf").exists())
        self.assertTrue((self.tmp / "2024-b.PDF").exists())      # not asked for: untouched

    def test_pattern_without_match_exits_1(self):
        self.assertEqual(self.run_cli("-d", self.pattern("zzz*.pdf")), 1)

    def test_undo_covers_a_multi_path_run(self):
        self.run_cli(self.pattern("2023-a.pdf"), self.pattern("sub/other.pdf"))
        (log,) = self.tmp.glob(f"{api.UNDO_LOG_PREFIX}*.json")
        self.assertEqual(cli.main(["--undo", str(log)]), 0)
        self.assertTrue((self.tmp / "2023-a.pdf").exists())
        self.assertTrue((self.tmp / "sub" / "other.pdf").exists())

    def test_no_paths_at_all_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.parse_and_validate_arguments(["-p"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
