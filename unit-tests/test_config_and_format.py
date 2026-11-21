"""`.nameitrc` configuration and the --format filename template. Offline."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import nameit.config as config
import nameit.crossref as crossref
from nameit import cli
from nameit.models.data_models import DEFAULT_NAME_TEMPLATE, Publication, validate_name_template
from nameit.utils.verbosity import NORMAL, set_verbosity

DATA = Path(__file__).resolve().parent.parent / "test-data"
PDF = DATA / "s40008-019-0169-8.pdf"   # has good embedded metadata: Yeo (2019) ... Journal of Economic Structures


def pub(**kw):
    base = dict(authors="Smith and Jones", year=2020, title="A: Study/of Things",
                publication="Journal of Tests", publisher="Elsevier")
    base.update(kw)
    return Publication(**base)


class TestTemplate(unittest.TestCase):
    def test_default_template_matches_the_standard(self):
        self.assertEqual(str(pub()), pub().render(DEFAULT_NAME_TEMPLATE))
        self.assertEqual(str(pub()), "Smith and Jones (2020). A Studyof Things. Journal of Tests. Elsevier.pdf")

    def test_custom_template(self):
        self.assertEqual(pub().render("{year} - {authors} - {title}"),
                         "2020 - Smith and Jones - A Studyof Things.pdf")

    def test_publisher_full_vs_short(self):
        p = pub(publisher="Association for Computing Machinery")
        self.assertIn(" ACM.pdf", p.render())
        self.assertIn("Association for Computing Machinery", p.render("{publisher_full}"))

    def test_long_titles_are_trimmed_with_any_template(self):
        name = pub(title="x" * 400).render("{title} ({year})")
        self.assertLessEqual(len(name), 255)
        self.assertTrue(name.endswith("... (2020).pdf"))

    def test_long_name_without_title_placeholder_is_cut(self):
        self.assertLessEqual(len(pub(publication="p" * 400).render("{publication}")), 255)

    def test_invalid_templates_are_rejected(self):
        for bad in ["", "   ", "no placeholders", "{nope}", "{title!r}", "{title:>10}", "{title.__class__}",
                    "{title", "a/{title}", "{0}"]:
            with self.subTest(template=bad), self.assertRaises(ValueError):
                validate_name_template(bad)

    def test_valid_templates_pass(self):
        for good in [DEFAULT_NAME_TEMPLATE, "{authors}-{year}", "{publisher_full}_{title}", "{{literal}} {year}"]:
            with self.subTest(template=good):
                validate_name_template(good)


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.folder = self.tmp / "papers"
        self.folder.mkdir()
        shutil.copy(PDF, self.folder / "paper.pdf")
        patcher = mock.patch.object(Path, "home", return_value=self.home)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(set_verbosity, NORMAL)
        self.addCleanup(config.set_active_mailto, None)

    def write(self, where: Path, text: str) -> Path:
        path = where / ".nameitrc"
        path.write_text(text, encoding="utf-8")
        return path


class TestLoadConfig(ConfigTestCase):
    def test_no_files_gives_defaults(self):
        cfg = config.load_config(self.folder)
        self.assertIsNone(cfg.name_format)
        self.assertEqual(cfg.sources, [])

    def test_project_file_overrides_user_file_key_by_key(self):
        self.write(self.home, 'format = "{year} {title}"\nrecursive = true\n')
        self.write(self.folder, 'format = "{authors} {year}"\n')
        cfg = config.load_config(self.folder)
        self.assertEqual(cfg.name_format, "{authors} {year}")
        self.assertTrue(cfg.recursive)               # still inherited from ~/.nameitrc
        self.assertEqual(len(cfg.sources), 2)

    def test_explicit_file_replaces_the_lookup(self):
        self.write(self.home, 'format = "{year}"\n')
        other = self.tmp / "other.toml"
        other.write_text('format = "{title}"\n')
        self.assertEqual(config.load_config(self.folder, other).name_format, "{title}")

    def test_missing_explicit_file_is_an_error(self):
        with self.assertRaises(config.ConfigError):
            config.load_config(self.folder, self.tmp / "nope.toml")

    def test_bad_toml_and_bad_values_are_clear_errors(self):
        for text in ["format = ", 'format = "{nope}"', 'methods = ["magic"]', 'methods = []',
                     'recursive = "yes"', 'crossref_mailto = "not-an-email"']:
            with self.subTest(text=text):
                self.write(self.folder, text)
                with self.assertRaises(config.ConfigError) as ctx:
                    config.load_config(self.folder)
                self.assertIn(".nameitrc", str(ctx.exception))

    def test_unknown_keys_warn_instead_of_failing(self):
        self.write(self.folder, 'formatt = "{year}"\n')
        cfg = config.load_config(self.folder)
        self.assertEqual(len(cfg.warnings), 1)
        self.assertIn("formatt", cfg.warnings[0])

    def test_duplicate_methods_collapse_keeping_order(self):
        self.write(self.folder, 'methods = ["pdf-metadata", "crossref", "pdf-metadata"]\n')
        self.assertEqual(config.load_config(self.folder).methods, ["pdf-metadata", "crossref"])


class TestCliUsesConfig(ConfigTestCase):
    def names(self):
        return sorted(p.name for p in self.folder.glob("*.pdf"))

    def test_format_flag_renames_with_template(self):
        self.assertEqual(cli.main(["-p", "--format", "{year} - {authors}", str(self.folder)]), 0)
        self.assertEqual(self.names(), ["2019 - Yeo.pdf"])

    def test_nameitrc_in_target_folder_is_picked_up(self):
        self.write(self.folder, 'format = "{authors}_{year}"\n')
        cli.main(["-p", str(self.folder)])
        self.assertEqual(self.names(), ["Yeo_2019.pdf"])

    def test_cli_flag_beats_nameitrc(self):
        self.write(self.folder, 'format = "{authors}_{year}"\n')
        cli.main(["-p", "--format", "{year}", str(self.folder)])
        self.assertEqual(self.names(), ["2019.pdf"])

    def test_methods_from_config_replace_the_crossref_default(self):
        self.write(self.folder, 'methods = ["pdf-metadata"]\n')
        # no -p/-c flags and no internet needed: config selects the offline method
        with mock.patch.object(cli, "is_there_internet_access", side_effect=AssertionError("must not be called")):
            self.assertEqual(cli.main(["-d", str(self.folder)]), 0)

    def test_invalid_format_flag_exits_2_before_touching_files(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["-p", "--format", "{nope}", str(self.folder)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(self.names(), ["paper.pdf"])

    def test_broken_nameitrc_exits_2(self):
        self.write(self.folder, "format = ")
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["-p", str(self.folder)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(self.names(), ["paper.pdf"])

    def test_config_flag_selects_file(self):
        custom = self.tmp / "my.toml"
        custom.write_text('format = "{title}"\n')
        cli.main(["-p", "--config", str(custom), str(self.folder)])
        self.assertTrue(self.names()[0].startswith("The trade policy effect"))


class TestCrossrefMailto(ConfigTestCase):
    def fetch(self):
        mailtos = []

        class FakeCrossref(crossref.Crossref):      # subclass keeps HttpError & co. that the code catches
            def __init__(self, mailto=None, **kwargs):
                mailtos.append(mailto)

            def works(self, ids=None, **kwargs):
                return None                          # -> "no metadata", no network

        with mock.patch.object(crossref, "Crossref", FakeCrossref):
            crossref.fetch_metadata_by_doi("10.1/x")
        return mailtos[-1]

    def test_no_hardcoded_address_by_default(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("NAMEIT_MAILTO", None)
            self.assertIsNone(self.fetch())

    def test_config_mailto_reaches_crossref(self):
        self.write(self.folder, 'crossref_mailto = "me@example.org"\n')
        cli.main(["-p", "-d", str(self.folder)])          # applies the config
        self.assertEqual(self.fetch(), "me@example.org")

    def test_environment_variable_is_the_fallback(self):
        with mock.patch.dict(os.environ, {"NAMEIT_MAILTO": "env@example.org"}):
            self.assertEqual(self.fetch(), "env@example.org")


if __name__ == "__main__":
    unittest.main()
