import React, { useState } from 'react';
import { DatabaseSchema, TableSchema, Column } from '../../types/api';
import './SchemasTree.css';

interface SchemasTreeProps {
  schema: DatabaseSchema | null;
  isLoading?: boolean;
  error?: string | null;
}

const SchemasTree: React.FC<SchemasTreeProps> = ({ 
  schema, 
  isLoading = false, 
  error = null 
}) => {
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [selectedTable, setSelectedTable] = useState<TableSchema | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName);
    } else {
      newExpanded.add(tableName);
    }
    setExpandedTables(newExpanded);
  };

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
      <div className="schemas-tree loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading database schema...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="schemas-tree error">
        <div className="error-message">
          <h3>❌ Error Loading Schema</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="schemas-tree empty">
        <div className="empty-message">
          <p>No schema data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="schemas-tree">
      <div className="tree-header">
        <h2>Database Schema</h2>
        <div className="schema-info">
          <span className="database-name">{schema.database_name}</span>
          <span className="table-count">{schema.total_tables} tables</span>
        </div>
      </div>

      <div className="tree-controls">
        <input
          type="text"
          placeholder="Search tables and columns..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="tree-content">
        {filteredTables.map((table) => (
          <TableNode
            key={table.name}
            table={table}
            isExpanded={expandedTables.has(table.name)}
            isSelected={selectedTable?.name === table.name}
            onToggle={() => toggleTable(table.name)}
            onSelect={() => setSelectedTable(table)}
          />
        ))}
        
        {filteredTables.length === 0 && (
          <div className="no-results">
            <p>No tables found matching "{searchTerm}"</p>
          </div>
        )}
      </div>

      <div className="tree-footer">
        <p>Click on columns to explore and build queries.</p>
      </div>
    </div>
  );
};

interface TableNodeProps {
  table: TableSchema;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
}

const TableNode: React.FC<TableNodeProps> = ({ 
  table, 
  isExpanded, 
  isSelected,
  onToggle, 
  onSelect 
}) => {
  const getPrimaryKeyColumns = () => {
    return table.columns.filter(col => 
      col.name.toLowerCase().includes('id')
    );
  };

  const primaryKeys = getPrimaryKeyColumns();

  return (
    <div className={`table-node ${isSelected ? 'selected' : ''}`}>
      <div 
        className="table-header"
        onClick={() => onSelect()}
      >
        <button
          className="expand-button"
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
        <span className="table-name">{table.name}</span>
        <span className="table-info">({table.row_count.toLocaleString()} rows)</span>
        {primaryKeys.length > 0 && (
          <span className="primary-key-indicator">
            🔑 {primaryKeys.length} PK{primaryKeys.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {table.description && (
        <div className="table-description">
          {table.description}
        </div>
      )}

      {isExpanded && (
        <div className="table-columns">
          {table.columns.map((column) => (
            <ColumnItem key={column.name} column={column} />
          ))}
        </div>
      )}
    </div>
  );
};

interface ColumnItemProps {
  column: Column;
}

const ColumnItem: React.FC<ColumnItemProps> = ({ column }) => {
  const isPrimaryKey = column.name.toLowerCase().includes('id');
  
  return (
    <div className={`column-item ${isPrimaryKey ? 'primary-key' : ''} ${!column.nullable ? 'required' : ''}`}>
      <span className="column-name">{column.name}</span>
      <span className="column-type">{column.type}</span>
      {!column.nullable && <span className="required-indicator">*</span>}
      {isPrimaryKey && <span className="pk-indicator">🔑</span>}
      
      {column.description && (
        <div className="column-description">
          {column.description}
        </div>
      )}
    </div>
  );
};

export default SchemasTree;