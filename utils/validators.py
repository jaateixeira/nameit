from typing import Optional, Dict, List
import os
import argparse
import sys
from datetime import datetime
import unicodedata
import magic

from nameparser import HumanName

from utils.unified_console import console
from utils.unified_logger import logger


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


def validate_family_names_in_metadata_retrieved_from_cross_ref(meta_data_authors: list) -> list:
    #TODO implement it
    return meta_data_authors


def validate_title(title: Optional[str]) -> bool:
    """Validate that the title is either None or a non-empty string.
    @param title:
    @return:
    """
    if title is None:
        return True
    return not (not isinstance(title, str) or not title.strip())


def validate_year(pub_year: int) -> int:
    """Validate that the year is a reasonable value."""
    current_year = datetime.now().year
    if 1900 <= pub_year <= current_year:
        return pub_year
    else:
        raise ValueError("Invalid year provided.")


def validate_journal(journal: str) -> bool:
    """Validate that the journal is a non-empty string."""
    return isinstance(journal, str) and journal.strip()


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


def validate_publisher_name(publisher_name: str) -> str:
    if isinstance(publisher_name, str) and bool(publisher_name.strip()):
        return publisher_name
    else:
        raise ValueError(f"Invalid publisher name provided {publisher_name}")


def is_pdf_file(file_path: str) -> bool:
    mime = magic.from_file(file_path, mime=True)
    return mime == 'application/pdf'


def valid_path(path_to_rename: os.path) -> os.path:
    """
    Validate that the path_to_rename exists, is a file/directory, and meets PDF/directory constraints.

    Ensures:
    1. No wildcards (e.g., `*.pdf`) are present.
    2. The path_to_rename exists on the filesystem.
    3. If a file, it has a `.pdf` extension and a valid PDF header.
    4. If a directory, it is not empty.
    5. If a file, it has at least 2KB <- otherwise is probably not an academic article in pdf

    Args:
        path_to_rename (os.path): Input path_to_rename to validate.

    Returns:
        str: The validated path_to_rename if all checks pass.

    Raises:
        argparse.ArgumentTypeError: If any validation fails, with a descriptive message.
    """

    print(f"UnitTest - Testing valid_path with path_to_rename={path_to_rename}")

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
        # Check file size is at minimum 20KB

        min_pdf_file_size_in_kb = 20

        file_size_in_kb = os.path.getsize(path_to_rename) / 1024

        print(f"UnitTest - file size of path_to_rename={path_to_rename} is {file_size_in_kb} KB")

        if file_size_in_kb < min_pdf_file_size_in_kb:
            raise argparse.ArgumentTypeError(
                f"File '{path_to_rename}' seems took small to be a valid PDF article "
                f"( {file_size_in_kb} < {min_pdf_file_size_in_kb}KB).")

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


def validate_author_family_name(author_family_name: str) -> bool:
    """
    Validate that the input is a valid scientific journal article author's family name.

    The function checks that:
    - The input is a non-empty string
    - The name has at least 2 characters (allowing for short names like "Li")
    - The name contains only valid name characters (letters, spaces, hyphens, apostrophes, and accented chars)
    - Each part of the name is properly capitalized (e.g., "de Van", "von Müller")

    Args:
        author_family_name: The family name to validate

    Returns:
        bool: True if the name is valid, False otherwise

    Raises:
        TypeError: If the input is not a string
        ValueError: If the name fails any validation checks with specific error messages
    """
    # Check if input is a string
    if not isinstance(author_family_name, str):
        error_msg = f"Author family name must be a string, got {type(author_family_name)}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Remove any surrounding whitespace
    stripped_name = author_family_name.strip()

    # Check for empty string
    if not stripped_name:
        error_msg = "Author family name cannot be empty or whitespace only"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # check that there are no digits in the names

    digits = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '0'}

    for digit in digits:
        if digit in stripped_name:
            error_msg = f"Author family name should not contain digits/numbers'{digit}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

    # Check minimum length (reduced to 2 to accommodate names like "Li")
    if len(stripped_name.replace(" ", "")) < 2:
        error_msg = f"Author family name must have at least 2 non-space characters, got '{stripped_name}'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Check for invalid characters
    valid_categories = {'Ll', 'Lu', 'Lt', 'Lo', 'Lm', 'Mn', 'Mc', 'Nd'}
    valid_punctuation = {"-", "'", " "}  # Added space as valid

    invalid_strings = {"''", "--", "  "}

    for invalid_str in invalid_strings:
        if invalid_str in stripped_name:
            error_msg = f"Invalid substring {invalid_str} found in  '{stripped_name}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

    for c in stripped_name:
        # Allow standard name punctuation and spaces
        if c in valid_punctuation:
            continue

        # Check Unicode character categories
        cat = unicodedata.category(c)
        if cat not in valid_categories:
            error_msg = f"Author family name contains invalid character '{c}' in name '{stripped_name}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

    # Check proper capitalization for each part of the name
    name_parts = stripped_name.split()
    for part in name_parts:

        if len(part.strip()) == 0:
            error_msg = f"The part '{part}' is empty in name '{stripped_name}. Should not happen. Fatal error.'"
            logger.error(error_msg)
            sys.exit()
            # raise ValueError(error_msg)

        # Special handling for prefixes like "de", "van", "von" (optional)
        lowercase_prefixes = ["de", "den", "van", "von", "di", "de", "la", "del", "der", "della", "y", "na"]

        # Check if the first alphabetic character is uppercase
        first_letter = next((c for c in part if c.isalpha()), None)

        if first_letter.islower() and part in lowercase_prefixes:
            continue
        elif first_letter.islower() and part not in lowercase_prefixes:
            error_msg = (f"First letter {first_letter} of '{part}' should start with an uppercase letter: "
                         f"'{stripped_name}' {name_parts=} {lowercase_prefixes}")
            logger.error(error_msg)
            raise ValueError(error_msg)

    # All checks passed
    logger.debug(f"Valid author family name: '{stripped_name}'")
    return True


# Validate that the issued field is a positive integer
def validate_issued(issued):
    if not isinstance(issued, int) or issued <= 0:
        logger.error(f"Issued is not a positive integer: {issued}")
        return False
    return True


# Validate that the container-title field is a string
def validate_container_title(container_title):
    if not isinstance(container_title, str):
        logger.error(f"Container-title is not a string: {container_title}")
        return False
    return True


# Validate that the publisher field is a string
def validate_publisher(publisher):
    if not isinstance(publisher, str):
        logger.error(f"Publisher is not a string: {publisher}")
        return False
    return True


# Validate that the fetched metadata contains the required information
def validate_metadata(metadata):
    logger.info("Validating the metadata obtained through crossref.org")

    # Note the year is found in the issued field in the metadata
    # Note also that publication is found in the container-title in the metadata
    required_fields = ['author', 'published', 'container-title', 'title', 'publisher']

    for field in required_fields:
        if field not in metadata['message']:
            logger.error(f"Metadata is missing required field: {field}")
            sys.exit()

        if not metadata['message'][field]:
            logger.error(f"Metadata field is empty: {field}")
            sys.exit()

    # So far only journal article are supported
    if metadata['message']['type'] != 'journal-article':
        logger.error(f"Type of publication is not a journal-article. Not supported.")
        sys.exit()

    logger.info("Metadata have the required fields")
    return True


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
