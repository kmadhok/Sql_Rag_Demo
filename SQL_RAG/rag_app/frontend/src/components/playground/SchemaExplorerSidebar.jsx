import { useState, useEffect, useMemo } from 'react';
import Card from '../Card.jsx';
import { getTables, getTableColumns } from '../../services/ragClient.js';

/**
 * Schema Explorer Sidebar
 * Displays available tables and columns with click-to-insert helpers.
 */
export default function SchemaExplorerSidebar({ onInsert, isVisible, onToggle }) {
  const [tables, setTables] = useState([]);
  const [expandedTables, setExpandedTables] = useState({});
  const [tableMetadata, setTableMetadata] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchTables = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getTables();
        if (!isMounted) return;

        setTables(response.tables || []);
      } catch (err) {
        console.error('Failed to fetch tables:', err);
        if (isMounted) {
          setError('Failed to load schema');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchTables();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleToggleTable = async (tableName) => {
    if (expandedTables[tableName]) {
      setExpandedTables((prev) => {
        const updated = { ...prev };
        delete updated[tableName];
        return updated;
      });
      return;
    }

    try {
      const response = await getTableColumns(tableName);
      const columns = response.columns || [];
      const fqn = response.fully_qualified_name || tableName;

      setExpandedTables((prev) => ({
        ...prev,
        [tableName]: columns,
      }));
      setTableMetadata((prev) => ({
        ...prev,
        [tableName]: {
          fqn,
          columnCount: response.column_count || columns.length,
        },
      }));
    } catch (err) {
      console.error(`Failed to fetch columns for ${tableName}:`, err);
    }
  };

  const filteredTables = useMemo(() => {
    if (!searchTerm) {
      return tables;
    }
    const search = searchTerm.toLowerCase();
    return tables.filter((table) => table.toLowerCase().includes(search));
  }, [searchTerm, tables]);

  const handleInsertTable = (tableName) => {
    const fqn = tableMetadata[tableName]?.fqn;
    const insertValue = fqn ? (fqn.startsWith('`') ? fqn : `\`${fqn}\``) : `\`bigquery-public-data.thelook_ecommerce.${tableName}\``;
    if (onInsert) {
      onInsert(insertValue);
    }
  };

  const handleInsertColumn = (tableName, columnName) => {
    if (!columnName || !onInsert) {
      return;
    }
    onInsert(`${tableName}.${columnName}`);
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="schema-explorer flex-shrink-0" style={{ width: '300px', borderRight: '1px solid #374151' }}>
      <Card className="h-full flex flex-col bg-gray-900 border border-gray-800 rounded-lg">
        <div className="flex justify-between items-center mb-3 pb-3 border-b border-gray-800">
          <h3 className="text-lg font-semibold text-gray-200">Schema Explorer</h3>
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-gray-200 text-xl"
            title="Close schema explorer"
          >
            ×
          </button>
        </div>

        <div className="mb-3">
          <input
            type="text"
            placeholder="🔍 Search tables..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-200 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex-1 overflow-auto pr-1">
          {isLoading && (
            <div className="text-gray-400 text-sm text-center py-4">
              Loading schema...
            </div>
          )}

          {error && (
            <div className="text-red-400 text-sm text-center py-4">
              {error}
            </div>
          )}

          {!isLoading && !error && filteredTables.length === 0 && (
            <div className="text-gray-500 text-sm text-center py-4">
              No tables found
            </div>
          )}

          {!isLoading && !error && filteredTables.map((table) => {
            const tableColumns = expandedTables[table];
            const columnCount = tableMetadata[table]?.columnCount ?? (tableColumns ? tableColumns.length : 0);

            return (
              <div key={table} className="mb-2">
                <div
                  className="flex items-center gap-2 px-3 py-2 hover:bg-gray-800 rounded cursor-pointer transition-colors"
                  onClick={() => handleToggleTable(table)}
                >
                  <span className="text-gray-400 w-4 inline-flex justify-center">
                    {tableColumns ? '▼' : '▶'}
                  </span>
                  <span
                    className="text-blue-400 font-medium flex-1"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleInsertTable(table);
                    }}
                    title="Click to insert table name"
                  >
                    {table}
                  </span>
                  {tableColumns && (
                    <span className="text-xs text-gray-500">
                      ({columnCount} cols)
                    </span>
                  )}
                </div>

                {tableColumns && (
                  <div className="ml-6 mt-1 space-y-1">
                    {tableColumns.map((column, index) => {
                      const columnName = column.name || column.column || `column_${index}`;
                      const columnType = column.type || column.datatype || '';
                      const tooltip = column.description
                        ? `${columnType || 'unknown'} - ${column.description}`
                        : columnType || undefined;

                      return (
                        <button
                          key={`${table}-${columnName}-${index}`}
                          type="button"
                          className="w-full flex items-center gap-2 px-3 py-1 text-left hover:bg-gray-800 rounded cursor-pointer text-sm transition-colors"
                          onClick={() => handleInsertColumn(table, columnName)}
                          title={tooltip}
                        >
                          <span className="text-gray-500">├─</span>
                          <span className="text-gray-300 flex-1">{columnName}</span>
                          {columnType && (
                            <span className="text-xs text-gray-500">({columnType})</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-3 pt-3 border-t border-gray-800 text-xs text-gray-500">
          {filteredTables.length} table{filteredTables.length !== 1 ? 's' : ''} • Click to insert
        </div>
      </Card>
    </div>
  );
}
