import React, { useState } from 'react';
import { DatabaseSchema, TableSchema, Column } from '../../types/api';
import './SchemaViewer.css';

interface SchemaViewerProps {
  schema: DatabaseSchema | null;
  isLoading?: boolean;
  error?: string | null;
}

const SchemaViewer: React.FC<SchemaViewerProps> = ({ 
  schema, 
  isLoading = false, 
  error = null 
}) => {
  const [selectedTable, setSelectedTable] = useState<TableSchema | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTables = React.useMemo(() => {
    if (!schema) return [];
    
    if (!searchTerm) return schema.tables;
    
    const lowerSearch = searchTerm.toLowerCase();
    return schema.tables.filter(table => 
      table.name.toLowerCase().includes(lowerSearch) ||
      table.description?.toLowerCase().includes(lowerSearch) ||
      table.columns.some(col => 
        col.name.toLowerCase().includes(lowerSearch) ||
        col.description?.toLowerCase().includes(lowerSearch)
      )
    );
  }, [schema, searchTerm]);

  if (isLoading) {
    return (
      <div className="schema-viewer loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading database schema...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="schema-viewer error">
        <div className="error-message">
          <h3>❌ Error Loading Schema</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="schema-viewer empty">
        <div className="empty-message">
          <p>No schema data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="schema-viewer">
      <div className="schema-header">
        <h2>Database Schema</h2>
        <div className="schema-stats">
          <span>{schema.database_name}</span>
          <span>{schema.total_tables} tables</span>
        </div>
      </div>

      <div className="schema-controls">
        <input
          type="text"
          placeholder="Search tables, columns, or descriptions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        {selectedTable && (
          <button
            onClick={() => setSelectedTable(null)}
            className="back-button"
          >
            ← Back to All Tables
          </button>
        )}
      </div>

      {selectedTable ? (
        <TableDetailView table={selectedTable} onBack={() => setSelectedTable(null)} />
      ) : (
        <div className="tables-grid">
          {filteredTables.map((table) => (
            <TableCard 
              key={table.name} 
              table={table} 
              onClick={() => setSelectedTable(table)}
            />
          ))}
        </div>
      )}

      {filteredTables.length === 0 && (
        <div className="no-results">
          <p>No tables found matching "{searchTerm}"</p>
        </div>
      )}
    </div>
  );
};

interface TableCardProps {
  table: TableSchema;
  onClick: () => void;
}

const TableCard: React.FC<TableCardProps> = ({ table, onClick }) => {
  const primaryKeyColumns = table.columns.filter(col => 
    col.name.toLowerCase().includes('id')
  );

  return (
    <div className="table-card" onClick={onClick}>
      <div className="table-header">
        <h3>{table.name}</h3>
        <span className="row-count">{table.row_count.toLocaleString()} rows</span>
      </div>
      
      {table.description && (
        <p className="table-description">{table.description}</p>
      )}
      
      <div className="table-preview">
        <div className="column-count">
          {table.columns.length} columns
        </div>
        
        {primaryKeyColumns.length > 0 && (
          <div className="primary-keys">
            <strong>PK:</strong> {primaryKeyColumns.map(col => col.name).join(', ')}
          </div>
        )}
        
        <div className="sample-columns">
          {table.columns.slice(0, 3).map(col => (
            <span 
              key={col.name} 
              className={`column-type ${col.nullable ? 'nullable' : 'required'}`}
            >
              {col.name}: {col.type}
            </span>
          ))}
          {table.columns.length > 3 && (
            <span className="more-columns">+{table.columns.length - 3} more</span>
          )}
        </div>
      </div>
    </div>
  );
};

interface TableDetailViewProps {
  table: TableSchema;
  onBack: () => void;
}

const TableDetailView: React.FC<TableDetailViewProps> = ({ table, onBack }) => {
  const [showExtendedInfo, setShowExtendedInfo] = useState(false);

  return (
    <div className="table-detail">
      <div className="table-detail-header">
        <div>
          <h2>{table.name}</h2>
          <p className="table-stats">
            {table.row_count.toLocaleString()} rows • {table.columns.length} columns
          </p>
          {table.description && (
            <p className="table-description">{table.description}</p>
          )}
        </div>
        <button onClick={onBack} className="back-button">
          Back
        </button>
      </div>

      <div className="columns-list">
        <div className="columns-header">
          <h3>Columns</h3>
          <button
            onClick={() => setShowExtendedInfo(!showExtendedInfo)}
            className="toggle-info"
          >
            {showExtendedInfo ? 'Hide' : 'Show'} Details
          </button>
        </div>

        <table className="columns-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Nullable</th>
              {showExtendedInfo && <th>Description</th>}
            </tr>
          </thead>
          <tbody>
            {table.columns.map((column) => (
              <tr key={column.name}>
                <td>{column.name}</td>
                <td className="column-type">{column.type}</td>
                <td>
                  <span className={`nullable-badge ${column.nullable ? 'nullable' : 'required'}`}>
                    {column.nullable ? 'YES' : 'NO'}
                  </span>
                </td>
                {showExtendedInfo && (
                  <td className="column-description">
                    {column.description || '-'}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SchemaViewer;