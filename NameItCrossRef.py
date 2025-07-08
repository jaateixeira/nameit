
from utils.unified_logger import console, logger

# Opening PDF file, reading the first page and extracting DOI with a very common patter
import fitz  # PyMuPDF
import re
from typing import Optional, Dict

def extract_doi_from_pdf(pdf_file: str) -> Optional[Dict]:
    """
    Extract metadata from a PDF file by identifying the DOI on the first page and fetching its metadata.

    Args:
        pdf_file (str): Path to the PDF file.

    Returns:
        Optional[Dict]: Metadata associated with the DOI if found, otherwise None.
    """
    try:
        pdf_document = fitz.open(pdf_file)
        first_page = pdf_document[0]
        text = first_page.get_text("text")
        doi_pattern = r'10[.][\d.]{1,15}\/[-._;:()\/A-Za-z0-9<>]+[A-Za-z0-9]'
        doi_match = re.search(doi_pattern, text)
        if doi_match:
            doi = doi_match.group()
            logger.info("Extracting DOI from file")
            return fetch_metadata_by_doi(doi)
        else:
            return None
    except re.error as e:
        logger.error(f"Error with DOI regex pattern: {e}")
    except Exception as e:
        logger.error(f"Unexpected error extracting metadata from PDF: {e}")
    return None



# Using Crossref API to match the extracted DOI
def fetch_metadata_by_doi(doi):
    try:
        cr = Crossref()
        metadata = cr.works(doi)
        logger.info("Extracting metadata through crossref.org")
        rprint(metadata)  # Use rich to print the metadata
        return metadata
    except Crossref.exceptions.CrossrefError as e:
        logger.error(f"Crossref API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata by DOI: {e}")
    return None

