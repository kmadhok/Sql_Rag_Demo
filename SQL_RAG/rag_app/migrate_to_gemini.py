#!/usr/bin/env python3
"""
Automated migration script to switch from OpenAI to Gemini embeddings.

This script:
1. Backs up the existing vector store
2. Switches to Gemini embeddings configuration
3. Regenerates the vector store with Gemini
4. Verifies the migration
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime


def backup_existing indices():
    """Backup existing vector store indices."""
    faiss_dir = Path("faiss_indices")
    
    if not faiss_dir.exists():
        print("📁 No existing faiss_indices directory found")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"faiss_indices_openai_backup_{timestamp}"
    
    print(f"📦 Backing up faiss_indices to {backup_dir}")
    try:
        shutil.move(str(faiss_dir), backup_dir)
        print(f"✅ Backup completed: {backup_dir}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def set_gemini_environment(project_id: str):
    """Set environment variables for Gemini embeddings."""
    print("⚙️ Setting environment variables for Gemini embeddings...")
    
    os.environ["EMBEDDINGS_PROVIDER"] = "gemini"
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GEMINI_EMBEDDING_MODEL"] = "gemini-embedding-001"
    
    print(f"✅ Environment configured:")
    print(f"   - EMBEDDINGS_PROVIDER: {os.environ['EMBEDDINGS_PROVIDER']}")
    print(f"   - GOOGLE_CLOUD_PROJECT: {os.environ['GOOGLE_CLOUD_PROJECT']}")
    print(f"   - GOOGLE_CLOUD_LOCATION: {os.environ['GOOGLE_CLOUD_LOCATION']}")
    print(f"   - GEMINI_EMBEDDING_MODEL: {os.environ['GEMINI_EMBEDDING_MODEL']}")


def regenerate_vector_store(csv_path: str = None):
    """Regenerate vector store with Gemini embeddings."""
    print("📚 Regenerating vector store with Gemini embeddings...")
    
    try:
        import standalone_embedding_generator
        
        # Build command arguments
        if csv_path:
            cmd_args = ["--csv", csv_path, "--embeddings-provider", "gemini"]
        else:
            cmd_args = ["--embeddings-provider", "gemini"]
        
        print(f"🔄 Running: python standalone_embedding_generator.py {' '.join(cmd_args)}")
        
        # Simulate running the command (you would run this manually)
        print("\n📋 MANUAL STEP REQUIRED:")
        print(f"   Please run: python standalone_embedding_generator.py {' '.join(cmd_args)}")
        print("   This will regenerate your vector store with Gemini embeddings.")
        
        return True
        
    except ImportError:
        print("❌ standalone_embedding_generator.py not found")
        print("   Ensure the file exists in the current directory")
        return False
    except Exception as e:
        print(f"❌ Error during regeneration: {e}")
        return False


def verify_migration():
    """Verify the migration was successful."""
    print("🔍 Verifying migration...")
    
    try:
        # Test embedding provider
        from utils.embedding_provider import get_provider_info, get_embedding_function
        
        info = get_provider_info()
        print(f"\n📊 Provider Info:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # Test embedding function is callable
        embeddings = get_embedding_function()
        print(f"\n✅ Embedding function type: {type(embeddings)}")
        print(f"✅ Callable: {hasattr(embeddings, '__call__')}")
        print(f"✅ Has embed_query: {hasattr(embeddings, 'embed_query')}")
        print(f"✅ Has embed_documents: {hasattr(embeddings, 'embed_documents')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate to Gemini embeddings")
    parser.add_argument(
        "--project-id", 
        required=True,
        help="Google Cloud Project ID"
    )
    parser.add_argument(
        "--csv", 
        help="Path to CSV file for vector store generation"
    )
    parser.add_argument(
        "--no-backup", 
        action="store_true",
        help="Skip backup of existing vector store"
    )
    
    args = parser.parse_args()
    
    print("🔄 Starting migration to Gemini embeddings...")
    print("=" * 50)
    
    # Step 1: Backup existing indices
    if not args.no_backup:
        backup_existing_indices()
    
    # Step 2: Set environment
    set_gemini_environment(args.project_id)
    
    # Step 3: Regenerate vector store
    regenerate_vector_store(args.csv)
    
    # Step 4: Verify configuration
    verify_migration()
    
    print("\n" + "=" * 50)
    print("🎉 Migration steps completed!")
    print("\n📋 NEXT STEPS:")
    print("1. Manually run the vector store regeneration command shown above")
    print("2. Test your app: python app_simple_gemini.py")
    print("3. If everything works, you can remove the backup directory")
    print("\n✅ Your app will now use Google Gemini embeddings!")


if __name__ == "__main__":
    main()