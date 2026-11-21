"""`.nameitrc` configuration (TOML).

Lookup order, later files override earlier ones, command-line flags override everything:

    1. ~/.nameitrc                      (your defaults)
    2. <folder being renamed>/.nameitrc (per-collection settings)
    or just the file given with --config.

Example::

    format = "{authors} ({year}). {title}. {publication}. {publisher}"
    methods = ["crossref", "pdf-metadata"]   # tried in this order
    recursive = true
    git = true                               # rename tracked files with `git mv`
    crossref_mailto = "you@example.org"      # identifies you to Crossref's faster "polite" pool
"""
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from nameit.api import METHOD_CROSSREF, METHOD_LAYOUT, METHOD_PDF_METADATA
from nameit.models.data_models import validate_name_template

CONFIG_FILE_NAME = ".nameitrc"
KNOWN_KEYS = {"format", "methods", "recursive", "crossref_mailto", "git"}
KNOWN_METHODS = (METHOD_CROSSREF, METHOD_PDF_METADATA, METHOD_LAYOUT)


class ConfigError(Exception):
    """A .nameitrc file is unreadable or contains an invalid value."""


@dataclass
class Config:
    name_format: Optional[str] = None
    methods: Optional[List[str]] = None
    recursive: bool = False
    use_git: bool = False
    crossref_mailto: Optional[str] = None
    sources: List[Path] = field(default_factory=list)       # files that were read
    warnings: List[str] = field(default_factory=list)       # e.g. unknown keys


def _read(path: Path) -> Dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: not valid TOML ({e})") from e
    except OSError as e:
        raise ConfigError(f"{path}: cannot be read ({e})") from e


def _apply(config: Config, path: Path, data: Dict[str, Any]) -> None:
    for key in sorted(set(data) - KNOWN_KEYS):
        config.warnings.append(f"{path}: unknown setting '{key}' ignored (known: {', '.join(sorted(KNOWN_KEYS))})")

    if "format" in data:
        try:
            validate_name_template(data["format"])
        except ValueError as e:
            raise ConfigError(f"{path}: format: {e}") from e
        config.name_format = data["format"]

    if "methods" in data:
        methods = data["methods"]
        if not (isinstance(methods, list) and methods and all(m in KNOWN_METHODS for m in methods)):
            raise ConfigError(f"{path}: methods must be a non-empty list drawn from {list(KNOWN_METHODS)}")
        config.methods = list(dict.fromkeys(methods))  # drop duplicates, keep order

    if "recursive" in data:
        if not isinstance(data["recursive"], bool):
            raise ConfigError(f"{path}: recursive must be true or false")
        config.recursive = data["recursive"]

    if "git" in data:
        if not isinstance(data["git"], bool):
            raise ConfigError(f"{path}: git must be true or false")
        config.use_git = data["git"]

    if "crossref_mailto" in data:
        mailto = data["crossref_mailto"]
        if not (isinstance(mailto, str) and "@" in mailto):
            raise ConfigError(f"{path}: crossref_mailto must be an email address")
        config.crossref_mailto = mailto

    config.sources.append(path)


def load_config(target: Optional[Path] = None, explicit: Optional[Path] = None) -> Config:
    """Load and merge the configuration files that apply to `target` (a file or folder)."""
    config = Config()
    if explicit is not None:
        if not explicit.is_file():
            raise ConfigError(f"{explicit}: config file not found")
        _apply(config, explicit, _read(explicit))
        return config

    candidates = [Path.home() / CONFIG_FILE_NAME]
    if target is not None:
        folder = target if target.is_dir() else target.parent
        candidates.append(folder / CONFIG_FILE_NAME)
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not candidate.is_file():
            continue
        seen.add(resolved)
        _apply(config, candidate, _read(candidate))
    return config


# The Crossref lookup (in another module) needs the mailto without threading the config through every call.
_active_mailto: Optional[str] = None


def set_active_mailto(mailto: Optional[str]) -> None:
    global _active_mailto
    _active_mailto = mailto


def crossref_mailto() -> Optional[str]:
    """Config value, else the NAMEIT_MAILTO environment variable, else None (anonymous pool)."""
    return _active_mailto or os.environ.get("NAMEIT_MAILTO") or None
