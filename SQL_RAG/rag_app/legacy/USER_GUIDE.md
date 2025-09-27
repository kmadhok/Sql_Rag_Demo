# SQL RAG System - User Guide

## 📖 Overview

The SQL RAG (Retrieval-Augmented Generation) system allows you to ask natural language questions about your SQL queries and get intelligent answers with source citations. The system uses local AI models for privacy and processes your SQL metadata to provide rich, contextual responses.

---

## 🎯 Key Features

### ✨ **Natural Language Query Search**
- Ask questions in plain English about your SQL codebase
- Get AI-generated answers with source citations
- Search across query content, descriptions, table names, and joins

### 🗃️ **Smart Vector Database**
- Composite embeddings from multiple fields (query + description + tables + joins)
- Incremental updates for efficient processing
- Local FAISS vector storage for fast search

### 📊 **Rich Query Catalog**
- Browse all your SQL queries with descriptions
- Interactive join relationship graphs
- Full-text search across all metadata
- Table and transformation analysis

### 🔒 **Privacy & Performance** 
- All processing happens locally (no API calls)
- Free to use (no API costs)
- Fast incremental updates
- Supports both CSV and BigQuery data sources

---

## 🚀 Getting Started

### First Time Setup

1. **Prepare Your Data**: Create a CSV file with your SQL queries
2. **Run Setup**: Follow the `SETUP_GUIDE.md` for installation
3. **Launch App**: Start with `streamlit run app.py`
4. **Wait for Processing**: Initial embedding creation (1-2 minutes for 1000+ queries)
5. **Start Querying**: Use the web interface to ask questions

### Understanding the Interface

The application has two main tabs:

#### 🔎 **Query Search** - Natural Language Interface
- Primary interaction method for asking questions
- AI-powered responses with source citations
- Token usage tracking
- Expandable source code view

#### 📚 **Browse Queries** - Catalog Explorer
- View all queries with descriptions and metadata
- Interactive join relationship graphs  
- Full-text search across all fields
- Raw query examination

---

## 💬 Query Search Tab

### How to Ask Questions

The system understands various types of questions about your SQL codebase:

#### **Table-Focused Queries**
```
"Show me queries that use the customers table"
"Which queries join customers with orders?"  
"Find queries that access the inventory table"
```

#### **Functionality-Focused Queries**
```
"Which queries calculate totals or sums?"
"Show me queries with date filtering"
"Find queries that use window functions"
"Which queries perform aggregations?"
```

#### **Pattern-Focused Queries**  
```
"Show me complex joins with multiple tables"
"Which queries use CTEs or subqueries?"
"Find queries with WHERE clauses on dates"
"Show me queries that group by customer"
```

#### **Business Logic Queries**
```
"How do we calculate customer lifetime value?"
"Which queries generate sales reports?"
"Show me inventory management queries"
"Find queries for financial reporting"
```

### Understanding Results

#### **AI Answer Section**
- Contextual explanation of relevant queries
- Summary of functionality and patterns
- Recommendations based on your question

#### **Token Usage Metrics**
- **Tokens Used**: Input and output token counts
- **Model Info**: Shows "Ollama Phi3" with "Free" cost
- **Session Tracking**: Cumulative usage statistics

#### **Sources Section** 
- **Tabbed Interface**: Organized by source files/queries
- **Code Snippets**: Formatted SQL with syntax highlighting
- **Metadata Display**: Shows query descriptions, tables, and joins
- **Relevance Ranking**: Most relevant results shown first

### Best Practices for Queries

#### ✅ **Effective Query Patterns**
- **Be specific**: "Customer queries with joins" vs "customer stuff"
- **Use domain terms**: "revenue", "orders", "inventory" 
- **Ask about patterns**: "complex joins", "aggregations", "filtering"
- **Focus on business logic**: "reporting", "analysis", "calculations"

#### ❌ **Less Effective Patterns**
- Too vague: "show me queries"
- Too technical: "SELECT statements with GROUP BY"
- Single words: "customers" (try "customer queries" instead)

---

## 📚 Browse Queries Tab

### Query Catalog Overview

This tab provides a comprehensive view of all your SQL queries with rich metadata:

#### **Join Relationship Analysis**

The system automatically detects and visualizes table relationships:

- **Join Map Table**: Shows detected joins with left/right tables and conditions
- **Interactive Graphs**: Click "Show join graph" for visual relationship maps
- **Filter Capabilities**: Filter joins by specific tables
- **Relationship Insights**: Understand your data model structure

#### **Full-Text Search**

Use the search box to find queries containing specific terms:

```
# Search examples:
"customer_id"     # Find queries using this column
"SUM("            # Find aggregation queries  
"LEFT JOIN"       # Find specific join types
"WHERE date"      # Find date filtering queries
```

#### **Query Details**

Each query shows:
- **Description**: Human-readable explanation
- **Tables**: All tables involved  
- **Joins**: Join conditions and relationships
- **Raw SQL**: Formatted and syntax-highlighted code

### Advanced Features

#### **Table Filtering**
- Use the table filter dropdown to focus on specific tables
- Multiple table selection supported
- Filters apply to both join map and query list

#### **Graph Visualization**
- **Static Graphs**: Graphviz-based relationship diagrams
- **Interactive Graphs**: Pyvis-based network visualizations (if installed)
- **Node/Edge Information**: Hover for additional details

---

## ⚙️ Settings & Configuration

### Sidebar Settings

#### **Query Parameters**
- **Top-K chunks**: Number of relevant code snippets to retrieve (1-10)
- **Default: 4** - Good balance of context vs. response speed
- **Higher values**: More context, slower responses
- **Lower values**: Faster responses, less context

#### **Vector Database Controls**
- **Rebuild Vector Store**: Force complete rebuild of embeddings
- **Use when**: Data has changed significantly or troubleshooting
- **Process**: Clears existing store and rebuilds from scratch

#### **Token Tracking**
- **Session Statistics**: View cumulative token usage
- **Reset Counter**: Clear session statistics  
- **Model Information**: Details about local Ollama models

#### **Embedding Status**
- **Current Status**: Shows processing progress and completion
- **Data Sources**: Lists processed data sources with timestamps
- **Vector Store**: Indicates if ready for queries

### Advanced Settings

#### **Environment Variables**
```bash
# For BigQuery integration (future)
export BIGQUERY_PROJECT="your-project-id"
export BIGQUERY_QUERY="SELECT * FROM dataset.table"
export PREFER_BIGQUERY="true"
```

#### **CSV Configuration**
Update `app.py` to point to your data:
```python
csv_path = '/path/to/your/queries.csv'
```

---

## 📊 Data Management

### CSV File Requirements

#### **Required Columns**
- **query**: SQL query text (required)

#### **Optional Columns** (for enhanced search)
- **description**: Human-readable explanation
- **table**: Comma-separated list of tables used
- **joins**: Join conditions and relationships

#### **Example Structure**
```csv
query,description,table,joins
"SELECT * FROM customers WHERE status = 'active'","Get active customers","customers",""
"SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id","Customer orders","customers,orders","c.id = o.customer_id"
```

### Incremental Updates

The system automatically detects data changes:

- **Hash-based Detection**: MD5 hash of CSV content
- **Smart Caching**: Reuses embeddings when data unchanged  
- **Automatic Updates**: Rebuilds only when necessary
- **Status Tracking**: Shows last update time and source info

### BigQuery Migration

When ready to move from CSV to BigQuery:

1. **Set Environment Variables**: Configure project and query
2. **Update Preferences**: Change `prefer_bigquery=True` in app.py
3. **Install Dependencies**: `pip install google-cloud-bigquery`
4. **Test Connection**: Verify BigQuery access and permissions

---

## 🔍 Search Tips & Tricks

### Getting Better Results

#### **Use Business Context**
```
✅ "How do we track customer purchase history?"
❌ "SELECT statements with customer_id"
```

#### **Ask About Relationships**
```  
✅ "Which queries connect customers to their orders?"
❌ "Show me JOIN statements"
```

#### **Focus on Use Cases**
```
✅ "Find queries for sales reporting and analytics"
❌ "Queries with GROUP BY"
```

#### **Be Specific About Tables**
```
✅ "Show me all queries that work with the inventory table"
❌ "Table queries"
```

### Understanding Search Results

#### **Result Ranking**
- Results ranked by semantic similarity to your question
- Most relevant queries appear first
- Multiple snippets from same query grouped together

#### **Source Attribution**
- Every answer includes source citations
- Click on expandable sections to see full query context
- Metadata shows table relationships and descriptions

#### **Context Windows**
- System retrieves surrounding context for each match
- Balances specificity with broader understanding
- Adjust Top-K setting to control context amount

---

## 🔧 Troubleshooting

### Common Issues

#### **"No results found"**
- **Try broader terms**: "customer" instead of "customer_acquisition"
- **Check spelling**: Ensure query terms match your data
- **Verify data**: Make sure CSV loaded correctly
- **Rebuild index**: Use "Rebuild Vector Store" button

#### **Slow query responses**
- **Reduce Top-K**: Lower the number of chunks retrieved
- **Check Ollama**: Ensure `ollama serve` is running
- **System resources**: Close other applications to free memory
- **Restart services**: Restart both Ollama and Streamlit

#### **Incomplete answers**
- **Increase Top-K**: More context may provide better answers
- **Rephrase question**: Try different wording or approach
- **Check source data**: Ensure descriptions are comprehensive
- **Verify embeddings**: Rebuild vector store if needed

### Performance Optimization

#### **For Large Datasets (5000+ queries)**
- Monitor initial embedding creation time
- Consider processing in smaller batches during off-hours
- Ensure adequate system RAM (8GB+ recommended)
- Use SSD storage for faster vector store access

#### **For Better Search Quality**
- Ensure good query descriptions in your CSV
- Include table and join information where relevant
- Use consistent naming conventions
- Regular data quality checks

---

## 📈 Advanced Usage

### Power User Features

#### **Custom Search Strategies**
- Combine multiple search approaches
- Use Browse tab for exploration, Query tab for specific questions
- Cross-reference join graphs with query results

#### **Data Analysis Workflows**
1. **Discovery**: Browse queries to understand codebase structure
2. **Exploration**: Use join graphs to map table relationships  
3. **Specific Search**: Ask targeted questions about functionality
4. **Validation**: Examine source code for implementation details

#### **Integration Patterns**
- Export search results for documentation
- Use insights for code review and optimization
- Identify patterns for standardization
- Find opportunities for query consolidation

### API-Style Usage

While primarily a web interface, you can integrate components:

```python
# Direct SmartEmbeddingProcessor usage
from smart_embedding_processor import SmartEmbeddingProcessor

processor = SmartEmbeddingProcessor(vector_path, status_path)
vector_store, stats = processor.process_dataframe(df)

# Direct search
results = vector_store.similarity_search("your query", k=5)
```

---

## 📚 Reference

### Supported Query Types
- **Semantic search**: Natural language understanding
- **Keyword matching**: Exact term searches
- **Pattern recognition**: SQL construct identification  
- **Relationship mapping**: Table join analysis
- **Business logic**: Functional understanding

### Performance Expectations
- **Initial setup**: 1-3 minutes for 1000 queries
- **Query response**: 2-5 seconds typical
- **Incremental updates**: <1 second for unchanged data
- **Search accuracy**: High relevance for well-described queries

### System Limits
- **CSV size**: Tested up to 10,000+ queries
- **Memory usage**: ~2-4GB for large datasets
- **Concurrent users**: Single-user application
- **Storage**: ~100-500MB for vector indices

---

## ✅ Best Practices Summary

### Data Preparation
- ✅ Include comprehensive descriptions
- ✅ Normalize table and join information  
- ✅ Use consistent naming conventions
- ✅ Regular data quality validation

### Query Crafting
- ✅ Use business terminology
- ✅ Be specific about intent
- ✅ Focus on functionality over syntax
- ✅ Iterate and refine questions

### System Maintenance
- ✅ Monitor performance regularly
- ✅ Keep Ollama models updated
- ✅ Backup vector stores before major changes
- ✅ Document custom configurations

### Troubleshooting
- ✅ Check logs for error messages
- ✅ Verify all services are running
- ✅ Test with simple queries first
- ✅ Rebuild indices when in doubt

---

## 🎉 You're Ready to Explore!

This guide covers everything you need to effectively use the SQL RAG system. Start with simple queries to get familiar with the interface, then gradually explore more complex use cases as you become comfortable with the system.

**Remember**: The system learns from your data, so the quality of results depends on the quality of your query descriptions and metadata. Invest time in good data preparation for the best experience!

Happy querying! 🚀