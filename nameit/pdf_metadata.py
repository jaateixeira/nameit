"""Build a Publication from the metadata embedded in a PDF (``-p`` mode).

Embedded metadata is incomplete and sometimes wrong, so this module is strict
about what it accepts: a usable title, at least one author and a plausible
year are required.

The work is split in small pure steps so each can be tested without a PDF:

    read_raw_metadata(pdf)          -> RawMetadata        (only step that touches the file)
    parse_citation_line(subject)    -> CitationLine       (journal / year / DOI from "Journal, 7 (2023) 100818. doi:...")
    publisher_from_doi(doi)         -> publisher or None  (known DOI prefixes only)
    publication_from_metadata(raw)  -> Publication | None

The PDF ``keywords`` field is read but deliberately not used for the file name:
it holds topic words, not bibliographic data.
"""
import re
from dataclasses import dataclass
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
_JOURNAL_IN_CITATION = re.compile(r"^\s*(.{3,100}?),\s*(?:\d|https?:|doi\b)", re.IGNORECASE)
_YEAR_IN_PARENTHESES = re.compile(r"\(((?:19|20)\d{2})\)")
_YEAR_AFTER_COMMA = re.compile(r",\s*((?:19|20)\d{2})\b")
_DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,}(?:\.\d+)*/[^\s\"'<>]*[^\s\"'<>.,;])")
_AUTHOR_SPLIT = re.compile(r"\s*(?:;|,|\band\b|&)\s*")
_MAX_CITATION_LINE = 250  # longer subjects are abstracts, not citation lines

# DOI registrant prefix -> publisher. Only prefixes seen in practice and certain; unknown prefixes stay unknown.
PUBLISHER_BY_DOI_PREFIX = {
    "10.1016": "Elsevier",
    "10.1080": "Taylor & Francis",
    "10.1186": "Springer",
    "10.1007": "Springer",
    "10.1002": "Wiley",
    "10.1111": "Wiley",
    "10.1108": "Emerald",
    "10.4236": "Scientific Research Publishing",
    "10.1145": "ACM",
    "10.1109": "IEEE",
}


@dataclass(frozen=True)
class RawMetadata:
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creation_date: str = ""


@dataclass(frozen=True)
class CitationLine:
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None


def read_raw_metadata(pdf_file: str) -> Optional[RawMetadata]:
    """Embedded metadata of the PDF, or None when the file cannot be opened."""
    try:
        with pymupdf.open(pdf_file) as doc:
            meta = doc.metadata or {}
    except Exception:  # unreadable/corrupt PDF: let the caller report "no metadata"
        return None
    return RawMetadata(
        title=meta.get("title") or "",
        author=meta.get("author") or "",
        subject=meta.get("subject") or "",
        keywords=meta.get("keywords") or "",
        creation_date=meta.get("creationDate") or "",
    )


def usable_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    title = " ".join(title.split())
    return None if _JUNK_TITLE.match(title) else title


def family_names(author_field: Optional[str]) -> List[Dict[str, str]]:
    """'K. Janani; S. Ramamoorthy' -> [{'family': 'Janani'}, {'family': 'Ramamoorthy'}]."""
    if not author_field:
        return []
    families = []
    for name in _AUTHOR_SPLIT.split(author_field.strip()):
        parts = name.split()
        if parts:
            families.append({"family": parts[-1]})
    return families


def parse_citation_line(subject: str) -> CitationLine:
    """Read 'Journal Name, 7 (2023) 100818. doi:10.x/y' style subjects.

    Subjects that are not citation lines (abstracts, free text) give an empty CitationLine.
    """
    subject = " ".join((subject or "").split())
    if not subject or len(subject) > _MAX_CITATION_LINE:
        return CitationLine()
    journal_match = _JOURNAL_IN_CITATION.match(subject)
    if not journal_match:
        return CitationLine()
    year_match = _YEAR_IN_PARENTHESES.search(subject) or _YEAR_AFTER_COMMA.search(subject)
    doi_match = _DOI_IN_TEXT.search(subject)
    return CitationLine(
        journal=journal_match.group(1).strip(),
        year=int(year_match.group(1)) if year_match else None,
        doi=doi_match.group(1) if doi_match else None,
    )


def publisher_from_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    return PUBLISHER_BY_DOI_PREFIX.get(doi.split("/", 1)[0])


def _plausible(year: Optional[int]) -> bool:
    return year is not None and 1900 <= year <= datetime.now().year


def choose_year(citation: CitationLine, creation_date: str) -> Optional[int]:
    """Prefer the year in the citation line; fall back to the PDF creation date."""
    if _plausible(citation.year):
        return citation.year
    created = re.match(r"D:(\d{4})", creation_date or "")
    if created and _plausible(int(created.group(1))):
        return int(created.group(1))
    return None


def publication_from_metadata(raw: RawMetadata) -> Optional[Publication]:
    """Pure function: a Publication if the metadata is good enough, otherwise None."""
    from nameit.crossref import format_author_names  # lazy: avoids importing the Crossref stack

    title = usable_title(raw.title)
    families = family_names(raw.author)
    citation = parse_citation_line(raw.subject)
    year = choose_year(citation, raw.creation_date)
    if not (title and families and year):
        return None

    return Publication(
        authors=format_author_names(families),
        year=year,
        title=title,
        publication=citation.journal or UNKNOWN_PUBLICATION,
        publisher=publisher_from_doi(citation.doi) or UNKNOWN_PUBLISHER,
    )


def extract_publication_from_pdf_metadata(pdf_file: str) -> Optional[Publication]:
    """Return a Publication built from embedded metadata, or None if it is not good enough."""
    raw = read_raw_metadata(pdf_file)
    return publication_from_metadata(raw) if raw else None
