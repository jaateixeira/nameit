
from utils.unified_logger import console, logger

import re
from typing import Optional, Dict, Any

# Opening PDF file, reading the first page and extracting DOI with a very common patter
import fitz  # PyMuPDF

from habanero import Crossref

def extract_doi_from_pdf(pdf_file: str) -> Optional[Dict]:
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

            # Define the DOI pattern
            doi_pattern = r'10[.][\d.]{1,15}\/[-._;:()\/A-Za-z0-9<>]+[A-Za-z0-9]'

            # Search for DOI in the text
            doi_match = re.search(doi_pattern, text)
            if doi_match:
                doi = doi_match.group()
                logger.info(f"Extracting DOI: {doi} from file: {pdf_file}")
                return fetch_metadata_by_doi(doi)
            else:
                logger.warning(f"No DOI found in the file: {pdf_file}")
                return None

        except FileNotFoundError:
            logger.error(f"PDF file not found: {pdf_file}")
        except PermissionError:
            logger.error(f"Permissions error: Cannot open the PDF file: {pdf_file}")
        except re.error as e:
            logger.error(f"Error with DOI regex pattern: {e}")
        except Exception as e:
            logger.error(f"Unexpected error extracting metadata from PDF: {e}", exc_info=True)

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


