"""Importable NameIt API.

    from nameit import rename_pdf, plan_rename

    plan = plan_rename("papers/", methods=("crossref", "pdf-metadata"), recursive=True)
    for item in plan:
        print(item.source.name, "->", item.target and item.target.name, item.reason)

``plan_rename`` never touches the file system (apart from reading PDFs and, for the
Crossref method, the network); ``apply_plan`` performs the renames and writes an undo log.
"""
import glob
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Union

from nameit.models.data_models import DEFAULT_NAME_TEMPLATE, Publication, validate_name_template
from nameit.models.exceptions import InvalidNameItPath
from nameit.models.types import PathLike
from nameit.utils.unified_logger import logger
from nameit.utils.validators import is_pdf_file, is_valid_path

ProgressCallback = Callable[[Path, int, int], None]  # (file, zero-based index, total)
PathInput = Union[PathLike, Sequence[PathLike]]      # one path/pattern, or several

METHOD_CROSSREF = "crossref"
METHOD_PDF_METADATA = "pdf-metadata"
METHOD_LAYOUT = "layout"
UNDO_LOG_PREFIX = ".nameit-undo-"

STATUS_RENAME = "rename"
STATUS_UNCHANGED = "unchanged"
STATUS_SKIPPED = "skipped"


@dataclass
class RenamePlan:
    """What NameIt intends to do with one PDF."""
    source: Path
    target: Optional[Path] = None
    method: Optional[str] = None
    status: str = STATUS_SKIPPED
    reason: str = ""
    via_git: bool = False      # set by apply_plan: renamed with `git mv` (and so staged)


# ---------------------------------------------------------------- file helpers

def iter_pdf_files(root: Path, recursive: bool) -> Iterator[Path]:
    """Yield root itself if it is a file, else the PDFs inside it (subfolders only if recursive)."""
    root = Path(root)
    if root.is_file():
        yield root
        return
    entries = root.rglob("*") if recursive else root.iterdir()
    for item in sorted(entries):
        if item.is_file() and item.suffix.lower() == ".pdf":
            yield item


def unique_target_path(target: Path, reserved: Iterable[Path] = ()) -> Path:
    """Return target, or 'name (1).pdf', 'name (2).pdf', ... if it exists or is already reserved."""
    reserved = set(reserved)
    if not target.exists() and target not in reserved:
        return target
    counter = 1
    while True:
        candidate = target.with_name(f"{target.stem} ({counter}){target.suffix}")
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1


def target_path_for(source: PathLike, new_file_name: str) -> Path:
    """Where `source` would be renamed to: same folder, separators neutralised, .pdf ensured."""
    source = Path(source)
    safe_name = new_file_name.replace(os.sep, "_").replace("/", "_")
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    return source.with_name(safe_name)


def rename_pdf_file(pdf_file: PathLike, new_file_name: str) -> Path:
    """Rename pdf_file inside its own directory and return the new path (never overwrites)."""
    source = Path(pdf_file)
    target = target_path_for(source, new_file_name)
    if target == source:
        logger.info(f"{source} already follows the NameIt standard")
        return source
    target = unique_target_path(target)
    logger.info(f"renaming pdf file {source} to {target.name}")
    source.rename(target)
    return target


# ------------------------------------------------------------------ extraction

def _extract_crossref(pdf_file: str) -> Optional[Publication]:
    from nameit.crossref import extract_publication_metadata_from_crossref_using_doi_in_pdf
    return extract_publication_metadata_from_crossref_using_doi_in_pdf(pdf_file)


def _extract_pdf_metadata(pdf_file: str) -> Optional[Publication]:
    from nameit.pdf_metadata import extract_publication_from_pdf_metadata
    return extract_publication_from_pdf_metadata(pdf_file)


def _extract_layout(pdf_file: str) -> Optional[Publication]:
    from nameit.layout import extract_publication_from_layout
    return extract_publication_from_layout(pdf_file)


EXTRACTORS: Dict[str, Callable[[str], Optional[Publication]]] = {
    METHOD_CROSSREF: _extract_crossref,
    METHOD_PDF_METADATA: _extract_pdf_metadata,
    METHOD_LAYOUT: _extract_layout,
}


# ------------------------------------------------------------- inputs / wildcards

_GLOB_CHARS = ("*", "?", "[")


def _as_list(inputs: PathInput) -> List[PathLike]:
    if isinstance(inputs, (str, os.PathLike)):
        return [inputs]
    return list(inputs)


def expand_inputs(inputs: PathInput) -> List[tuple]:
    """Turn paths and glob patterns into [(path, from_pattern)] entries.

    An existing path is taken literally (so a file called ``a[1].pdf`` still works). Otherwise a
    pattern with ``*``, ``?`` or ``[]`` is expanded here, which also makes quoted patterns and
    Windows shells (that do not expand them) work. ``**`` matches subfolders.
    """
    entries: List[tuple] = []
    for item in _as_list(inputs):
        path = Path(os.path.expanduser(str(item)))
        if path.exists():
            entries.append((path, False))
        elif any(c in str(path) for c in _GLOB_CHARS):
            matches = sorted(glob.glob(str(path), recursive=True))
            if not matches:
                raise InvalidNameItPath(path, "no file matches the pattern", "check the pattern and quote it")
            entries.extend((Path(m), True) for m in matches)
        else:
            raise InvalidNameItPath(path, "path does not exist", "check the path")
    return entries


def collect_pdf_files(inputs: PathInput, recursive: bool = False) -> List[tuple]:
    """Resolve inputs to [(pdf_path, explicit)] without duplicates, in the order given.

    `explicit` is True for a file named directly (it is validated and reported if it is not a PDF);
    files found by scanning a folder or by a pattern are only kept when they end in .pdf.
    """
    collected: List[tuple] = []
    seen = set()

    def add(path: Path, explicit: bool) -> None:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            collected.append((path, explicit))

    for path, from_pattern in expand_inputs(inputs):
        if path.is_dir():
            for pdf in iter_pdf_files(path, recursive):
                add(pdf, False)
        elif from_pattern:
            if path.suffix.lower() == ".pdf":
                add(path, False)
        else:
            add(path, True)
    return collected


def input_folder(inputs: PathInput) -> Optional[Path]:
    """The folder that contains everything the inputs refer to (where undo logs and .nameitrc live)."""
    folders = []
    for path, _ in expand_inputs(inputs):
        folders.append(path if path.is_dir() else path.parent)
    if not folders:
        return None
    try:
        return Path(os.path.commonpath([str(f.resolve()) for f in folders]))
    except ValueError:  # different drives on Windows
        return folders[0]


# -------------------------------------------------------------------- planning

def plan_rename(path: PathInput,
                methods: Sequence[str] = (METHOD_CROSSREF,),
                recursive: bool = False,
                progress: Optional[ProgressCallback] = None,
                name_format: Optional[str] = None) -> List[RenamePlan]:
    """Work out the new name of every PDF at `path` without renaming anything.

    `path` is a PDF, a folder, a glob pattern such as "papers/2024*.pdf", or a list of those.

    Methods are tried in the given order; the first that yields a publication wins.
    `progress(file, index, total)` is called before each file is examined.
    `name_format` is a filename template such as "{authors} ({year}). {title}" (see nameit.config).
    """
    validate_name_template(name_format or DEFAULT_NAME_TEMPLATE)
    unknown = [m for m in methods if m not in EXTRACTORS]
    if unknown:
        raise ValueError(f"Unknown method(s) {unknown}; choose from {sorted(EXTRACTORS)}")

    plans: List[RenamePlan] = []
    reserved: List[Path] = []
    pdf_files = collect_pdf_files(path, recursive)
    total = len(pdf_files)
    for index, (pdf, explicit) in enumerate(pdf_files):
        if explicit and not is_pdf_file(pdf):
            plans.append(RenamePlan(pdf, reason="not a pdf file"))
            continue
        if progress:
            progress(pdf, index, total)
        try:
            is_valid_path(pdf)
        except InvalidNameItPath as e:
            plans.append(RenamePlan(pdf, reason=e.reason or "invalid pdf"))
            continue
        except PermissionError as e:
            plans.append(RenamePlan(pdf, reason=str(e)))
            continue

        publication, used = None, None
        for method in methods:
            publication = EXTRACTORS[method](str(pdf))
            if publication:
                used = method
                break
        if not publication:
            plans.append(RenamePlan(pdf, reason=f"no metadata found ({', '.join(methods)})"))
            continue

        wanted = target_path_for(pdf, publication.render(name_format or DEFAULT_NAME_TEMPLATE))
        if wanted == pdf:
            plans.append(RenamePlan(pdf, pdf, used, STATUS_UNCHANGED, "already named"))
            continue
        target = unique_target_path(wanted, reserved)
        reserved.append(target)
        plans.append(RenamePlan(pdf, target, used, STATUS_RENAME))
    return plans


# -------------------------------------------------------------------- applying

def git_mv(source: Path, target: Path) -> bool:
    """Rename a git-tracked file with `git mv` (history kept, rename staged).

    Returns False, having changed nothing, when git is missing, the folder is not a repository,
    or the file is not tracked: the caller then falls back to a plain rename.
    """
    git = shutil.which("git")
    if git is None:
        return False
    folder = str(source.parent)
    try:
        tracked = subprocess.run([git, "-C", folder, "ls-files", "--error-unmatch", "--", source.name],
                                 capture_output=True, timeout=30)
        if tracked.returncode != 0:
            return False
        moved = subprocess.run([git, "-C", folder, "mv", "--", source.name, target.name],
                               capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"git mv failed for {source}: {e}")
        return False
    if moved.returncode != 0:
        logger.warning(f"git mv refused {source}: {moved.stderr.decode(errors='replace').strip()}")
        return False
    return True


def apply_plan(plans: Sequence[RenamePlan], write_undo_log: bool = True,
               log_dir: Optional[PathLike] = None, use_git: bool = False) -> Optional[Path]:
    """Perform the planned renames. Returns the undo-log path (None if nothing was renamed).

    The undo log goes into `log_dir` (default: the folder of the first renamed file).
    With `use_git`, tracked files are renamed with `git mv`; others use a plain rename.
    """
    done = []
    for item in plans:
        if item.status != STATUS_RENAME or item.target is None:
            continue
        item.via_git = use_git and git_mv(item.source, item.target)
        if not item.via_git:
            item.source.rename(item.target)
        done.append({"from": str(item.source), "to": str(item.target), "git": item.via_git})
        logger.info(f"renamed {item.source} -> {item.target}{' (git mv)' if item.via_git else ''}")

    if not (done and write_undo_log):
        return None
    target_dir = Path(log_dir) if log_dir else Path(str(done[0]["to"])).parent
    log_path = target_dir / f"{UNDO_LOG_PREFIX}{datetime.now():%Y%m%d-%H%M%S}.json"
    log_path.write_text(json.dumps(done, indent=2, ensure_ascii=False), encoding="utf-8")
    return log_path


def undo_renames(log_path: PathLike) -> List[Path]:
    """Reverse the renames recorded in an undo log. Returns the restored paths."""
    entries = json.loads(Path(log_path).read_text(encoding="utf-8"))
    restored = []
    for entry in reversed(entries):
        current, original = Path(entry["to"]), Path(entry["from"])
        if not current.exists():
            logger.warning(f"undo: {current} is gone, skipping")
            continue
        if original.exists():
            logger.warning(f"undo: {original} already exists, skipping {current}")
            continue
        if not (entry.get("git") and git_mv(current, original)):
            current.rename(original)
        restored.append(original)
    return restored


def rename_pdf(path: PathInput,
               methods: Sequence[str] = (METHOD_CROSSREF,),
               dry_run: bool = False,
               recursive: bool = False,
               name_format: Optional[str] = None,
               use_git: bool = False) -> List[RenamePlan]:
    """Plan and (unless dry_run) apply renames for PDFs, folders or patterns (see plan_rename)."""
    plans = plan_rename(path, methods, recursive, name_format=name_format)
    if not dry_run:
        apply_plan(plans, log_dir=input_folder(path), use_git=use_git)
    return plans
