#!/usr/bin/env python3
"""
Script to recover and properly merge generated metadata from checkpoint files
"""

import json
import pandas as pd
import re
from pathlib import Path

def normalize_query(query):
    """Normalize query string for matching"""
    # Remove extra whitespace and newlines
    normalized = re.sub(r'\s+', ' ', query.strip())
    return normalized

def recover_metadata_from_checkpoint():
    """Recover metadata from checkpoint file and create proper CSV"""
    
    # Paths
    checkpoint_file = Path("checkpoints/sql_metadata_generation_results.json")
    original_csv = Path("data_new/sample_queries_with_metadata.csv")
    output_csv = Path("data_new/sample_queries_with_metadata_recovered.csv")
    
    print("🔧 Recovering metadata from checkpoint files...")
    
    # Load checkpoint data
    if not checkpoint_file.exists():
        print(f"❌ Checkpoint file not found: {checkpoint_file}")
        return False
    
    print(f"📂 Loading checkpoint data from: {checkpoint_file}")
    with open(checkpoint_file, 'r') as f:
        checkpoint_data = json.load(f)
    
    # Extract results from checkpoint
    if 'results' not in checkpoint_data:
        print("❌ No results found in checkpoint file")
        return False
    
    results = checkpoint_data['results']
    print(f"✅ Found {len(results)} results in checkpoint")
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    print(f"📊 Converted to DataFrame with columns: {list(results_df.columns)}")
    
    # Load original CSV to get the original order
    print(f"📂 Loading original CSV: {original_csv}")
    original_df = pd.read_csv(original_csv)
    original_df = original_df[['query']].copy()  # Only keep query column
    
    print(f"📋 Original CSV has {len(original_df)} queries")
    print(f"📋 Checkpoint has {len(results_df)} queries with metadata")
    
    # Create lookup dictionary using normalized queries
    print("🔗 Creating lookup dictionary for query matching...")
    metadata_lookup = {}
    for _, row in results_df.iterrows():
        normalized_query = normalize_query(row['query'])
        metadata_lookup[normalized_query] = {
            'description': row['description'],
            'tables': row['tables'],
            'joins': row['joins']
        }
    
    print(f"📚 Created lookup dictionary with {len(metadata_lookup)} entries")
    
    # Match and merge data
    print("🔗 Matching queries and merging metadata...")
    matched_count = 0
    merged_data = []
    
    for idx, row in original_df.iterrows():
        original_query = row['query']
        normalized_original = normalize_query(original_query)
        
        # Try to find metadata for this query
        if normalized_original in metadata_lookup:
            metadata = metadata_lookup[normalized_original]
            merged_data.append({
                'query': original_query,
                'description': metadata['description'],
                'tables': metadata['tables'],
                'joins': metadata['joins']
            })
            matched_count += 1
        else:
            # No metadata found
            merged_data.append({
                'query': original_query,
                'description': '',
                'tables': '',
                'joins': ''
            })
    
    # Create final DataFrame
    merged_df = pd.DataFrame(merged_data)
    
    print(f"✅ Merged DataFrame has {len(merged_df)} rows")
    print(f"📈 Matched queries: {matched_count}/{len(merged_df)} ({matched_count/len(merged_df)*100:.1f}%)")
    
    # Check coverage
    filled_descriptions = merged_df['description'].str.len().gt(0).sum()
    print(f"📈 Coverage: {filled_descriptions}/{len(merged_df)} queries have descriptions ({filled_descriptions/len(merged_df)*100:.1f}%)")
    
    # Save to new CSV
    print(f"💾 Saving recovered data to: {output_csv}")
    merged_df.to_csv(output_csv, index=False)
    
    print("✅ Recovery complete!")
    print(f"📁 Recovered file: {output_csv}")
    
    # Show sample of recovered data
    print("\n📊 Sample of recovered data:")
    sample_with_data = merged_df[merged_df['description'].str.len() > 0].head(3)
    for idx, row in sample_with_data.iterrows():
        print(f"\n🔍 Query {idx + 1}:")
        print(f"   Description: {row['description'][:100]}...")
        print(f"   Tables: {row['tables']}")
        print(f"   Joins: {row['joins']}")
    
    return True

if __name__ == "__main__":
    success = recover_metadata_from_checkpoint()
    if success:
        print("\n🚀 Next step: Use the recovered CSV file for embedding generation:")
        print("   python standalone_embedding_generator.py --csv \"data_new/sample_queries_with_metadata_recovered.csv\"")
    else:
        print("\n❌ Recovery failed!")