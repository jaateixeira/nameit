#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pep 8 - suggests standard imports first, then third-party libraries, then local imports.

import re
import string
import requests
import sys
import unicodedata
import argparse
import os

# To allow functions to accept paths as pathlib paths or str
from pathlib import Path
from typing import Union, Dict

from rich.panel import Panel
from rich.table import Table

from NameItCrossRef import extract_publication_metadata_from_crossref_using_doi_in_pdf
from models.types import PathLike,  Nameit_processing_args

from models.error_model import ErrorModel
from models.exceptions import InvalidNameItPath

from utils.unified_logger import logger
from utils.unified_console import console
from utils.validators import is_valid_path


def normalize_path(nameit_path: Union[str, PathLike]) -> Path:
    """
    Convert input to a Path object regardless of input type.

    Args:
        nameit_path (Union[str, PathLike]): Input path to normalize.

    Returns:
        Path: A pathlib.Path object representing the normalized path.

    Raises:
        TypeError: If the input type is not a string or a path-like object.
    """
    if nameit_path is None:
        raise TypeError("Input path cannot be None.")

    if isinstance(nameit_path, Path):
        return nameit_path

    if isinstance(nameit_path, str):
        return Path(nameit_path)

    # Handle other path-like objects
    try:
        return Path(nameit_path)
    except Exception as e:
        raise TypeError(f"Could not convert input to Path object: {e}. Verify your given opath {nameit_path}")


def validate_no_wildcards(file_path: str):
    if re.search(r'[\*\?\[\]]', file_path):
        raise argparse.ArgumentTypeError("Wildcards (*, ?, []) are not allowed. Provide a literal path.")
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError(f"Path '{file_path}' does not exist.")
    return file_path


def parse_arguments() -> argparse.Namespace:
    """

    @rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="NameIt is a software tool that renames research articles in pdf files in a standardised way.",
        epilog="[dim]Created with ❤️ using Python[/dim]")

    parser.add_argument("path", help="Path to PDF file or folder containing PDFs", type=is_valid_path)

    # Logging level options
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("-v", "--verbose", action="store_true",
                           help="Enable verbose logging (INFO level)")
    log_group.add_argument("-vv", "--very-verbose", action="store_true",
                           help="Enable very verbose logging (DEBUG level)")
    log_group.add_argument("-s", "--silent", action="store_true",
                           help="Disable all logging output")

    # Metadata source options
    meta_group = parser.add_argument_group()
    meta_group.add_argument("-p", "--use-pdf-metadata", action="store_true",
                            help="Use PDF embedded metadata only",
                            )
    meta_group.add_argument("-c", "--use-crossref", action="store_true",
                            help="Use Crossref API (default)")
    meta_group.add_argument("-l", "--use-layoutlmv3", action="store_true",
                            help="Use LayoutLMv3 model for extraction")
    # Support for recursion in directory trees
    parser.add_argument('-r', '--recursive', action='store_true', help='Enable recursive processing')

    # Add the --dry-run option
    parser.add_argument('--dry-run', action='store_true',
                        help='Inspect the given path but take no actions on the filesystem')

    return parser.parse_args()


def is_there_internet_access():
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
    }

    try:
        response = requests.get("http://www.google.com/", headers=headers,timeout=5)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX, 5XX)
        console.print(f"\t Online access to internet [green]checked[/green] ")
        return True
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
        console.print(f"\t Online access to internet [green]failed[/green] ")
        console.print(e)
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
def rename_pdf_file(pdf_file: os.path, new_file_name: str) -> None:
    logger.info(f"renaming pdf file  {pdf_file} to {new_file_name}")

    os.rename(pdf_file, os.path.join(os.path.dirname(pdf_file), new_file_name))

    return None


def process_folder_or_file_dry_run(
        nameit_path: PathLike,
        cli_args: Nameit_processing_args
) -> None:
    """
    Simulates processing by recursively listing all files and directories found at the specified path,
    counting PDF files, and displaying a summary of rename operations that would occur.

    Args:
        nameit_path: The path to a file or directory (accepts str, os.PathLike, or Path)
        cli_args: Parsed command-line arguments with these attributes:
            - recursive (bool): Whether to traverse directories recursively
            - verbose (bool): Show detailed output
            - debug (bool): Show debug information

    Returns:
        Dictionary mapping original paths to their proposed new paths
    """
    # Convert input to Path object regardless of input type
    normalized_path: PathLike = normalize_path(nameit_path)

    file_count: int = 0
    pdf_to_be_renamed: int = 0
    dir_count: int = 0

    rename_operations: dict[PathLike, PathLike] = {}

    # Initialize summary table
    summary_table = Table(title="Dry Run Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    console.print(f"[yellow]DEBUG: Starting dry run for path: {normalized_path}[/yellow]")

    if not normalized_path.exists():
        error_message = f"[red]Error: Path does not exist - {normalized_path}[/red]"
        console.print(error_message)
        raise InvalidNameItPath(normalized_path, error_message, f"check the {normalize_path=} and {nameit_path=}")

    def process_item(process_path: PathLike, depth: int) -> None:
        nonlocal file_count, dir_count, pdf_to_be_renamed
        indent = "  " * depth

        logger.debug(f"\t func call process_item {process_path=} {depth=} ")

        if item.is_dir():
            console.print(f"{indent}[blue]DIR: {item.name}[/blue] {item=}")

            if cli_args.recursive:

                try:
                    for child in item.iterdir():
                        if child.is_dir():

                            console.print(f"{indent}[blue]  Processing recursively DIR: {child}[/blue]")
                            process_item(child, depth + 1)
                        elif child.is_file():
                            process_item(child, depth + 0)

                except PermissionError:
                    if cli_args.debug:
                        console.print(f"{indent}[red]Permission denied: {item}[/red]")

        elif item.is_file():
            file_count += 1
            if item.suffix.lower() == '.pdf':
                pdf_to_be_renamed += 1
                rename_operations[item] = "To be renamed"

                #if cli_args.verbose:
                console.print(f"{indent}[green]PDF: {item.name}[/green] → [yellow]{rename_operations[item]}[/yellow]")
            #elif cli_args.debug:
            else:
                rename_operations[item] = "Not to be renamed"
                console.print(f"{indent}[red]PDF: {item.name}[/red] → [yellow]{rename_operations[item]}[/yellow]")

            #console.print(f"{indent}[dim]FILE: {item.name}[/dim]")

    # Process the initial normalized_path
    if normalized_path.is_file():
        if normalized_path.suffix.lower() == '.pdf':
            file_count += 1
            pdf_to_be_renamed += 1
            rename_operations[normalized_path] = "Single file to be renamed"
            console.print(
                f"[green]PDF: {normalized_path.name}[/green] → [yellow]{rename_operations[normalized_path]}[/yellow]")
    elif normalized_path.is_dir():
        dir_count += 1
        try:
            for item in sorted(normalized_path.iterdir()):
                process_item(item, 0)
        except PermissionError:
            error_message = f"[red]Permission denied accessing directory: {normalized_path}[/red]"
            console.print(error_message)
            raise PermissionError(normalized_path)
    else:
        error_message = f"[red] Neither a file neither a directory: {normalized_path}[/red]"
        console.print(error_message)
        logger.error(error_message)
        sys.exit()

    # Generate summary
    summary_table.add_row("Total Directories", str(dir_count))
    summary_table.add_row("Total Files", str(file_count))
    summary_table.add_row("PDFs to be Renamed", str(pdf_to_be_renamed))

    console.print(Panel(summary_table, title="[bold]Dry Run Results[/bold]"))

    #if cli_args.debug and rename_operations:
    #console.print("\n[bold yellow]DEBUG: Full rename operations list:[/bold yellow]")
    #for old, new in rename_operations.items():
    #    console.print(f"  {old} → {new}")

    return None


def process_folder_or_file(nameit_path: os.PathLike, cli_args: argparse.Namespace) -> None:
    """
    Process either a folder or a PDF file based on the given path and arguments.

    For directories, it processes all DPF file within. For PDF files, it extracts metadata
    and optionally renames the file based on the metadata. The specific metadata
    extraction method is determined by the provided arguments.

    Args:
        nameit_path (os.path): The path to either a directory or a PDF file to be processed.
        cli_args (Any): Command line arguments object containing processing options:
            - use_pdf_metadata (bool): Whether to use PDF embedded metadata
            - use_crossref (bool): Whether to use Crossref API
            - use_layoutlmv3 (bool): Whether to use LayoutLMv3 model

    Returns:
        None: This function performs operations but doesn't return a value.

    Raises:
        SystemExit: If an invalid processing method is specified or if the input path is invalid.
        @param nameit_path:
        @param cli_args:

    """

    # Test if the path is a directory
    if os.path.isdir(nameit_path):
        for root, dirs, files in os.walk(nameit_path):
            # Goes after sub_directories  TODO Add -r to options
            for dir_name in dirs:
                process_folder_or_file(dir_name, cli_args)

            # Goes after files
            for filename in files:
                process_folder_or_file(root + filename, cli_args)

    # Handle if the path is a single pdf file
    elif os.path.isfile(nameit_path) and os.path.lower().endswith('.pdf'):

        try:
            logger.info(f"validating path {nameit_path}")
            if is_valid_path(nameit_path):
                validated_path = nameit_path
                logger.info(f"path {validated_path} is validated without raising exceptions")
            else:
                return None
        except InvalidNameItPath as e:
            error = ErrorModel.capture(e)
            error.display_user_friendly()
            console.print(f"[red] Invalid file path {nameit_path}[/red]")
            console.print(f"[blue] Caught exception:{e}")
            raise InvalidNameItPath(
                path=str(nameit_path),
                reason="Invalid path",
                suggestion="Check file extension, or provide a different file or directory."
            )
        except argparse.ArgumentTypeError as e:
            console.print(f"[red] Argument file path {nameit_path}[/red]")
            console.print(f"[blue] Caught exception:{e}")

        # Verify at least one processing method is specified
        if cli_args.use_pdf_metadata or cli_args.use_crossref or cli_args.use_layoutlmv3:
            pdf_file_path = nameit_path
            extracted_publication_from_crossref_api = (
                extract_publication_metadata_from_crossref_using_doi_in_pdf(str(pdf_file_path)))
        else:
            console.print("[red]Method not known.[/red]")
            console.print("[blue]Are you sure you don't want to use pdf metadata? "
                          "or the Crossref API? Or the LayoutLMv3 model?[/blue]")
            sys.exit()

        # Process metadata if found
        if extracted_publication_from_crossref_api:
            new_file_name = rename_pdf_file(pdf_file_path, str(extracted_publication_from_crossref_api))
            if new_file_name:
                console.print(f"[green]File renamed to: {new_file_name}[/green]")
        else:
            console.print(f"[yellow]DOI not found in {pdf_file_path}.[/yellow]")


def list_files_and_directories(fs_path: PathLike) -> None:
    """
    List files and directories in the given directory.
    If recursive is True, list them recursively.
    """
    console.print(f"[blue]Listing  {fs_path} [/blue] with {args.recursive=}")

    def list_items(directory: Path, depth: int = 0):
        indent = "  " * depth
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    console.print(f"{indent}[blue][DIR][/blue] {item.name}")
                    if args.recursive:
                        list_items(item, depth + 1)
                else:
                    console.print(f"{indent}[green][FILE][/green] {item.name}")
        except PermissionError:
            print(f"{indent}[ERROR] Permission denied: {directory}")

    if fs_path.is_dir():
        list_items(fs_path)
    if fs_path.is_file():
        console.print(f"[green][FILE][/green] {fs_path} is to be renamed")


def parse_and_validate_arguments() -> argparse.Namespace:
    console.print("\n[bold green]Parsing arguments[/bold green]")
    parsed_args: argparse.Namespace = parse_arguments()
    console.print(f"{type(parsed_args)} {parsed_args=}")

    if parsed_args.use_pdf_metadata:
        console.print("\n[bold green]We are going to take pdf own metadata in consideration[/bold green]")

    if parsed_args.use_crossref:
        console.print(
            "\n[bold green]We will attempt find DOIs in the pdf first page to call the Crossref API[/bold green]")
        if not is_there_internet_access():
            console.print(
                "\n [red]Internet Connection Unavailable. The program requires internet access for Crossref API.[/red]")
        sys.exit(1)

    if parsed_args.use_layoutlmv3:
        console.print("\n[bold green]We will use LayoutLMv3 to find the required information[/bold green]")

    return parsed_args


def execute_main_logic() -> None:
    path: PathLike = normalize_path(args.path)
    if args.verbose or args.very_verbose:
        list_files_and_directories(path)
    # process_folder_or_file_dry_run(path, args)
    # process_folder_or_file(path, args)


if __name__ == "__main__":
    args: argparse.Namespace = parse_and_validate_arguments()
    execute_main_logic()
