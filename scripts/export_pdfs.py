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
PRES = 'Pres'
PRIM = 'Prim'
MUN = 'Mun'
LEG = 'Leg'

VALID_CATEGORIES = [PRES, PRIM, MUN, LEG]


def export_pdfs(
    category=None,
    after_date=None,
    before_date=None,
    output_dir='exported_pdfs',
    catalog_csv='notices_catalog.csv',
    dry_run=False
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
    required_cols = ['filename']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Error: Missing required columns: {', '.join(missing_cols)}")
        return
    
    # Check which path column is available
    has_pdf_path = 'pdf_path' in df.columns
    has_path_local = 'path_local' in df.columns
    
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
        
        df = df[df['categorie'] == category].copy()
        print(f"Filtered to {len(df)} entries with category '{category}'")
    
    # Parse dates if provided
    if after_date:
        try:
            after_dt = pd.to_datetime(after_date)
            # Note: We need to parse dates from the 'name' or 'href' or have a date column
            print(f"⚠️  Note: Date filtering requires a date column in base.csv")
            print(f"   Skipping date filter for now. Consider adding date parsing to scrap.py")
        except Exception as e:
            print(f"⚠️  Warning: Could not parse after_date '{after_date}': {e}")
    
    if before_date:
        try:
            before_dt = pd.to_datetime(before_date)
            print(f"⚠️  Note: Date filtering requires a date column in base.csv")
        except Exception as e:
            print(f"⚠️  Warning: Could not parse before_date '{before_date}': {e}")
    
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
        if 'pdf_path' in df.columns and pd.notna(row.get('pdf_path')):
            pdf_path = workspace_root / row['pdf_path']
        elif 'path_local' in df.columns and pd.notna(row.get('path_local')):
            path_local = row['path_local']
            filename = row.get('filename', '')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export PDF files based on category and date filters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all presidential polls
  python export_pdfs.py --category Pres
  
  # Export all primaries
  python export_pdfs.py --category Prim
  
  # Export municipal polls to custom directory
  python export_pdfs.py --category Mun --output municipal_pdfs
  
  # Dry run to see what would be exported
  python export_pdfs.py --category Pres --dry-run
  
  # Export all categories
  python export_pdfs.py --output all_pdfs
        """
    )
    
    parser.add_argument(
        '--category',
        choices=VALID_CATEGORIES,
        help='Election category to export (Pres, Prim, Mun, Leg). If not specified, exports all.'
    )
    
    parser.add_argument(
        '--after',
        help='Only include files after this date (YYYY-MM-DD format) - NOT YET IMPLEMENTED'
    )
    
    parser.add_argument(
        '--before',
        help='Only include files before this date (YYYY-MM-DD format) - NOT YET IMPLEMENTED'
    )
    
    parser.add_argument(
        '--output',
        default='exported_pdfs',
        help='Output directory for exported PDFs (default: exported_pdfs)'
    )
    
    parser.add_argument(
        '--catalog',
        default='notices_catalog.csv',
        help='Path to catalog CSV file (default: notices_catalog.csv)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be copied without actually copying files'
    )
    
    args = parser.parse_args()
    
    export_pdfs(
        category=args.category,
        after_date=args.after,
        before_date=args.before,
        output_dir=args.output,
        catalog_csv=args.catalog,
        dry_run=args.dry_run
    )
