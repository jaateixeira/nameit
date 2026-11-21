"""Output levels for the NameIt console (built on rich).

    -s   SILENT        nothing except real errors
    (default) NORMAL   progress bar for batches, the rename table and a summary
    -v   VERBOSE       + one line per step (DOI found, Crossref answered, name chosen) and warnings
    -vv  VERY_VERBOSE  + rich tables of raw/validated Crossref data, debug logs, tracebacks
"""
from typing import Any

from rich.table import Table

from nameit.utils.unified_console import console
from nameit.utils.unified_logger import set_console_level

SILENT = -1
NORMAL = 0
VERBOSE = 1
VERY_VERBOSE = 2

_level = NORMAL


def set_verbosity(level: int) -> None:
    """Set the output level and the matching console log level."""
    global _level
    _level = level
    set_console_level({SILENT: "NONE", NORMAL: "ERROR", VERBOSE: "WARNING", VERY_VERBOSE: "DEBUG"}[level])


def get_verbosity() -> int:
    return _level


def configure_output(verbose: bool = False, very_verbose: bool = False, silent: bool = False) -> int:
    """Translate the -v / -vv / -s flags into a level and apply it."""
    level = SILENT if silent else VERY_VERBOSE if very_verbose else VERBOSE if verbose else NORMAL
    set_verbosity(level)
    return level


def vprint(*objects: Any, **kwargs: Any) -> None:
    """Print at -v and above."""
    if _level >= VERBOSE:
        console.print(*objects, **kwargs)


def vvprint(*objects: Any, **kwargs: Any) -> None:
    """Print at -vv only."""
    if _level >= VERY_VERBOSE:
        console.print(*objects, **kwargs)


def vv_exception() -> None:
    """Show the current exception as a rich traceback at -vv only."""
    if _level >= VERY_VERBOSE:
        console.print_exception(show_locals=False, extra_lines=2)


def key_value_table(title: str, rows: "list[tuple[str, str]]") -> Table:
    """Two-column rich table used for the raw/validated metadata dumps."""
    table = Table(title=title, header_style="bold magenta")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for field, value in rows:
        table.add_row(field, value)
    return table
