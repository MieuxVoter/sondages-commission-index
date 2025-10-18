#!/usr/bin/env python3
"""
Merge base.csv and files.csv to create a comprehensive catalog.
Creates notices_catalog.csv with all file information and categories.
"""

import pandas as pd
from pathlib import Path
import sys


def merge_files(base_csv='base.csv', files_csv='files.csv', output_csv='notices_catalog.csv'):
    """
    Merge base.csv and files.csv into a comprehensive catalog.
    
    Args:
        base_csv: Path to base CSV with categories
        files_csv: Path to files CSV with PDF metadata
        output_csv: Output path for merged catalog
    
    Returns:
        Path to the created catalog file
    """
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    
    base_path = workspace_root / base_csv
    files_path = workspace_root / files_csv
    output_path = workspace_root / output_csv
    
    # Check if input files exist
    if not base_path.exists():
        print(f"❌ Error: {base_path} not found!")
        print("Run scrap.py first to generate base.csv")
        sys.exit(1)
    
    if not files_path.exists():
        print(f"❌ Error: {files_path} not found!")
        print("Run download.py first to generate files.csv")
        sys.exit(1)
    
    print(f"Reading {base_path}...")
    df_base = pd.read_csv(base_path)
    print(f"  Loaded {len(df_base)} entries")
    
    print(f"Reading {files_path}...")
    df_files = pd.read_csv(files_path)
    print(f"  Loaded {len(df_files)} entries")
    
    # Check for categorie column in base
    if 'categorie' not in df_base.columns:
        print(f"⚠️  Warning: 'categorie' column not found in {base_csv}")
        print("   Categories will not be included in the merged file")
    
    # Merge strategy: Match by 'name' field
    # base.csv has: name, href, year, categorie
    # files.csv has: url, path_local, filename, http last-modified, pdf creation-date, name
    
    # Both have 'name' column, so we can merge on that
    print("\nMerging files on 'name' column...")
    
    # Perform left merge to keep all files even if not in base
    merged_df = df_files.merge(
        df_base[['name', 'categorie', 'year', 'href']], 
        on='name', 
        how='left'
    )
    
    # Combine path_local and filename to create full path
    merged_df['pdf_path'] = merged_df.apply(
        lambda row: str(Path(row['path_local']) / row['filename']) if pd.notna(row['path_local']) and pd.notna(row['filename']) else None,
        axis=1
    )
    
    # Reorder columns for better readability
    column_order = [
        'filename',
        'categorie',
        'year',
        'name',
        'pdf_path',
        'path_local',
        'url',
        'href',
        'http last-modified',
        'pdf creation-date'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in merged_df.columns]
    merged_df = merged_df[column_order]
    
    # Save merged catalog
    merged_df.to_csv(output_path, index=False)
    
    print(f"\n{'='*80}")
    print(f"Merge Summary:")
    print(f"{'='*80}")
    print(f"  Total entries: {len(merged_df)}")
    print(f"  With category: {merged_df['categorie'].notna().sum()}")
    print(f"  Without category: {merged_df['categorie'].isna().sum()}")
    print(f"\n  Category breakdown:")
    if 'categorie' in merged_df.columns:
        for cat, count in merged_df['categorie'].value_counts().items():
            print(f"    {cat}: {count}")
    print(f"\n  📁 Output file: {output_path}")
    print(f"{'='*80}\n")
    
    return output_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Merge base.csv and files.csv into a comprehensive catalog'
    )
    
    parser.add_argument(
        '--base-csv',
        default='base.csv',
        help='Path to base CSV file (default: base.csv)'
    )
    
    parser.add_argument(
        '--files-csv',
        default='files.csv',
        help='Path to files CSV file (default: files.csv)'
    )
    
    parser.add_argument(
        '--output',
        default='notices_catalog.csv',
        help='Output path for merged catalog (default: notices_catalog.csv)'
    )
    
    args = parser.parse_args()
    
    merge_files(
        base_csv=args.base_csv,
        files_csv=args.files_csv,
        output_csv=args.output
    )
