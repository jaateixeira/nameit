import os
import unittest
import argparse
from src.path_validator import valid_path

class TestPathValidator(unittest.TestCase):
    def setUp(self):
        """Create test data (files/dirs) if they don't exist."""
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Create a valid PDF file
        self.valid_pdf = os.path.join(self.test_data_dir, 'valid.pdf')
        with open(self.valid_pdf, 'wb') as f:
            f.write(b'%PDF-This is a valid PDF header.')
        
        # Create an invalid PDF file (.pdf extension but wrong content)
        self.invalid_pdf = os.path.join(self.test_data_dir, 'invalid.pdf')
        with open(self.invalid_pdf, 'wb') as f:
            f.write(b'NOT_A_PDF_HEADER')
        
        # Create an empty directory
        self.empty_dir = os.path.join(self.test_data_dir, 'empty_dir')
        os.makedirs(self.empty_dir, exist_ok=True)
        
        # Create a non-empty directory
        self.non_empty_dir = os.path.join(self.test_data_dir, 'non_empty_dir')
        os.makedirs(self.non_empty_dir, exist_ok=True)
        with open(os.path.join(self.non_empty_dir, 'dummy.pdf'), 'wb') as f:
            f.write(b'%PDF-Dummy')

    def tearDown(self):
        """Clean up test data (optional)."""
        pass

    # --- Test Cases ---
    def test_valid_pdf_file(self):
        """Test that a valid PDF file passes validation."""
        self.assertEqual(valid_path(self.valid_pdf), self.valid_pdf)

    def test_invalid_pdf_extension(self):
        """Test rejection of non-PDF files with .pdf extension."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(self.invalid_pdf)

    def test_non_pdf_file(self):
        """Test rejection of files without .pdf extension."""
        non_pdf_file = os.path.join(self.test_data_dir, 'text.txt')
        with open(non_pdf_file, 'w') as f:
            f.write("Not a PDF.")
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(non_pdf_file)

    def test_empty_directory(self):
        """Test rejection of empty directories."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(self.empty_dir)

    def test_non_empty_directory(self):
        """Test acceptance of non-empty directories."""
        self.assertEqual(valid_path(self.non_empty_dir), self.non_empty_dir)

    def test_nonexistent_path(self):
        """Test rejection of nonexistent paths."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(os.path.join(self.test_data_dir, 'ghost.pdf'))

    def test_wildcards_in_path(self):
        """Test rejection of paths containing wildcards."""
        with self.assertRaises(argparse.ArgumentTypeError):
            valid_path(os.path.join(self.test_data_dir, '*.pdf'))

if __name__ == '__main__':
    unittest.main()
