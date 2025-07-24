# models/types.py

"""
Python type hints (via the typing module or built-in syntax) are annotations that specify the expected data types of variables, function parameters,
and return values, enabling static type checking with tools like mypy or IDE autocompletion without affecting runtime behavior. They include primitives
(int, str), containers (List[int], Dict[str, float]), unions (Union[str, int] or str | int), optionals (Optional[Path]), and advanced patterns like
generics (TypeVar) or protocols for structural typing. Introduced in PEP 484 and enhanced in later Python versions (e.g., | syntax in 3.10), type hints
improve code clarity and catch type-related errors early while remaining optional and erased at runtime.
"""


from typing import Union, Dict
import pathlib
import os
import argparse

"""
The PathLike = Union[str, os.PathLike, pathlib.Path] type annotation allows functions to flexibly accept file paths as strings, os.PathLike objects, or 
pathlib.Path instances, ensuring compatibility across different path representations while enabling static type checking.
"""
PathLike = Union[str, os.PathLike, pathlib.Path]  # All supported path types

"""
nameit_processing_args can be a argparge or a dictionary
When passing a dictionary as a function argument, it's generally a good practice to use type hints to specify the expected types of the keys and values in the dictionary. This can help with code readability and type checking.
In the context of your function, you can use the Dict type from the typing module to specify the type of the dictionary
Dictionary has string keys and values that can be booleans, strings, or integers.
"""
Nameit_processing_args = Union[argparse.Namespace, Dict[str, Union[bool, str, int]]]

