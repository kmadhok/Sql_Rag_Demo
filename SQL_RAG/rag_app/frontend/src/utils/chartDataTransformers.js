/**
 * Data transformation utilities for chart visualizations.
 * Handles aggregation, grouping, and formatting of query results for Recharts.
 */

/**
 * Aggregation types supported by the chart engine
 */
export const AGGREGATION_TYPES = {
  COUNT: 'count',
  SUM: 'sum',
  AVG: 'avg',
  MIN: 'min',
  MAX: 'max',
};

/**
 * Aggregate data by a categorical column (x-axis) and numeric column (y-axis)
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} xColumn - Column name for grouping (categorical)
 * @param {string} yColumn - Column name for aggregation (numeric) - optional for COUNT
 * @param {string} aggregationType - One of AGGREGATION_TYPES
 * @param {number} topN - Limit to top N results (default: 10)
 * @returns {Array<{name: string, value: number}>} - Formatted data for Recharts
 */
export function aggregateData(data, xColumn, yColumn, aggregationType = 'count', topN = 10) {
  if (!data || data.length === 0) {
    return [];
  }

  // Group data by xColumn
  const groups = {};

  data.forEach((row) => {
    const key = String(row[xColumn] ?? 'N/A');

    if (!groups[key]) {
      groups[key] = {
        name: key,
        values: [],
      };
    }

    // For non-COUNT aggregations, collect the y-column values
    if (aggregationType !== AGGREGATION_TYPES.COUNT && yColumn) {
      const value = parseFloat(row[yColumn]);
      if (!isNaN(value)) {
        groups[key].values.push(value);
      }
    } else {
      // For COUNT, just increment
      groups[key].values.push(1);
    }
  });

  // Perform aggregation
  const aggregated = Object.values(groups).map((group) => {
    let value = 0;

    switch (aggregationType) {
      case AGGREGATION_TYPES.COUNT:
        value = group.values.length;
        break;

      case AGGREGATION_TYPES.SUM:
        value = group.values.reduce((sum, v) => sum + v, 0);
        break;

      case AGGREGATION_TYPES.AVG:
        value = group.values.length > 0
          ? group.values.reduce((sum, v) => sum + v, 0) / group.values.length
          : 0;
        break;

      case AGGREGATION_TYPES.MIN:
        value = group.values.length > 0 ? Math.min(...group.values) : 0;
        break;

      case AGGREGATION_TYPES.MAX:
        value = group.values.length > 0 ? Math.max(...group.values) : 0;
        break;

      default:
        value = group.values.length;
    }

    return {
      name: group.name,
      value: Math.round(value * 100) / 100, // Round to 2 decimal places
    };
  });

  // Sort by value descending and take top N
  aggregated.sort((a, b) => b.value - a.value);
  return aggregated.slice(0, topN);
}

/**
 * Extract unique values from a column (for filtering/selection)
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} columnName - Column to extract values from
 * @returns {Array<string>} - Unique values sorted
 */
export function getUniqueValues(data, columnName) {
  if (!data || data.length === 0) {
    return [];
  }

  const unique = new Set();
  data.forEach((row) => {
    const value = row[columnName];
    if (value !== null && value !== undefined) {
      unique.add(String(value));
    }
  });

  return Array.from(unique).sort();
}

/**
 * Detect if a column is numeric based on data
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} columnName - Column to check
 * @returns {boolean} - True if column appears to be numeric
 */
export function isNumericColumn(data, columnName) {
  if (!data || data.length === 0) {
    return false;
  }

  // Sample first 10 rows
  const sample = data.slice(0, Math.min(10, data.length));

  let numericCount = 0;
  sample.forEach((row) => {
    const value = row[columnName];
    if (value !== null && value !== undefined) {
      const num = parseFloat(value);
      if (!isNaN(num) && isFinite(num)) {
        numericCount++;
      }
    }
  });

  // If >70% of sampled values are numeric, consider it numeric
  return numericCount / sample.length > 0.7;
}

/**
 * Get recommended chart type based on data characteristics
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} xColumn - X-axis column
 * @param {string} yColumn - Y-axis column
 * @returns {string} - Recommended chart type ('bar', 'line', 'pie')
 */
export function getRecommendedChartType(data, xColumn, yColumn) {
  if (!data || data.length === 0) {
    return 'bar';
  }

  const uniqueXValues = getUniqueValues(data, xColumn);

  // Few unique values → good for pie/bar
  if (uniqueXValues.length <= 5) {
    return 'bar'; // Could also be 'pie' but bar is safer default
  }

  // Many unique values → better for bar/line
  if (uniqueXValues.length > 20) {
    // Check if x-axis looks like time series
    const isTimeSeries = uniqueXValues.some(v =>
      /\d{4}-\d{2}-\d{2}/.test(v) || /\d{4}\/\d{2}\/\d{2}/.test(v)
    );
    return isTimeSeries ? 'line' : 'bar';
  }

  return 'bar'; // Default safe choice
}

/**
 * Format value for display in charts (abbreviate large numbers)
 *
 * @param {number} value - Numeric value
 * @returns {string} - Formatted string (e.g., "1.2K", "3.4M")
 */
export function formatChartValue(value) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  const num = parseFloat(value);
  if (isNaN(num)) {
    return String(value);
  }

  if (num >= 1_000_000) {
    return (num / 1_000_000).toFixed(1) + 'M';
  }
  if (num >= 1_000) {
    return (num / 1_000).toFixed(1) + 'K';
  }
  if (num % 1 !== 0) {
    return num.toFixed(2);
  }
  return String(num);
}

/**
 * Detect if a column contains date/datetime values
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} columnName - Column to check
 * @returns {boolean} - True if column appears to be date/datetime
 */
export function isDateColumn(data, columnName) {
  if (!data || data.length === 0) {
    return false;
  }

  // Sample first 10 rows
  const sample = data.slice(0, Math.min(10, data.length));
  let dateCount = 0;

  sample.forEach((row) => {
    const value = row[columnName];
    if (value !== null && value !== undefined) {
      const str = String(value);

      // Check for common date formats
      const datePatterns = [
        /^\d{4}-\d{2}-\d{2}/, // YYYY-MM-DD
        /^\d{2}\/\d{2}\/\d{4}/, // MM/DD/YYYY
        /^\d{4}\/\d{2}\/\d{2}/, // YYYY/MM/DD
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/, // ISO datetime
      ];

      if (datePatterns.some(pattern => pattern.test(str))) {
        dateCount++;
      }
    }
  });

  // If >70% of sampled values match date patterns
  return dateCount / sample.length > 0.7;
}

/**
 * Parse and format date for chart display
 *
 * @param {string|Date} dateValue - Date value to format
 * @param {string} format - Format type ('short', 'medium', 'long')
 * @returns {string} - Formatted date string
 */
export function formatDate(dateValue, format = 'short') {
  if (!dateValue) return 'N/A';

  const date = new Date(dateValue);
  if (isNaN(date.getTime())) {
    return String(dateValue);
  }

  switch (format) {
    case 'short':
      // MMM DD (e.g., "Jan 15")
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    case 'medium':
      // MMM DD, YYYY (e.g., "Jan 15, 2024")
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    case 'long':
      // Full date with time
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });

    default:
      return date.toLocaleDateString();
  }
}

/**
 * Transform data for line charts (handles time-series data)
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} xColumn - Column name for X-axis (usually date/time)
 * @param {string} yColumn - Column name for Y-axis (numeric)
 * @param {string} aggregation - Aggregation type
 * @returns {Array<{name: string, value: number}>} - Sorted data for LineChart
 */
export function transformForLineChart(data, xColumn, yColumn, aggregation = 'count') {
  if (!data || data.length === 0) {
    return [];
  }

  // First aggregate the data
  const aggregated = aggregateData(data, xColumn, yColumn, aggregation, 50); // More points for trends

  // Check if X column is date-based
  const isDate = isDateColumn(data, xColumn);

  if (isDate) {
    // Sort by date
    aggregated.sort((a, b) => {
      const dateA = new Date(a.name);
      const dateB = new Date(b.name);
      return dateA - dateB;
    });

    // Format dates for display
    return aggregated.map(item => ({
      ...item,
      name: formatDate(item.name, 'short'),
    }));
  }

  // For non-date data, return as-is
  return aggregated;
}

/**
 * Transform data for pie charts (limit to top categories)
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} column - Column name for categories
 * @param {string} valueColumn - Column for values (optional, uses count if not provided)
 * @param {string} aggregation - Aggregation type
 * @param {number} maxSlices - Maximum number of pie slices (default: 8)
 * @returns {Array<{name: string, value: number, percent: number}>} - Data with percentages
 */
export function transformForPieChart(data, column, valueColumn, aggregation = 'count', maxSlices = 8) {
  if (!data || data.length === 0) {
    return [];
  }

  // Aggregate data
  const aggregated = aggregateData(data, column, valueColumn, aggregation, maxSlices);

  // Calculate total
  const total = aggregated.reduce((sum, item) => sum + item.value, 0);

  // Add percentage to each item
  return aggregated.map(item => ({
    ...item,
    percent: total > 0 ? Math.round((item.value / total) * 100 * 10) / 10 : 0,
  }));
}

/**
 * Validate data for scatter chart (both columns must be numeric)
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} xColumn - X-axis column
 * @param {string} yColumn - Y-axis column
 * @returns {{valid: boolean, message: string}} - Validation result
 */
export function validateScatterData(data, xColumn, yColumn) {
  if (!data || data.length === 0) {
    return { valid: false, message: 'No data available' };
  }

  if (!xColumn || !yColumn) {
    return { valid: false, message: 'Both X and Y columns are required' };
  }

  const xNumeric = isNumericColumn(data, xColumn);
  const yNumeric = isNumericColumn(data, yColumn);

  if (!xNumeric) {
    return { valid: false, message: `X column "${xColumn}" must be numeric` };
  }

  if (!yNumeric) {
    return { valid: false, message: `Y column "${yColumn}" must be numeric` };
  }

  return { valid: true, message: 'Valid scatter chart data' };
}

/**
 * Get all numeric columns from dataset
 *
 * @param {Array<Object>} data - Raw query results
 * @returns {Array<string>} - List of numeric column names
 */
export function getNumericColumns(data) {
  if (!data || data.length === 0) {
    return [];
  }

  const columns = Object.keys(data[0]);
  return columns.filter(col => isNumericColumn(data, col));
}

/**
 * Get all date columns from dataset
 *
 * @param {Array<Object>} data - Raw query results
 * @returns {Array<string>} - List of date column names
 */
export function getDateColumns(data) {
  if (!data || data.length === 0) {
    return [];
  }

  const columns = Object.keys(data[0]);
  return columns.filter(col => isDateColumn(data, col));
}

/**
 * Get all categorical columns from dataset (non-numeric, non-date)
 *
 * @param {Array<Object>} data - Raw query results
 * @returns {Array<string>} - List of categorical column names
 */
export function getCategoricalColumns(data) {
  if (!data || data.length === 0) {
    return [];
  }

  const columns = Object.keys(data[0]);
  return columns.filter(col => !isNumericColumn(data, col) && !isDateColumn(data, col));
}

/**
 * Recommend best chart type based on data characteristics
 *
 * @param {Array<Object>} data - Raw query results
 * @param {string} xColumn - X-axis column
 * @param {string} yColumn - Y-axis column (optional)
 * @returns {string} - Recommended chart type
 */
export function recommendChartType(data, xColumn, yColumn) {
  if (!data || data.length === 0 || !xColumn) {
    return 'column';
  }

  const uniqueXValues = getUniqueValues(data, xColumn);
  const isXNumeric = isNumericColumn(data, xColumn);
  const isXDate = isDateColumn(data, xColumn);
  const isYNumeric = yColumn ? isNumericColumn(data, yColumn) : false;

  // Scatter chart: Both X and Y are numeric
  if (isXNumeric && isYNumeric) {
    return 'scatter';
  }

  // Line/Area chart: X is date/time
  if (isXDate) {
    return 'line'; // Could also be 'area'
  }

  // Pie chart: Few categories (≤ 8) and simple distribution
  if (uniqueXValues.length <= 8 && uniqueXValues.length >= 2) {
    return 'pie';
  }

  // Bar chart: Many categories (better horizontal layout)
  if (uniqueXValues.length > 15) {
    return 'bar';
  }

  // Default to column chart
  return 'column';
}
