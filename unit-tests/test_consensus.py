"""Majority vote, interactive chooser, and the vote/default behaviour of plan_rename and the CLI."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from nameit import api, cli
from nameit.consensus import Candidate, agreement_key, decide
from nameit.interactive import Chooser
from nameit.models.data_models import Publication

SAMPLE = Path(__file__).resolve().parent.parent / "test-data" / "s40537-014-0007-7.pdf"


def pub(authors="Smith", year=2020, title="A Study of Things", journal="Journal of Tests", publisher="Elsevier"):
    return Publication(authors, year, title, journal, publisher)


class TestDecide(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(decide([]))

    def test_three_agree(self):
        d = decide([Candidate("crossref", pub()), Candidate("pdf-metadata", pub()), Candidate("layout", pub())])
        self.assertTrue(d.consensus)
        self.assertEqual((d.label, d.method), ("3/3 agree", "crossref"))

    def test_majority_beats_the_best_ranked_method(self):
        d = decide([Candidate("crossref", pub(title="Wrong Paper Entirely")),
                    Candidate("pdf-metadata", pub()), Candidate("layout", pub())])
        self.assertTrue(d.consensus)
        self.assertEqual(d.method, "pdf-metadata")
        self.assertEqual(d.publication.title, "A Study of Things")
        self.assertEqual(list(d.agreeing), ["pdf-metadata", "layout"])

    def test_no_majority_uses_best_ranked(self):
        d = decide([Candidate("crossref", pub(title="One")), Candidate("pdf-metadata", pub(title="Two")),
                    Candidate("layout", pub(title="Three"))])
        self.assertFalse(d.consensus)
        self.assertEqual((d.label, d.method, d.publication.title), ("no consensus", "crossref", "One"))

    def test_single_source(self):
        d = decide([Candidate("layout", pub())])
        self.assertEqual((d.label, d.method), ("single source", "layout"))

    def test_agreement_ignores_case_punctuation_journal_and_extra_authors(self):
        a = pub(authors="Shah", title="The past: a view", journal="Unknown publication", publisher="Unknown publisher")
        b = pub(authors="Shah et al.", title="THE PAST, A VIEW!", journal="Data Management", publisher="Elsevier")
        self.assertEqual(agreement_key(a), agreement_key(b))
        self.assertNotEqual(agreement_key(a), agreement_key(pub(authors="Jones", title="The past: a view")))
        self.assertNotEqual(agreement_key(a), agreement_key(pub(authors="Shah", year=2021, title="The past: a view")))

    def test_unknown_journal_filled_from_agreeing_method(self):
        d = decide([Candidate("pdf-metadata", pub(journal="Unknown publication", publisher="Unknown publisher")),
                    Candidate("layout", pub(journal="Patterns", publisher="Elsevier"))])
        self.assertEqual((d.publication.publication, d.publication.publisher), ("Patterns", "Elsevier"))


class TestChooser(unittest.TestCase):
    def chooser(self, answers):
        answers = iter(answers)
        return Chooser(Console(quiet=True), lambda c: c.publication.title, ask=lambda prompt: next(answers))

    def setUp(self):
        self.cands = [Candidate("crossref", pub(title="One")), Candidate("pdf-metadata", pub(title="Two")),
                      Candidate("layout", pub(title="Two"))]
        self.decision = decide(self.cands)

    def test_enter_accepts_suggestion(self):
        self.assertEqual(self.chooser([""])(Path("a.pdf"), self.cands, self.decision).method, "pdf-metadata")

    def test_number_picks_that_candidate(self):
        self.assertEqual(self.chooser(["1"])(Path("a.pdf"), self.cands, self.decision).method, "crossref")

    def test_skip(self):
        self.assertIsNone(self.chooser(["s"])(Path("a.pdf"), self.cands, self.decision))

    def test_invalid_answer_is_asked_again(self):
        self.assertEqual(self.chooser(["9", "x", "3"])(Path("a.pdf"), self.cands, self.decision).method, "layout")

    def test_accept_all_stops_asking(self):
        c = self.chooser(["a"])  # a second question would raise StopIteration
        self.assertIsNotNone(c(Path("a.pdf"), self.cands, self.decision))
        self.assertIsNotNone(c(Path("b.pdf"), self.cands, self.decision))

    def test_quit_skips_the_rest(self):
        c = self.chooser(["q"])
        self.assertIsNone(c(Path("a.pdf"), self.cands, self.decision))
        self.assertIsNone(c(Path("b.pdf"), self.cands, self.decision))


class TestInteractiveRun(unittest.TestCase):
    def test_interactive_cli_shows_each_name_with_a_single_pdf_extension(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copy(SAMPLE, tmp / "paper.pdf")
        with mock.patch.object(cli, "is_there_internet_access", return_value=False), \
                mock.patch.object(Console, "input", return_value=""), \
                cli.console.capture() as capture:
            code = cli.main(["-i", str(tmp)])
        self.assertEqual(code, 0)
        self.assertNotIn(".pdf.pdf", capture.get())
        self.assertIn("(suggested)", capture.get())
        self.assertTrue(any(p.name.startswith("Najafabadi") for p in tmp.glob("*.pdf")))


class TestPlanRenameVote(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")

    def plan(self, extractors, **kw):
        with mock.patch.dict(api.EXTRACTORS, extractors, clear=True):
            return api.plan_rename(self.tmp, methods=tuple(extractors), strategy="vote", **kw)[0]

    def test_vote_renames_by_majority_and_records_agreement(self):
        item = self.plan({"crossref": lambda f: pub(title="Wrong"), "pdf-metadata": lambda f: pub(),
                          "layout": lambda f: pub()})
        self.assertEqual((item.status, item.method, item.agreement), ("rename", "pdf-metadata", "2/3 agree"))
        self.assertIn("A Study of Things", item.target.name)

    def test_crashing_method_is_ignored(self):
        def boom(f):
            raise RuntimeError("model exploded")
        item = self.plan({"crossref": boom, "layout": lambda f: pub()})
        self.assertEqual((item.status, item.method), ("rename", "layout"))

    def test_nobody_answers_is_skipped(self):
        item = self.plan({"crossref": lambda f: None, "layout": lambda f: None})
        self.assertEqual(item.status, "skipped")

    def test_chooser_can_skip_or_override(self):
        ex = {"crossref": lambda f: pub(title="One"), "layout": lambda f: pub(title="Two")}
        skipped = self.plan(ex, chooser=lambda pdf, cands, dec: None)
        self.assertEqual((skipped.status, skipped.reason), ("skipped", "skipped by the user"))
        other = self.plan(ex, chooser=lambda pdf, cands, dec: cands[1])
        self.assertEqual((other.method, other.agreement), ("layout", "chosen by user"))

    def test_first_strategy_is_unchanged(self):
        with mock.patch.dict(api.EXTRACTORS, {"crossref": lambda f: pub(title="One"),
                                              "layout": lambda f: pub(title="Two")}, clear=True):
            item = api.plan_rename(self.tmp, methods=("crossref", "layout"))[0]
        self.assertEqual((item.method, item.agreement), ("crossref", ""))

    def test_unknown_strategy_rejected(self):
        with self.assertRaises(ValueError):
            api.plan_rename(self.tmp, strategy="coin-toss")


class TestCliDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(SAMPLE, self.tmp / "paper.pdf")

    def parse(self, *argv, online=True):
        with mock.patch.object(cli, "is_there_internet_access", return_value=online):
            return cli.parse_and_validate_arguments([*argv, str(self.tmp)])

    def test_default_is_all_three_methods_voting(self):
        args = self.parse()
        self.assertEqual(cli.selected_methods(args), ["crossref", "pdf-metadata", "layout"])
        self.assertTrue(args.vote)

    def test_default_offline_votes_between_the_offline_methods(self):
        args = self.parse(online=False)
        self.assertEqual(cli.selected_methods(args), ["pdf-metadata", "layout"])
        self.assertTrue(args.vote)

    def test_explicit_methods_keep_first_wins(self):
        args = self.parse("-c", "-p")
        self.assertFalse(args.vote)

    def test_vote_flag_with_explicit_methods(self):
        self.assertTrue(self.parse("-p", "-l", "--vote").vote)

    def test_not_interactive_without_a_terminal_or_with_yes_or_dry_run(self):
        self.assertFalse(cli.interactive_mode(self.parse()))             # tests run without a tty
        self.assertFalse(cli.interactive_mode(self.parse("-y")))
        self.assertFalse(cli.interactive_mode(self.parse("-i", "-d")))
        self.assertTrue(cli.interactive_mode(self.parse("-i")))

    def test_interactive_in_a_terminal(self):
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("sys.stdout.isatty", return_value=True):
            self.assertTrue(cli.interactive_mode(self.parse()))
            self.assertFalse(cli.interactive_mode(self.parse("-y")))

    def test_default_run_votes_and_renames_without_prompting(self):
        with mock.patch.object(cli, "is_there_internet_access", return_value=False):
            code = cli.main([str(self.tmp)])
        self.assertEqual(code, 0)
        names = [p.name for p in self.tmp.glob("*.pdf")]
        self.assertEqual(len(names), 1)
        self.assertTrue(names[0].startswith("Najafabadi et al. (2015)."), names)   # layout was the only offline source


if __name__ == "__main__":
    unittest.main()
