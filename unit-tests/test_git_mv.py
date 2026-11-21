"""--git: rename tracked files with `git mv`. Uses real git repositories in temp folders."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nameit import api, cli, config
from nameit.models.data_models import Publication

BIG = Path(__file__).resolve().parent.parent / "test-data" / "ecis-2025.pdf"
HAVE_GIT = shutil.which("git") is not None


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def fake_extractor():
    counter = iter(range(1, 99))
    return mock.patch.dict(api.EXTRACTORS, {api.METHOD_CROSSREF: lambda p: Publication(
        authors="Smith", year=2020, title=f"Title {next(counter)}", publication="J", publisher="P")})


@unittest.skipUnless(HAVE_GIT, "git is not installed")
class GitTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.org")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "commit.gpgsign", "false")
        shutil.copy(BIG, self.repo / "tracked.pdf")
        shutil.copy(BIG, self.repo / "untracked.pdf")
        git(self.repo, "add", "tracked.pdf")
        git(self.repo, "commit", "-q", "-m", "add paper")

    def status(self) -> str:
        return git(self.repo, "status", "--porcelain")


class TestGitMvApi(GitTestCase):
    def test_tracked_file_is_renamed_by_git_and_staged(self):
        with fake_extractor():
            plans = api.rename_pdf(self.repo / "tracked.pdf", use_git=True)
        self.assertTrue(plans[0].via_git)
        self.assertIn('R  tracked.pdf -> "Smith (2020). Title 1. J. P.pdf"', self.status())

    def test_untracked_file_falls_back_to_plain_rename(self):
        with fake_extractor():
            plans = api.rename_pdf(self.repo / "untracked.pdf", use_git=True)
        self.assertFalse(plans[0].via_git)
        self.assertFalse((self.repo / "untracked.pdf").exists())
        self.assertIn("?? ", self.status())               # still untracked: nothing was staged for it

    def test_without_the_flag_nothing_is_staged(self):
        with fake_extractor():
            api.rename_pdf(self.repo / "tracked.pdf")
        self.assertNotIn("R  ", self.status())            # plain rename: git sees delete + untracked

    def test_mixed_batch(self):
        with fake_extractor():
            plans = api.rename_pdf(self.repo, use_git=True)
        self.assertEqual(sorted(p.via_git for p in plans), [False, True])

    def test_outside_a_repository_it_falls_back(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        shutil.copy(BIG, outside / "a.pdf")
        with fake_extractor():
            plans = api.rename_pdf(outside / "a.pdf", use_git=True)
        self.assertFalse(plans[0].via_git)
        self.assertFalse((outside / "a.pdf").exists())

    def test_missing_git_binary_falls_back(self):
        with fake_extractor(), mock.patch.object(api.shutil, "which", return_value=None):
            plans = api.rename_pdf(self.repo / "tracked.pdf", use_git=True)
        self.assertFalse(plans[0].via_git)
        self.assertFalse((self.repo / "tracked.pdf").exists())

    def test_undo_restores_with_git_for_git_renames(self):
        with fake_extractor():
            api.rename_pdf(self.repo / "tracked.pdf", use_git=True)
        (log,) = self.repo.glob(f"{api.UNDO_LOG_PREFIX}*.json")
        self.assertTrue(json.loads(log.read_text())[0]["git"])
        api.undo_renames(log)
        self.assertTrue((self.repo / "tracked.pdf").exists())
        self.assertNotIn("R  ", self.status())            # back to the committed state for that file
        self.assertNotIn("D ", self.status().replace("?? ", ""))

    def test_old_undo_logs_without_git_key_still_work(self):
        (self.repo / "a.pdf").write_bytes(b"x")
        (self.repo / "b.pdf").write_bytes(b"x")
        log = self.repo / ".nameit-undo-old.json"
        (self.repo / "b.pdf").rename(self.repo / "c.pdf")
        log.write_text(json.dumps([{"from": str(self.repo / "b.pdf"), "to": str(self.repo / "c.pdf")}]))
        api.undo_renames(log)
        self.assertTrue((self.repo / "b.pdf").exists())

    def test_names_starting_with_a_dash_are_not_taken_as_options(self):
        tracked = self.repo / "-weird.pdf"
        shutil.copy(BIG, tracked)
        git(self.repo, "add", "--", "-weird.pdf")
        self.assertTrue(api.git_mv(tracked, self.repo / "normal.pdf"))


class TestGitMvCli(GitTestCase):
    def run_cli(self, *argv):
        with fake_extractor(), mock.patch.object(cli, "is_there_internet_access", return_value=True):
            return cli.main(list(argv))

    def test_flag_stages_the_rename(self):
        self.assertEqual(self.run_cli("--git", str(self.repo / "tracked.pdf")), 0)
        self.assertIn("R  tracked.pdf", self.status())

    def test_nameitrc_can_turn_it_on(self):
        (self.repo / ".nameitrc").write_text("git = true\n")
        self.run_cli(str(self.repo / "tracked.pdf"))
        self.assertIn("R  tracked.pdf", self.status())

    def test_config_rejects_non_boolean(self):
        (self.repo / ".nameitrc").write_text('git = "yes"\n')
        with self.assertRaises(config.ConfigError):
            config.load_config(self.repo)


if __name__ == "__main__":
    unittest.main()
