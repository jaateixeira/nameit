"""Rename from what the first page looks like (``--layout``): works offline, no DOI needed.

Scientific articles follow a visual convention: the title is the largest text near the top,
the authors are the next lines, and a year appears in a copyright / published / citation line.
This module reads the first page with PyMuPDF (text, font sizes, positions) and applies that
convention. It is a heuristic, not a trained model, so it is deterministic and testable; it is
meant for when Crossref is unreachable or the PDF has no DOI and no useful embedded metadata.

Steps (each is a pure function over `Line` objects, so they can be tested without a PDF):

    read_first_page(pdf)  -> (lines, page_height)
    find_title(lines)     -> (title, last line index)
    find_authors(lines, start)
    find_year(page_text, creation_date)
    find_journal(lines)
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import pymupdf

from nameit.models.data_models import Publication
from nameit.pdf_metadata import (
    UNKNOWN_PUBLICATION, UNKNOWN_PUBLISHER, parse_citation_line, publisher_from_doi, read_raw_metadata,
)


@dataclass(frozen=True)
class Line:
    text: str
    size: float
    y: float


_TOP_FRACTION = 0.6   # title and authors live in the upper part of page 1
_NOT_A_TITLE = re.compile(
    r"\b(journal|proceedings|conference|issn|doi|http|www\.|open access|research article|original|"
    r"article|review|electronic library|association for|university|abstract|keywords|received|accepted|"
    r"copyright|contents lists|available online|check for updates|elsevier|springer|wiley|taylor)\b|^research$",
    re.IGNORECASE,
)
_AFFILIATION = re.compile(
    r"\b(university|universit[aàäy]|department|dept\.|institute|school|faculty|college|laborator|centre|center|"
    r"correspondence|corresponding|e-?mail|hospital|academy)\b|@",
    re.IGNORECASE,
)
_STOP_AUTHORS = re.compile(
    r"\b(abstract|keywords?|received|accepted|published|to cite|introduction|follow this|full list)\b", re.IGNORECASE)
_NAME_TOKEN = re.compile(r"^[A-ZÀ-ÖØ-Þ][\w'’.\-]*$")
_MARKS = re.compile(r"[\d*†‡§¶‖#¹²³⁴⁵⁶⁷⁸⁹⁰]+")
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_YEAR_PATTERNS = [
    re.compile(r"(?:Published|©|Copyright|\(c\))\D{0,3}.{0,30}?\b((?:19|20)\d{2})\b", re.IGNORECASE),
    re.compile(r"\(((?:19|20)\d{2})\)\s*\d"),            # "Journal of X (2015) 2:1"
    re.compile(rf"\b(?:{_MONTHS})\s+((?:19|20)\d{{2}})\b"),
]
_JOURNAL = re.compile(r"\b((?:The\s+)?(?:Journal|Annals|Review|Transactions|Letters)\s+of\s+[A-Z][\w&\- ]{2,60}?)(?=\s*[\(,:.\d]|\s*$)")


def read_first_page(pdf_file: str) -> Tuple[List[Line], float, str]:
    """Lines of page 1 in reading order (duplicates removed), page height and the page text."""
    with pymupdf.open(pdf_file) as doc:
        if len(doc) == 0:
            return [], 0.0, ""
        page = doc[0]
        lines: List[Line] = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = " ".join("".join(s["text"] for s in line["spans"]).split())
                if text:
                    lines.append(Line(text, round(max(s["size"] for s in line["spans"]), 1), line["bbox"][1]))
        seen = set()
        unique = []
        for ln in sorted(lines, key=lambda l: (round(l.y), l.text)):
            key = (ln.text, round(ln.y))
            if key not in seen:
                seen.add(key)
                unique.append(ln)
        return unique, page.rect.height, page.get_text("text")


def find_title(lines: List[Line], page_height: float) -> Optional[Tuple[str, int]]:
    """The largest, consecutive lines in the upper page that do not look like a journal banner."""
    running_head = " ".join(l.text for l in lines if l.y < 0.07 * page_height)
    eligible = [i for i, l in enumerate(lines)
                if l.y < _TOP_FRACTION * page_height and len(l.text) >= 3 and not _NOT_A_TITLE.search(l.text)
                and not (l.y >= 0.07 * page_height and l.text in running_head)]  # journal banner repeats the running head
    if not eligible:
        return None
    biggest = max(lines[i].size for i in eligible)
    start = next(i for i in eligible if lines[i].size >= biggest - 0.5)
    end = start
    while (end + 1 < len(lines) and abs(lines[end + 1].size - lines[start].size) <= 0.5
           and lines[end + 1].y - lines[end].y < 2.2 * lines[start].size
           and not _NOT_A_TITLE.search(lines[end + 1].text)):
        end += 1
    parts = [lines[i].text for i in range(start, end + 1)]
    title = parts[0]
    for part in parts[1:]:
        title = title[:-1] + part if title.endswith("-") and part[:1].islower() else f"{title} {part}"
    return (title, end) if len(title) >= 8 else None


def _names_in(text: str) -> Tuple[List[str], bool]:
    """(valid full names, only_noise) for one line; marks such as 1, *, † are ignored."""
    cleaned = _MARKS.sub(" ", text)
    names: List[str] = []
    junk = False
    for piece in re.split(r"\s*(?:,|;|&|\band\b)\s*", cleaned):
        tokens = [t for t in piece.split() if not re.fullmatch(r"[a-z]", t)]
        if not tokens:
            continue
        if 2 <= len(tokens) <= 5 and all(_NAME_TOKEN.match(t) for t in tokens):
            names.append(" ".join(tokens))
        elif len(" ".join(tokens)) > 2:
            junk = True
    return names, junk


def find_authors(lines: List[Line], title_end: int, page_height: float) -> List[str]:
    authors: List[str] = []
    for line in lines[title_end + 1:title_end + 30]:
        if line.y > _TOP_FRACTION * page_height or _STOP_AUTHORS.search(line.text):
            break
        if _AFFILIATION.search(line.text):
            continue
        if line.text.endswith(".") and len(line.text.split()) > 8:
            break  # a sentence: the abstract has started
        names, junk = _names_in(line.text)
        if names and not junk:
            authors.extend(names)
        elif authors:
            if junk:
                break
    return authors


def find_year(page_text: str, creation_date: str = "") -> Optional[int]:
    now = datetime.now().year
    flat = " ".join(page_text.split())
    for pattern in _YEAR_PATTERNS:
        for match in pattern.finditer(flat):
            year = int(match.group(1))
            if 1900 <= year <= now:
                return year
    created = re.match(r"D:(\d{4})", creation_date or "")
    if created and 1900 <= int(created.group(1)) <= now:
        return int(created.group(1))
    return None


def find_journal(lines: List[Line], page_height: float) -> Optional[str]:
    for line in lines:
        if line.y > 0.35 * page_height:
            break
        match = _JOURNAL.search(line.text)
        if match:
            return match.group(1).strip()
    return None


def extract_publication_from_layout(pdf_file: str) -> Optional[Publication]:
    """Publication guessed from the layout of page 1, or None when title, authors or year are not found."""
    from nameit.crossref import find_doi_in_text, format_author_names  # lazy: avoid the Crossref stack

    try:
        lines, height, text = read_first_page(pdf_file)
    except Exception:  # unreadable PDF
        return None
    if not lines:
        return None
    raw = read_raw_metadata(pdf_file)
    found_title = find_title(lines, height)
    if not found_title:
        return None
    title, title_end = found_title
    names = find_authors(lines, title_end, height)
    year = find_year(text, raw.creation_date if raw else "")
    if not (names and year):
        return None

    citation = parse_citation_line(raw.subject) if raw else None
    journal = (citation.journal if citation and citation.journal else None) or find_journal(lines, height)
    doi = (citation.doi if citation and citation.doi else None) or find_doi_in_text(text)
    return Publication(
        authors=format_author_names([{"family": n.split()[-1]} for n in names]),
        year=year,
        title=title,
        publication=journal or UNKNOWN_PUBLICATION,
        publisher=publisher_from_doi(doi) or UNKNOWN_PUBLISHER,
    )
