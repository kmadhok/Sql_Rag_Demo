import React, { useState } from 'react';
import { QueryItem } from '../../types/data';
import '../styles/QueryCard.css';

interface QueryCardProps {
  query: QueryItem;
  onCopy: (sql: string) => void;
}

const QueryCard: React.FC<QueryCardProps> = ({ query, onCopy }) => {
  const [expanded, setExpanded] = useState(false);
  
  const handleCopy = () => {
    onCopy(query.query);
    // Could add a toast notification here
  };
  
  const truncateQuery = (sql: string, maxLength: number = 80) => {
    if (sql.length <= maxLength) return sql;
    return sql.substring(0, maxLength) + '...';
  };
  
  return (
    <div className="query-card">
      <div className="query-header">
        <h4 className="query-title">
          Query #{query.id}
          {query.tags && query.tags.length > 0 && (
            <div className="query-tags">
              {query.tags.slice(0, 3).map((tag, index) => (
                <span key={index} className="tag">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </h4>
      </div>
      
      {query.description && (
        <p className="query-description">{query.description}</p>
      )}
      
      <div className="query-meta">
        {query.tables && query.tables.length > 0 && (
          <div className="query-tables">
            <span className="meta-label">Tables:</span>
            {query.tables.slice(0, 3).map((table, index) => (
              <span key={index} className="table-tag">
                {table}
              </span>
            ))}
            {query.tables.length > 3 && (
              <span className="table-more">
                +{query.tables.length - 3} more
              </span>
            )}
          </div>
        )}
        
        {query.joins && query.joins.length > 0 && (
          <div className="query-joins">
            <span className="meta-label">Joins:</span>
            <span className="join-count">
              {query.joins.length} {query.joins.length === 1 ? 'join' : 'joins'}
            </span>
          </div>
        )}
      </div>
      
      <div className="query-sql">
        <div className="sql-preview">
          <code>{truncateQuery(query.query)}</code>
        </div>
        
        {expanded && (
          <div className="sql-full">
            <pre>
              <code>{query.query}</code>
            </pre>
          </div>
        )}
      </div>
      
      <div className="query-actions">
        <button
          onClick={() => setExpanded(!expanded)}
          className="expand-button"
        >
          {expanded ? '▼ Show Less' : '▶ Show More'}
        </button>
        
        <button
          onClick={handleCopy}
          className="copy-button"
          title="Copy SQL to clipboard"
        >
          📋 Copy SQL
        </button>
      </div>
      
      {query.joins && query.joins.length > 0 && expanded && (
        <div className="query-joins-detail">
          <h5>Join Details:</h5>
          {query.joins.map((join, index) => (
            <div key={index} className="join-info">
              <span className="join-type">
                {join.type.toUpperCase()}
              </span>
              <span className="join-relationship">
                {join.leftTable}.{join.leftColumn} ↔ {join.rightTable}.{join.rightColumn}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default QueryCard;