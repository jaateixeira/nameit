# models/types.py
from typing import Union
import pathlib
import os

# Structure to allow functions to accept paths as pathlib paths or str
PathLike = Union[str, os.PathLike, pathlib.Path]  # All supported path types

