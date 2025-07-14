import sys

from utils.unified_logger import console, logger

import re
from typing import Optional, Dict, Any

# Opening PDF file, reading the first page and extracting DOI with a very common patter
import fitz  # PyMuPDF

from habanero import Crossref

from rich.table import Table

from utils.unified_console import console
from utils.unified_logger import logger

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

from models.data_models import Publication


def format_author_names(authors: list) -> str:
    """
    Formats a list of author names, typically obtained from the CrossRef API, into a string representation.

    This function processes a list of author dictionaries, where each dictionary is expected to contain
    at least a 'family' key representing the family name of the author. This data is typically obtained
    from the CrossRef API under the path `meta_data['message']['author']`. The function formats the
    authors' names into a string according to the following rules:
    - If there is only one author, it returns the family name of that author.
    - If there are two authors, it returns the family names joined by " and ".
    - If there are more than two authors, it returns the family name of the first author followed by " et al."

    Parameters:
    authors (list of dict): A list of author dictionaries obtained from the CrossRef API. Each dictionary
                           should contain at least a 'family' key with the author's family name.

    Returns:
    str: A formatted string representing the authors' names.

    Examples:
    >>> format_author_names([{'family': 'Smith'}])
    'Smith'
    >>> format_author_names([{'family': 'Smith'}, {'family': 'Johnson'}])
    'Smith and Johnson'
    >>> format_author_names([{'family': 'Smith'}, {'family': 'Johnson'}, {'family': 'Williams'}])
    'Smith et al.'
    """
    logger.info(f"Formatting authors {authors}")
    if len(authors) == 1:
        return authors[0]['family']
    elif len(authors) == 2:
        return f"{authors[0]['family']} and {authors[1]['family']}"
    else:
        return f"{authors[0]['family']} et al."


def validate_crossref_returned_meta_data(meta_data: Optional[Dict]) -> Publication:
    console.print("\n [bold green]. Validating the data returned by the CrossRef API")
    logger.info("Validating the data returned by CrossRef API ")
    logger.info(meta_data)
    # Extracting relevant information
    raw_authors = meta_data['message']['author']
    raw_year = meta_data['message']['issued']['date-parts'][0][0]
    raw_title = meta_data['message']['title'][0]
    raw_publication = meta_data['message']['container-title'][0] if 'container-title' in meta_data[
        'message'] else 'Unknown publication'
    raw_publisher = meta_data['message']['publisher'] if 'publisher' in meta_data['message'] else 'Unknown publisher'

    progress_message: str = "Picking the relevant data from the metadata returned from CrossRef"
    console.print(progress_message)
    logger.info(progress_message)

    console.print(f"{raw_authors=}")
    console.print(f"{raw_year=}")
    console.print(f"{raw_title=}")
    console.print(f"{raw_publication=}")
    console.print(f"{raw_publisher=}")

    # Creating a table
    raw_table = Table(title="RAW CrossRef MetaData Information")

    # Adding columns
    raw_table.add_column("Field", style="cyan", no_wrap=True)
    raw_table.add_column("Value", style="magenta")

    # Adding rows
    raw_table.add_row("Authors", str(raw_authors))
    raw_table.add_row("format_author_names(Authors)", format_author_names(raw_authors))
    raw_table.add_row("Year", str(raw_year))
    raw_table.add_row("Title", raw_title)
    raw_table.add_row("Publication", raw_publication)
    raw_table.add_row("Publisher", raw_publisher)

    console.print(raw_table)

    # Formatting the information
    authors_str = format_author_names(raw_authors)
    title_str = " ".join(raw_title) if raw_title else "No title available via CrossRef API"
    container_title_str = " ".join(container_title) if container_title else "No container title (e.g. journal) available via CrossRef API"
    publisher_str = publisher if publisher else "No publisher available via CrossRef API"

    # Creating a table
    valid_table = Table(title="Validated (fixed as good as possible) CrossRef MetaData Information")

    # Adding columns
    valid_table.add_column("Field", style="cyan", no_wrap=True)
    valid_table.add_column("Value", style="magenta")

    # Adding rows
    valid_table.add_row("Authors", authors_str)
    valid_table.add_row("Year", str(year) if year else "No year available")
    valid_table.add_row("Title", title_str)
    valid_table.add_row("Publication", container_title_str)
    raw_table.add_row("Publisher", f"{publisher_str}.pdf")

    console.print(raw_table)

    return False


def extract_metadata_from_crossref_using_doi_in_pdf(pdf_file: str) -> Optional[Dict]:
    """
        Extract metadata from a PDF file by identifying the DOI on the first page and fetching its metadata.

        Args:
            pdf_file (str): Path to the PDF file.

        Returns:
            Optional[Dict]: Metadata associated with the DOI if found, otherwise None.
        """
    try:
        # Open the PDF file
        with fitz.open(pdf_file) as pdf_document:
            first_page = pdf_document[0]
            text = first_page.get_text("text")

        console.print(f"Looking for a DOI in the first page of the {pdf_file} pdf file")

        # Define the DOI pattern
        doi_pattern = r'10[.][\d.]{1,15}\/[-._;:()\/A-Za-z0-9<>]+[A-Za-z0-9]'

        # Search for DOI in the text
        doi_match = re.search(doi_pattern, text)
        if doi_match:
            doi = doi_match.group()
            logger.info(f"Extracting DOI: {doi} from file: {pdf_file}")

            meta_data_fetched_via_CrossRef_API = fetch_metadata_by_doi(doi)

            console.print("\n [bold green]. CrossRef API returned metadata 😀")
            console.print("\n [bold blue]. Time to validate the returned metadata")

            validate_crossref_returned_meta_data(meta_data_fetched_via_CrossRef_API)
            sys.exit()
            if validate_crossref_returned_meta_data(meta_data_fetched_via_CrossRef_API):

                return meta_data_fetched_via_CrossRef_API
            else:
                console.print("\n [bold red]. The metadata returned by CrossRef is invalid")
                return None

        else:
            logger.warning(f"No DOI found in the file: {pdf_file}")
            return None

    except FileNotFoundError:
        logger.error(f"PDF file not found: {pdf_file}")
    except PermissionError:
        logger.error(f"Permissions error: Cannot open the PDF file: {pdf_file}")
    except re.error as e:
        logger.error(f"Error with DOI regex pattern: {e}")
    #except Exception as e:
    #    logger.error(f"Unexpected error extracting metadata from PDF: {e}", exc_info=True)

    return None


# Using Crossref API to match the extracted DOI
def fetch_metadata_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
        Fetches metadata for a given DOI using the Crossref API.

        Args:
            doi (str): The DOI for which to fetch metadata.

        Returns:
            Optional[Dict[str, Any]]: The metadata associated with the DOI if successful, otherwise None.
        """
    try:
        cr = Crossref()
        metadata = cr.works(doi)

        if metadata:
            logger.info(f"Successfully extracted metadata for DOI: {doi} through crossref.org")
            console.print(metadata)  # Use rich to print the metadata
            return metadata
        else:
            logger.warning(f"No metadata found for DOI: {doi}")

    except Crossref.HttpError as e:
        logger.error(f"HTTP error occurred while accessing Crossref API for DOI: {doi}. Error: {e}")
    except Crossref.RateLimitError as e:
        logger.error(f"Rate limit exceeded while accessing Crossref API for DOI: {doi}. Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata by DOI: {doi}. Error: {e}", exc_info=True)

    return None
