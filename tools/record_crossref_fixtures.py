#!/usr/bin/env python3
"""Record real Crossref responses for the PDFs in a folder, and print the names NameIt derives.

Run this ON A MACHINE WITH INTERNET ACCESS (needs api.crossref.org):

    python tools/record_crossref_fixtures.py test-data            # writes test-data/crossref/<doi>.json
    python tools/record_crossref_fixtures.py ~/papers --report    # only prints a success table

Review the printed names, then commit the JSON files plus the generated expected_names.json.
unit-tests/test_crossref_replay.py replays them offline and compares against expected_names.json.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from nameit.crossref import find_dois_in_pdf, fetch_metadata_by_doi, validate_crossref_returned_meta_data



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--report", action="store_true", help="do not write fixtures, just print the success rate")
    args = ap.parse_args(argv)

    out_dir = os.path.join(args.folder, "crossref")
    expected_path = os.path.join(out_dir, "expected_names.json")
    expected = {}
    pdfs = sorted(f for f in os.listdir(args.folder) if f.lower().endswith(".pdf"))
    ok = 0
    for name in pdfs:
        found = find_dois_in_pdf(os.path.join(args.folder, name))
        if not found:
            print(f"NO DOI   {name}")
            continue
        doi = found[0][1]
        meta = fetch_metadata_by_doi(doi)
        if not meta:
            print(f"NO META  {name}  ({doi})")
            continue
        try:
            pub = validate_crossref_returned_meta_data(meta)
        except Exception as e:  # unusable record
            print(f"UNUSABLE {name}  ({doi}): {e}")
            continue
        ok += 1
        print(f"OK       {name}\n         -> {pub}.pdf")
        if not args.report:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, doi.replace("/", "_") + ".json"), "w") as fh:
                json.dump({"doi": doi, "message": meta}, fh, indent=1, ensure_ascii=False, sort_keys=True)
            expected[doi] = str(pub)
    print(f"\n{ok}/{len(pdfs)} PDFs renamed via Crossref")
    if not args.report and expected:
        with open(expected_path, "w") as fh:
            json.dump(expected, fh, indent=1, ensure_ascii=False, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
