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
      case 'Easy': return 'easy';
      case 'Medium': return 'medium';
      case 'Hard': return 'hard';
      default: return 'medium';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Basic': return '🔍';
      case 'Analytics': return '📊';
      case 'Reports': return '📈';
      case 'Admin': return '⚙️';
      default: return '🔍';
    }
  };

  return (
    <div className="query-card">
      <div className="query-header">
        <div className="query-title">
          <h3>{query.title}</h3>
          <div className="query-badges">
            <span className="category-badge">
              {getCategoryIcon(query.category)} {query.category}
            </span>
            <span className={`complexity-badge ${getComplexityColor(query.complexity)}`}>
              {query.complexity}
            </span>
          </div>
        </div>
        <div className="query-actions">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="view-button"
          >
            {showDetails ? 'Hide' : 'View'}
          </button>
          <button
            onClick={handleCopy}
            className={`copy-button ${copied ? 'copied' : ''}`}
          >
            {copied ? '✓ Copied!' : '📋 Copy'}
          </button>
          {onExecute && (
            <button
              onClick={() => onExecute(query.sql)}
              className="execute-button"
            >
              ▶ Execute
            </button>
          )}
        </div>
      </div>

      <p className="query-description">{query.description}</p>

      {query.tags && query.tags.length > 0 && (
        <div className="query-tags">
          {query.tags.map((tag, index) => (
            <span key={index} className="tag">
              {tag}
            </span>
          ))}
        </div>
      )}

      {showDetails && (
        <div className="query-details">
          <div className="sql-section">
            <h4>SQL Query:</h4>
            <pre className="sql-code">
              <code>{query.sql}</code>
            </pre>
          </div>
          
          {query.usage_count !== undefined && (
            <div className="usage-info">
              <span>Used {query.usage_count} times</span>
              {query.last_used && (
                <span>Last used: {new Date(query.last_used).toLocaleDateString()}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QueryCard;