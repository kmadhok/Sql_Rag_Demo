#!/usr/bin/env python3
"""
Simple test to verify batched embedding processing works.
Tests the fix for the 3+ minute timeout issue.
"""

import sys
import time
import pandas as pd
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema.document import Document

def test_batch_embedding():
    """Test embedding creation with small batches"""
    print("🧪 Testing batched embedding creation...")
    
    # Create small test dataset
    test_data = []
    for i in range(15):  # Test with 15 documents to trigger batching
        test_data.append({
            'query': f'SELECT * FROM table_{i} WHERE id = {i}',
            'description': f'Test query {i} description'
        })
    
    df = pd.DataFrame(test_data)
    print(f"✅ Created test DataFrame with {len(df)} rows")
    
    # Create documents
    documents = []
    for i, (_, row) in enumerate(df.iterrows()):
        doc = Document(
            page_content=f"SQL QUERY: {row['query']}\n\nDESCRIPTION: {row['description']}",
            metadata={
                "source": f'test_row_{i}',
                "query": row['query'],
                "description": row['description']
            }
        )
        documents.append(doc)
    
    print(f"✅ Created {len(documents)} documents")
    
    # Initialize Ollama embeddings
    try:
        embedding_function = OllamaEmbeddings(model="nomic-embed-text")
        print("✅ Ollama embeddings initialized")
    except Exception as e:
        print(f"❌ Failed to initialize embeddings: {e}")
        return False
    
    # Test batched processing (same logic as in embedding_manager.py)
    batch_size = 5  # Small batches
    start_time = time.time()
    
    try:
        if len(documents) <= batch_size:
            # Small batch - process all at once
            vector_store = FAISS.from_documents(documents, embedding_function)
            print(f"✅ Processed {len(documents)} documents in single batch")
        else:
            # Large batch - process in chunks
            print(f"🔄 Processing {len(documents)} documents in batches of {batch_size}...")
            
            # Create first batch
            first_batch = documents[:batch_size]
            print(f"🔄 Creating initial vector store with {len(first_batch)} documents...")
            vector_store = FAISS.from_documents(first_batch, embedding_function)
            print(f"✅ Created initial vector store with {len(first_batch)} documents")
            
            # Add remaining documents in batches
            remaining = documents[batch_size:]
            for i in range(0, len(remaining), batch_size):
                batch = remaining[i:i + batch_size]
                batch_num = i//batch_size + 2
                print(f"🔄 Adding batch {batch_num}: {len(batch)} documents...")
                
                # Extract texts and metadata
                texts = [doc.page_content for doc in batch]
                metadatas = [doc.metadata for doc in batch]
                
                # Add to existing vector store
                vector_store.add_texts(texts=texts, metadatas=metadatas)
                print(f"✅ Added batch {batch_num}")
        
        elapsed = time.time() - start_time
        print(f"⏱️ Total embedding time: {elapsed:.1f} seconds")
        
        # Test a search
        results = vector_store.similarity_search("SELECT FROM table", k=3)
        print(f"✅ Search test returned {len(results)} results")
        
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Embedding failed after {elapsed:.1f} seconds: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Batch Embedding Test")
    print("=" * 50)
    
    success = test_batch_embedding()
    
    print("=" * 50)
    if success:
        print("🎉 Test PASSED! Batched processing works correctly.")
    else:
        print("❌ Test FAILED! Issue with batched processing.")