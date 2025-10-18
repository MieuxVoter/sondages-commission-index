#!/usr/bin/env python3
"""
Export PDF files based on category and date filters.
Copies matching PDFs to an output directory.
"""

import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime
import argparse


# Election category constants
PRES = "Pres"
PRIM = "Prim"
MUN = "Mun"
LEG = "Leg"

VALID_CATEGORIES = [PRES, PRIM, MUN, LEG]


def get_best_date(row):
    """
    Extract the best available date from a row using multiple strategies.
    Priority:
    1. pdf creation-date (most accurate)
    2. http last-modified (server timestamp)
    3. year column (fallback to middle of year: July 1st)

    Returns:
        datetime or None if no date can be determined (all returned as tz-naive)
    """
    # Strategy 1: PDF creation date
    if pd.notna(row.get("pdf creation-date")):
        try:
            dt = pd.to_datetime(row["pdf creation-date"])
            # Convert to naive datetime if timezone-aware
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
        except:
            pass

    # Strategy 2: HTTP last-modified
    if pd.notna(row.get("http last-modified")):
        try:
            dt = pd.to_datetime(row["http last-modified"])
            # Convert to naive datetime if timezone-aware
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
        except:
            pass

    # Strategy 3: Year column (use July 1st as midpoint)
    if pd.notna(row.get("year")):
        try:
            year = int(float(row["year"]))
            return pd.to_datetime(f"{year}-07-01")
        except:
            pass

    return None


def apply_date_filter(df, after_date=None, before_date=None):
    """
    Filter dataframe by date using multiple date sources.

    Args:
        df: DataFrame to filter
        after_date: Only include entries after this date (YYYY-MM-DD format)
        before_date: Only include entries before this date (YYYY-MM-DD format)

    Returns:
        Filtered DataFrame
    """
    if not after_date and not before_date:
        return df

    # Parse filter dates
    after_dt = pd.to_datetime(after_date) if after_date else None
    before_dt = pd.to_datetime(before_date) if before_date else None

    # Extract best date for each row
    print("\nApplying date filters...")
    if after_dt:
        print(f"  After: {after_dt.strftime('%Y-%m-%d')}")
    if before_dt:
        print(f"  Before: {before_dt.strftime('%Y-%m-%d')}")

    df_copy = df.copy()
    df_copy["_filter_date"] = df_copy.apply(get_best_date, axis=1)

    # Count how many have valid dates
    valid_dates = df_copy["_filter_date"].notna().sum()
    print(f"  Found dates for {valid_dates}/{len(df_copy)} entries")

    # Show date source breakdown
    pdf_dates = df_copy["pdf creation-date"].notna().sum()
    http_dates = df_copy["http last-modified"].notna().sum()
    year_only = df_copy["year"].notna().sum()
    print(f"  Date sources: {pdf_dates} PDF creation dates, {http_dates} HTTP dates, {year_only} year-only")

    # Apply filters
    mask = pd.Series([True] * len(df_copy), index=df_copy.index)

    if after_dt:
        date_mask = df_copy["_filter_date"] >= after_dt
        # Include rows without dates (don't exclude them)
        mask = mask & (date_mask | df_copy["_filter_date"].isna())
        filtered_by_after = date_mask.sum()
        print(f"  {filtered_by_after} entries match 'after' filter")

    if before_dt:
        date_mask = df_copy["_filter_date"] <= before_dt
        # Include rows without dates (don't exclude them)
        mask = mask & (date_mask | df_copy["_filter_date"].isna())
        filtered_by_before = date_mask.sum()
        print(f"  {filtered_by_before} entries match 'before' filter")

    # Drop temporary column and return filtered df
    return df[mask]


def export_pdfs(
    category=None,
    after_date=None,
    before_date=None,
    output_dir="exported_pdfs",
    catalog_csv="notices_catalog.csv",
    dry_run=False,
):
    """
    Export PDF files based on category and date filters.

    Args:
        category: Election category ('Pres', 'Prim', 'Mun', 'Leg') or None for all
        after_date: Only include files after this date (YYYY-MM-DD format)
        before_date: Only include files before this date (YYYY-MM-DD format)
        output_dir: Directory to copy PDFs to
        catalog_csv: Path to catalog CSV file with file information
        dry_run: If True, only show what would be copied without actually copying
    """
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent

    # Read catalog CSV
    catalog_path = workspace_root / catalog_csv
    if not catalog_path.exists():
        print(f"❌ Error: {catalog_path} not found!")
        print("Run merge_files.py first to generate notices_catalog.csv")
        return

    print(f"Reading {catalog_path}...")
    df = pd.read_csv(catalog_path)

    # Check if required columns exist
    required_cols = ["filename"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Error: Missing required columns: {', '.join(missing_cols)}")
        return

    # Check which path column is available
    has_pdf_path = "pdf_path" in df.columns
    has_path_local = "path_local" in df.columns

    if not has_pdf_path and not has_path_local:
        print("❌ Error: Neither 'pdf_path' nor 'path_local' column found")
        return

    print(f"Loaded {len(df)} entries")

    # Filter by category
    if category:
        if category not in VALID_CATEGORIES:
            print(f"❌ Error: Invalid category '{category}'")
            print(f"Valid categories: {', '.join(VALID_CATEGORIES)}")
            return

        df = df[df["categorie"] == category].copy()
        print(f"Filtered to {len(df)} entries with category '{category}'")

    # Apply date filtering using multiple strategies
    if after_date or before_date:
        df = apply_date_filter(df, after_date, before_date)
        print(f"After date filtering: {len(df)} entries remaining")

    # Create output directory
    output_path = workspace_root / output_dir
    if not dry_run:
        output_path.mkdir(exist_ok=True)
        print(f"Output directory: {output_path}")
    else:
        print(f"[DRY RUN] Would create output directory: {output_path}")

    # Process each file
    copied_count = 0
    error_count = 0

    print(f"\n{'='*80}")
    print(f"Processing {len(df)} files...")
    print(f"{'='*80}\n")

    for idx, row in df.iterrows():
        # Use pdf_path if available, otherwise construct from path_local + filename
        if "pdf_path" in df.columns and pd.notna(row.get("pdf_path")):
            pdf_path = workspace_root / row["pdf_path"]
        elif "path_local" in df.columns and pd.notna(row.get("path_local")):
            path_local = row["path_local"]
            filename = row.get("filename", "")
            if filename:
                pdf_path = workspace_root / path_local / filename
            else:
                print(f"  ⚠️  No filename for: {row.get('name', 'unknown')}")
                error_count += 1
                continue
        else:
            print(f"  ⚠️  No path for: {row.get('name', 'unknown')}")
            error_count += 1
            continue

        pdf_filename = Path(pdf_path).name

        if pdf_path.exists():
            if dry_run:
                print(f"[DRY RUN] Would copy: {pdf_filename}")
                copied_count += 1
            else:
                try:
                    dest_path = output_path / pdf_filename
                    shutil.copy2(pdf_path, dest_path)
                    print(f"✅ Copied: {pdf_filename}")
                    copied_count += 1
                except Exception as e:
                    print(f"  ❌ Error copying {pdf_filename}: {e}")
                    error_count += 1
        else:
            print(f"  ⚠️  Not found: {pdf_path}")
            error_count += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"Export Summary:")
    print(f"{'='*80}")
    if dry_run:
        print(f"  [DRY RUN - No files were actually copied]")
    print(f"  ✅ Successfully copied: {copied_count} files")
    print(f"  ❌ Errors: {error_count} files")
    print(f"  📁 Output directory: {output_path}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export PDF files based on category and date filters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all presidential polls
  python export_pdfs.py --category Pres
  
  # Export all primaries from 2024 onwards
  python export_pdfs.py --category Prim --after 2024-01-01
  
  # Export presidential polls from Dec 2023 to now
  python export_pdfs.py --category Pres --after 2023-12-01
  
  # Export municipal polls before 2020
  python export_pdfs.py --category Mun --before 2020-01-01
  
  # Export municipal polls to custom directory
  python export_pdfs.py --category Mun --output municipal_pdfs
  
  # Dry run to see what would be exported
  python export_pdfs.py --category Pres --dry-run
  
  # Export all categories
  python export_pdfs.py --output all_pdfs
        """,
    )

    parser.add_argument(
        "--category",
        choices=VALID_CATEGORIES,
        help="Election category to export (Pres, Prim, Mun, Leg). If not specified, exports all.",
    )

    parser.add_argument(
        "--after",
        help="Only include files after this date (YYYY-MM-DD format). Uses PDF creation date, HTTP last-modified, or year column.",
    )

    parser.add_argument(
        "--before",
        help="Only include files before this date (YYYY-MM-DD format). Uses PDF creation date, HTTP last-modified, or year column.",
    )

    parser.add_argument(
        "--output", default="exported_pdfs", help="Output directory for exported PDFs (default: exported_pdfs)"
    )

    parser.add_argument(
        "--catalog", default="notices_catalog.csv", help="Path to catalog CSV file (default: notices_catalog.csv)"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be copied without actually copying files"
    )

    args = parser.parse_args()

    export_pdfs(
        category=args.category,
        after_date=args.after,
        before_date=args.before,
        output_dir=args.output,
        catalog_csv=args.catalog,
        dry_run=args.dry_run,
    )
