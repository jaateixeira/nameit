import argparse
import os
import unittest

from rich import print
from rich.style import Style
from rich.text import Text

from NameIt import valid_path  # If renamed to NameIt.py

print("\033[31mRED\033[0m \033[32mGREEN\033[0m")  # Should show colored words


class RichTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        print(Text(f"✓ {test._testMethodName}", style="bold green"))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(Text(f"✗ {test._testMethodName} failed: {err[1]}", style="bold red"))

    def addError(self, test, err):
        super().addError(test, err)
        print(Text(f"⚠ {test._testMethodName} errored: {err[1]}", style="bold yellow"))

class TestPathValidator(unittest.TestCase):
    def setUp(self):
        """Create test data (files/dirs)."""
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "unit_tests_data")
        os.makedirs(self.test_data_dir, exist_ok=True)

        # Valid PDF
        self.valid_pdf = os.path.join(self.test_data_dir, "valid.pdf")
        with open(self.valid_pdf, "wb") as f:
            f.write(b"%PDF-valid")

        # Invalid PDF (wrong header)
        self.invalid_pdf = os.path.join(self.test_data_dir, "invalid.pdf")
        with open(self.invalid_pdf, "wb") as f:
            f.write(b"NOT_A_PDF")

        # Empty directory
        self.empty_dir = os.path.join(self.test_data_dir, "empty_dir")
        os.makedirs(self.empty_dir, exist_ok=True)

        # Non-empty directory
        self.non_empty_dir = os.path.join(self.test_data_dir, "non_empty_dir")
        os.makedirs(self.non_empty_dir, exist_ok=True)
        with open(os.path.join(self.non_empty_dir, "dummy.pdf"), "wb") as f:
            f.write(b"%PDF-dummy")

    def test_valid_pdf(self):
        """Accept valid PDF file."""
        self.assertEqual(valid_path(self.valid_pdf), self.valid_pdf)

    def test_invalid_pdf_header(self):
        """Reject .pdf file with invalid header."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(self.invalid_pdf)

    def test_empty_dir(self):
        """Reject empty directory."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(self.empty_dir)

    def test_non_empty_dir(self):
        """Accept non-empty directory."""
        self.assertEqual(valid_path(self.non_empty_dir), self.non_empty_dir)

    def test_nonexistent_path(self):
        """Reject nonexistent path."""
        fake_path = os.path.join(self.test_data_dir, "ghost.pdf")
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(fake_path)

    def test_wildcards(self):
        """Reject paths with wildcards."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(os.path.join(self.test_data_dir, "*.pdf"))

    def test_pdf_with_missing_dash_in_header(self):
        """Reject PDF with header '%PDF' (missing '-')."""
        path = os.path.join(self.test_data_dir, "broken_header.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDFInvalid")  # Missing '-'
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)

    def test_pdf_with_leading_whitespace(self):
        """Accept PDF with leading whitespace before '%PDF-'."""
        path = os.path.join(self.test_data_dir, "whitespace_header.pdf")
        with open(path, "wb") as f:
            f.write(b"  \n%PDF-valid")  # Whitespace allowed
        self.assertEqual(valid_path(path), path)  # Should pass

    def test_pdf_header_not_at_start(self):
        """Reject PDF where '%PDF-' appears after byte 0."""
        path = os.path.join(self.test_data_dir, "late_header.pdf")
        with open(path, "wb") as f:
            f.write(b"Garbage%PDF-")  # Header not at start
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)

    def test_symlink_to_valid_pdf(self):
        """Accept symlink pointing to a valid PDF."""
        pdf_path = os.path.join(self.test_data_dir, "valid_link_target.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-valid")

        symlink_path = os.path.join(self.test_data_dir, "valid_link.pdf")
        os.symlink(pdf_path, symlink_path)
        self.assertEqual(valid_path(symlink_path), symlink_path)  # Should resolve

    def test_symlink_to_invalid_pdf(self):
        """Reject symlink pointing to an invalid PDF."""
        invalid_path = os.path.join(self.test_data_dir, "invalid_link_target.pdf")
        with open(invalid_path, "wb") as f:
            f.write(b"NOT_A_PDF")

        symlink_path = os.path.join(self.test_data_dir, "invalid_link.pdf")
        os.symlink(invalid_path, symlink_path)
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(symlink_path)

    def test_unreadable_pdf_file(self):
        """Reject PDF with no read permissions."""
        path = os.path.join(self.test_data_dir, "no_permission.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-valid")
        os.chmod(path, 0o000)  # No permissions
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)
        os.chmod(path, 0o644)  # Restore permissions (for cleanup)

    def test_empty_pdf_file(self):
        """Reject empty .pdf file (0 bytes)."""
        path = os.path.join(self.test_data_dir, "empty.pdf")
        open(path, "wb").close()  # Create 0-byte file
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)

    def test_corrupted_pdf(self):
        """Reject corrupted PDF with valid header but invalid content."""
        path = os.path.join(self.test_data_dir, "corrupted.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-")  # Valid header
            f.write(os.urandom(100))  # Random garbage
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)  # Fails if deeper validation is added

    def test_pdf_with_version_header(self):
        """Accept PDF with version header (e.g., '%PDF-1.4')."""
        path = os.path.join(self.test_data_dir, "versioned.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\nvalid")
        self.assertEqual(valid_path(path), path)

    def test_pdf_with_binary_garbage(self):
        """Reject PDF with binary data before header."""
        path = os.path.join(self.test_data_dir, "binary_garbage.pdf")
        with open(path, "wb") as f:
            f.write(b"\x89PNG\x0D\x0A%PDF-")  # PNG header sneaks in
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)

    def test_zip_renamed_to_pdf(self):
        """Reject .zip file renamed to .pdf."""
        path = os.path.join(self.test_data_dir, "fake.pdf")
        with open(path, "wb") as f:
            f.write(b"PK\x03\x04")  # ZIP header
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(path)

    def test_argparse_integration(self):
        """Test valid_path as an argparse type."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--file", type=valid_path)

        # Valid PDF
        args = parser.parse_args(["--file", self.valid_pdf])
        self.assertEqual(args.file, self.valid_pdf)

        # Invalid PDF
        with self.assertRaises(SystemExit):  # argparse exits on error
            parser.parse_args(["--file", self.invalid_pdf])



if __name__ == "__main__":
    # Print a header for clarity
    from rich.console import Console
    console = Console()
    console.rule("[bold]Running Unit Tests")

    # Run tests with rich-colored output
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPathValidator)
    runner = unittest.TextTestRunner(resultclass=RichTestResult, verbosity=2)
    runner.run(suite)

    # Print a summary footer
    console.rule("[bold]Test Summary")
