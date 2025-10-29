import React, { useState } from 'react';
import { ExecuteSQLResponse } from '../../types/api';
import './DataTable.css';

interface DataTableProps {
  data: ExecuteSQLResponse | null;
  isLoading?: boolean;
  error?: string | null;
}

const DataTable: React.FC<DataTableProps> = ({ 
  data, 
  isLoading = false, 
  error = null 
}) => {
  const [sortConfig, setSortConfig] = useState<{
    key: string | null;
    direction: 'asc' | 'desc';
  }>({ key: null, direction: 'asc' });

  const handleSort = (column: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig.key === column && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key: column, direction });
  };

  const sortedData = React.useMemo(() => {
    if (!data?.data || !sortConfig.key) return data?.data || [];

    return [...data.data].sort((a, b) => {
      const aValue = a[columns.indexOf(sortConfig.key!)];
      const bValue = b[columns.indexOf(sortConfig.key!)];
      
      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [data?.data, sortConfig]);

  if (isLoading) {
    return (
      <div className="data-table loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Executing query...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-table error">
        <div className="error-message">
          <h3>❌ Query Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.success) {
    return (
      <div className="data-table empty">
        <div className="empty-message">
          <p>Execute a query to see results here</p>
        </div>
      </div>
    );
  }

  if (!data.data || data.data.length === 0) {
    return (
      <div className="data-table empty">
        <div className="empty-message">
          <p>Query executed successfully, but no results returned</p>
        </div>
      </div>
    );
  }

  const columns = data.columns || [];
  const rows = sortedData;

  return (
    <div className="data-table">
      <div className="table-info">
        <span className="row-count">
          {rows.length} row{rows.length !== 1 ? 's' : ''} returned
        </span>
        {data.executionTime && (
          <span className="execution-time">
            in {data.executionTime.toFixed(3)}s
          </span>
        )}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th 
                  key={index}
                  onClick={() => handleSort(column)}
                  className={sortConfig.key === column ? sortConfig.direction : ''}
                >
                  {column}
                  {sortConfig.key === column && (
                    <span className="sort-indicator">
                      {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((_, colIndex) => (
                  <td key={colIndex}>
                    {typeof row[colIndex] === 'object' 
                      ? JSON.stringify(row[colIndex]) 
                      : String(row[colIndex] ?? '')
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > 50 && (
        <div className="table-footer">
          <p className="truncated-notice">
            Showing first 50 rows of {rows.length} total rows
          </p>
        </div>
      )}
    </div>
  );
};

export default DataTable;