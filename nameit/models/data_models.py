import os
import pathlib
import re
import string
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple, Union
from nameparser import HumanName
from nameit.utils.validators import (
    validate_first_name,
    validate_last_name,
    validate_suffix,
    validate_title,
    validate_journal,
    validate_year,
    validate_author,
    validate_publication, validate_author_family_name, validate_publisher, validate_publisher_name
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


DEFAULT_NAME_TEMPLATE = "{authors} ({year}). {title}. {publication}. {publisher}"
NAME_PLACEHOLDERS = ("authors", "year", "title", "publication", "publisher", "publisher_full")


def validate_name_template(template: str) -> None:
    """Raise ValueError unless `template` only uses plain {placeholders} from NAME_PLACEHOLDERS."""
    if not isinstance(template, str) or not template.strip():
        raise ValueError("The filename template must be a non-empty string")
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError as e:  # unbalanced braces
        raise ValueError(f"Invalid filename template {template!r}: {e}") from e
    used = 0
    for _, field, spec, conversion in parsed:
        if field is None:
            continue
        if field not in NAME_PLACEHOLDERS or spec or conversion:
            raise ValueError(
                f"Unknown placeholder {{{field}{'!' + conversion if conversion else ''}"
                f"{':' + spec if spec else ''}}} in the filename template; "
                f"use plain placeholders from: {', '.join('{' + n + '}' for n in NAME_PLACEHOLDERS)}")
        used += 1
    if not used:
        raise ValueError("The filename template needs at least one placeholder, "
                         "otherwise every file would get the same name")
    if "/" in template or "\\" in template:
        raise ValueError("The filename template must not contain path separators")


@dataclass
class Publication:
    authors: str
    year: int
    title: str
    publication: str
    publisher: str

    @property
    def validate(self) -> dict:
        """Problems with the fields, as {field: message}; empty when the publication is fine."""
        checks: Tuple[Tuple[str, Callable[[Any], Any], Any], ...] = (
            ("authors", validate_author_family_name, self.authors),
            ("year", validate_year, self.year),
            ("title", validate_title, self.title),
            ("publication", validate_journal, self.publication),
            ("publisher", validate_publisher_name, self.publisher),
        )
        errors = {}
        for name, check, value in checks:
            try:
                check(value)
            except (ValueError, TypeError) as e:
                errors[name] = str(e)
        return errors

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
            match = re.search(r'(?:^|\s)([A-ZÅÄÖÁÉÍÓÚÑ][^\s]*)$', name)
            return match.group(1) if match else name

        if len(authors) > 2:
            return f"{surname(authors[0])} et al."
        return " and ".join(surname(a) for a in authors)

    def render(self, template: str = DEFAULT_NAME_TEMPLATE) -> str:
        """Filename (with .pdf) for this publication according to `template`.

        Over-long names (> 255 characters) are shortened by trimming the title.
        """
        validate_name_template(template)
        fields = {
            "authors": self._format_authors(),
            "year": str(self.year),
            "title": _clean_filename_part(self.title),
            "publication": _clean_filename_part(self.publication),
            "publisher": self._short_publisher(),
            "publisher_full": _clean_filename_part(self.publisher),
        }
        suffix = ".pdf"
        name = template.format(**fields) + suffix

        max_len = 255
        if len(name) > max_len:
            over = len(name) - max_len
            if "{title}" in template:
                title = fields["title"]
                fields["title"] = title[:max(len(title) - over - 3, 0)] + "..."  # show it's trimmed
                name = template.format(**fields) + suffix
            if len(name) > max_len:  # template without {title}, or still too long
                name = name[:max_len - len(suffix)] + suffix
        return name

    def __str__(self) -> str:
        return self.render(DEFAULT_NAME_TEMPLATE)


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
