import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union
from nameparser import HumanName
from nameit.utils.validators import (
    validate_first_name,
    validate_last_name,
    validate_suffix,
    validate_title,
    validate_journal,
    validate_year,
    validate_author,
    validate_publication, validate_author_family_name, validate_publisher
)



@dataclass
class Author:
    """Deprecated: This class is not used in the current version."""
    full_name: str
    first_name: Optional[str] = field(init=False)
    last_name: Optional[str] = field(init=False)
    suffix: Optional[str] = field(init=False)
    author_title: Optional[str] = field(init=False)

    def __post_init__(self):
        name = HumanName(self.full_name)
        self.first_name = name.first
        self.last_name = name.last
        self.suffix = name.suffix
        self.title = name.title

    def validate(self) -> dict:
        return validate_author({"full_name": self.full_name})


def _clean_filename_part(text: str) -> str:
    # Replace forbidden characters with safe equivalents
    return re.sub(r'[\\:*?"<>|/]', '', text).strip()


@dataclass
class Publication:
    authors: str
    year: int
    title: str
    publication: str
    publisher: str

    @property
    def validate(self) -> dict:
        publication_data = {
            "authors": validate_author_family_name(self.authors),
            "year": validate_year(self.year),
            "title": validate_title(self.title),
            "publication": validate_journal(self.publication),
            "publisher": validate_publisher(self.publisher)
        }

        return validate_publication(publication_data)

    def _short_publisher(self) -> str:
        mapping = {
            "Springer International Publishing": "Springer",
            "Sage UK": "Sage",
            "Association for Information Systems": "AIS",
            "Association for Computing Machinery": "ACM",
            "Institute of Electrical and Electronics Engineers": "IEEE",
            "Cambridge": "MIT Press",
            "MIT Press": "MIT Press",
            "Elsevier": "Elsevier",
            "Emerald Group Publishing Limited": "Emerald",
            "Emerald": "Emerald",
        }
        for long, short in mapping.items():
            if long.lower() in self.publisher.lower():
                return short
        return self.publisher  # fallback

    def _format_authors(self) -> str:
        """NameIt standard: one author -> 'Smith'; two -> 'Smith and Jones'; more -> 'Smith et al.'"""
        authors = [a.strip() for a in re.split(r'\s*(?:\band\b|&|,)\s*', self.authors) if a.strip()]
        if not authors:
            return self.authors.strip()

        def surname(name: str) -> str:
            match = re.search(r'([A-ZÅÄÖÁÉÍÓÚÑ][a-zà-ž]*)$', name)
            return match.group(1) if match else name

        if len(authors) > 2:
            return f"{surname(authors[0])} et al."
        return " and ".join(surname(a) for a in authors)

    def __str__(self) -> str:
        author_str = self._format_authors()
        year_str = f"({self.year})"
        publication_str = _clean_filename_part(self.publication)
        publisher_str = self._short_publisher()

        title_clean = _clean_filename_part(self.title)
        base = f"{author_str} {year_str}. {title_clean}. {publication_str}. {publisher_str}.pdf"

        # Cut title if filename is over 255 characters
        max_len = 255
        if len(base) > max_len:
            over = len(base) - max_len
            cut_title = title_clean[:-over - 3] + "..."  # show it's trimmed
            base = f"{author_str} {year_str}. {cut_title}. {publication_str}. {publisher_str}.pdf"

        return base


if __name__ == "__main__":
    # Example usage
    publication = Publication(
        title="An Example Title",
        publication="Journal of Examples",
        year=2022,
        authors="Doe and Smith",
        publisher="Nature")
    print(publication)

    # Validate the publication
    validation_errors = publication.validate
    if not validation_errors:
        print("Publication data is valid.")
    else:
        print("Validation errors:", validation_errors)
