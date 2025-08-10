#!/usr/bin/env python3
"""
Comprehensive Embedding Testing Script

This script performs a thorough validation of the SQL RAG embedding system,
testing all aspects from vector store integrity to end-to-end query processing.
"""

import os
import sys
import time
import json
import pickle
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
import traceback

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def print_section(title: str, char: str = "=") -> None:
    """Print a formatted section header."""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}")

def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n🔍 {title}")
    print("-" * 40)

def print_result(test_name: str, success: bool, details: str = "") -> None:
    """Print a formatted test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"    {details}")

class EmbeddingTestSuite:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.faiss_indices_path = base_path / "faiss_indices"
        self.results = {}
        self.detailed_results = {}
        
        # Test data
        self.test_queries = [
            "How to join customer and orders tables?",
            "Show me queries with multiple table joins",
            "Find examples of LEFT JOIN operations",
            "What are the common aggregation patterns?",
            "Show customer analysis queries",
            "Find inventory management queries",
            "Get transaction data examples"
        ]
        
        self.table_queries = [
            "customers",
            "orders", 
            "products",
            "inventory",
            "panelist",
            "transactions"
        ]
        
    def test_1_faiss_indices_integrity(self) -> Dict[str, Any]:
        """Test 1: Verify FAISS indices exist and are loadable."""
        print_subsection("Testing FAISS Indices Integrity")
        
        results = {
            "indices_found": [],
            "indices_loaded": [],
            "document_counts": {},
            "errors": []
        }
        
        if not self.faiss_indices_path.exists():
            results["errors"].append("FAISS indices directory not found")
            print_result("FAISS Directory Exists", False, "Directory not found")
            return results
            
        print_result("FAISS Directory Exists", True, f"Found at {self.faiss_indices_path}")
        
        # Find all index directories
        for item in self.faiss_indices_path.iterdir():
            if item.is_dir() and (item / "index.faiss").exists():
                results["indices_found"].append(item.name)
                
                try:
                    from langchain_ollama import OllamaEmbeddings
                    from langchain_community.vectorstores import FAISS
                    
                    embeddings = OllamaEmbeddings(model="nomic-embed-text")
                    vector_store = FAISS.load_local(
                        str(item),
                        embeddings,
                        allow_dangerous_deserialization=True
                    )
                    
                    # Get document count if possible
                    doc_count = len(vector_store.docstore._dict) if hasattr(vector_store, 'docstore') else "Unknown"
                    results["indices_loaded"].append(item.name)
                    results["document_counts"][item.name] = doc_count
                    
                    print_result(f"Index {item.name}", True, f"{doc_count} documents")
                    
                except Exception as e:
                    results["errors"].append(f"{item.name}: {str(e)}")
                    print_result(f"Index {item.name}", False, str(e))
            
            elif item.is_file() and item.name in ["index.faiss", "index.pkl"]:
                # Root level index files
                if "root_index" not in results["indices_found"]:
                    results["indices_found"].append("root_index")
                    try:
                        from langchain_ollama import OllamaEmbeddings
                        from langchain_community.vectorstores import FAISS
                        
                        embeddings = OllamaEmbeddings(model="nomic-embed-text")
                        vector_store = FAISS.load_local(
                            str(self.faiss_indices_path),
                            embeddings,
                            allow_dangerous_deserialization=True
                        )
                        
                        doc_count = len(vector_store.docstore._dict) if hasattr(vector_store, 'docstore') else "Unknown"
                        results["indices_loaded"].append("root_index")
                        results["document_counts"]["root_index"] = doc_count
                        
                        print_result("Root Index", True, f"{doc_count} documents")
                        
                    except Exception as e:
                        results["errors"].append(f"root_index: {str(e)}")
                        print_result("Root Index", False, str(e))
        
        return results
    
    def test_2_csv_data_validation(self) -> Dict[str, Any]:
        """Test 2: Validate CSV data structure and content quality."""
        print_subsection("Testing CSV Data Structure and Quality")
        
        results = {
            "csv_files_found": [],
            "data_quality": {},
            "schema_validation": {},
            "errors": []
        }
        
        csv_patterns = [
            "queries_with_descriptions.csv",
            "sample_queries_v1.csv", 
            "sample_test.csv"
        ]
        
        for pattern in csv_patterns:
            # Check in rag_app directory
            csv_path = self.base_path / pattern
            if not csv_path.exists():
                # Check in parent SQL_RAG directory  
                csv_path = self.base_path.parent / pattern
                
            if csv_path.exists():
                results["csv_files_found"].append(str(csv_path))
                
                try:
                    df = pd.read_csv(csv_path)
                    file_key = csv_path.name
                    
                    # Schema validation
                    schema_info = {
                        "columns": list(df.columns),
                        "required_columns_present": {
                            "query": "query" in df.columns,
                            "description": "description" in df.columns,
                            "table": any(col in df.columns for col in ["table", "tables"]),
                            "joins": "joins" in df.columns
                        },
                        "row_count": len(df)
                    }
                    results["schema_validation"][file_key] = schema_info
                    
                    # Data quality analysis
                    quality_info = {
                        "total_rows": len(df),
                        "empty_queries": 0,
                        "empty_descriptions": 0,
                        "has_table_info": 0,
                        "has_join_info": 0,
                        "avg_query_length": 0
                    }
                    
                    if "query" in df.columns:
                        non_empty_queries = df["query"].notna() & (df["query"].str.len() > 0)
                        quality_info["empty_queries"] = len(df) - non_empty_queries.sum()
                        if non_empty_queries.sum() > 0:
                            quality_info["avg_query_length"] = df.loc[non_empty_queries, "query"].str.len().mean()
                    
                    if "description" in df.columns:
                        non_empty_desc = df["description"].notna() & (df["description"].str.len() > 0)
                        quality_info["empty_descriptions"] = len(df) - non_empty_desc.sum()
                    
                    # Check for table information
                    table_cols = [col for col in df.columns if col.lower() in ["table", "tables"]]
                    if table_cols:
                        table_col = table_cols[0]
                        quality_info["has_table_info"] = (df[table_col].notna() & (df[table_col].str.len() > 0)).sum()
                    
                    # Check for join information
                    if "joins" in df.columns:
                        quality_info["has_join_info"] = (df["joins"].notna() & (df["joins"].str.len() > 0)).sum()
                    
                    results["data_quality"][file_key] = quality_info
                    
                    # Print results
                    all_required_present = all(schema_info["required_columns_present"].values())
                    print_result(f"CSV Schema {file_key}", all_required_present, 
                               f"{len(df)} rows, {len(df.columns)} columns")
                    
                    data_quality_score = (
                        (quality_info["total_rows"] - quality_info["empty_queries"]) / max(quality_info["total_rows"], 1) * 100
                    )
                    print_result(f"CSV Quality {file_key}", data_quality_score > 80, 
                               f"{data_quality_score:.1f}% non-empty queries")
                    
                except Exception as e:
                    results["errors"].append(f"{pattern}: {str(e)}")
                    print_result(f"CSV {pattern}", False, str(e))
                    
        return results
    
    def test_3_ollama_integration(self) -> Dict[str, Any]:
        """Test 3: Verify Ollama service and model availability."""
        print_subsection("Testing Ollama Integration")
        
        results = {
            "ollama_available": False,
            "models_available": {},
            "embedding_test": False,
            "errors": []
        }
        
        try:
            from actions.ollama_llm_client import check_ollama_availability
            available, message = check_ollama_availability()
            results["ollama_available"] = available
            print_result("Ollama Service", available, message)
            
        except Exception as e:
            results["errors"].append(f"Ollama check failed: {str(e)}")
            print_result("Ollama Service", False, str(e))
        
        # Test embedding model
        try:
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Test with simple text
            test_text = "SELECT * FROM customers"
            embedding_result = embeddings.embed_query(test_text)
            
            if embedding_result and len(embedding_result) > 0:
                results["embedding_test"] = True
                results["models_available"]["nomic-embed-text"] = True
                print_result("Embedding Model", True, f"Generated {len(embedding_result)}-dimensional embedding")
            else:
                results["models_available"]["nomic-embed-text"] = False
                print_result("Embedding Model", False, "No embedding generated")
                
        except Exception as e:
            results["errors"].append(f"Embedding test failed: {str(e)}")
            results["models_available"]["nomic-embed-text"] = False
            print_result("Embedding Model", False, str(e))
        
        return results
    
    def test_4_similarity_search_quality(self) -> Dict[str, Any]:
        """Test 4: Test similarity search quality with various query types."""
        print_subsection("Testing Similarity Search Quality")
        
        results = {
            "vector_stores_tested": [],
            "search_results": {},
            "relevance_scores": {},
            "errors": []
        }
        
        try:
            from langchain_ollama import OllamaEmbeddings
            from langchain_community.vectorstores import FAISS
            
            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Find and test the best available vector store
            vector_store = None
            store_name = None
            
            # Try different stores in order of preference
            store_priorities = [
                ("index_csv_sample_queries", self.faiss_indices_path / "index_csv_sample_queries"),
                ("root_index", self.faiss_indices_path),
                ("index_bigquery_data", self.faiss_indices_path / "index_bigquery_data")
            ]
            
            for name, path in store_priorities:
                if path.exists() and (path / "index.faiss").exists():
                    try:
                        vector_store = FAISS.load_local(
                            str(path),
                            embeddings,
                            allow_dangerous_deserialization=True
                        )
                        store_name = name
                        results["vector_stores_tested"].append(name)
                        print_result(f"Vector Store {name}", True, "Loaded successfully")
                        break
                    except Exception as e:
                        results["errors"].append(f"Failed to load {name}: {str(e)}")
                        print_result(f"Vector Store {name}", False, str(e))
            
            if not vector_store:
                print_result("Vector Store Loading", False, "No vector store could be loaded")
                return results
            
            # Test similarity searches
            search_results = {}
            relevance_scores = {}
            
            for query in self.test_queries:
                try:
                    docs = vector_store.similarity_search(query, k=3)
                    search_results[query] = {
                        "num_results": len(docs),
                        "results": []
                    }
                    
                    relevance_score = 0
                    for i, doc in enumerate(docs):
                        doc_info = {
                            "content_preview": doc.page_content[:200],
                            "metadata": dict(doc.metadata),
                            "relevance_indicators": []
                        }
                        
                        # Check relevance indicators
                        content_lower = doc.page_content.lower()
                        query_lower = query.lower()
                        
                        # Simple relevance scoring
                        if "join" in query_lower and "join" in content_lower:
                            doc_info["relevance_indicators"].append("contains_join")
                            relevance_score += 1
                        
                        if "customer" in query_lower and "customer" in content_lower:
                            doc_info["relevance_indicators"].append("contains_customer")
                            relevance_score += 1
                        
                        if "table" in query_lower and any(word in content_lower for word in ["table", "from", "join"]):
                            doc_info["relevance_indicators"].append("contains_table_references")
                            relevance_score += 1
                        
                        search_results[query]["results"].append(doc_info)
                    
                    relevance_scores[query] = relevance_score / max(len(docs), 1)
                    
                    success = len(docs) > 0 and relevance_score > 0
                    print_result(f"Search '{query[:30]}...'", success, 
                               f"{len(docs)} results, relevance: {relevance_score}")
                    
                except Exception as e:
                    results["errors"].append(f"Search failed for '{query}': {str(e)}")
                    print_result(f"Search '{query[:30]}...'", False, str(e))
            
            results["search_results"] = search_results
            results["relevance_scores"] = relevance_scores
            
        except Exception as e:
            results["errors"].append(f"Similarity search test failed: {str(e)}")
            print_result("Similarity Search Setup", False, str(e))
        
        return results
    
    def test_5_metadata_preservation(self) -> Dict[str, Any]:
        """Test 5: Verify metadata (tables, joins) is preserved in embeddings."""
        print_subsection("Testing Metadata Preservation")
        
        results = {
            "metadata_fields_found": set(),
            "table_info_preserved": False,
            "join_info_preserved": False,
            "sample_metadata": {},
            "errors": []
        }
        
        try:
            from langchain_ollama import OllamaEmbeddings
            from langchain_community.vectorstores import FAISS
            
            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Try to load a vector store with rich metadata
            for store_path in [
                self.faiss_indices_path / "index_csv_sample_queries",
                self.faiss_indices_path
            ]:
                if store_path.exists() and (store_path / "index.faiss").exists():
                    try:
                        vector_store = FAISS.load_local(
                            str(store_path),
                            embeddings,
                            allow_dangerous_deserialization=True
                        )
                        
                        # Analyze metadata from a sample of documents
                        if hasattr(vector_store, 'docstore') and hasattr(vector_store.docstore, '_dict'):
                            docs_sample = list(vector_store.docstore._dict.values())[:10]
                            
                            for doc in docs_sample:
                                if hasattr(doc, 'metadata'):
                                    for key in doc.metadata.keys():
                                        results["metadata_fields_found"].add(key)
                                    
                                    # Store sample metadata
                                    if not results["sample_metadata"]:
                                        results["sample_metadata"] = dict(doc.metadata)
                        
                        # Test search for table/join information
                        table_query_results = vector_store.similarity_search("customers orders join", k=5)
                        
                        table_info_count = 0
                        join_info_count = 0
                        
                        for doc in table_query_results:
                            if hasattr(doc, 'metadata'):
                                # Check for table information
                                metadata_str = str(doc.metadata).lower()
                                content_str = doc.page_content.lower()
                                
                                if any(indicator in metadata_str or indicator in content_str 
                                      for indicator in ["table", "customer", "order", "product"]):
                                    table_info_count += 1
                                
                                if any(indicator in metadata_str or indicator in content_str 
                                      for indicator in ["join", "inner", "left", "right"]):
                                    join_info_count += 1
                        
                        results["table_info_preserved"] = table_info_count > 0
                        results["join_info_preserved"] = join_info_count > 0
                        
                        print_result("Metadata Fields", len(results["metadata_fields_found"]) > 3, 
                                   f"Found {len(results['metadata_fields_found'])} field types")
                        print_result("Table Info Preserved", results["table_info_preserved"], 
                                   f"{table_info_count}/5 results contain table info")
                        print_result("Join Info Preserved", results["join_info_preserved"], 
                                   f"{join_info_count}/5 results contain join info")
                        
                        break
                        
                    except Exception as e:
                        results["errors"].append(f"Failed to analyze {store_path}: {str(e)}")
                        continue
            
        except Exception as e:
            results["errors"].append(f"Metadata preservation test failed: {str(e)}")
            print_result("Metadata Preservation", False, str(e))
        
        return results
    
    def test_6_end_to_end_pipeline(self) -> Dict[str, Any]:
        """Test 6: Test the complete RAG pipeline end-to-end."""
        print_subsection("Testing End-to-End RAG Pipeline")
        
        results = {
            "pipeline_components": {},
            "query_processing": {},
            "response_quality": {},
            "errors": []
        }
        
        try:
            # Test simple_rag.py functionality
            from simple_rag import answer_question
            
            test_pipeline_queries = [
                "How do I join customer and order tables?",
                "Show me an example of GROUP BY with aggregation",
                "What are common SQL patterns for analytics?"
            ]
            
            for query in test_pipeline_queries:
                try:
                    start_time = time.time()
                    
                    # Test with return_docs and return_tokens
                    answer, docs, token_usage = answer_question(
                        query,
                        k=3,
                        return_docs=True,
                        return_tokens=True
                    )
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    query_result = {
                        "answer_length": len(answer) if answer else 0,
                        "docs_retrieved": len(docs) if docs else 0,
                        "processing_time": processing_time,
                        "token_usage": token_usage,
                        "answer_preview": answer[:200] if answer else "No answer"
                    }
                    
                    results["query_processing"][query] = query_result
                    
                    # Evaluate response quality
                    quality_score = 0
                    if answer and len(answer) > 50:
                        quality_score += 1
                    if docs and len(docs) > 0:
                        quality_score += 1
                    if processing_time < 30:  # Reasonable response time
                        quality_score += 1
                    if any(keyword in answer.lower() for keyword in ["sql", "query", "table", "join"]):
                        quality_score += 1
                    
                    success = quality_score >= 3
                    print_result(f"Pipeline Query '{query[:30]}...'", success, 
                               f"Score: {quality_score}/4, Time: {processing_time:.1f}s")
                    
                except Exception as e:
                    results["errors"].append(f"Pipeline query failed: {query} - {str(e)}")
                    print_result(f"Pipeline Query '{query[:30]}...'", False, str(e))
            
            results["pipeline_components"]["simple_rag"] = True
            
        except Exception as e:
            results["errors"].append(f"End-to-end pipeline test failed: {str(e)}")
            print_result("Pipeline Import", False, str(e))
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all embedding tests and generate comprehensive report."""
        print_section("🧪 COMPREHENSIVE EMBEDDING TESTING SUITE")
        print(f"Testing Path: {self.base_path}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_results = {}
        
        # Run all tests
        test_methods = [
            ("FAISS Indices Integrity", self.test_1_faiss_indices_integrity),
            ("CSV Data Validation", self.test_2_csv_data_validation), 
            ("Ollama Integration", self.test_3_ollama_integration),
            ("Similarity Search Quality", self.test_4_similarity_search_quality),
            ("Metadata Preservation", self.test_5_metadata_preservation),
            ("End-to-End Pipeline", self.test_6_end_to_end_pipeline)
        ]
        
        for test_name, test_method in test_methods:
            print_section(f"TEST: {test_name}", "=")
            try:
                test_results = test_method()
                all_results[test_name] = test_results
                
                # Print summary for this test
                error_count = len(test_results.get("errors", []))
                if error_count == 0:
                    print_result(f"{test_name} Overall", True, "All checks passed")
                else:
                    print_result(f"{test_name} Overall", False, f"{error_count} errors found")
                    
            except Exception as e:
                all_results[test_name] = {"fatal_error": str(e), "errors": [str(e)]}
                print_result(f"{test_name} Overall", False, f"Fatal error: {str(e)}")
                traceback.print_exc()
        
        # Generate summary report
        self._generate_summary_report(all_results)
        
        return all_results
    
    def _generate_summary_report(self, all_results: Dict[str, Any]) -> None:
        """Generate a comprehensive summary report."""
        print_section("📊 COMPREHENSIVE TEST SUMMARY", "=")
        
        total_tests = len(all_results)
        passed_tests = 0
        total_errors = 0
        
        # Count overall results
        for test_name, results in all_results.items():
            if "fatal_error" not in results and len(results.get("errors", [])) == 0:
                passed_tests += 1
            total_errors += len(results.get("errors", []))
            
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 Overall Results:")
        print(f"   Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"   Total Errors: {total_errors}")
        
        # Key findings
        print(f"\n🔍 Key Findings:")
        
        # FAISS indices
        faiss_results = all_results.get("FAISS Indices Integrity", {})
        if faiss_results.get("indices_loaded"):
            print(f"   ✅ Found {len(faiss_results['indices_loaded'])} working FAISS indices")
            for idx_name, doc_count in faiss_results.get("document_counts", {}).items():
                print(f"      - {idx_name}: {doc_count} documents")
        else:
            print(f"   ❌ No working FAISS indices found")
        
        # CSV data
        csv_results = all_results.get("CSV Data Validation", {})
        if csv_results.get("csv_files_found"):
            print(f"   ✅ Found {len(csv_results['csv_files_found'])} CSV files")
            total_rows = sum(info.get("total_rows", 0) for info in csv_results.get("data_quality", {}).values())
            print(f"      - Total query records: {total_rows}")
        else:
            print(f"   ❌ No CSV data files found")
            
        # Ollama integration
        ollama_results = all_results.get("Ollama Integration", {})
        if ollama_results.get("ollama_available"):
            print(f"   ✅ Ollama service is available")
            if ollama_results.get("embedding_test"):
                print(f"      - Embedding model working correctly")
        else:
            print(f"   ⚠️  Ollama service issues detected")
        
        # Search quality
        search_results = all_results.get("Similarity Search Quality", {})
        if search_results.get("search_results"):
            avg_relevance = sum(search_results.get("relevance_scores", {}).values()) / max(len(search_results.get("relevance_scores", {})), 1)
            print(f"   📊 Average search relevance: {avg_relevance:.2f}")
        
        # Pipeline
        pipeline_results = all_results.get("End-to-End Pipeline", {})
        if pipeline_results.get("query_processing"):
            successful_queries = len([q for q, r in pipeline_results["query_processing"].items() 
                                   if r.get("answer_length", 0) > 50])
            total_pipeline_queries = len(pipeline_results["query_processing"])
            print(f"   🔄 Pipeline success: {successful_queries}/{total_pipeline_queries} queries")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if total_errors == 0:
            print("   🎉 All tests passed! Your embedding system is working correctly.")
            print("   📈 Consider running performance tests with larger datasets.")
        else:
            if not faiss_results.get("indices_loaded"):
                print("   🔧 Rebuild FAISS indices - no working indices found")
            
            if not ollama_results.get("ollama_available"):
                print("   🚀 Start Ollama service and pull required models")
                print("      Run: ollama pull phi3:3.8b && ollama pull nomic-embed-text")
            
            if total_errors > 3:
                print("   🔍 Multiple issues detected - check error logs above")
                print("   📋 Consider running debug_embedding_test.py for detailed diagnostics")
        
        # Save detailed results
        results_file = self.base_path / "comprehensive_test_results.json"
        try:
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            print(f"\n💾 Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save results file: {e}")

def main():
    """Main test execution function."""
    base_path = Path(__file__).parent
    
    test_suite = EmbeddingTestSuite(base_path)
    results = test_suite.run_all_tests()
    
    print_section("🏁 TESTING COMPLETE")
    print(f"Results available in comprehensive_test_results.json")
    
    return results

if __name__ == "__main__":
    main()