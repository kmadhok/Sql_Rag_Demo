import React, { useState } from 'react';
import { QueryItem } from '../../types/api';
import './QueryCard.css';

interface QueryCardProps {
  query: QueryItem;
  onExecute?: (sql: string) => void;
  onView?: (sql: string) => void;
}

const QueryCard: React.FC<QueryCardProps> = ({ 
  query, 
  onExecute, 
  onView 
}) => {
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showSQL, setShowSQL] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(query.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'Easy': return '#10b981';
      case 'Medium': return '#f59e0b';
      case 'Hard': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Basic': return '📊';
      case 'Analytics': return '📈';
      case 'Revenue': return '💰';
      default: return '🔍';
    }
  };

  return (
    <div className="query-card">
      <div className="card-header">
        <div className="card-title">
          <span className="category-icon">{getCategoryIcon(query.category)}</span>
          <h3>{query.title}</h3>
        </div>
        <div className="difficulty-badge" style={{ color: getComplexityColor(query.complexity) }}>
          {query.complexity}
        </div>
      </div>

      <div className="card-description">
        <p>{query.description}</p>
      </div>

      <div className="card-meta">
        <div className="meta-tags">
          <span className="tag category-tag">{query.category}</span>
          {query.tables && (
            <span className="tag tables-tag">
              📋 {query.tables.length > 1 ? `${query.tables.length} tables` : query.tables[0]}
            </span>
          )}
          {query.has_aggregation && (
            <span className="tag feature-tag">Σ Aggregation</span>
          )}
          {query.has_window_function && (
            <span className="tag feature-tag">🪟 Window</span>
          )}
          {query.has_subquery && (
            <span className="tag feature-tag">🔄 Subquery</span>
          )}
        </div>
        {query.usage_count && (
          <div className="usage-count">
            <span>👁 {query.usage_count} views</span>
          </div>
        )}
      </div>

      {showDetails && (
        <div className="card-details">
          <div className="detail-row">
            <span className="detail-label">Performance:</span>
            <span className="detail-value">
              ⚡ {query.execution_time?.toFixed(3)}s | 
              📊 Difficulty: {query.difficulty_score?.toFixed(1) || 'N/A'} | 
              ⭐ {query.performance_rating?.toFixed(1) || 'N/A'}/10
            </span>
          </div>
          {query.author && (
            <div className="detail-row">
              <span className="detail-label">Author:</span>
              <span className="detail-value">{query.author}</span>
            </div>
          )}
          {query.notes && (
            <div className="detail-row">
              <span className="detail-label">Notes:</span>
              <span className="detail-value">{query.notes}</span>
            </div>
          )}
          {query.created_at && (
            <div className="detail-row">
              <span className="detail-label">Created:</span>
              <span className="detail-value">{new Date(query.created_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      )}

      {showSQL && (
        <div className="sql-display">
          <div className="sql-header">
            <h4>SQL Query</h4>
            <button
              className="copy-sql-btn"
              onClick={handleCopy}
              title="Copy SQL"
            >
              {copied ? '✓ Copied!' : '📋 Copy'}
            </button>
          </div>
          <pre className="sql-code">{query.sql}</pre>
        </div>
      )}

      <div className="card-actions">
        <button
          className="action-btn secondary"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
        <button
          className="action-btn secondary"
          onClick={() => setShowSQL(!showSQL)}
        >
          {showSQL ? 'Hide SQL' : 'View SQL'}
        </button>
        <button
          className="action-btn primary"
          onClick={() => handleCopy()}
        >
          {copied ? '✓ Copied!' : '📋 Copy Query'}
        </button>
        {onExecute && (
          <button
            className="action-btn execute"
            onClick={() => onExecute(query.sql)}
          >
            ▶ Execute
          </button>
        )}
      </div>
    </div>
  );
};

export default QueryCard;