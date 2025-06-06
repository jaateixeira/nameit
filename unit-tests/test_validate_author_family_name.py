

import argparse
import os
import unittest

from rich import print
from rich.style import Style
from rich.text import Text

from NameIt import validate_author_family_name  # If renamed to NameIt.py

print("\033[31mRED\033[0m \033[32mGREEN\033[0m")  # Should show colored words


class ColorfulTestResult(unittest.TextTestResult):
    """Custom test result class with rich colorized output"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.console = Console()
        self.test_table = Table(title="Test Results", show_header=True, header_style="bold magenta")
        self.test_table.add_column("Test", style="cyan")
        self.test_table.add_column("Status", justify="right")
        self.test_table.add_column("Time", justify="right")
        self.test_table.add_column("Details", style="yellow")

    def startTest(self, test):
        super().startTest(test)
        self._test_start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.time() - self._test_start_time
        self.test_table.add_row(
            str(test),
            Text("PASS", style="bold green"),
            f"{elapsed:.3f}s",
            ""
        )

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = time.time() - self._test_start_time
        self.test_table.add_row(
            str(test),
            Text("FAIL", style="bold red"),
            f"{elapsed:.3f}s",
            str(err[1])
        )

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = time.time() - self._test_start_time
        self.test_table.add_row(
            str(test),
            Text("ERROR", style="bold white on red"),
            f"{elapsed:.3f}s",
            str(err[1])
        )

    def printErrors(self):
        """Print all errors in a rich formatted way"""
        self.console.print(self.test_table)

        if self.failures or self.errors:
            print("\n[bold]Failure Details:[/bold]")
            for test, err in self.failures + self.errors:
                print(f"\n[red]FAIL: {test.id()}[/red]")
                print(f"[yellow]{err}[/yellow]")


class TestValidateAuthorFamilyName(unittest.TestCase):

    def test_valid_names(self):
        """Test valid family names including spaces and UTF-8 characters"""
        self.assertTrue(validate_author_family_name("de Van"))
        self.assertTrue(validate_author_family_name("van der Waals"))
        self.assertTrue(validate_author_family_name("González Martínez"))
        self.assertTrue(validate_author_family_name("Åkesson Lindgren"))
        self.assertTrue(validate_author_family_name("Hernández-López y Castillo"))
        self.assertTrue(validate_author_family_name("O'Conchúir na Coille"))
        self.assertTrue(validate_author_family_name("Li"))  # Short but valid
        self.assertTrue(validate_author_family_name("Déspreaux de la Roche"))
        self.assertTrue(validate_author_family_name("Nguyễn Văn An"))
        self.assertTrue(validate_author_family_name("Ærø Sørensen"))

    def test_invalid_type(self):
        """Test non-string inputs"""
        with self.assertRaises(TypeError):
            validate_author_family_name(123)
        with self.assertRaises(TypeError):
            validate_author_family_name(None)
        with self.assertRaises(TypeError):
            validate_author_family_name([])

    def test_empty_string(self):
        """Test empty or whitespace-only names"""
        with self.assertRaises(ValueError):
            validate_author_family_name("")
        with self.assertRaises(ValueError):
            validate_author_family_name("  ")
        with self.assertRaises(ValueError):
            validate_author_family_name("\t\n")

    def test_too_short(self):
        """Test names that are too short"""
        with self.assertRaises(ValueError):
            validate_author_family_name("A")  # Too short
        with self.assertRaises(ValueError):
            validate_author_family_name(" - ")  # Punctuation only

    def test_invalid_characters(self):
        """Test names with invalid characters"""
        with self.assertRaises(ValueError):
            validate_author_family_name("Sm1th")  # Contains number
        with self.assertRaises(ValueError):
            validate_author_family_name("O'Brien@")  # Contains symbol
        with self.assertRaises(ValueError):
            validate_author_family_name("Doe?")  # Contains punctuation

    def test_capitalization(self):
        """Test improper capitalization"""
        with self.assertRaises(ValueError):
            validate_author_family_name("garcía lópez")  # Lowercase first letter
        with self.assertRaises(ValueError):
            validate_author_family_name("müller van den berg")  # Lowercase first letter
        with self.assertRaises(ValueError):
            validate_author_family_name("íñigo montoya")  # Lowercase accented first letter

    def test_special_cases(self):
        """Test special cases and edge cases"""
        # Valid names with prefixes
        self.assertTrue(validate_author_family_name("van den Berg"))
        self.assertTrue(validate_author_family_name("de la Rosa"))

        # Invalid names
        with self.assertRaises(ValueError):
            validate_author_family_name("O''Reilly")  # Double apostrophe
        with self.assertRaises(ValueError):
            validate_author_family_name("Jean--Luc")  # Double hyphen
        with self.assertRaises(ValueError):
            validate_author_family_name("van  der Meer")  # Double space


# Usage
if __name__ == "__main__":
    import time
    from rich import print

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.discover('tests')

    # Run with colorful output
    runner = unittest.TextTestRunner(
        resultclass=ColorfulTestResult,
        verbosity=3,
        descriptions=True
    )
    runner.run(suite)
