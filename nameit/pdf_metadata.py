"""Build a Publication from the metadata embedded in a PDF (``-p`` mode).

Embedded metadata is incomplete and sometimes wrong, so this module is strict
about what it accepts: a usable title, at least one author and a plausible
year are required; the journal is taken from the ``subject`` field only when it
looks like a citation line (``Journal Name, 7 (2023) 100818. doi:...``);
the publisher is rarely present and falls back to a placeholder.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional

import pymupdf

from nameit.models.data_models import Publication

UNKNOWN_PUBLICATION = "Unknown publication"
UNKNOWN_PUBLISHER = "Unknown publisher"

# Titles that word processors and PDF writers put in when nobody filled it in.
_JUNK_TITLE = re.compile(
    r"^(untitled|document\d*|microsoft word\b.*|.*\.(docx?|tex|pdf|indd|qxd)|"
    r"title|paper|article|manuscript|\s*)$",
    re.IGNORECASE,
)
_YEAR_IN_SUBJECT = re.compile(r"\((\d{4})\)|,\s*(\d{4})\b|\b(?:19|20)(\d{2})\b")
_JOURNAL_IN_SUBJECT = re.compile(r"^\s*(.{3,100}?),\s*(?:\d|https?:|doi\b)", re.IGNORECASE)
_AUTHOR_SPLIT = re.compile(r"\s*(?:;|,|\band\b|&)\s*")


def _usable_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    title = " ".join(title.split())
    return None if _JUNK_TITLE.match(title) else title


def _family_names(author_field: Optional[str]) -> List[Dict[str, str]]:
    """'K. Janani; S. Ramamoorthy' -> [{'family': 'Janani'}, {'family': 'Ramamoorthy'}]."""
    if not author_field:
        return []
    families = []
    for name in _AUTHOR_SPLIT.split(author_field.strip()):
        parts = name.split()
        if parts:
            families.append({"family": parts[-1]})
    return families


def _year(subject: str, creation_date: str) -> Optional[int]:
    """Prefer a year written in the citation line; fall back to the PDF creation date."""
    candidates = []
    match = re.search(r"\((\d{4})\)", subject) or re.search(r",\s*((?:19|20)\d{2})\b", subject)
    if match:
        candidates.append(int(match.group(1)))
    created = re.match(r"D:(\d{4})", creation_date or "")
    if created:
        candidates.append(int(created.group(1)))
    for year in candidates:
        if 1900 <= year <= datetime.now().year:
            return year
    return None


def _journal(subject: str) -> str:
    match = _JOURNAL_IN_SUBJECT.match(subject or "")
    return match.group(1).strip() if match else UNKNOWN_PUBLICATION


def extract_publication_from_pdf_metadata(pdf_file: str) -> Optional[Publication]:
    """Return a Publication built from embedded metadata, or None if it is not good enough."""
    from nameit.crossref import format_author_names  # lazy: avoids importing the Crossref stack

    try:
        with pymupdf.open(pdf_file) as doc:
            meta = doc.metadata or {}
    except Exception:  # unreadable/corrupt PDF: let the caller report "no metadata"
        return None

    title = _usable_title(meta.get("title"))
    families = _family_names(meta.get("author"))
    subject = meta.get("subject") or ""
    year = _year(subject, meta.get("creationDate", ""))
    if not (title and families and year):
        return None

    return Publication(
        authors=format_author_names(families),
        year=year,
        title=title,
        publication=_journal(subject),
        publisher=UNKNOWN_PUBLISHER,
    )
