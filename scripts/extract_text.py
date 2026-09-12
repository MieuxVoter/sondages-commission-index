#!/usr/bin/env python3
"""
Extract PDF notices to plain text with pdfplumber.

Produces archives_txt/<year>/<month>/<slug>.txt mirroring archives/, so the notices
can be fed to a LLM without going through the PDF.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

# Election category constants (same as export_pdfs.py)
PRES = "Pres"
PRIM = "Prim"
MUN = "Mun"
LEG = "Leg"

VALID_CATEGORIES = [PRES, PRIM, MUN, LEG]

PDF_DIR = "archives"
TXT_DIR = "archives_txt"

# Below this, the PDF very likely has no text layer (scanned images)
MIN_USEFUL_CHARS = 200


def txt_path_for(pdf_path):
    """
    Derive the text file path from a PDF path.

    archives/2026/septembre/10260-pres.pdf -> archives_txt/2026/septembre/10260-pres.txt

    Args:
        pdf_path: PDF path relative to the workspace root

    Returns:
        Path (relative) of the corresponding text file
    """
    parts = Path(pdf_path).parts
    if parts and parts[0] == PDF_DIR:
        parts = (TXT_DIR,) + parts[1:]
    else:
        parts = (TXT_DIR,) + parts
    return Path(*parts).with_suffix(".txt")


def clean_layout_text(text):
    """
    Trim the whitespace padding that layout mode adds, while keeping column alignment.

    Strips trailing spaces on each line and collapses runs of blank lines into one.
    Typically cuts a notice from ~95k to ~34k characters.
    """
    if not text:
        return ""

    lines = []
    blank = 0
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped:
            blank = 0
        else:
            blank += 1
            if blank > 1:
                continue
        lines.append(stripped)

    return "\n".join(lines).strip()


def extract_pdf_text(pdf_path):
    """
    Extract the whole PDF as layout-preserving text.

    Layout mode matters here: notices often show two borderless tables side by side,
    and the default mode interleaves them line by line, which misleads a LLM.

    Args:
        pdf_path: path to the PDF file

    Returns:
        Extracted text, pages separated by a `--- page N ---` marker
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            content = clean_layout_text(page.extract_text(layout=True))
            pages.append(f"--- page {number} ---\n\n{content}")

    return "\n\n".join(pages).strip()


def build_header(pdf_path, row=None):
    """
    Build a provenance header, so the text file carries its own context.

    Args:
        pdf_path: PDF path relative to the workspace root
        row: matching notices_catalog.csv row, if any

    Returns:
        Header string ending with a blank line
    """
    fields = [("source_pdf", str(pdf_path))]

    if row is not None:
        for key in ("name", "categorie", "year", "url", "pdf creation-date"):
            value = row.get(key)
            if pd.notna(value):
                if key == "year":
                    value = int(float(value))
                fields.append((key.replace(" ", "_"), value))

    lines = ["# notice commission des sondages"]
    lines += [f"# {key}: {value}" for key, value in fields]
    lines.append("# extraction: pdfplumber (layout=True)")

    return "\n".join(lines) + "\n\n"


def load_catalog(workspace_root, catalog_csv="notices_catalog.csv"):
    """Load the catalog indexed by pdf_path, or None if it is not available."""
    catalog_path = workspace_root / catalog_csv
    if not catalog_path.exists():
        print(f"⚠️  {catalog_path} not found, text files will have a minimal header")
        return None

    df = pd.read_csv(catalog_path)
    if "pdf_path" not in df.columns:
        print(f"⚠️  No 'pdf_path' column in {catalog_csv}, text files will have a minimal header")
        return None

    return df.dropna(subset=["pdf_path"]).drop_duplicates(subset=["pdf_path"]).set_index("pdf_path")


def list_new_pdfs(workspace_root):
    """
    List the PDFs git does not track yet under archives/.

    These are exactly the files download.py fetched during the current run.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", PDF_DIR],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"❌ Unable to ask git for new files: {error}")
        return []

    return [line for line in result.stdout.splitlines() if line.strip().lower().endswith(".pdf")]


def list_missing_pdfs(workspace_root, catalog, category=None):
    """List every catalog PDF that has no text file yet."""
    if catalog is None:
        print("❌ --missing needs notices_catalog.csv, run merge_files.py first")
        return []

    df = catalog
    if category:
        df = df[df["categorie"] == category]
        print(f"Filtered to {len(df)} entries with category '{category}'")

    pdf_paths = []
    for pdf_path in df.index:
        if not (workspace_root / pdf_path).exists():
            continue
        if (workspace_root / txt_path_for(pdf_path)).exists():
            continue
        pdf_paths.append(pdf_path)

    return pdf_paths


def extract_many(pdf_paths, workspace_root, catalog=None, overwrite=False):
    """
    Extract a list of PDFs to text files.

    A broken notice must never fail the daily workflow, so every file is guarded.

    Args:
        pdf_paths: PDF paths relative to the workspace root
        workspace_root: repository root
        catalog: catalog indexed by pdf_path, for the provenance header
        overwrite: re-extract files that already exist

    Returns:
        (extracted, skipped, errors) counts
    """
    extracted = skipped = errors = 0

    print(f"\n{'='*80}")
    print(f"Extracting {len(pdf_paths)} PDF(s) to text...")
    print(f"{'='*80}\n")

    for pdf_path in pdf_paths:
        pdf_path = str(pdf_path)
        txt_path = txt_path_for(pdf_path)
        full_txt_path = workspace_root / txt_path

        if full_txt_path.exists() and not overwrite:
            print(f"⏭️  Already extracted: {txt_path}")
            skipped += 1
            continue

        full_pdf_path = workspace_root / pdf_path
        if not full_pdf_path.exists():
            print(f"  ⚠️  Not found: {pdf_path}")
            errors += 1
            continue

        try:
            text = extract_pdf_text(full_pdf_path)
        except Exception as error:
            print(f"  ❌ Error extracting {pdf_path}: {error}")
            errors += 1
            continue

        row = None
        if catalog is not None and pdf_path in catalog.index:
            row = catalog.loc[pdf_path]

        full_txt_path.parent.mkdir(parents=True, exist_ok=True)
        full_txt_path.write_text(build_header(pdf_path, row) + text + "\n", encoding="utf-8")

        if len(text) < MIN_USEFUL_CHARS:
            print(f"⚠️  {txt_path} ({len(text)} chars, probably a scanned PDF)")
        else:
            print(f"✅ {txt_path} ({len(text):,} chars)")
        extracted += 1

    return extracted, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description="Extract PDF notices to plain text with pdfplumber",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract the PDFs just downloaded by download.py (what the workflow runs)
  python extract_text.py --new

  # Extract specific notices
  python extract_text.py archives/2026/septembre/10260-pres-iv-opinionway-cnews-11-septembre.pdf

  # Backfill the presidential notices that have no text yet
  python extract_text.py --missing --category Pres

  # Backfill everything, a few files at a time
  python extract_text.py --missing --limit 50
        """,
    )

    parser.add_argument("pdfs", nargs="*", help="PDF paths to extract (default: --new)")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--new",
        action="store_true",
        help="Extract the PDFs not tracked by git yet, i.e. those downloaded during this run (default)",
    )
    mode.add_argument(
        "--missing", action="store_true", help="Extract every catalog PDF that has no text file yet (backfill)"
    )

    parser.add_argument(
        "--category", choices=VALID_CATEGORIES, help="With --missing, restrict to an election category"
    )
    parser.add_argument("--limit", type=int, help="Stop after this many PDFs")
    parser.add_argument("--overwrite", action="store_true", help="Re-extract files that already exist")
    parser.add_argument(
        "--catalog", default="notices_catalog.csv", help="Path to catalog CSV file (default: notices_catalog.csv)"
    )

    args = parser.parse_args()

    workspace_root = Path(__file__).parent.parent
    catalog = load_catalog(workspace_root, args.catalog)

    if args.pdfs:
        if args.new or args.missing:
            parser.error("explicit PDF paths cannot be combined with --new or --missing")
        pdf_paths = args.pdfs
    elif args.missing:
        pdf_paths = list_missing_pdfs(workspace_root, catalog, args.category)
        print(f"Found {len(pdf_paths)} PDF(s) without text file")
    else:
        pdf_paths = list_new_pdfs(workspace_root)
        print(f"Found {len(pdf_paths)} new PDF(s) in {PDF_DIR}/")

    if args.limit:
        pdf_paths = pdf_paths[: args.limit]

    if not pdf_paths:
        print("✅ Nothing to extract")
        return

    extracted, skipped, errors = extract_many(pdf_paths, workspace_root, catalog, args.overwrite)

    print(f"\n{'='*80}")
    print("Extraction Summary:")
    print(f"{'='*80}")
    print(f"  ✅ Extracted: {extracted} files")
    print(f"  ⏭️  Skipped (already extracted): {skipped} files")
    print(f"  ❌ Errors: {errors} files")
    print(f"  📁 Output directory: {workspace_root / TXT_DIR}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    sys.exit(main())
