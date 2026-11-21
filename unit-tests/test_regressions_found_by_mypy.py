"""Regression tests for real bugs that the type-check pass uncovered."""
import unittest

from nameit.models.data_models import Publication
from nameit.utils.validators import (
    validate_author_family_name,
    validate_first_name,
    validate_last_name,
    validate_publication,
    validate_suffix,
)


class TestValidatorsReturnBooleans(unittest.TestCase):
    def test_name_validators_return_real_bools(self):
        for fn, value, expected in [
            (validate_first_name, "Jose", True), (validate_first_name, "   ", False),
            (validate_last_name, "Teixeira", True), (validate_last_name, "", False),
            (validate_suffix, "Jr", True), (validate_suffix, None, True), (validate_suffix, " ", False),
        ]:
            with self.subTest(fn=fn.__name__, value=value):
                self.assertIs(fn(value), expected)


class TestFamilyNameWithoutLetters(unittest.TestCase):
    def test_punctuation_only_part_does_not_crash(self):
        # used to raise AttributeError: 'NoneType' has no attribute 'islower'
        try:
            validate_author_family_name("Smith -")
        except AttributeError as e:  # pragma: no cover - the regression
            self.fail(f"AttributeError raised: {e}")
        except ValueError:
            pass  # rejecting the name is fine; crashing is not


class TestPublicationValidate(unittest.TestCase):
    def test_validate_property_does_not_raise_attribute_error(self):
        pub = Publication(authors="Doe", year=2020, title="T", publication="J", publisher="P")
        self.assertIsInstance(pub.validate, dict)   # used to read the non-existent self.journal

    def test_journal_error_message_is_clean(self):
        errors = validate_publication({"authors": [], "year": 2020, "title": "T", "journal": "", "publisher": "P"})
        self.assertEqual(errors.get("journal"), "Invalid or missing journal.")


if __name__ == "__main__":
    unittest.main()
