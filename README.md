# NameIt # 

NameIt is a software tool that renames research articles in pdf files in a standardised way. 

Based on the pdf metadata and on the content of the document first page, it renames the file  with author, year, title, publication, and publisher. 
It can extract structured data from PDFs using: (1) pdf meta-data, (2) the CrossRef API, and (3) the layout of the first page (font sizes and positions), which works offline and without a DOI.

![PDF](https://img.shields.io/badge/PDF-Renaming-FF0000?style=for-the-badge&logo=adobe-acrobat-reader&logoColor=white)
![PDF Tools](https://img.shields.io/badge/PDF-Tools-FF0000?style=for-the-badge&logo=pdf&logoColor=white)
![PDF Renamer](https://img.shields.io/badge/PDF-Renamer-FF0000?style=for-the-badge&logo=adobe-acrobat-reader&logoColor=white)
![Batch Rename](https://img.shields.io/badge/Batch-Rename-00599C?style=for-the-badge&logo=windowsterminal&logoColor=white)
![Python 3](https://img.shields.io/badge/Python-3-blue)
![unittest](https://img.shields.io/badge/Testing-unittest-green)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![REST](https://img.shields.io/badge/API-REST-red)
![Cross Ref API](https://img.shields.io/badge/API-Cross%20Ref%20API-orange)
![Habanero](https://img.shields.io/badge/Tool-Habanero-brightgreen)
![Transformers](https://img.shields.io/badge/🤗-Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![PDF%20AI](https://img.shields.io/badge/PDF_AI-Structured_Data-FF0000?style=for-the-badge&logo=adobe-acrobat-reader&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)




## Build Status

[![CI Tests](https://github.com/jaateixeira/nameit/actions/workflows/tests.yml/badge.svg)](https://github.com/jaateixeira/nameit/actions/workflows/tests.yml)
![Nightly Tests](https://github.com/jaateixeira/NameIt/workflows/Nightly%20Unit%20Tests/badge.svg)

# In-and-out

## INPUT: 
* One or several pdf files (e.g., journal articles) 

## OUTPUT: 
* The same pdf files are renamed in a standardised way - author, year, title, publication (e.g., journal name), and publisher. 

Example: "s13174-015-0028-2.pdf" as downloaded from the publisher would become "Teixeira et al. (2015). Lessons learned from applying social network analysis on an industrial Free/Libre/Open Source Software ecosystem. Journal of Internet Services and Applications. Springer.pdf" as renamed by the NameIt tool. 

# Mission # 

* MISSION 1 - Enable researchers across the world to store and find research articles in their computers, servers or shared folders in a easier and faster way.
* MISSION 2 - Advance the standardisation on how research articles in pdf format are named. 

# Benefits of using NameIT

* Research articles are easier to get.
* Research articles are stored in a standardized way.

## Advantages of retrieving a well named pdf file from a hard drive over the publisher's website

- Faster to find it 
- Faster to open it
- Faster to print it (consider sustainability and ecological issues before printing)
- Less duplication of digital resources (note that you are saving space on your hard disk and saving traffic on the web)
- No need to login
- No need to connect to VPN
- No need to resolve some DOI
- No adds
- No paywalls
- No overload with related or non-related information 
- You can get the pdf straight before even seeing the HTML web version
- No cookies tracking your behaviour online
- No hidden fingerprinting codes or watermarking schemes that identify the buyers for every copy of each PDF sold


## Advantages of adoptiong the NameIt standard for naming research articles in pdf. 

- Easier to understand what is on a file as its filename encodes information on author, year, title, publication (e.g., journal name), and publisher.
- Easier to link pdf files to entries on software tools suporting systematic literature reviews (see [https://aut.ac.nz.libguides.com/systematic_reviews/tools](https://aut.ac.nz.libguides.com/systematic_reviews/tools) for more information). 
- Easier to link pdf files to reference management systems (see [https://www.helsinki.fi/en/helsinki-university-library/using-collections/courses-and-workshops/reference-management-software](https://www.helsinki.fi/en/helsinki-university-library/using-collections/courses-and-workshops/reference-management-software) for more information).
- Better interopability between software tools that deal with research articles in pdf. 
- Predictability (i.e., you will not be surprised on how a pdf file is named after being downloaded from a publisher website or the website of colleague). 
- Easier exchangability of collection of research articles between researchers, research groups, libraries and publishers.

# TARGET USERS:  # 

* Human users - Researchers or research teams that want to store and exchange files with a standard naming convention. 
* Software users -  Software tools supporting the management of citations, bibliometrics, references, and literature reviews have now a tool and a standard way to "file name" research articles in PDF format.

# Requirements # 

* Python 3 -  Tested on 3.10 - 3.13
* Habanero (Crossref API)
* PyMuPDF
* libmagic (system library; `apt install libmagic1` or `brew install libmagic`)

We suport the ext3, ext4, xfs, zfs, NTFS, APFS, HFS+ and xFAT filesystems. Support for FAT32 pending. 
Should work in most modern computers running Linux, macOS and Windows. Problems could arise with the use of old  USB flash drives  and SDcard disks in old Linux Kernels. 

# Dependencies 

NameIt is pure python3 code.  It depends on several online public packages, published on the Python Package Index (PyPI). Those dependencies can be installed then using pip/pip3 - the package installer for Python. 

## Habanero ##
`$ pip3  install habanero` <- required to call the Crossref API (it returns the article's metadata for a given DOI identifier). 

## PyMuPDF ##

`$ pip3 install PyMuPDF` <- required to process the first page of a pdf article. 


# How to use it 

## Install

```
$ git clone https://github.com/jaateixeira/nameit && cd nameit
$ pip install .            # or: pip install -e ".[dev]"   for development
```

This gives you the `nameit` command (`python -m nameit` and the old `./NameIt` launcher work too).
On Linux you also need libmagic (`apt install libmagic1`); on macOS `brew install libmagic`.

## Command line

```
$ nameit paper.pdf                  # look up the DOI found in the PDF in Crossref (default)
$ nameit -d research-articles       # dry run: show old -> new names, rename nothing
$ nameit -r research-articles       # include subfolders
$ nameit -p research-articles       # use the metadata embedded in the PDF (offline)
$ nameit -c -p research-articles    # Crossref first, PDF metadata as a fallback
$ nameit -l research-articles       # page layout only: offline, no DOI needed (use when Crossref is down)
$ nameit -c -p -l research-articles # all three, in that order
$ nameit "papers/2024*.pdf"         # patterns: quote them (works on every shell) ...
$ nameit papers/2024*.pdf a.pdf b/  # ... or let the shell expand them; several paths are fine
$ nameit "papers/**/*.pdf"          # ** reaches into subfolders
$ nameit --git research-articles    # rename git-tracked files with `git mv` (history kept, rename staged)
$ nameit --undo research-articles/.nameit-undo-20261120-225603.json
```

* Patterns only pick up `.pdf` files; a pattern that matches nothing is an error. A file you name explicitly that is not a PDF is reported and skipped.
* `--git` (or `git = true` in `.nameitrc`) uses `git mv` for files that git tracks, so the rename is staged and history follows the file; untracked files, or folders outside a repository, are renamed normally and the summary says how many. Commit when you are happy. The undo log is an untracked file in your repository: add `.nameit-undo-*.json` to your `.gitignore`.
* Existing files are never overwritten: a clash gets a ` (1)`, ` (2)`, ... suffix.
* Every real run writes a `.nameit-undo-<timestamp>.json` log in the folder you gave, and `--undo` reverses it.
* `-p` needs a usable title, author and year in the PDF; the journal is taken from the PDF's subject field when it looks like a citation, otherwise the filename says `Unknown publication` / `Unknown publisher`.
* Logs and the Crossref cache live in your user cache/log directory (e.g. `~/.cache/nameit`), not in the folder you are renaming. 
* Output levels (all rich): by default you get a progress bar for batches, the old → new table and a summary. `-v` adds one line per step (DOI found, Crossref answered, name chosen) and warnings. `-vv` adds rich tables of the raw and validated Crossref data, debug logs and tracebacks. `-s` prints nothing but errors; use the exit code.
* Exit code is 1 when nothing could be renamed.

## Configuration (`.nameitrc`) and filename templates

`nameit` reads a small TOML file named `.nameitrc`: first `~/.nameitrc`, then one inside the folder you are renaming
(so a collection can have its own rules). Command-line flags always win; `--config FILE` reads only that file.

```toml
# ~/.nameitrc
format = "{authors} ({year}). {title}. {publication}. {publisher}"   # the NameIt standard (default)
methods = ["crossref", "pdf-metadata", "layout"]       # tried in this order when you give no -c / -p / -l
recursive = true
crossref_mailto = "you@example.org"          # identifies you to Crossref's faster "polite" pool
```

* Placeholders: `{authors}` `{year}` `{title}` `{publication}` `{publisher}` (short form, e.g. ACM) `{publisher_full}`.
  Anything else is rejected before a single file is touched, as is a template without placeholders or with `/`.
* One-off: `nameit --format "{year} - {authors} - {title}" papers/`. Names longer than 255 characters get a shortened title.
* `crossref_mailto` (or the `NAMEIT_MAILTO` environment variable) is optional; without it Crossref still answers, just from its anonymous pool.
* Unknown settings in the file produce a warning; invalid values stop with exit code 2.
* Crossref answers are cached for a year under your user cache directory, and temporary failures (rate limits, server errors, network) are retried with backoff.

## Releasing (maintainers)

The package is published as `nameit-pdf` (the command stays `nameit`). Build and check locally with
`pip install build twine && python -m build && twine check dist/*`. For TestPyPI, set up trusted publishing once
(see the header of `.github/workflows/publish-testpypi.yml`), then run that workflow from the Actions tab; it tests,
builds and uploads without any stored token. Bump `__version__` in `nameit/__init__.py` before each release.

## From Python

```python
from nameit import plan_rename, rename_pdf

for item in plan_rename("papers/", methods=("crossref", "pdf-metadata"), recursive=True):
    print(item.source.name, "->", item.target and item.target.name, item.reason)

rename_pdf("papers/", dry_run=False)   # plan + apply, writes an undo log
plan_rename(["papers/2024*.pdf", "inbox/"])   # patterns and several paths work here too
```

# How it works 

By default, the tool first tries to find pdf's metadata to rename the file. If no metadata is found, it will look on the article first page for a DOI (Digital Object Identifier) and then tries 
to connect to Internet to retrieve the metadata associated to the DOI. 

If pdf's metadata is not found and the retrieval of metadata via the DOI fails, the tool will still try to find the author, year, title, publication, and publisher from the article 1st page. 
The layout method (`-l`) reads the first page with PyMuPDF: the title is the largest text near the top (journal banners are skipped), the authors are the lines below it, and the year comes from a published/copyright/citation line. It is a deterministic heuristic, not a trained model, so it can be wrong for unusual designs; use `--dry-run` to check. The journal is only filled when it is visible on the page or in the PDF's subject field.

How well does it work? An early, informal check by the author on 100+ journal articles downloaded from publisher websites renamed most of them without issues, but that collection and its results were not kept, so the figure cannot be reproduced and we no longer quote a number. Author names with uncommon accents and titles with uncommon characters can be problematic.

What is reproducibly tested today (`unit-tests/`): the DOI found in each sample PDF in `test-data/` (offline golden tests), the `-p` PDF-metadata names, and the Crossref client against mocked responses. To measure the success rate on your own collection, with internet access run:

    python tools/record_crossref_fixtures.py path/to/pdfs --report

It prints one line per PDF and a final `N/M PDFs renamed via Crossref` count. Run it without `--report` on `test-data` to record real Crossref answers as fixtures that `unit-tests/test_crossref_replay.py` then replays offline.


# Future features 
- A GUI version for less tech users is forthcoming  <funding needed - funding being appied - new contributors welcome>.
- Support for wildcards (e.g., NameIt folder1/\*pdf Elon\*.pdf) 

# License #

MIT license. Please acknowledge derivative works. 

# Acknowledgements 

* First created by Jose Teixeira <jose.teixeira@abo.fi>
* First contribuitions by Sukrit 
* Support from the Academy of Finland via the DiWIL project  <see https://web.abo.fi/projekt/diwil/> 
* Support from the open-science initiatives of Åbo Akademi 
