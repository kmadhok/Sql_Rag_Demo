import { useState, useMemo } from 'react';
import Card from '../Card.jsx';

/**
 * Results Data Grid component
 * Displays query results in a table with sorting, filtering, and export
 */
export default function ResultsDataGrid({ result, sql }) {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  if (!result || !result.success) {
    // Always show error card if result failed, even without error_message
    const errorMsg = result?.error_message
      || result?.validation_message
      || 'Query execution failed. Check browser console for details.';

    return (
      <Card className="bg-red-900/20 border-red-700">
        <div className="text-red-300">
          <div className="font-semibold mb-2">Query Error</div>
          <pre className="text-sm whitespace-pre-wrap">{errorMsg}</pre>
          {result?.validation_message && result?.error_message && (
            <div className="mt-2 text-yellow-300">
              <div className="font-semibold">Validation Warning:</div>
              <pre className="text-sm">{result.validation_message}</pre>
            </div>
          )}
        </div>
      </Card>
    );
  }

  const { data = [], row_count, execution_time, bytes_processed, cache_hit } = result;

  // Handle empty results
  if (!data || data.length === 0) {
    return (
      <Card>
        <div className="text-gray-400 text-center py-8">
          Query executed successfully but returned no results
        </div>
      </Card>
    );
  }

  const columns = Object.keys(data[0] || {});

  /**
   * Handle column sorting
   */
  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  /**
   * Sorted data based on current sort settings
   */
  const sortedData = useMemo(() => {
    if (!sortColumn) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle null/undefined
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // Compare values
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      const comparison = aStr.localeCompare(bStr);

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [data, sortColumn, sortDirection]);

  /**
   * Export to CSV
   */
  const exportToCSV = () => {
    const csv = [
      columns.join(','),
      ...sortedData.map(row =>
        columns.map(col => {
          const val = row[col];
          if (val == null) return '';
          // Escape quotes and wrap in quotes if contains comma
          const str = String(val);
          return str.includes(',') || str.includes('"') || str.includes('\n')
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /**
   * Export to JSON
   */
  const exportToJSON = () => {
    const json = JSON.stringify(sortedData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /**
   * Format large numbers
   */
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Metadata */}
      <Card>
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div className="flex gap-6 text-sm">
            <div className="text-gray-400">
              <span className="font-semibold text-gray-300">{row_count || data.length}</span> rows
            </div>
            {execution_time && (
              <div className="text-gray-400">
                <span className="font-semibold text-gray-300">{execution_time.toFixed(2)}s</span> execution
              </div>
            )}
            {bytes_processed && (
              <div className="text-gray-400">
                <span className="font-semibold text-gray-300">{formatBytes(bytes_processed)}</span> processed
              </div>
            )}
            {cache_hit !== undefined && (
              <div className={cache_hit ? "text-green-400" : "text-gray-400"}>
                {cache_hit ? "✓ Cache hit" : "Cache miss"}
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={exportToCSV}
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
            >
              Export CSV
            </button>
            <button
              onClick={exportToJSON}
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
            >
              Export JSON
            </button>
          </div>
        </div>
      </Card>

      {/* Results Table */}
      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 sticky top-0">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-4 py-2 text-left font-semibold text-gray-300 cursor-pointer hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {col}
                    {sortColumn === col && (
                      <span className="text-blue-400">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, idx) => (
              <tr
                key={idx}
                className="border-t border-gray-700 hover:bg-gray-800/50 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 text-gray-300">
                    {row[col] == null ? (
                      <span className="text-gray-500 italic">null</span>
                    ) : (
                      String(row[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
