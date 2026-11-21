import sys

from nameit.models.exceptions import InvalidCrossrefDataError
from nameit.utils.unified_logger import console, logger

import os
import re
from typing import Optional, Dict, Any, Union



import pymupdf  # This is the package name


# To query CrossRef API online
from habanero import Crossref

# For caching habanero API requests to CrossRef
import requests_cache

from rich.table import Table

from rich.traceback import install
# Install rich traceback handler
install(show_locals=True)  # Shows local variables in traceback


from nameit.utils.paths import cache_dir
from nameit.utils.verbosity import key_value_table, vprint, vv_exception, vvprint
from nameit.utils.unified_console import console
from nameit.utils.unified_logger import logger

from nameit.utils.validators import (
    validate_first_name,
    validate_last_name,
    validate_suffix,
    validate_title,
    validate_journal,
    validate_year,
    validate_author,
    validate_publication, validate_publisher_name, validate_family_names_in_metadata_retrieved_from_cross_ref,
    validate_authors_list_retrieved_from_cross_ref, valid_crossref_metadata
)

from nameit.models.data_models import Publication

# Enable caching with 1-year expiration
requests_cache.install_cache(str(cache_dir() / 'crossref_cache'), expire_after=31536000)  #

def format_author_names(authors: list, debug: bool = False) -> str:
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
    debug (bool): If True, prints detailed debug information.

    Returns:
    str: A formatted string representing the authors' names.

    Raises:
    ValueError: If authors list is empty or if any author dictionary is missing the 'family' key.

    Examples:
    >>> format_author_names([{'family': 'Smith'}])
    'Smith'
    >>> format_author_names([{'family': 'Smith'}, {'family': 'Johnson'}])
    'Smith and Johnson'
    >>> format_author_names([{'family': 'Smith'}, {'family': 'Johnson'}, {'family': 'Williams'}])
    'Smith et al.'
    """
    try:
        if debug:
            logger.info(f"Formatting authors {authors}")
        
        # Validate input
        if not authors:
            raise ValueError("Authors list cannot be empty")
        
        if not isinstance(authors, list):
            raise ValueError(f"Authors must be a list, got {type(authors).__name__}")
        
        # Check all authors have 'family' key before processing
        for i, author in enumerate(authors):
            if not isinstance(author, dict):
                raise ValueError(f"Author at index {i} must be a dictionary, got {type(author).__name__}")
            
            if 'family' not in author:
                # Try to find alternative keys
                alternative_keys = ['surname', 'last_name', 'lastName', 'name']
                for key in alternative_keys:
                    if key in author:
                        author['family'] = author[key]
                        if debug:
                            logger.warning(f"Using alternative key '{key}' for author at index {i}")
                        break
                else:
                    # No alternative key found
                    raise KeyError(
                        f"Author dictionary at index {i} is missing 'family' key. "
                        f"Available keys: {list(author.keys())}. "
                        f"Author data: {author}"
                    )
            
            # Additional validation
            if not author['family'] or str(author['family']).strip() == '':
                logger.warning(f"Author at index {i} has empty or whitespace-only family name")
        
        # Format based on number of authors
        if len(authors) == 1:
            return authors[0]['family']
        elif len(authors) == 2:
            return f"{authors[0]['family']} and {authors[1]['family']}"
        else:
            return f"{authors[0]['family']} et al."
    
    except (KeyError, ValueError) as e:
        # Create a detailed error message
        error_context = {
            "function": "format_author_names",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "authors_received": str(authors),
            "authors_type": type(authors).__name__,
            "authors_length": len(authors) if isinstance(authors, list) else "N/A",
            "debug_mode": debug
        }
        
        # Log the error with context
        error_msg = (
            f"Failed to format author names:\n"
            f"  Error: {type(e).__name__}: {str(e)}\n"
            f"  Input type: {type(authors).__name__}\n"
            f"  Input length: {len(authors) if isinstance(authors, list) else 'N/A'}\n"
            f"  First few items: {authors[:3] if isinstance(authors, list) else authors}"
        )
        
        logger.error(error_msg)
        
        if debug:
            # Print detailed debugging information
            print("\n" + "="*60)
            print("DEBUG - Author Formatting Error")
            print("="*60)
            print(f"Error: {type(e).__name__}: {e}")
            print(f"\nAuthors data received:")
            print(f"  Type: {type(authors)}")
            print(f"  Length: {len(authors) if isinstance(authors, list) else 'N/A'}")
            print(f"  Content: {authors}")
            
            if isinstance(authors, list) and authors:
                print(f"\nDetailed author inspection:")
                for i, author in enumerate(authors[:5]):  # Show first 5
                    print(f"  Author {i}:")
                    print(f"    Type: {type(author)}")
                    if isinstance(author, dict):
                        print(f"    Keys: {list(author.keys())}")
                        print(f"    Values: {author}")
                    else:
                        print(f"    Value: {author}")
            print("="*60 + "\n")
        
        # Re-raise with more informative error
        raise ValueError(f"Failed to format author names: {e}. "
                        f"Input: {authors[:3] if isinstance(authors, list) and len(authors) > 3 else authors}") from e
    


def validate_crossref_returned_meta_data(meta_data: Dict[str, Any], debug: bool = False) -> Publication:
    """Validate Crossref's answer and turn it into a Publication.

    Raises InvalidCrossrefDataError when essential fields are missing or invalid.
    """
    vvprint("[bold green]Validating the data returned by the Crossref API[/bold green]")
    logger.info("Validating the data returned by CrossRef API ")

    try:
        message = meta_data['message']
        raw_authors = message['author']
        raw_year = message['issued']['date-parts'][0][0]
        raw_title = message['title'][0]
    except (KeyError, IndexError, TypeError) as e:
        raise InvalidCrossrefDataError([f"author/issued/title ({type(e).__name__}: {e})"]) from e
    raw_publication = message['container-title'][0] if message.get('container-title') else 'Unknown publication'
    raw_publisher = message.get('publisher') or 'Unknown publisher'

    vvprint(key_value_table("RAW Crossref metadata", [
        ("Authors", str(raw_authors)),
        ("format_author_names(Authors)", format_author_names(raw_authors)),
        ("Year", str(raw_year)),
        ("Title", raw_title),
        ("Publication", raw_publication),
        ("Publisher", raw_publisher),
    ]))

    # First validate the authors structure retrieved is acceptable to work with
    if not validate_authors_list_retrieved_from_cross_ref(raw_authors):
        raise InvalidCrossrefDataError(["author (every author needs a given and a family name)"])

    # Then validate the individual fields; validators raise ValueError on bad values
    try:
        valid_authors: list = validate_family_names_in_metadata_retrieved_from_cross_ref(raw_authors)
        valid_year: int = validate_year(raw_year)
        valid_title: str = validate_title(raw_title)
        valid_publication: str = validate_journal(raw_publication)
        valid_publisher: str = validate_publisher_name(raw_publisher)
    except ValueError as e:
        raise InvalidCrossrefDataError([str(e)]) from e

    vvprint(key_value_table("Validated Crossref metadata (fixed as well as possible)", [
        ("Authors", str(valid_authors)),
        ("format_author_names(Authors)", format_author_names(valid_authors)),
        ("Year", str(valid_year) if valid_year else "No year available"),
        ("Title", valid_title),
        ("Publication", valid_publication),
        ("Publisher", valid_publisher),
    ]))

    return Publication(
        authors=format_author_names(valid_authors),
        year=valid_year,
        title=valid_title,
        publication=valid_publication,
        publisher=valid_publisher)


def extract_publication_metadata_from_crossref_using_doi_in_pdf(pdf_file: str) -> Union[Publication, None]:
    """
    Extract metadata from a PDF file by identifying the DOI on the first, second, 
    and last pages and fetching its metadata.

    Args:
        pdf_file (str): Path to the PDF file.

    Returns:
        Optional[Dict]: Metadata associated with the DOI if found, otherwise None.
    """
    try:
        vprint(f"[bold]{os.path.basename(pdf_file)}[/bold]: looking for a DOI")
        
        with pymupdf.open(pdf_file) as pdf_document:
            # Define pages to check: first (0), second (1), and last (-1)
            pages_to_check = [0, 1, -1]
            pages_checked = set()
            
            for page_index in pages_to_check:
                # Skip if page doesn't exist
                if page_index >= len(pdf_document) or page_index < -len(pdf_document):
                    continue
                    
                # Convert negative index to positive
                if page_index < 0:
                    actual_page_index = len(pdf_document) + page_index
                else:
                    actual_page_index = page_index
                    
                # Skip if we've already checked this page
                if actual_page_index in pages_checked:
                    continue
                    
                pages_checked.add(actual_page_index)
                
                page = pdf_document[actual_page_index]
                text = page.get_text("text")
                
                vvprint(f"  Checking page {actual_page_index + 1} of {len(pdf_document)}")
                
                # Method 1: First find all DOI-like patterns, then filter out JSTOR
                # Basic DOI pattern (captures most DOIs)
                basic_doi_pattern = r'\b(10\.\d{4,}(?:\.\d+)*/[^\s"\'<>()\[\]{}]*[^\s"\'<>()\[\]{}.])'
                
                # Find all potential DOIs
                potential_dois = list(re.finditer(basic_doi_pattern, text, re.IGNORECASE))
                
                doi_match = None
                doi_text = None
                
                for match in potential_dois:
                    candidate = match.group(0)
                    
                    # Clean up the DOI
                    candidate = candidate.rstrip('.,;:')
                    
                    # Method 1: Check if this is a JSTOR URL by examining the match and context
                    # Get a larger context around the match to check for URL patterns
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Look at context before and after
                    context_start = max(0, start_pos - 100)  # Look 100 chars before
                    context_end = min(len(text), end_pos + 50)  # Look 50 chars after
                    full_context = text[context_start:context_end]
                    
                    # Check if this appears to be a JSTOR URL
                    # JSTOR URLs typically have patterns like:
                    # - https://www.jstor.org/stable/10.xxxx/xxxx
                    # - http://jstor.org/stable/10.xxxx/xxxx
                    # - www.jstor.org/stable/10.xxxx/xxxx
                    
                    # Extract the full potential URL containing this match
                    # Look for URL patterns ending at whitespace or punctuation
                    url_pattern = r'(https?://[^\s<>"\'()]+|www\.[^\s<>"\'()]+)'
                    urls_in_context = re.findall(url_pattern, full_context, re.IGNORECASE)
                    
                    is_jstor_url = False
                    for url in urls_in_context:
                        if candidate in url and ('jstor.org' in url.lower() or '/stable/' in url.lower()):
                            is_jstor_url = True
                            vvprint(f"  Skipping JSTOR URL: {url[:80]}...")
                            break
                    
                    if is_jstor_url:
                        continue
                    
                    # Additional check: if the candidate itself looks like a JSTOR pattern
                    if '/stable/10.' in candidate.lower() or 'jstor.org' in candidate.lower():
                        continue
                    
                    # Method 2: Check if the match is preceded by URL indicators
                    # Simple check: look for http://, https://, or www. immediately before
                    text_before = text[max(0, start_pos - 20):start_pos]
                    url_indicators = ['http://', 'https://', 'www.']
                    
                    # If there's a URL indicator close before and JSTOR in the text, skip
                    has_url_indicator = any(indicator in text_before.lower() for indicator in url_indicators)
                    has_jstor_nearby = 'jstor' in text_before.lower() or 'jstor' in text[start_pos:end_pos + 20].lower()
                    
                    if has_url_indicator and has_jstor_nearby:
                        continue
                    
                    # Clean any URL prefixes from the candidate
                    url_prefixes = [
                        'https://doi.org/', 'http://doi.org/',
                        'https://dx.doi.org/', 'http://dx.doi.org/',
                        'doi.org/', 'dx.doi.org/'
                    ]
                    
                    original_candidate = candidate
                    for prefix in url_prefixes:
                        if candidate.lower().startswith(prefix):
                            candidate = candidate[len(prefix):]
                            break
                    
                    # Validate the cleaned DOI
                    # Basic validation: should start with 10. and have a slash
                    if not candidate.startswith('10.'):
                        continue
                    
                    if '/' not in candidate:
                        continue
                    
                    # Should not contain spaces
                    if ' ' in candidate:
                        continue
                    
                    # Final check: should match the basic DOI pattern after cleaning
                    if re.match(r'^10\.\d{4,}(?:\.\d+)*/[^\s]+$', candidate, re.IGNORECASE):
                        doi_match = match
                        doi_text = candidate
                        vprint(f"  Found DOI [cyan]{doi_text}[/cyan] on page {actual_page_index + 1}")
                        break
                
                if doi_match and doi_text:
                    doi = doi_text
                    logger.info(f"Extracting DOI: {doi} from file: {pdf_file} (found on page {actual_page_index + 1})")
                    
                    meta_data_fetched_via_CrossRef_API: Optional[Dict[str, Any]] = fetch_metadata_by_doi(doi)
                    
                    if meta_data_fetched_via_CrossRef_API:
                        vprint("  Crossref returned metadata")
                        try:
                            article_publication: Publication = validate_crossref_returned_meta_data(
                                meta_data_fetched_via_CrossRef_API)
                        except InvalidCrossrefDataError as e:
                            logger.warning(f"Crossref metadata for {doi} is not usable: {e}")
                            vprint(f"  [yellow]Crossref metadata for {doi} is not usable: {e}[/yellow]")
                            continue  # try the next page

                        vprint(f"  [green]Name: {article_publication}[/green]")
                        return article_publication
                    else:
                        vprint(f"  [yellow]No Crossref metadata found for DOI {doi}[/yellow]")
                        continue

            # If we get here, no DOI was found on any of the checked pages
            logger.warning(f"No DOI found in the file: {pdf_file} (checked pages: {sorted([p+1 for p in pages_checked])})")
            vprint(f"  [yellow]No DOI found (checked pages {sorted([p+1 for p in pages_checked])})[/yellow]")
            return None
            
    except FileNotFoundError:
        logger.error(f"PDF file not found: {pdf_file}")
        vprint(f"[red]PDF file not found: {pdf_file}[/red]")
    except PermissionError:
        logger.error(f"Permissions error: Cannot open the PDF file: {pdf_file}")
        vprint(f"[red]Permissions error: cannot open {pdf_file}[/red]")
    except re.error as e:
        logger.error(f"Error with DOI regex pattern: {e}")
        vprint(f"[red]Error with DOI regex pattern: {e}[/red]")
    except Exception as e:
        logger.opt(exception=True).error(f"Unexpected error extracting metadata from {pdf_file}: {e}")
        vprint(f"[red]Unexpected error for {os.path.basename(pdf_file)}: {e}[/red]")
        vv_exception()

    return None


# Alternative simpler function that extracts DOIs while excluding JSTOR
def extract_doi_without_jstor(text):
    """
    Extract DOIs from text while excluding JSTOR URLs.
    
    Args:
        text (str): Text to search
        
    Returns:
        list: List of found DOIs
    """
    # First, find all URLs in the text
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    # Filter out JSTOR URLs
    non_jstor_urls = [url for url in urls if 'jstor.org' not in url.lower() and '/stable/' not in url.lower()]
    
    # Now look for DOIs that aren't in URLs (or are in non-JSTOR URLs)
    doi_pattern = r'\b(10\.\d{4,}(?:\.\d+)*/[^\s"\'<>()\[\]{}]*[^\s"\'<>()\[\]{}.])'
    
    all_matches = list(re.finditer(doi_pattern, text, re.IGNORECASE))
    valid_dois = []
    
    for match in all_matches:
        doi_candidate = match.group(0).rstrip('.,;:')
        start, end = match.start(), match.end()
        
        # Check if this DOI is part of any URL
        is_part_of_url = False
        for url in urls:
            url_start = text.find(url)
            if url_start != -1:
                url_end = url_start + len(url)
                if start >= url_start and end <= url_end:
                    is_part_of_url = True
                    # If it's part of a URL, only accept if it's a non-JSTOR URL
                    if 'jstor.org' in url.lower() or '/stable/' in url.lower():
                        # Skip JSTOR URLs
                        continue
                    else:
                        # Extract DOI from the URL (remove URL parts)
                        for prefix in ['https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/', 'doi.org/']:
                            if url.lower().startswith(prefix):
                                doi_candidate = url[len(prefix):]
                                break
        
        # If not part of a URL, or part of a non-JSTOR URL, add it
        if not is_part_of_url or (is_part_of_url and doi_candidate.startswith('10.')):
            # Clean any remaining URL prefixes
            for prefix in ['https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/', 'doi.org/']:
                if doi_candidate.lower().startswith(prefix):
                    doi_candidate = doi_candidate[len(prefix):]
                    break
            
            # Validate
            if re.match(r'^10\.\d{4,}(?:\.\d+)*/[^\s]+$', doi_candidate, re.IGNORECASE):
                valid_dois.append(doi_candidate)
    
    return valid_dois


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
        cr = Crossref(mailto="jose.teixeira@abo.fi")
        metadata = cr.works(doi)

        if not metadata or 'message' not in metadata:
            raise InvalidCrossrefDataError("No 'message' in response.")

        message = metadata['message']
        if not message.get('title') or not message.get('author'):
            raise InvalidCrossrefDataError("Missing required fields like title or author.")

        if not valid_crossref_metadata(metadata):
            raise InvalidCrossrefDataError(f"Invalid CrossRefData. Did not pass valid_crossref_metadata")

        logger.info(f"Successfully extracted metadata for DOI: {doi} through crossref.org")
        #console.print(metadata)  # Use rich to print the metadata
        #console.print(metadata.get("author"))

    except Crossref.HttpError as e:
        logger.error(f"HTTP error occurred while accessing Crossref API for DOI: {doi}. Error: {e}")
    except Crossref.RateLimitError as e:
        logger.error(f"Rate limit exceeded while accessing Crossref API for DOI: {doi}. Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata by DOI: {doi}. Error: {e}", exc_info=True)

    return metadata
