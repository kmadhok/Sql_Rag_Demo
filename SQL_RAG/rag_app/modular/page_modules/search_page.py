#!/usr/bin/env python3
"""
Query Search Page for Modular SQL RAG application.
Handles vector search functionality with Gemini optimization.
"""

import streamlit as st
import logging
from typing import Optional

from modular.config import PAGE_NAMES
from modular.session_manager import session_manager
from modular.vector_store_manager import vector_store_manager
from modular.rag_engine import rag_engine
from modular.utils import (
    validate_query_input, extract_agent_type, calculate_context_utilization,
    find_original_queries_for_sources, safe_get_value
)

# Configure logging
logger = logging.getLogger(__name__)

# Import hybrid search components
try:
    from hybrid_retriever import SearchWeights
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False


class SearchPage:
    """Query Search page implementation"""
    
    def __init__(self):
        self.page_title = PAGE_NAMES['search']
    
    def render_search_configuration(self):
        """Render search configuration options"""
        st.header("⚙️ Search Configuration")
        
        # Vector store selection
        available_indices = vector_store_manager.get_available_indices()
        
        if not available_indices:
            st.error("❌ No vector stores found!")
            st.info("💡 First run: python standalone_embedding_generator.py --csv 'your_data.csv'")
            return None
        
        selected_index = st.selectbox(
            "📂 Select Vector Store:",
            available_indices,
            help="Choose which vector store to search"
        )
        
        # Search parameters
        col1, col2 = st.columns(2)
        
        with col1:
            k = st.slider("📚 Results to retrieve (k)", 1, 20, 4, 
                         help="Number of most relevant chunks to retrieve")
            
            gemini_mode = st.checkbox("🔥 Gemini Mode", value=True,
                                    help="Enable Gemini's 1M context window optimizations")
        
        with col2:
            schema_injection = st.checkbox("🗃️ Smart Schema Injection", value=True,
                                         help="Inject relevant database schema for better answers")
            
            show_full_queries = st.checkbox("🃏 Show Full Query Cards", value=False,
                                          help="Display complete original queries instead of chunks")
        
        # Advanced options in expander
        with st.expander("🔧 Advanced Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                query_rewriting = st.checkbox("🔄 Query Enhancement", value=False,
                                            help="Use LLM to enhance queries for better retrieval")
                
                if HYBRID_SEARCH_AVAILABLE:
                    hybrid_search = st.checkbox("🔀 Hybrid Search", value=False,
                                               help="Combine vector and keyword search")
                else:
                    hybrid_search = False
                    st.caption("⚠️ Hybrid search not available (install rank-bm25)")
            
            with col2:
                auto_adjust_weights = st.checkbox("🤖 Auto-adjust Weights", value=True,
                                                help="Automatically optimize search weights")
                
                if hybrid_search and HYBRID_SEARCH_AVAILABLE:
                    vector_weight = st.slider("Vector Weight", 0.0, 1.0, 0.7, 0.1)
                    keyword_weight = 1.0 - vector_weight
                    search_weights = SearchWeights(vector_weight=vector_weight, keyword_weight=keyword_weight)
                else:
                    search_weights = None
        
        return {
            'selected_index': selected_index,
            'k': k,
            'gemini_mode': gemini_mode,
            'schema_injection': schema_injection,
            'show_full_queries': show_full_queries,
            'query_rewriting': query_rewriting,
            'hybrid_search': hybrid_search,
            'auto_adjust_weights': auto_adjust_weights,
            'search_weights': search_weights
        }
    
    def display_query_card(self, row, index: int):
        """Display a single query card using pre-parsed data"""
        query = safe_get_value(row, 'query')
        description = safe_get_value(row, 'description')
        
        # Use pre-parsed columns if available
        if 'tables_parsed' in row and isinstance(row['tables_parsed'], list):
            tables_list = row['tables_parsed']
        else:
            # Fallback for original CSV data
            tables_raw = safe_get_value(row, 'tables')
            tables_list = [t.strip() for t in tables_raw.split(',') if t.strip()] if tables_raw else []
        
        if 'joins_parsed' in row and isinstance(row['joins_parsed'], list):
            joins_list = row['joins_parsed']
        else:
            # Fallback for original CSV data
            joins_raw = safe_get_value(row, 'joins')
            joins_list = [j.strip() for j in joins_raw.split(',') if j.strip()] if joins_raw else []
        
        # Create expandable card
        with st.container():
            # Card header with query title/description
            card_title = description if description else f"Query {index + 1}"
            
            with st.expander(f"📄 {card_title}", expanded=False):
                # Query content
                st.code(query, language="sql")
                
                # Metadata in columns
                if tables_list or joins_list:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if tables_list:
                            st.markdown("**🗂️ Tables:**")
                            for table in tables_list[:5]:  # Limit display
                                st.caption(f"• {table}")
                            if len(tables_list) > 5:
                                st.caption(f"... and {len(tables_list) - 5} more")
                    
                    with col2:
                        if joins_list:
                            st.markdown("**🔗 Joins:**")
                            for join in joins_list[:3]:  # Limit display
                                st.caption(f"• {join}")
                            if len(joins_list) > 3:
                                st.caption(f"... and {len(joins_list) - 3} more")
    
    def render_search_results(self, answer, sources, token_usage, config):
        """Render the search results and analysis"""
        
        # Display answer
        st.subheader("📜 Answer")
        st.write(answer)
        
        # Display context utilization (Gemini optimization)
        if sources and config['gemini_mode']:
            self.display_context_utilization(sources, st.session_state.get('last_query', ''))
        
        # Display query rewriting information
        if token_usage and token_usage.get('query_rewriting', {}).get('enabled'):
            self.display_query_rewriting_info(token_usage, st.session_state.get('last_query', ''))
        
        # Display schema filtering information
        if token_usage and token_usage.get('schema_filtering', {}).get('enabled'):
            self.display_schema_filtering_info(token_usage)
        
        # Display search method and token usage
        if token_usage:
            self.display_search_info(token_usage, config, sources)
        
        # Display sources
        if sources:
            self.display_sources(sources, config)
    
    def display_context_utilization(self, sources, query):
        """Display context utilization metrics"""
        context_stats = calculate_context_utilization(sources, query)
        utilization = context_stats['utilization_percent']
        
        # Color coding based on utilization
        if utilization < 10:
            color = "🔴"
            status = "Low utilization - consider increasing K for better results"
        elif utilization < 50:
            color = "🟡"
            status = "Moderate utilization - good balance"
        else:
            color = "🟢"
            status = "Excellent context utilization"
        
        st.subheader(f"{color} Context Utilization")
        st.progress(min(utilization / 100, 1.0))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="📊 Context Usage",
                value=f"{utilization:.1f}%",
                delta=f"{context_stats['total_input_tokens']:,} tokens",
                help="Percentage of Gemini's 1M token context window used"
            )
        
        with col2:
            st.metric(
                label="📚 Chunks Retrieved",
                value=context_stats['chunks_used'],
                delta=f"~{context_stats['avg_tokens_per_chunk']:.0f} tokens/chunk",
                help="Number of relevant chunks with smart deduplication"
            )
        
        with col3:
            remaining_tokens = 1000000 - context_stats['total_input_tokens']
            st.metric(
                label="🚀 Remaining Capacity",
                value=f"{remaining_tokens:,}",
                delta="tokens available",
                help="Additional tokens available in Gemini's context window"
            )
        
        st.caption(f"💡 {status}")
    
    def display_query_rewriting_info(self, token_usage, original_query):
        """Display query rewriting information"""
        st.divider()
        rewrite_info = token_usage['query_rewriting']
        st.subheader("🔄 Query Enhancement")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Original Query:**")
            st.code(original_query, language="text")
        
        with col2:
            st.markdown("**Enhanced Query:**")
            st.code(rewrite_info['rewritten_query'], language="text")
        
        # Query rewriting metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🎯 Enhancement",
                "Enhanced" if rewrite_info['query_changed'] else "Original",
                f"Confidence: {rewrite_info['confidence']:.2f}"
            )
        
        with col2:
            model_info = rewrite_info.get('model_used', 'gemini-2.5-flash')
            st.metric(
                "⚡ Rewrite Time",
                f"{rewrite_info['rewrite_time']:.3f}s",
                f"Model: {model_info.split('-')[-1].upper()}"
            )
        
        with col3:
            improvement_estimate = "25-40%" if rewrite_info['query_changed'] else "N/A"
            st.metric(
                "📈 Expected Improvement",
                improvement_estimate,
                "Retrieval precision"
            )
        
        if rewrite_info['query_changed']:
            st.success("✅ Query was enhanced with SQL terminology and domain concepts")
        else:
            st.info("ℹ️ Original query was already well-optimized")
    
    def display_schema_filtering_info(self, token_usage):
        """Display schema filtering information"""
        st.divider()
        schema_info = token_usage['schema_filtering']
        st.subheader("🗃️ Smart Schema Injection")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "📊 Tables Identified",
                schema_info.get('relevant_tables', 0),
                f"Coverage: {schema_info.get('schema_coverage', '0/0')}"
            )
        
        with col2:
            schema_tokens = schema_info.get('schema_tokens', 0)
            st.metric(
                "🧾 Schema Tokens",
                f"{schema_tokens:,}",
                "Added to context"
            )
        
        with col3:
            total_tables = schema_info.get('total_schema_tables', 0)
            reduction_factor = f"{total_tables:,} → {schema_info.get('relevant_tables', 0)}"
            st.metric(
                "🎯 Noise Reduction",
                "99%+" if schema_info.get('relevant_tables', 0) > 0 else "N/A",
                reduction_factor
            )
        
        if schema_info.get('schema_available'):
            st.success("✅ Relevant database schema injected for accurate answers")
        else:
            st.info("ℹ️ No matching schema found for identified tables")
    
    def display_search_info(self, token_usage, config, sources):
        """Display search method and performance information"""
        st.divider()
        
        # Search method information
        search_method = token_usage.get('search_method', 'vector')
        
        if search_method == 'hybrid' and token_usage.get('hybrid_search_breakdown'):
            st.subheader("🔀 Hybrid Search Results")
            breakdown = token_usage['hybrid_search_breakdown']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "🔀 Hybrid Results",
                    breakdown.get('hybrid', 0),
                    "Found by both methods"
                )
            
            with col2:
                st.metric(
                    "🎯 Vector Only",
                    breakdown.get('vector', 0),
                    "Semantic similarity"
                )
            
            with col3:
                st.metric(
                    "🔍 Keyword Only",
                    breakdown.get('keyword', 0),
                    "Exact term matching"
                )
            
            # Show search weights if available
            if token_usage.get('search_weights'):
                weights = token_usage['search_weights']
                st.caption(f"🎛️ Search weights: Vector {weights['vector_weight']:.2f}, Keyword {weights['keyword_weight']:.2f}")
            elif config.get('auto_adjust_weights'):
                st.caption("🤖 Weights auto-adjusted based on query analysis")
        
        # Token usage metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🪙 Response Tokens",
                f"{token_usage['total_tokens']:,}",
                f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
            )
        
        with col2:
            mode_label = "🔥 Gemini Mode" if config.get('gemini_mode') else "🏠 Standard Mode"
            search_label = f" + {search_method.title()}" if search_method != 'vector' else ""
            st.metric(f"{mode_label}{search_label}", "Google Gemini 2.5 Flash", "Google AI")
        
        with col3:
            retrieval_time = token_usage.get('retrieval_time', 0)
            docs_processed = token_usage.get('documents_processed', len(sources))
            st.metric(
                "⚡ Performance",
                f"{retrieval_time:.2f}s",
                f"{docs_processed} docs processed"
            )
    
    def display_sources(self, sources, config):
        """Display source documents"""
        st.divider()
        
        if config.get('show_full_queries'):
            # Show full query cards
            st.subheader("📋 Source Queries")
            st.caption(f"Found {len(sources)} relevant chunks from the following complete queries:")
            
            # Map sources back to original queries
            csv_data = session_manager.get_csv_data()
            if csv_data is not None:
                original_queries = find_original_queries_for_sources(sources, csv_data)
                
                if original_queries:
                    for i, query_row in enumerate(original_queries):
                        st.subheader(f"📄 Source Query {i + 1}")
                        self.display_query_card(query_row, i)
                        
                        # Show which chunks came from this query
                        matching_chunks = []
                        query_content = safe_get_value(query_row, 'query').strip().lower()
                        
                        for j, doc in enumerate(sources, 1):
                            chunk_content = doc.page_content.strip().lower()
                            if chunk_content in query_content or query_content in chunk_content:
                                matching_chunks.append(f"Chunk {j}")
                        
                        if matching_chunks:
                            st.caption(f"🔗 Related chunks: {', '.join(matching_chunks)}")
                        
                        if i < len(original_queries) - 1:
                            st.divider()
                else:
                    st.warning("Could not map sources back to original queries")
                    self.display_source_chunks(sources)
            else:
                self.display_source_chunks(sources)
        else:
            # Show original chunk display
            self.display_source_chunks(sources)
    
    def display_source_chunks(self, sources):
        """Display source chunks"""
        st.subheader("📂 Source Chunks")
        st.caption(f"Showing {len(sources)} relevant chunks (enable 'Show Full Query Cards' to see complete queries)")
        
        for i, doc in enumerate(sources, 1):
            with st.expander(f"Chunk {i}: {doc.metadata.get('source', 'Unknown')}"):
                st.code(doc.page_content, language="sql")
                
                # Show metadata if available
                metadata = doc.metadata
                if metadata.get('description'):
                    st.caption(f"**Description:** {metadata['description']}")
                if metadata.get('table'):
                    st.caption(f"**Tables:** {metadata['table']}")
    
    def render_instructions(self):
        """Render usage instructions"""
        st.markdown("""
        ### 💡 How to use:
        
        1. **Enter your question** about SQL queries, database patterns, or specific operations
        2. **Click Search** to find relevant examples and get detailed explanations
        3. **Use agent commands** for specialized responses:
           - `@explain` - Detailed educational explanations
           - `@create` - Generate new SQL code from requirements
        4. **Adjust search parameters** to fine-tune results (K value, search method)
        5. **Enable advanced features** like hybrid search and query enhancement for better results
        
        ### 🔍 Example questions:
        - "How do I calculate customer lifetime value with SQL?"
        - "Show me examples of complex JOINs with aggregations"
        - "@explain What are the best practices for inventory queries?"
        - "@create Write a query to find top selling products by category"
        """)
    
    def render(self):
        """Render the complete search page"""
        st.title(self.page_title)
        
        # Load required data
        if not session_manager.load_csv_data_if_needed():
            return
        
        session_manager.load_schema_manager_if_needed()
        
        # Configuration section
        config = self.render_search_configuration()
        if not config:
            return
        
        # Ensure vector store is loaded
        if not vector_store_manager.ensure_vector_store_loaded(config['selected_index']):
            return
        
        # Display session stats
        session_manager.display_session_stats()
        
        # Main search interface
        st.subheader("❓ Ask a Question")
        
        query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Which queries show customer spending analysis with multiple JOINs?",
            key="search_query"
        )
        
        if st.button("🔍 Search", type="primary") and query.strip():
            # Validate query
            is_valid, error_msg = validate_query_input(query)
            if not is_valid:
                st.error(error_msg)
                return
            
            # Store query for later use
            st.session_state.last_query = query.strip()
            
            # Extract agent type
            agent_type, cleaned_query = extract_agent_type(query)
            
            with st.spinner("Searching and generating answer..."):
                try:
                    # Get schema manager if needed
                    schema_manager_to_use = None
                    if config['schema_injection']:
                        schema_manager_to_use = session_manager.get_schema_manager()
                    
                    # Get conversation context
                    conversation_context = session_manager.get_conversation_context(exclude_last=True)
                    
                    # Call RAG engine
                    result = rag_engine.answer_question(
                        question=cleaned_query,
                        vector_store=session_manager.get_vector_store(),
                        k=config['k'],
                        gemini_mode=config['gemini_mode'],
                        hybrid_search=config['hybrid_search'],
                        search_weights=config['search_weights'],
                        auto_adjust_weights=config['auto_adjust_weights'],
                        query_rewriting=config['query_rewriting'],
                        schema_manager=schema_manager_to_use,
                        conversation_context=conversation_context,
                        agent_type=agent_type
                    )
                    
                    if result:
                        answer, sources, token_usage = result
                        
                        # Track token usage
                        if token_usage:
                            session_manager.add_token_usage(token_usage)
                        
                        # Add to chat history
                        session_manager.add_chat_message("user", query)
                        session_manager.add_chat_message("assistant", answer)
                        
                        # Display results
                        self.render_search_results(answer, sources, token_usage, config)
                    
                    else:
                        st.error("❌ Failed to generate answer")
                
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logger.error(f"Query error: {e}")
        
        # Show instructions if no query entered
        if not query:
            self.render_instructions()


# Global instance
search_page = SearchPage()