"""fetch_metadata_by_doi: caching, retries and error handling. Offline: habanero is faked."""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import nameit.crossref as crossref
from habanero import RequestError

GOOD = {"message": {
    "author": [{"given": "Jose", "family": "Teixeira"}],
    "issued": {"date-parts": [[2015]]}, "title": ["A title"],
    "container-title": ["A journal"], "publisher": "Springer"}}


class FetchTestCase(unittest.TestCase):
    def setUp(self):
        self.cache = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.cache, ignore_errors=True)
        patcher = mock.patch.object(crossref, "cache_dir", return_value=self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.calls = 0
        self.sleeps = []

    def fake(self, *answers):
        """Crossref fake that returns/raises the given answers in order."""
        answers = list(answers)
        test = self

        class FakeCrossref(crossref.Crossref):
            def __init__(self, mailto=None, **kw):
                pass

            def works(self, ids=None, **kw):
                test.calls += 1
                answer = answers.pop(0) if len(answers) > 1 else answers[0]
                if isinstance(answer, BaseException):
                    raise answer
                return answer

        return mock.patch.object(crossref, "Crossref", FakeCrossref)

    def fetch(self, doi="10.1/x"):
        return crossref.fetch_metadata_by_doi(doi, sleep=self.sleeps.append)


class TestFetch(FetchTestCase):
    def test_good_answer_is_returned_and_cached(self):
        with self.fake(GOOD):
            self.assertEqual(self.fetch(), GOOD)
            self.assertEqual(self.fetch(), GOOD)          # second time: from the cache
        self.assertEqual(self.calls, 1)

    def test_cache_is_case_insensitive_on_the_doi(self):
        with self.fake(GOOD):
            self.fetch("10.1/ABC")
            self.fetch("10.1/abc")
        self.assertEqual(self.calls, 1)

    def test_expired_cache_is_refreshed(self):
        with self.fake(GOOD):
            self.fetch()
            old = time.time() - crossref.CACHE_TTL_SECONDS - 10
            for f in (self.cache / "crossref").glob("*.json"):
                os.utime(f, (old, old))
            self.fetch()
        self.assertEqual(self.calls, 2)

    def test_corrupt_cache_file_is_ignored(self):
        with self.fake(GOOD):
            self.fetch()
            for f in (self.cache / "crossref").glob("*.json"):
                f.write_text("{not json")
            self.assertEqual(self.fetch(), GOOD)
        self.assertEqual(self.calls, 2)

    def test_unknown_doi_404_is_not_retried(self):
        with self.fake(RequestError(404, "Resource not found.")):
            self.assertIsNone(self.fetch())
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.sleeps, [])

    def test_rate_limit_is_retried_with_backoff_then_succeeds(self):
        with self.fake(RequestError(429, "slow down"), RequestError(503, "busy"), GOOD):
            self.assertEqual(self.fetch(), GOOD)
        self.assertEqual(self.calls, 3)
        self.assertEqual(self.sleeps, [1, 2])

    def test_persistent_server_error_gives_up_after_max_attempts(self):
        with self.fake(RequestError(503, "busy")):
            self.assertIsNone(self.fetch())
        self.assertEqual(self.calls, crossref.MAX_ATTEMPTS)

    def test_network_errors_are_retried_and_never_propagate(self):
        with self.fake(ConnectionError("proxy says no")):
            self.assertIsNone(self.fetch())
        self.assertEqual(self.calls, crossref.MAX_ATTEMPTS)

    def test_unusable_records_are_none_and_not_cached(self):
        for bad in [None, {}, {"message": {}}, {"message": {"title": ["t"]}},
                    {"message": {"title": ["t"], "author": [{"given": "A", "family": "B"}]}}]:   # no year
            with self.subTest(bad=bad), self.fake(bad):
                self.assertIsNone(self.fetch("10.1/bad"))
        self.assertEqual(list((self.cache / "crossref").glob("*.json")), [])

    def test_missing_journal_and_publisher_are_still_accepted(self):
        preprint = {"message": {"title": ["t"], "author": [{"given": "A", "family": "B"}],
                                "issued": {"date-parts": [[2021]]}}}
        with self.fake(preprint):
            self.assertEqual(self.fetch("10.1/preprint"), preprint)

    def test_failures_are_not_cached(self):
        with self.fake(RequestError(404, "nope"), GOOD):
            self.assertIsNone(self.fetch())
            self.assertEqual(self.fetch(), GOOD)

    def test_unwritable_cache_does_not_break_the_lookup(self):
        with self.fake(GOOD), mock.patch.object(crossref, "_write_cache", wraps=crossref._write_cache), \
                mock.patch.object(Path, "mkdir", side_effect=OSError("read-only")):
            self.assertEqual(self.fetch(), GOOD)


if __name__ == "__main__":
    unittest.main()
