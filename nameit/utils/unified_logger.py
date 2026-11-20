#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pep 8 - suggests standard imports first, then third-party libraries, then local imports.


from loguru import logger
from rich import print as rprint
from rich.logging import RichHandler

from nameit.utils.unified_console import console

from nameit.utils.paths import log_dir

# Remove the default logger
logger.remove()

_console_handler_id = None


def set_console_level(level: str = "WARNING") -> None:
    """(Re)attach the console handler at `level`; use "CRITICAL+1"-style silence via level="NONE"."""
    global _console_handler_id
    if _console_handler_id is not None:
        logger.remove(_console_handler_id)
        _console_handler_id = None
    if level != "NONE":
        _console_handler_id = logger.add(
            RichHandler(console=console, show_time=True, show_path=True, rich_tracebacks=True),
            format="{message}",
            level=level,
        )


# Quiet by default; the CLI raises this with -v (INFO) / -vv (DEBUG) or silences it with -s.
set_console_level("WARNING")

# Full debug log goes to the per-user log directory, not the current working directory.
logger.add(
    str(log_dir() / "nameit.log"),
    format="{time} | {level} | {message}",
    level="DEBUG",
    rotation="10 MB",
    compression="zip",
)


def log_messages() -> None:
    rprint("\n\t [green] Testing logger messages:\n")

    # Log messages at different levels
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")


    # logging exception with logger.error() with full traceback
    try:
        1 + "1"
    except Exception as e:
        logger.error("Error message", stack_info=True, exc_info=True)

    # logging just the exception
    try:
        1 + "1"
    except Exception as e:
        logger.exception(e)

    rprint("\n")
    return None


if __name__ == '__main__':
    console.print("[bold blue] Welcome to [blink] ScrapLogGit2Net unified logger [/blink]![/bold blue] Let's go .. ")
    console.print("[bold blue] \n You can log messages to terminal or separate log file")
    log_messages()
