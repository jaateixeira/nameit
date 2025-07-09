#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pep 8 - suggests standard imports first, then third-party libraries, then local imports.

from utils.unified_console import console
from loguru import logger
from rich import print as rprint
from rich.logging import RichHandler

# Remove the default logger
logger.remove()

# Add RichHandler to the loguru logger for console output
logger.add(
    RichHandler(console=console, show_time=True, show_path=True, rich_tracebacks=True),
    format="{message}",
    level="DEBUG",
)

# Add a file handler for logging to a file
logger.add(
    "app.log",  # Log file name
    format="{time} | {level} | {message}",  # Customize the log format
    level="DEBUG",  # Set the desired logging level
    rotation="10 MB",  # Rotate log file when it reaches 10 MB
    compression="zip",  # Compress rotated log files
)


def log_messages() -> None:
    rprint("\n\t [green] Testing logger messages:\n")

    # Log messages at different levels
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

    rprint("\n")
    return None


if __name__ == '__main__':
    console.print("[bold blue] Welcome to [blink] ScrapLogGit2Net unified logger [/blink]![/bold blue] Let's go .. ")
    console.print("[bold blue] \n You can log messages to terminal or separate log file")
    log_messages()
