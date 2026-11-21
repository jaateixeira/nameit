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
from typing import Optional, Sequence, Union, Dict

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from nameit.api import (
    METHOD_CROSSREF, METHOD_LAYOUT, METHOD_PDF_METADATA, STRATEGY_FIRST, STRATEGY_VOTE, STATUS_RENAME, STATUS_SKIPPED, STATUS_UNCHANGED,
    RenamePlan, apply_plan, input_folder, iter_pdf_files, plan_rename, rename_pdf_file, undo_renames,
    unique_target_path,
)
from nameit.config import ConfigError, load_config, set_active_mailto
from nameit.models.data_models import DEFAULT_NAME_TEMPLATE, validate_name_template
from nameit.models.exceptions import InvalidNameItPath
from nameit.models.types import PathLike
from nameit.utils.unified_logger import logger
from nameit.interactive import Chooser

from nameit.utils.verbosity import NORMAL, SILENT, configure_output, get_verbosity, vprint, vvprint
from nameit.utils.unified_console import console
from nameit.utils.validators import is_valid_path


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


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """

    @rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="NameIt is a software tool that renames research articles in pdf files in a standardised way.",
        epilog="[dim]Created with ❤️ using Python[/dim]")

    parser.add_argument("paths", nargs="*", metavar="PATH",
                        help='PDF files, folders with PDFs, or quoted patterns such as "papers/2024*.pdf" '
                             '("**" reaches into subfolders)')
    parser.add_argument("--format", dest="name_format", metavar="TEMPLATE",
                        help='Filename template, e.g. "{authors} ({year}). {title}". Placeholders: '
                             '{authors} {year} {title} {publication} {publisher} {publisher_full}. '
                             'Default: "{authors} ({year}). {title}. {publication}. {publisher}"')
    parser.add_argument("--config", type=Path, metavar="FILE",
                        help="Read this .nameitrc instead of ~/.nameitrc and the one in the target folder")
    parser.add_argument("--git", dest="use_git", action="store_true",
                        help="Rename git-tracked files with `git mv` (history kept, rename staged); "
                             "other files are renamed normally")
    parser.add_argument("--undo", metavar="LOGFILE", type=Path,
                        help="Revert the renames recorded in a .nameit-undo-*.json log and exit")

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
                            help="Use the metadata embedded in the PDF (title, author, year; journal when present)",
                            )
    meta_group.add_argument("-c", "--use-crossref", action="store_true",
                            help="Look up the DOI found in the PDF in the Crossref API (default when no method is given)")
    meta_group.add_argument("-l", "--use-layout", "--use-layoutlmv3", dest="use_layout", action="store_true",
                            help="Read title, authors and year from how the first page looks (font sizes and "
                                 "position). Works offline and without a DOI; use when Crossref is unavailable")
    meta_group.add_argument("--vote", action="store_true",
                            help="With several methods, ask them all and take the majority instead of "
                                 "using the first that answers (the default when no method is given)")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-i", "--interactive", action="store_true",
                            help="Show the suggestions of every method and let you choose, file by file "
                                 "(the default when run in a terminal and no method is given)")
    mode_group.add_argument("-y", "--yes", action="store_true",
                            help="Never ask: use the majority vote (the default in scripts and pipes)")
    # Support for recursion in directory trees
    parser.add_argument('-r', '--recursive', action='store_true', help='Enable recursive processing')

    # Add the --dry-run option
    parser.add_argument('-d','--dry-run', action='store_true',
                        help='Show old -> new names without renaming anything')

    return parser.parse_args(argv)


def is_there_internet_access() -> bool:
    """Return True if Crossref is reachable."""
    try:
        with requests.Session() as s:
            response = s.get("https://api.crossref.org/", timeout=5)
        response.raise_for_status()
        vprint("Crossref is [green]reachable[/green]")
        return True
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
        logger.warning(f"Crossref not reachable: {e}")
        vprint("Crossref is [red]not reachable[/red]")
        vvprint(f"[dim]{e}[/dim]")
        return False
    



    
# Limiting filenames to valid characters
def remove_invalid_characters(text):
    valid_characters = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleaned_text = ''.join(
        c if c in valid_characters or unicodedata.category(c) in ('Mn', 'Mc', 'Ll', 'Lu', 'Lt', 'Lo') else '_'
        for c in text
    )
    return cleaned_text


def interactive_mode(cli_args: argparse.Namespace) -> bool:
    """Ask the user per file? Only with several suggestions to choose from, in a terminal, never in -s / -d."""
    if cli_args.yes or cli_args.dry_run or get_verbosity() == SILENT or len(selected_methods(cli_args)) < 2:
        return False
    if cli_args.interactive:
        return True
    return bool(cli_args.vote and sys.stdin.isatty() and sys.stdout.isatty())


def selected_methods(cli_args: argparse.Namespace) -> list:
    """Order matters: Crossref is authoritative, embedded PDF metadata is the fallback."""
    methods = []
    if cli_args.use_crossref:
        methods.append(METHOD_CROSSREF)
    if cli_args.use_pdf_metadata:
        methods.append(METHOD_PDF_METADATA)
    if cli_args.use_layout:
        methods.append(METHOD_LAYOUT)
    configured = getattr(cli_args, "methods_order", None)  # order set in .nameitrc
    if configured:
        methods = [m for m in configured if m in methods] + [m for m in methods if m not in configured]
    return methods


def apply_configuration(parsed_args: argparse.Namespace) -> None:
    """Merge .nameitrc settings under the command-line flags (flags always win)."""
    try:
        target = input_folder(parsed_args.paths) if parsed_args.paths else None
    except InvalidNameItPath:
        target = None  # the bad path is reported later, with a clearer message
    try:
        config = load_config(target, parsed_args.config)
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(2)

    if get_verbosity() > SILENT:
        for warning in config.warnings:
            console.print(f"[yellow]{warning}[/yellow]")
    if config.sources:
        vprint(f"Configuration read from: {', '.join(str(s) for s in config.sources)}")

    if not parsed_args.name_format:
        parsed_args.name_format = config.name_format
    if config.recursive:
        parsed_args.recursive = True
    if config.use_git:
        parsed_args.use_git = True
    if config.methods and not (parsed_args.use_crossref or parsed_args.use_pdf_metadata or parsed_args.use_layout):
        parsed_args.use_crossref = METHOD_CROSSREF in config.methods
        parsed_args.use_pdf_metadata = METHOD_PDF_METADATA in config.methods
        parsed_args.use_layout = METHOD_LAYOUT in config.methods
        parsed_args.methods_order = config.methods
    set_active_mailto(config.crossref_mailto)


def parse_and_validate_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse the command line, apply defaults and check the chosen methods can work."""
    parsed_args = parse_arguments(argv)

    configure_output(parsed_args.verbose, parsed_args.very_verbose, parsed_args.silent)

    apply_configuration(parsed_args)

    if parsed_args.name_format:
        try:
            validate_name_template(parsed_args.name_format)
        except ValueError as e:
            console.print(f"[red]Invalid --format: {e}[/red]")
            sys.exit(2)

    if parsed_args.undo is None and not parsed_args.paths:
        console.print("[red]A path to a PDF file, a folder or a pattern is required.[/red]")
        sys.exit(2)

    if not (parsed_args.use_crossref or parsed_args.use_pdf_metadata or parsed_args.use_layout):
        # documented default: ask all three methods and let them vote
        parsed_args.use_crossref = parsed_args.use_pdf_metadata = parsed_args.use_layout = True
        parsed_args.vote = True

    if parsed_args.interactive:
        parsed_args.vote = True  # choosing needs every method's suggestion

    if parsed_args.use_crossref and parsed_args.undo is None and not is_there_internet_access():
        if parsed_args.use_pdf_metadata or parsed_args.use_layout:
            console.print("[yellow]Crossref unreachable: using the offline methods only.[/yellow]")
            parsed_args.use_crossref = False
        else:
            console.print("[red]Internet connection unavailable: Crossref lookups need internet access. "
                          "Use -p (PDF metadata) and/or -l (page layout) to work offline.[/red]")
            sys.exit(1)

    return parsed_args


def print_plan(plans: Sequence[RenamePlan], dry_run: bool) -> None:
    """Show what is (or would be) renamed, and why anything is skipped."""
    table = Table(title="Dry run - nothing has been renamed" if dry_run else "Renaming plan",
                  show_lines=False, header_style="bold magenta")
    table.add_column("Current name", overflow="fold")
    table.add_column("New name / reason", overflow="fold")
    table.add_column("Via", style="cyan")
    for item in plans:
        if item.status == STATUS_RENAME:
            via = f"{item.method} ({item.agreement})" if item.agreement else (item.method or "")
            table.add_row(item.source.name, f"[green]{item.target.name if item.target else ''}[/green]", via)
        elif item.status == STATUS_UNCHANGED:
            table.add_row(item.source.name, "[dim]already named[/dim]", item.method or "")
        else:
            table.add_row(item.source.name, f"[yellow]skipped: {item.reason}[/yellow]", "")
    console.print(table)


def plan_with_progress(path: Sequence[str], cli_args: argparse.Namespace) -> list:
    """plan_rename with a rich progress bar (normal output level only: -v/-vv print their own lines)."""
    methods = selected_methods(cli_args)
    strategy = STRATEGY_VOTE if cli_args.vote else STRATEGY_FIRST
    chooser = None
    if interactive_mode(cli_args):
        template = cli_args.name_format or DEFAULT_NAME_TEMPLATE
        chooser = Chooser(console, lambda c: c.publication.render(template) + ".pdf")
    if get_verbosity() != NORMAL or chooser is not None:  # prompts and a live progress bar do not mix
        return plan_rename(path, methods, cli_args.recursive, name_format=cli_args.name_format,
                           strategy=strategy, chooser=chooser)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(),
                  MofNCompleteColumn(), console=console, transient=True) as bar:
        task = bar.add_task("Reading PDFs", total=None)

        def on_progress(pdf: Path, index: int, total: int) -> None:
            bar.update(task, total=total, completed=index, description=f"[cyan]{pdf.name[:60]}[/cyan]")

        return plan_rename(path, methods, cli_args.recursive, progress=on_progress,
                           name_format=cli_args.name_format, strategy=strategy)


def execute_main_logic(cli_args: argparse.Namespace) -> int:
    if cli_args.undo:
        restored = undo_renames(cli_args.undo)
        console.print(f"[green]Restored {len(restored)} file(s).[/green]")
        return 0

    paths = list(cli_args.paths)
    logger.info(f"Processing {paths} with {selected_methods(cli_args)}")

    try:
        plans = plan_with_progress(paths, cli_args)
    except InvalidNameItPath as e:
        console.print(f"[red]{e.reason}: {e.path}[/red]")
        return 1

    if get_verbosity() > SILENT:
        print_plan(plans, cli_args.dry_run)

    renamed = [p for p in plans if p.status == STATUS_RENAME]
    skipped = [p for p in plans if p.status == STATUS_SKIPPED]
    if not cli_args.dry_run:
        log_path = apply_plan(plans, log_dir=input_folder(paths), use_git=cli_args.use_git)
        if get_verbosity() > SILENT:
            via_git = sum(1 for p in renamed if p.via_git)
            git_note = f" ({via_git} with git mv, staged)" if cli_args.use_git else ""
            console.print(f"[green]Renamed {len(renamed)} file(s)[/green]{git_note}, skipped {len(skipped)}.")
            if cli_args.use_git and via_git < len(renamed):
                console.print(f"[yellow]{len(renamed) - via_git} file(s) are not tracked by git "
                              f"(or git is unavailable) and were renamed normally.[/yellow]")
            if log_path:
                console.print(f"Undo with: nameit --undo '{log_path}'")
    elif get_verbosity() > SILENT:
        console.print(f"Would rename {len(renamed)} file(s), skip {len(skipped)}.")

    nothing_usable = not renamed and not any(p.status == STATUS_UNCHANGED for p in plans)
    return 1 if (skipped and nothing_usable) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point (also used by `python -m nameit` and the `nameit` script)."""
    cli_args = parse_and_validate_arguments(argv)
    return execute_main_logic(cli_args)


if __name__ == "__main__":
    sys.exit(main())
