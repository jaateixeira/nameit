"""Importable NameIt API.

    from nameit import rename_pdf, plan_rename

    plan = plan_rename("papers/", methods=("crossref", "pdf-metadata"), recursive=True)
    for item in plan:
        print(item.source.name, "->", item.target and item.target.name, item.reason)

``plan_rename`` never touches the file system (apart from reading PDFs and, for the
Crossref method, the network); ``apply_plan`` performs the renames and writes an undo log.
"""
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Union

ProgressCallback = Callable[[Path, int, int], None]  # (file, zero-based index, total)

from nameit.models.exceptions import InvalidNameItPath
from nameit.models.types import PathLike
from nameit.utils.unified_logger import logger
from nameit.utils.validators import is_pdf_file, is_valid_path

METHOD_CROSSREF = "crossref"
METHOD_PDF_METADATA = "pdf-metadata"
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

def _extract_crossref(pdf_file: str):
    from nameit.crossref import extract_publication_metadata_from_crossref_using_doi_in_pdf
    return extract_publication_metadata_from_crossref_using_doi_in_pdf(pdf_file)


def _extract_pdf_metadata(pdf_file: str):
    from nameit.pdf_metadata import extract_publication_from_pdf_metadata
    return extract_publication_from_pdf_metadata(pdf_file)


EXTRACTORS: Dict[str, Callable[[str], object]] = {
    METHOD_CROSSREF: _extract_crossref,
    METHOD_PDF_METADATA: _extract_pdf_metadata,
}


# -------------------------------------------------------------------- planning

def plan_rename(path: PathLike,
                methods: Sequence[str] = (METHOD_CROSSREF,),
                recursive: bool = False,
                progress: Optional[ProgressCallback] = None) -> List[RenamePlan]:
    """Work out the new name of every PDF at `path` without renaming anything.

    Methods are tried in the given order; the first that yields a publication wins.
    `progress(file, index, total)` is called before each file is examined.
    """
    unknown = [m for m in methods if m not in EXTRACTORS]
    if unknown:
        raise ValueError(f"Unknown method(s) {unknown}; choose from {sorted(EXTRACTORS)}")

    root = Path(path)
    if not root.exists():
        raise InvalidNameItPath(root, "path does not exist", "check the path")
    if root.is_file() and not is_pdf_file(root):
        return [RenamePlan(root, reason="not a pdf file")]

    plans: List[RenamePlan] = []
    reserved: List[Path] = []
    pdf_files = list(iter_pdf_files(root, recursive))
    for index, pdf in enumerate(pdf_files):
        if progress:
            progress(pdf, index, len(pdf_files))
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

        wanted = target_path_for(pdf, str(publication))
        if wanted == pdf:
            plans.append(RenamePlan(pdf, pdf, used, STATUS_UNCHANGED, "already named"))
            continue
        target = unique_target_path(wanted, reserved)
        reserved.append(target)
        plans.append(RenamePlan(pdf, target, used, STATUS_RENAME))
    return plans


# -------------------------------------------------------------------- applying

def apply_plan(plans: Sequence[RenamePlan], write_undo_log: bool = True,
               log_dir: Optional[PathLike] = None) -> Optional[Path]:
    """Perform the planned renames. Returns the undo-log path (None if nothing was renamed).

    The undo log goes into `log_dir` (default: the folder of the first renamed file).
    """
    done = []
    for item in plans:
        if item.status != STATUS_RENAME or item.target is None:
            continue
        item.source.rename(item.target)
        done.append({"from": str(item.source), "to": str(item.target)})
        logger.info(f"renamed {item.source} -> {item.target}")

    if not (done and write_undo_log):
        return None
    target_dir = Path(log_dir) if log_dir else Path(done[0]["to"]).parent
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
        current.rename(original)
        restored.append(original)
    return restored


def rename_pdf(path: PathLike,
               methods: Sequence[str] = (METHOD_CROSSREF,),
               dry_run: bool = False,
               recursive: bool = False) -> List[RenamePlan]:
    """Plan and (unless dry_run) apply renames for a PDF file or a folder of PDFs."""
    plans = plan_rename(path, methods, recursive)
    if not dry_run:
        root = Path(path)
        apply_plan(plans, log_dir=root if root.is_dir() else root.parent)
    return plans
