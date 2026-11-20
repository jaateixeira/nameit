#!/usr/bin/env python3
"""Backwards-compatible launcher: ./NameIt <path> still works from a source checkout."""
import sys

from nameit.cli import main

if __name__ == "__main__":
    sys.exit(main())
