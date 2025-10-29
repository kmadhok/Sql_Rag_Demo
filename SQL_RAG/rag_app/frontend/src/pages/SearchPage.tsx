import React, { useState } from 'react';
import './SearchPage.css';

interface QuerySearchResponse {
  question: string;
  answer: string;
  sql_query?: string;
  retrieved_documents: any[];
  schema_injected?: string;
  validation_passed?: boolean;
  validation_errors: string[];
  execution_available: boolean;
  usage_stats: any;
  timestamp: string;
  session_id: string;
  processing_time: number;
}

interface ExecuteQueryResponse {
  success: boolean;
  data?: any[];
  columns?: string[];
  row_count: number;
  execution_time: number;
  bytes_processed?: number;
  bytes_billed?: number;
  job_id?: string;
  cache_hit: boolean;
  dry_run: boolean;
  error_message?: string;
  sql: string;
  timestamp: string;
}

const SearchPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [response, setResponse] = useState<QuerySearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRetrieved, setShowRetrieved] = useState(false);
  const [showSchema, setShowSchema] = useState(false);

  const handleSearch = async () => {
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    setIsSearching(true);
    setError(null);
    setResponse(null);

    try {
      const response = await fetch('/api/query-search/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question.trim(),
          k: 20,
          use_gemini: true,
          schema_injection: true,
          sql_validation: true
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: QuerySearchResponse = await response.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred during search');
    } finally {
      setIsSearching(false);
    }
  };

  const executeSQL = async (sql: string) => {
    try {
      const response = await fetch('/api/query-search/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          sql: sql,
          dry_run: false 
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: ExecuteQueryResponse = await response.json();
      
      if (result.success) {
        alert(`✅ Query executed successfully!\n\nRows returned: ${result.row_count}\nExecution time: ${result.execution_time.toFixed(3)}s\nBytes processed: ${result.bytes_processed ? (result.bytes_processed / 1024 / 1024).toFixed(2) + ' MB' : 'N/A'}\nCache hit: ${result.cache_hit ? 'Yes' : 'No'}`);
      } else {
        alert(`❌ Query execution failed:\n\n${result.error_message}`);
      }
    } catch (err: any) {
      alert(`Error executing SQL: ${err.message}`);
    }
  };

  const copySQL = async (sql: string) => {
    try {
      await navigator.clipboard.writeText(sql);
      alert('SQL copied to clipboard!');
    } catch (err) {
      alert('Failed to copy SQL');
    }
  };

  return (
    <div className="search-page">
      <div className="page-header">
        <h1>❓ Query Search</h1>
        <p>Ask a question and get SQL with vector search + AI generation</p>
      </div>

      <div className="search-container">
        <h3>Ask a Question</h3>
        <textarea
          className="question-input"
          placeholder="e.g., Write SQL to join users and orders and compute monthly spend"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          disabled={isSearching}
        />
        
        <button
          className="generate-button"
          onClick={handleSearch}
          disabled={isSearching || !question.trim()}
        >
          {isSearching ? 'Generating SQL with Gemini...' : 'Generate SQL'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && (
        <div className="response-container">
          {/* Pipeline Metrics */}
          {response.usage_stats && (
            <div className="metrics">
              <h4>📊 Pipeline Metrics</h4>
              <div className="metrics-grid">
                <span>Time: {response.processing_time.toFixed(2)}s</span>
                <span>Documents: {response.usage_stats.documents_retrieved || 0}</span>
                <span>Tables: {response.usage_stats.tables_retrieved || 0}</span>
                <span>Validation: {response.validation_passed ? '✅ Passed' : '❌ Failed'}</span>
              </div>
            </div>
          )}

          {/* Retrieved Documents */}
          {response.retrieved_documents.length > 0 && (
            <div className="retrieved-docs">
              <div className="section-header">
                <h4>📚 Retrieved Similar Queries ({response.retrieved_documents.length})</h4>
                <button onClick={() => setShowRetrieved(!showRetrieved)}>
                  {showRetrieved ? 'Hide' : 'Show'}
                </button>
              </div>
              {showRetrieved && (
                <div className="documents-list">
                  {response.retrieved_documents.map((doc, index) => (
                    <div key={index} className="document">
                      <div className="doc-score">Score: {doc.metadata?.score || 'N/A'}</div>
                      <code>{doc.content}</code>
                      {doc.metadata?.description && (
                        <div className="doc-desc">{doc.metadata.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Schema */}
          {response.schema_injected && (
            <div className="schema">
              <div className="section-header">
                <h4>🏗️ Injected Schema</h4>
                <button onClick={() => setShowSchema(!showSchema)}>
                  {showSchema ? 'Hide' : 'Show'}
                </button>
              </div>
              {showSchema && (
                <pre>{response.schema_injected}</pre>
              )}
            </div>
          )}

          {/* AI Response */}
          <div className="ai-response">
            <h4>🤖 AI Response</h4>
            <div className="answer">{response.answer}</div>
          </div>

          {/* Generated SQL */}
          {response.sql_query && (
            <div className="sql-result">
              <div className="sql-header">
                <h4>🔧 Generated SQL {response.validation_passed ? '✅' : '❌'}</h4>
                <div className="sql-actions">
                  <button onClick={() => copySQL(response.sql_query)}>
                    📋 Copy
                  </button>
                  {response.validation_passed && (
                    <button onClick={() => executeSQL(response.sql_query)}>
                      ▶ Execute
                    </button>
                  )}
                </div>
              </div>
              <pre>{response.sql_query}</pre>
              
              {response.validation_errors.length > 0 && (
                <div className="validation-errors">
                  <h5>⚠️ Validation Errors:</h5>
                  <ul>
                    {response.validation_errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchPage;
