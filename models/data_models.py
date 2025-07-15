from dataclasses import dataclass, field
from typing import List, Optional
from nameparser import HumanName
from utils.validators import (
    validate_first_name,
    validate_last_name,
    validate_suffix,
    validate_title,
    validate_journal,
    validate_year,
    validate_author,
    validate_publication
)


@dataclass
class Author:
    """Deprecated: This class is not used in the current version."""
    full_name: str
    first_name: Optional[str] = field(init=False)
    last_name: Optional[str] = field(init=False)
    suffix: Optional[str] = field(init=False)
    title: Optional[str] = field(init=False)

    def __post_init__(self):
        name = HumanName(self.full_name)
        self.first_name = name.first
        self.last_name = name.last
        self.suffix = name.suffix
        self.title = name.title

    def validate(self) -> dict:
        return validate_author({"full_name": self.full_name})


@dataclass
class Publication:
    authors: str
    year: int
    title: str
    journal: str
    publication:str

    def validate(self) -> dict:
        publication_data = {
            "title": self.title,
            "journal": self.journal,
            "year": self.year,
            "authors": [{"full_name": author.full_name} for author in self.authors]
        }

        return validate_publication(publication_data)

if __name__ == "__main__":
    # Example usage
    author1 = Author(full_name="Dr. John von Doe Jr.")
    author2 = Author(full_name="Jane Smith")
    publication = Publication(
    title="An Example Title",
    journal="Journal of Examples",
    year=2022,
    authors=[author1, author2])

    # Validate the publication
    validation_errors = publication.validate()
    if not validation_errors:
        print("Publication data is valid.")
    else:
        print("Validation errors:", validation_errors)
