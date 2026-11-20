"""Per-user locations for NameIt's cache and log files (never the working directory)."""
import os
import sys
from pathlib import Path


def _base_dir(kind: str) -> Path:
    """kind is 'cache' or 'log'."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / ("Caches" if kind == "cache" else "Logs")
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    if kind == "cache":
        return Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
    return Path(os.environ.get("XDG_STATE_HOME", home / ".local" / "state"))


def _ensure(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:  # read-only home, containers, ...: fall back to the temp dir
        import tempfile
        fallback = Path(tempfile.gettempdir()) / "nameit"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def cache_dir() -> Path:
    return _ensure(_base_dir("cache") / "nameit")


def log_dir() -> Path:
    return _ensure(_base_dir("log") / "nameit")
