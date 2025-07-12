from typing import Optional, Dict, List
import os
import argparse

import magic

from nameparser import HumanName


def validate_first_name(name: str) -> bool:
    """Validate that the first name is a non-empty string."""
    return isinstance(name, str) and name.strip()

def validate_last_name(name: str) -> bool:
    """Validate that the last name is a non-empty string."""
    return isinstance(name, str) and name.strip()

def validate_suffix(suffix: Optional[str]) -> bool:
    """Validate that the suffix is either None or a non-empty string."""
    if suffix is None:
        return True
    return isinstance(suffix, str) and suffix.strip()

def validate_title(title: Optional[str]) -> bool:
    """Validate that the title is either None or a non-empty string."""
    if title is None:
        return True
    return isinstance(title, str) and title.strip()

def validate_journal(journal: str) -> bool:
    """Validate that the journal is a non-empty string."""
    return isinstance(journal, str) and journal.strip()

def validate_year(year: int) -> bool:
    """Validate that the year is a reasonable value."""
    current_year = 2023  # Update this as necessary
    return isinstance(year, int) and 1900 <= year <= current_year

def validate_author(author: Dict) -> Dict:
    """Validate the components of an author's name using HumanName."""
    errors = {}

    name = HumanName(author.get("full_name", ""))
    if not validate_first_name(name.first):
        errors["first_name"] = "Invalid or missing first name."
    if not validate_last_name(name.last):
        errors["last_name"] = "Invalid or missing last name."
    if not validate_suffix(name.suffix):
        errors["suffix"] = "Invalid suffix."
    if not validate_title(name.title):
        errors["title"] = "Invalid title."

    return errors

def validate_publication(publication: Dict) -> Dict:
    """Validate the structure and content of a publication dictionary."""
    errors = {}

    if "authors" not in publication or not isinstance(publication["authors"], list):
        errors["authors"] = "Invalid or missing authors list."
    else:
        for i, author in enumerate(publication["authors"]):
            author_errors = validate_author(author)
            if author_errors:
                errors[f"author_{i}"] = author_errors

    if "year" not in publication or not validate_year(publication["year"]):
        errors["year"] = "Invalid or missing year."

    if "title" not in publication or not isinstance(publication["title"], str) or not publication["title"].strip():
        errors["title"] = "Invalid or missing title."

    if "journal" not in publication or not validate_journal(publication["journal"]):
        errors["journal"] = "Invalid or missing journal."

    return errors


def is_pdf_file(file_path: str) -> bool:
    mime = magic.from_file(file_path, mime=True)
    return mime == 'application/pdf'


def valid_path(path_to_rename: str) -> str:
    """
    Validate that the path_to_rename exists, is a file/directory, and meets PDF/directory constraints.

    Ensures:
    1. No wildcards (e.g., `*.pdf`) are present.
    2. The path_to_rename exists on the filesystem.
    3. If a file, it has a `.pdf` extension and a valid PDF header.
    4. If a directory, it is not empty.

    Args:
        path_to_rename (str): Input path_to_rename to validate.

    Returns:
        str: The validated path_to_rename if all checks pass.

    Raises:
        argparse.ArgumentTypeError: If any validation fails, with a descriptive message.
    """
    # --- Step 1: Reject wildcards ---
    if any(char in path_to_rename for char in '*?[]'):
        raise argparse.ArgumentTypeError(
            f"Wildcards (*, ?, []) are not allowed in path_to_rename: '{path_to_rename}'. "
            "Provide a literal path_to_rename or quote the argument (e.g., \"*.pdf\")."
        )

    # --- Step 2: Check existence ---
    if not os.path.exists(path_to_rename):
        raise argparse.ArgumentTypeError(f"path_to_rename '{path_to_rename}' does not exist.")

    # --- Step 3: Validate files ---
    if os.path.isfile(path_to_rename):
        # Check extension
        if not path_to_rename.lower().endswith('.pdf'):
            raise argparse.ArgumentTypeError(
                f"File '{path_to_rename}' is not a PDF (expected '.pdf' extension)."
            )
        # Check PDF magic number
        if not is_pdf_file(path_to_rename):
            raise argparse.ArgumentTypeError(
                f"File '{path_to_rename}' is not a valid PDF (missing '%PDF-' header)."
            )

    # --- Step 4: Validate directories ---
    elif os.path.isdir(path_to_rename):
        if not os.listdir(path_to_rename):
            raise argparse.ArgumentTypeError(
                f"Directory '{path_to_rename}' is empty. Provide a non-empty directory."
            )

    # --- Step 5: Reject invalid types (e.g., symlinks, devices) ---
    else:
        raise argparse.ArgumentTypeError(
            f"path_to_rename '{path_to_rename}' is neither a file nor a directory."
        )

    return path_to_rename



if __name__ == "__main__":

    # Example usage
    publication_data = {
    "authors": [{"full_name": "Dr. John von Doe Jr."}, {"full_name": "Jane Smith"}],
    "year": 2022,
    "title": "An Example Title",
    "journal": "Journal of Examples"
    }

    validation_errors = validate_publication(publication_data)
    if not validation_errors:
        print("Publication data is valid.")
    else:
        print("Validation errors:", validation_errors)
