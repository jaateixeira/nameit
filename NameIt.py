#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pep 8 - suggests standard imports first, then third-party libraries, then local imports.

import re
import string
import subprocess
import sys
import os
import argparse
import unicodedata

# For file type identification and MIME type detection
# Ensures we are dealing with pdf files
import magic

# 4 Dynamic module loading
from typing import Optional, Any

from NameItCrossRef import extract_metadata_from_crossref_using_doi_in_pdf
from utils.unified_logger import logger
from utils.unified_console import console


def is_pdf_file(file_path: str) -> bool:
    mime = magic.from_file(file_path, mime=True)
    return mime == 'application/pdf'


def validate_no_wildcards(path: str):
    if re.search(r'[\*\?\[\]]', path):
        raise argparse.ArgumentTypeError("Wildcards (*, ?, []) are not allowed. Provide a literal path.")
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Path '{path}' does not exist.")
    return path


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


class InvalidNameItPath(Exception):
    def __init__(self, path):
        """

        @type path: object
        """
        super().__init__(f"Directory  or file '{path}' is invalid. \n Is it a pdf file or a folder with pdf files?")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="NameIt is a software tool that renames research articles in pdf files in a standardised way.",
        epilog="[dim]Created with ❤️ using Python[/dim]")

    parser.add_argument("path", help="Path to PDF file or folder containing PDFs", type=valid_path)

    # Logging level options
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("-v", "--verbose", action="store_true",
                           help="Enable verbose logging (INFO level)")
    log_group.add_argument("-vv", "--very-verbose", action="store_true",
                           help="Enable very verbose logging (DEBUG level)")
    log_group.add_argument("-s", "--silent", action="store_true",
                           help="Disable all logging output")

    # Metadata source options
    meta_group = parser.add_mutually_exclusive_group()
    meta_group.add_argument("-p", "--use-pdf-metadata", action="store_true",
                            help="Use PDF embedded metadata only",
                            )
    meta_group.add_argument("-c", "--use-crossref", action="store_true",
                            help="Use Crossref API (default)", default=True)
    meta_group.add_argument("-l", "--use-layoutlmv3", action="store_true",
                            help="Use LayoutLMv3 model for extraction")

    return parser.parse_args()


# Checking for internet connection
def check_internet_access():
    try:
        subprocess.check_call(["ping", "-c", "1", "google.com"])
        return True
    except subprocess.CalledProcessError:
        return False


# Limiting filenames to valid characters
def remove_invalid_characters(text):
    valid_characters = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleaned_text = ''.join(
        c if c in valid_characters or unicodedata.category(c) in ('Mn', 'Mc', 'Ll', 'Lu', 'Lt', 'Lo') else '_'
        for c in text
    )
    return cleaned_text


# Validate that the author field is a string
def validate_author(author: str):
    if not isinstance(author, str):
        logger.error(f"Author is not a string: {author}")
        return False
    return True


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

    # Check minimum length (reduced to 2 to accommodate names like "Li")
    if len(stripped_name.replace(" ", "")) < 2:
        error_msg = f"Author family name must have at least 2 non-space characters, got '{stripped_name}'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Check for invalid characters
    valid_categories = {'Ll', 'Lu', 'Lt', 'Lo', 'Lm', 'Mn', 'Mc', 'Nd'}
    valid_punctuation = {"-", "'", " "}  # Added space as valid

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
        # Skip empty parts (shouldn't happen due to earlier checks)
        if not part:
            continue

        # Special handling for prefixes like "de", "van", "von" (optional)
        lowercase_prefixes = {"de", "van", "von", "di", "del", "della"}
        if part.lower() in lowercase_prefixes:
            continue

        # Check if the first alphabetic character is uppercase
        first_letter = next((c for c in part if c.isalpha()), None)
        if first_letter and not first_letter.isupper():
            error_msg = f"Name part '{part}' should start with an uppercase letter: '{stripped_name}'"
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


# Validate that the title field is a string
def validate_title(title):
    if not isinstance(title, str):
        logger.error(f"Title is not a string: {title}")
        return False
    return True


# Validate that the publisher field is a string
def validate_publisher(publisher):
    if not isinstance(publisher, str):
        logger.error(f"Publisher is not a string: {publisher}")
        return False
    return True


# Validate that the year field is a positive integer
def validate_year(year):
    if not isinstance(year, int) or year <= 0:
        logger.error(f"Year is not a positive integer: {year}")
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


# Extracting family name for the authors
def format_author_names(authors):
    logger.info(f"Formatting authors {authors}")

    if len(authors) == 1:
        return authors[0]['family']
    elif len(authors) == 2:
        return f"{authors[0]['family']} and {authors[1]['family']}"
    else:
        return f"{authors[0]['family']} et al."


# Saving required information from the metadata to the file and removing invalid characters
def rename_pdf_file(pdf_file, metadata):
    logger.info(f"renaming pdf file  {pdf_file}")

    if not validate_metadata(metadata):
        return None

    # Todo add description here the cross ref metadata     
    authors = metadata['message']['author']

    logger.info(f"Number of authors found in  metadata {len(authors)}")
    logger.info(f"validating authors metadata {authors}")

    for author in authors:
        logger.info(f"validating author {author}")
        validate_author_family_name(author['family'])

    author_names = format_author_names(authors)

    title = metadata['message']['title'][0]
    if not validate_title(title):
        return None

    year = metadata['message']['issued']['date-parts'][0][0]
    if not validate_year(year):
        return None

    publication = metadata['message']['container-title'][0] if 'container-title' in metadata[
        'message'] else 'Unknown publication'
    if not validate_container_title(publication):
        return None

    publisher = metadata['message']['publisher'] if 'publisher' in metadata['message'] else 'Unknown publisher'
    if not validate_publisher(publisher):
        return None

    cleaned_author_names = remove_invalid_characters(author_names)
    cleaned_title = remove_invalid_characters(title)
    cleaned_year = remove_invalid_characters(str(year))
    cleaned_publication = remove_invalid_characters(publication)
    cleaned_publisher = remove_invalid_characters(publisher)

    max_title_length = 255 - len(cleaned_author_names) - len(str(year)) - len(cleaned_publication) - len(
        cleaned_publisher) - len(" () ... @  - .pdf")

    if len(cleaned_title) <= max_title_length:
        cleaned_title = cleaned_title
    else:
        cleaned_title = cleaned_title[:max_title_length] + "..."

    new_filename = f"{cleaned_author_names} ({cleaned_year}) {cleaned_title} @ {cleaned_publication} - {cleaned_publisher}.pdf"

    os.rename(pdf_file, os.path.join(os.path.dirname(pdf_file), new_filename))
    return new_filename



def process_folder_or_file(path: str, args: argparse.Namespace) -> None:
    """
    Process either a folder or a PDF file based on the given path and arguments.

    For directories, it processes all DPF file within. For PDF files, it extracts metadata
    and optionally renames the file based on the metadata. The specific metadata
    extraction method is determined by the provided arguments.

    Args:
        path (str): The path to either a directory or a PDF file to be processed.
        args (Any): Command line arguments object containing processing options:
            - use_pdf_metadata (bool): Whether to use PDF embedded metadata
            - use_crossref (bool): Whether to use Crossref API
            - use_layoutlmv3 (bool): Whether to use LayoutLMv3 model

    Returns:
        None: This function performs operations but doesn't return a value.

    Raises:
        SystemExit: If an invalid processing method is specified or if the input path is invalid.
    """

    if not valid_path(path):
        raise InvalidNameItPath(path)

    # Test if the path is a directory
    if os.path.isdir(path):
        process_folder(path)

    # Handle PDF file case
    elif os.path.isfile(path) and path.lower().endswith('.pdf'):
        # Verify at least one processing method is specified
        if args.use_pdf_metadata or args.use_crossref or args.use_layoutlmv3:
            pdf_file = path
            metadata = extract_metadata_from_crossref_using_doi_in_pdf(pdf_file)
        else:
            console.print("[red]Method not known.[/red]")
            console.print("[blue]Are you sure you don't want to use pdf metadata? "
                          "or the Crossref API? Or the LayoutLMv3 model?[/blue]")
            sys.exit()

        # Process metadata if found
        if metadata:
            new_file_name = rename_pdf_file(pdf_file, metadata)
            if new_file_name:
                console.print(f"[green]File renamed to: {new_file_name}[/green]")
        else:
            console.print(f"[yellow]DOI not found in {pdf_file}.[/yellow]")
    else:
        console.print("[red]Invalid input. Please provide a valid folder path or PDF file path.[/red]")


# Processing folder
def process_folder(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".pdf"):
                pdf_file = os.path.join(root, file)
                metadata = extract_metadata_from_crossref_using_doi_in_pdf(file)
                if metadata:
                    new_file_name = rename_pdf_file(pdf_file, metadata)
                    if new_file_name:
                        console.print(f"[green]File renamed to: {new_file_name}[/green]")
                else:
                    console.print(f"[yellow]DOI not found in {pdf_file}.[/yellow]")


# Main code
if __name__ == "__main__":

    console.print("\n [bold green]. Parsing arguments")

    args = parse_arguments()

    console.print(f"{args=}")

    if args.use_pdf_metadata:
        console.print("\n [bold green].Taking pdf metadata in consideration")
    if args.use_crossref:
        console.print("\n [bold green].Attempting to find DOIs to call the Crossref API")

    if args.use_layoutlmv3:
        console.print("\n [bold green]. Using LayoutLMv3 to find the required information")

    if args.use_crossref and not args.use_pdf_metadata and not args.use_layoutlmv3 and not check_internet_access():
        console.print(
            "[red]Internet Connection Unavailable. The program requires internet access for Crossref API.[/red]")
        sys.exit(1)

    path = args.path

    process_folder_or_file(path, args)
