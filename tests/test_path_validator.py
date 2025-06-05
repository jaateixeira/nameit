import argparse
import os
import unittest

from NameIt import valid_path  # If renamed to NameIt.py


class TestNameIt(unittest.TestCase):
    def setUp(self):
        """Create test data (files/dirs)."""
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
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


if __name__ == "__main__":
    unittest.main()
