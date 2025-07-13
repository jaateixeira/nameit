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

from datamodels import Publication


def validate_crossref_returned_meta_data(meta_data:Optional[Dict]) -> Publication:
    console.print("\n [bold green]. Validating the data returned by the CrossRef API")
    logger.info("Validating the data returned by CrossRef API ")
    logger.info(meta_data)
git
    # Extracting relevant information
    authors = meta_data.get('author', [])
    year = meta_data.get('published-print', {}).get('date-parts', [[None]])[0][0]
    title = meta_data.get('title', [])
    container_title = meta_data.get('container-title', [])
    publisher = meta_data.get('publisher')

    console.print(authors)
    sys.exit()
    logger.info(str(authors),year,title,container_title,publisher)

    # Creating a table
    raw_table = Table(title="RAW CrossRef MetaData Information")

    # Adding columns
    raw_table.add_column("Field", style="cyan", no_wrap=True)
    raw_table.add_column("Value", style="magenta")

    # Adding rows
    raw_table.add_row("Authors", authors)
    raw_table.add_row("Year", str(year) if year else "No year available")
    raw_table.add_row("Title", title)
    raw_table.add_row("Publication", container_title)
    raw_table.add_row("Publisher", f"{publisher}.pdf")

    console.print(raw_table)


    # Formatting the information
    authors_str = ", ".join([f"{author.get('given', '')} {author.get('family', '')}".strip() for author in
                             authors]) if authors else "No authors available"
    title_str = " ".join(title) if title else "No title available"
    container_title_str = " ".join(container_title) if container_title else "No container title available"
    publisher_str = publisher if publisher else "No publisher available"

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

                return  meta_data_fetched_via_CrossRef_API
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
