"""Gap-filling tests: exceptions, validators, data models, paths, verbosity, config errors, api helpers, cli helpers."""
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from nameit import api, cli, config
from nameit.models import exceptions as exc
from nameit.models.data_models import Author, Publication, validate_name_template
from nameit.utils import paths, validators, verbosity

DATA = Path(__file__).resolve().parent.parent / "test-data"
SAMPLE = DATA / "s40537-014-0007-7.pdf"


class TmpDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class TestExceptions(unittest.TestCase):
    def test_messages_carry_their_arguments(self):
        cases = [
            (exc.PDFPermissionError("/a.pdf", "read"), ["/a.pdf", "read"]),
            (exc.PDFCorruptedError("/a.pdf"), ["/a.pdf", "corrupted"]),
            (exc.PDFMetadataError("/a.pdf", ["title", "year"]), ["title, year"]),
            (exc.PDFMetadataError("/a.pdf"), ["/a.pdf"]),
            (exc.PDFEncryptedError("/a.pdf"), ["encrypted"]),
            (exc.SourceFileNotFoundError("/a.pdf"), ["/a.pdf"]),
            (exc.DestinationExistsError("/b.pdf"), ["/b.pdf"]),
            (exc.StorageLimitExceededError("copy", 1, 2), ["copy"]),
            (exc.InvalidFilenamePatternError("{x}", "unknown"), ["{x}", "unknown"]),
            (exc.MissingMetadataError("year", ["title"]), ["year", "title"]),
            (exc.UnsupportedFileTypeError("/a.txt", "text/plain"), ["/a.txt", "text/plain"]),
            (exc.ConfigurationError("format", "bad"), ["format", "bad"]),
        ]
        for error, needles in cases:
            for needle in needles:
                with self.subTest(type(error).__name__, needle=needle):
                    self.assertIn(needle, str(error))

    def test_hierarchy(self):
        self.assertTrue(issubclass(exc.PDFCorruptedError, exc.PDFError))
        self.assertTrue(issubclass(exc.DestinationExistsError, exc.FileSystemError))
        self.assertTrue(issubclass(exc.MissingMetadataError, exc.ValidationError))
        self.assertTrue(issubclass(exc.NamingConflictError, exc.NameItError))
        self.assertEqual(exc.NamingConflictError("a", "b").new_path, "b")

    def test_invalid_path_exception_has_reason_and_hint(self):
        error = exc.InvalidNameItPath("/x", "why", "do this")
        self.assertEqual((error.path, error.reason), ("/x", "why"))
        self.assertIn("why", str(error))


class TestValidators(TmpDirCase):
    def test_name_part_validators(self):
        self.assertTrue(validators.validate_first_name("Ann"))
        self.assertFalse(validators.validate_first_name("  "))
        self.assertFalse(validators.validate_last_name(None))  # type: ignore[arg-type]
        self.assertTrue(validators.validate_suffix(None))
        self.assertTrue(validators.validate_suffix("Jr"))
        self.assertFalse(validators.validate_suffix(" "))

    def test_authors_list_from_crossref(self):
        ok = [{"given": "Ann", "family": "Smith"}]
        self.assertTrue(validators.validate_authors_list_retrieved_from_cross_ref(ok))
        for bad in (None, [], "x", ["x"], [{"family": "Smith"}], [{"given": "Ann"}],
                    [{"given": 1, "family": "Smith"}]):
            with self.subTest(bad=bad):
                self.assertFalse(validators.validate_authors_list_retrieved_from_cross_ref(bad))

    def test_title_year_journal_publisher(self):
        self.assertEqual(validators.validate_title("T"), "T")
        for bad in (None, "", "  "):
            with self.assertRaises(ValueError):
                validators.validate_title(bad)  # type: ignore[arg-type]
        self.assertEqual(validators.validate_year(2000), 2000)
        for bad_year in (1899, 3000):
            with self.assertRaises(ValueError):
                validators.validate_year(bad_year)
        self.assertEqual(validators.validate_journal("J"), "J")
        with self.assertRaises(ValueError):
            validators.validate_journal(None)  # type: ignore[arg-type]
        self.assertEqual(validators.validate_publisher_name("Elsevier"), "Elsevier")
        with self.assertRaises(ValueError):
            validators.validate_publisher_name(" ")

    def test_legacy_field_checks(self):
        self.assertTrue(validators.validate_issued(2020))
        self.assertFalse(validators.validate_issued(0))
        self.assertFalse(validators.validate_issued("2020"))
        self.assertTrue(validators.validate_container_title("J"))
        self.assertFalse(validators.validate_container_title(3))
        self.assertEqual(validators.validate_publisher("P"), "P")
        with self.assertRaises(exc.NameItError):
            validators.validate_publisher(3)  # type: ignore[arg-type]

    def test_validate_publication_collects_errors(self):
        errors = validators.validate_publication({"authors": "not a list", "title": " ", "journal": ""})
        self.assertIn("authors", errors)
        self.assertIn("year", errors)
        self.assertIn("title", errors)
        self.assertIn("journal", errors)

    def test_validate_metadata_exits_on_missing_fields(self):
        full = {"message": {"author": [1], "published": 1, "container-title": ["J"], "title": ["T"],
                            "publisher": "P", "type": "journal-article"}}
        self.assertTrue(validators.validate_metadata(full))
        missing = {"message": {k: v for k, v in full["message"].items() if k != "title"}}
        with self.assertRaises(SystemExit):
            validators.validate_metadata(missing)
        empty = {"message": {**full["message"], "title": []}}
        with self.assertRaises(SystemExit):
            validators.validate_metadata(empty)
        book = {"message": {**full["message"], "type": "book"}}
        with self.assertRaises(SystemExit):
            validators.validate_metadata(book)

    def test_path_validation(self):
        self.assertFalse(validators.is_valid_path("-"))
        self.assertTrue(validators.is_valid_path(SAMPLE))
        self.assertTrue(validators.is_pdf_file(SAMPLE))
        self.assertEqual(validators.valid_path(SAMPLE), SAMPLE)
        with self.assertRaises(exc.InvalidNameItPath):
            validators.valid_path(self.tmp / "nope.pdf")
        self.assertFalse(validators.is_valid_path(self.tmp / "nope.pdf"))

    def test_directory_validation(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        with self.assertRaises(exc.InvalidNameItPath):
            validators.is_valid_path_to_a_directory_with_files_that_should_be_renamed(empty)
        (empty / "notes.txt").write_text("x")
        with self.assertRaises(exc.InvalidNameItPath):
            validators.is_valid_path_to_a_directory_with_files_that_should_be_renamed(empty)
        shutil.copy(SAMPLE, empty / "a.pdf")
        self.assertTrue(validators.is_valid_path_to_a_directory_with_files_that_should_be_renamed(empty))
        with self.assertRaises(exc.InvalidNameItPath):
            validators.is_valid_path_to_a_directory_with_files_that_should_be_renamed(self.tmp / "absent")

    def test_file_validation(self):
        check = validators.is_valid_path_to_a_file_than_should_be_renamed
        with self.assertRaises(exc.InvalidNameItPath):
            check("papers/*.pdf")
        with self.assertRaises(exc.InvalidNameItPath):
            check(self.tmp / "absent.pdf")
        text = self.tmp / "a.txt"
        text.write_text("x")
        with self.assertRaises(exc.InvalidNameItPath):
            check(text)
        fake = self.tmp / "fake.pdf"
        fake.write_bytes(b"not a pdf" * 5000)
        with self.assertRaises(exc.InvalidNameItPath):
            check(fake)
        tiny = self.tmp / "tiny.pdf"
        tiny.write_bytes(b"%PDF-1.4 tiny")
        with self.assertRaises(exc.InvalidNameItPath):
            check(tiny)

    def test_family_name_rules(self):
        validate = validators.validate_author_family_name
        for good in ("Li", "Müller", "O'Brien", "Rodriguez-Cánovas", "de Van"):
            with self.subTest(good):
                self.assertEqual(validate(good), good)
        with self.assertRaises(TypeError):
            validate(3)  # type: ignore[arg-type]
        for bad in ("", " ", "A", "Sm1th", "smith!"):
            with self.subTest(bad), self.assertRaises(ValueError):
                validate(bad)


class TestDataModels(unittest.TestCase):
    def test_author_parsing(self):
        author = Author("Dr. Ann Smith Jr.")
        self.assertEqual((author.first_name, author.last_name), ("Ann", "Smith"))
        self.assertIn("Dr", author.title)
        self.assertEqual(author.suffix, "Jr.")

    def test_publication_validate_reports_problems(self):
        good = Publication("Smith", 2020, "T", "J", "P")
        self.assertEqual(good.validate, {})
        bad = Publication("", 1000, "", "J", "")
        self.assertEqual(sorted(bad.validate), ["authors", "publisher", "title", "year"])

    def test_render_and_templates(self):
        pub = Publication("Smith and Jones", 2020, "T", "J", "Elsevier")
        self.assertEqual(pub.render("{authors} ({year}). {title}"), "Smith and Jones (2020). T.pdf")
        self.assertEqual(str(pub), "Smith and Jones (2020). T. J. Elsevier.pdf")
        with self.assertRaises(Exception):
            validate_name_template("{nonsense}")

    def test_authors_variants(self):
        self.assertTrue(str(Publication("A, B, C", 2020, "T", "J", "P")).startswith("A et al."))
        self.assertTrue(str(Publication("A & B", 2020, "T", "J", "P")).startswith("A and B"))
        self.assertIn("2020", str(Publication("   ", 2020, "T", "J", "P")))   # blank authors do not crash


class TestPathsAndVerbosity(TmpDirCase):
    def test_dirs_honour_xdg(self):
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.tmp / "c"), "XDG_STATE_HOME": str(self.tmp / "s")}):
            self.assertEqual(paths.cache_dir().parent, self.tmp / "c")
            self.assertEqual(paths.log_dir().parent, self.tmp / "s")

    def test_other_platforms_and_unwritable_home_fall_back(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertIn("Library", str(paths._base_dir("cache")))
            self.assertIn("Logs", str(paths._base_dir("log")))
        with mock.patch.object(sys, "platform", "win32"), mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:/L"}):
            self.assertEqual(paths._base_dir("cache"), Path("C:/L"))
        with mock.patch.object(Path, "mkdir", side_effect=[OSError("ro"), None]):
            self.assertEqual(paths._ensure(self.tmp / "x").name, "nameit")

    def test_verbosity_levels(self):
        self.addCleanup(verbosity.set_verbosity, verbosity.NORMAL)
        self.assertEqual(verbosity.configure_output(silent=True), verbosity.SILENT)
        self.assertEqual(verbosity.configure_output(verbose=True), verbosity.VERBOSE)
        self.assertEqual(verbosity.configure_output(very_verbose=True), verbosity.VERY_VERBOSE)
        self.assertEqual(verbosity.configure_output(), verbosity.NORMAL)
        verbosity.set_verbosity(verbosity.VERY_VERBOSE)
        with mock.patch.object(verbosity.console, "print") as printed:
            verbosity.vprint("x")
            verbosity.vvprint("y")
            try:
                1 / 0
            except ZeroDivisionError:
                verbosity.vv_exception()
        self.assertEqual(printed.call_count, 3)
        verbosity.set_verbosity(verbosity.NORMAL)
        with mock.patch.object(verbosity.console, "print") as printed:
            verbosity.vprint("x")
            verbosity.vvprint("y")
            verbosity.vv_exception()
        printed.assert_not_called()


class TestConfigErrors(TmpDirCase):
    def test_invalid_toml_and_unreadable(self):
        bad = self.tmp / ".nameitrc"
        bad.write_text("format = = broken")
        with self.assertRaises(config.ConfigError):
            config.load_config(self.tmp)
        with self.assertRaises(config.ConfigError):
            config.load_config(explicit=self.tmp / "missing.toml")
        with mock.patch.object(Path, "open", side_effect=PermissionError("no")), self.assertRaises(config.ConfigError):
            config._read(bad)


class TestApiHelpers(TmpDirCase):
    def test_iter_pdf_files(self):
        (self.tmp / "sub").mkdir()
        for name in ("a.pdf", "B.PDF", "c.txt", "sub/d.pdf"):
            (self.tmp / name).write_bytes(b"x")
        flat = [p.name for p in api.iter_pdf_files(self.tmp, False)]
        deep = [p.name for p in api.iter_pdf_files(self.tmp, True)]
        self.assertEqual(sorted(flat), ["B.PDF", "a.pdf"])
        self.assertEqual(sorted(deep), ["B.PDF", "a.pdf", "d.pdf"])
        self.assertEqual(list(api.iter_pdf_files(self.tmp / "a.pdf", False)), [self.tmp / "a.pdf"])

    def test_unique_and_target_paths(self):
        (self.tmp / "x.pdf").write_bytes(b"1")
        (self.tmp / "x (1).pdf").write_bytes(b"1")
        self.assertEqual(api.unique_target_path(self.tmp / "x.pdf").name, "x (2).pdf")
        self.assertEqual(api.unique_target_path(self.tmp / "y.pdf", [self.tmp / "y.pdf"]).name, "y (1).pdf")
        self.assertEqual(api.target_path_for(self.tmp / "o.pdf", "a/b").name, "a_b.pdf")
        self.assertEqual(api.target_path_for(self.tmp / "o.pdf", "name.PDF").name, "name.PDF")

    def test_rename_pdf_file(self):
        src = self.tmp / "o.pdf"
        src.write_bytes(b"1")
        self.assertEqual(api.rename_pdf_file(src, "o.pdf"), src)                      # already named
        (self.tmp / "n.pdf").write_bytes(b"2")                                       # clash gets a suffix
        self.assertEqual(api.rename_pdf_file(src, "n").name, "n (1).pdf")

    def test_input_folder(self):
        (self.tmp / "a").mkdir()
        (self.tmp / "b").mkdir()
        (self.tmp / "a" / "1.pdf").write_bytes(b"x")
        (self.tmp / "b" / "2.pdf").write_bytes(b"x")
        self.assertEqual(api.input_folder([self.tmp / "a" / "1.pdf", self.tmp / "b" / "2.pdf"]).resolve(),
                         self.tmp.resolve())
        self.assertEqual(api.input_folder(self.tmp / "a").resolve(), (self.tmp / "a").resolve())

    def test_plan_reports_invalid_and_unchanged(self):
        tiny = self.tmp / "tiny.pdf"
        tiny.write_bytes(b"%PDF-1.4 tiny")
        text = self.tmp / "notes.txt"
        text.write_text("x")
        plans = api.plan_rename([tiny, text], methods=("pdf-metadata",))
        self.assertEqual([p.status for p in plans], ["skipped", "skipped"])
        self.assertIn("small", plans[0].reason)
        self.assertEqual(plans[1].reason, "not a pdf file")

    def test_plan_unchanged_when_already_named(self):
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")
        first = api.plan_rename(self.tmp, methods=("layout",))[0]
        first.source.rename(first.target)
        again = api.plan_rename(self.tmp, methods=("layout",))[0]
        self.assertEqual(again.status, "unchanged")

    def test_plan_rejects_unknown_method(self):
        with self.assertRaises(ValueError):
            api.plan_rename(self.tmp, methods=("magic",))

    def test_git_mv_failures_fall_back(self):
        src, dst = self.tmp / "a.pdf", self.tmp / "b.pdf"
        src.write_bytes(b"x")
        with mock.patch.object(api.shutil, "which", return_value=None):
            self.assertFalse(api.git_mv(src, dst))
        untracked = subprocess.CompletedProcess([], 1)
        with mock.patch.object(api.shutil, "which", return_value="git"), \
                mock.patch.object(api.subprocess, "run", return_value=untracked):
            self.assertFalse(api.git_mv(src, dst))
        refused = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1, stderr=b"nope")]
        with mock.patch.object(api.shutil, "which", return_value="git"), \
                mock.patch.object(api.subprocess, "run", side_effect=refused):
            self.assertFalse(api.git_mv(src, dst))
        with mock.patch.object(api.shutil, "which", return_value="git"), \
                mock.patch.object(api.subprocess, "run", side_effect=OSError("boom")):
            self.assertFalse(api.git_mv(src, dst))
        ok = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0)]
        with mock.patch.object(api.shutil, "which", return_value="git"), \
                mock.patch.object(api.subprocess, "run", side_effect=ok):
            self.assertTrue(api.git_mv(src, dst))

    def test_undo_skips_missing_and_clashing(self):
        gone, clash_now, clash_orig = self.tmp / "gone.pdf", self.tmp / "now.pdf", self.tmp / "orig.pdf"
        clash_now.write_bytes(b"1")
        clash_orig.write_bytes(b"2")
        log = self.tmp / "undo.json"
        log.write_text(json.dumps([{"from": str(self.tmp / "x.pdf"), "to": str(gone), "git": False},
                                   {"from": str(clash_orig), "to": str(clash_now), "git": False}]))
        self.assertEqual(api.undo_renames(log), [])
        self.assertTrue(clash_now.exists() and clash_orig.exists())


class TestCliHelpers(TmpDirCase):
    def test_normalize_path(self):
        self.assertEqual(cli.normalize_path("a/b"), Path("a/b"))
        self.assertEqual(cli.normalize_path(Path("a")), Path("a"))
        with self.assertRaises(TypeError):
            cli.normalize_path(None)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            cli.normalize_path(3.5)  # type: ignore[arg-type]

    def test_remove_invalid_characters(self):
        self.assertEqual(cli.remove_invalid_characters("a:b/c*d é"), "a_b_c_d é")

    def test_internet_check(self):
        good = mock.MagicMock()
        with mock.patch.object(cli.requests, "Session") as session:
            session.return_value.__enter__.return_value.get.return_value = good
            self.assertTrue(cli.is_there_internet_access())
        for error in (requests.ConnectionError("x"), requests.Timeout("t")):
            with mock.patch.object(cli.requests, "Session") as session:
                session.return_value.__enter__.return_value.get.side_effect = error
                self.assertFalse(cli.is_there_internet_access())
        bad = mock.MagicMock()
        bad.raise_for_status.side_effect = requests.HTTPError("503")
        with mock.patch.object(cli.requests, "Session") as session:
            session.return_value.__enter__.return_value.get.return_value = bad
            self.assertFalse(cli.is_there_internet_access())

    def test_print_plan_covers_all_statuses(self):
        plans = [api.RenamePlan(Path("a.pdf"), Path("A.pdf"), "layout", api.STATUS_RENAME, agreement="2/3 agree"),
                 api.RenamePlan(Path("b.pdf"), Path("b.pdf"), "crossref", api.STATUS_UNCHANGED, "already named"),
                 api.RenamePlan(Path("c.pdf"), reason="no metadata found")]
        with cli.console.capture() as capture:
            cli.print_plan(plans, dry_run=True)
        text = capture.get()
        for needle in ("A.pdf", "already named", "skipped: no metadata found", "layout (2/3 agree)", "Dry run"):
            self.assertIn(needle, text)

    def test_undo_flag_restores(self):
        src = self.tmp / "orig.pdf"
        moved = self.tmp / "moved.pdf"
        moved.write_bytes(b"x")
        log = self.tmp / "undo.json"
        log.write_text(json.dumps([{"from": str(src), "to": str(moved), "git": False}]))
        self.assertEqual(cli.main(["--undo", str(log)]), 0)
        self.assertTrue(src.exists() and not moved.exists())

    def test_unreadable_undo_log_is_reported_not_a_traceback(self):
        self.assertEqual(cli.main(["--undo", str(self.tmp / "absent.json")]), 1)
        broken = self.tmp / "broken.json"
        broken.write_text("{not json")
        self.assertEqual(cli.main(["--undo", str(broken)]), 1)
        wrong_shape = self.tmp / "shape.json"
        wrong_shape.write_text('[{"nothing": 1}]')
        self.assertEqual(cli.main(["--undo", str(wrong_shape)]), 1)

    def test_config_warnings_and_recursive_from_rc(self):
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")
        (self.tmp / ".nameitrc").write_text('recursive = true\nunknown_key = 1\n')
        with cli.console.capture() as capture:
            args = cli.parse_and_validate_arguments(["-p", str(self.tmp)])
        self.assertTrue(args.recursive)
        self.assertIn("unknown_key", capture.get())

    def test_git_summary_note_for_untracked_files(self):
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")
        with cli.console.capture() as capture:
            code = cli.main(["-l", "--git", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertIn("not tracked by git", capture.get())

    def test_python_dash_m_entry_point(self):
        with mock.patch.object(sys, "argv", ["nameit", "--undo", str(self.tmp / "nope.json")]), \
                self.assertRaises(SystemExit) as ctx:
            runpy.run_module("nameit", run_name="__main__")
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
