#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pep 8 - suggests standard imports first, then third-party libraries, then local imports.

import re
import string
import subprocess
import sys
import unicodedata
import argparse
import os


from NameItCrossRef import extract_metadata_from_crossref_using_doi_in_pdf
from models.error_model import ErrorModel
from models.exceptions import InvalidNameItPath

from utils.unified_logger import logger
from utils.unified_console import console
from utils.validators import validate_metadata, validate_author_family_name, validate_title, validate_year, \
    validate_container_title, validate_publisher, valid_path


def validate_no_wildcards(file_path: str):
    if re.search(r'[\*\?\[\]]', file_path):
        raise argparse.ArgumentTypeError("Wildcards (*, ?, []) are not allowed. Provide a literal path.")
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError(f"Path '{file_path}' does not exist.")
    return path


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

    new_filename = (f"{cleaned_author_names}"
                    f" ({cleaned_year})"
                    f" {cleaned_title} "
                    f"@ {cleaned_publication} "
                    f"- {cleaned_publisher}.pdf")

    os.rename(pdf_file, os.path.join(os.path.dirname(pdf_file), new_filename))
    return new_filename


def process_folder_or_file(file_path: str, args: argparse.Namespace) -> None:
    """
    Process either a folder or a PDF file based on the given path and arguments.

    For directories, it processes all DPF file within. For PDF files, it extracts metadata
    and optionally renames the file based on the metadata. The specific metadata
    extraction method is determined by the provided arguments.

    Args:
        file_path (str): The path to either a directory or a PDF file to be processed.
        args (Any): Command line arguments object containing processing options:
            - use_pdf_metadata (bool): Whether to use PDF embedded metadata
            - use_crossref (bool): Whether to use Crossref API
            - use_layoutlmv3 (bool): Whether to use LayoutLMv3 model

    Returns:
        None: This function performs operations but doesn't return a value.

    Raises:
        SystemExit: If an invalid processing method is specified or if the input path is invalid.
        @param args:
        @param file_path:
    """
    try:
        valid_path(file_path)
    except InvalidNameItPath as e:
        error = ErrorModel.capture(e)
        error.display_user_friendly()
        raise InvalidNameItPath(
            path=path,
            reason="Invalid path",
            suggestion="Check file extension, or provide a different file or directory."
        )

    # Test if the path is a directory
    if os.path.isdir(file_path):
        process_folder(file_path)

    # Handle PDF file case
    elif os.path.isfile(file_path) and path.lower().endswith('.pdf'):
        # Verify at least one processing method is specified
        if args.use_pdf_metadata or args.use_crossref or args.use_layoutlmv3:
            pdf_file = file_path
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
        console.print("\n [bold green]. Using LayoutLMv3 to find the required information" )

    if args.use_crossref and not args.use_pdf_metadata and not args.use_layoutlmv3 and not check_internet_access():
        console.print(
            "[red]Internet Connection Unavailable. The program requires internet access for Crossref API.[/red]")
        sys.exit(1)

    path = args.path

    process_folder_or_file(path, args)
