from nameparser import HumanName
from typing import Optional, Dict, List

def validate_first_name(name: str) -> bool:
    """Validate that the first name is a non-empty string."""
    return isinstance(name, str) and name.strip()

def validate_last_name(name: str) -> bool:
    """Validate that the last name is a non-empty string."""
    return isinstance(name, str) and name.strip()

def validate_suffix(suffix: Optional[str]) -> bool:
    """Validate that the suffix is either None or a non-empty string."""
    if suffix is None:
        return True
    return isinstance(suffix, str) and suffix.strip()

def validate_title(title: Optional[str]) -> bool:
    """Validate that the title is either None or a non-empty string."""
    if title is None:
        return True
    return isinstance(title, str) and title.strip()

def validate_journal(journal: str) -> bool:
    """Validate that the journal is a non-empty string."""
    return isinstance(journal, str) and journal.strip()

def validate_year(year: int) -> bool:
    """Validate that the year is a reasonable value."""
    current_year = 2023  # Update this as necessary
    return isinstance(year, int) and 1900 <= year <= current_year

def validate_author(author: Dict) -> Dict:
    """Validate the components of an author's name using HumanName."""
    errors = {}

    name = HumanName(author.get("full_name", ""))
    if not validate_first_name(name.first):
        errors["first_name"] = "Invalid or missing first name."
    if not validate_last_name(name.last):
        errors["last_name"] = "Invalid or missing last name."
    if not validate_suffix(name.suffix):
        errors["suffix"] = "Invalid suffix."
    if not validate_title(name.title):
        errors["title"] = "Invalid title."

    return errors

def validate_publication(publication: Dict) -> Dict:
    """Validate the structure and content of a publication dictionary."""
    errors = {}

    if "authors" not in publication or not isinstance(publication["authors"], list):
        errors["authors"] = "Invalid or missing authors list."
    else:
        for i, author in enumerate(publication["authors"]):
            author_errors = validate_author(author)
            if author_errors:
                errors[f"author_{i}"] = author_errors

    if "year" not in publication or not validate_year(publication["year"]):
        errors["year"] = "Invalid or missing year."

    if "title" not in publication or not isinstance(publication["title"], str) or not publication["title"].strip():
        errors["title"] = "Invalid or missing title."

    if "journal" not in publication or not validate_journal(publication["journal"]):
        errors["journal"] = "Invalid or missing journal."

    return errors

# Example usage
publication_data = {
    "authors": [{"full_name": "Dr. John von Doe Jr."}, {"full_name": "Jane Smith"}],
    "year": 2022,
    "title": "An Example Title",
    "journal": "Journal of Examples"
}

validation_errors = validate_publication(publication_data)
if not validation_errors:
    print("Publication data is valid.")
else:
    print("Validation errors:", validation_errors)
