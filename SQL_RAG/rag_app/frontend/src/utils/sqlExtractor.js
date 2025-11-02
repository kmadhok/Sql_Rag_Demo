/**
 * SQL Extraction Utility
 *
 * Extracts SQL queries from text responses, particularly from markdown code blocks.
 * Ported from Python's sql_extraction_service.py
 */

/**
 * Normalize SQL by removing code fences and whitespace
 * @param {string} sql - Raw SQL text
 * @returns {string|null} - Cleaned SQL or null
 */
function normalizeSql(sql) {
  if (!sql) return null;

  let stripped = sql.trim();

  // Remove leading ```
  if (stripped.startsWith('```')) {
    stripped = stripped.substring(3).trimStart();

    // Remove 'sql' language identifier
    if (stripped.toLowerCase().startsWith('sql')) {
      stripped = stripped.substring(3).trimStart();
    }
  }

  // Remove trailing ```
  if (stripped.includes('```')) {
    stripped = stripped.split('```')[0].trim();
  }

  return stripped || null;
}

/**
 * Extract SQL from text using pattern matching
 * @param {string} text - Text containing SQL
 * @returns {string|null} - Extracted SQL or null
 */
export function extractSql(text) {
  if (!text || text.trim().length < 10) {
    return null;
  }

  // Patterns to try (in order of specificity)
  const patterns = [
    // Fenced SQL code block
    { regex: /```sql\s*([^`]+)```/is, group: 1 },
    // Generic fenced code block
    { regex: /```([^`]*)```/is, group: 1 },
    // Bare SELECT statement
    { regex: /SELECT[^;]+;/is, group: 0 },
    // Bare WITH statement (CTEs)
    { regex: /WITH[^;]+;/is, group: 0 },
  ];

  for (const pattern of patterns) {
    try {
      const match = text.match(pattern.regex);
      if (match) {
        let result = match[pattern.group].trim();
        result = normalizeSql(result);

        if (result && result.length > 10) {
          // Basic validation - check for SQL keywords
          const resultUpper = result.toUpperCase();
          if (
            resultUpper.includes('SELECT') ||
            resultUpper.includes('WITH') ||
            resultUpper.includes('INSERT') ||
            resultUpper.includes('UPDATE')
          ) {
            return result;
          }
        }
      }
    } catch (error) {
      console.warn(`Pattern ${pattern.regex} failed:`, error);
      continue;
    }
  }

  return null;
}

/**
 * Check if text contains SQL
 * @param {string} text - Text to check
 * @returns {boolean}
 */
export function containsSql(text) {
  return extractSql(text) !== null;
}

/**
 * Extract SQL and return with metadata
 * @param {string} text - Text containing SQL
 * @returns {Object} - {sql: string|null, found: boolean, method: string|null}
 */
export function extractSqlWithMetadata(text) {
  const sql = extractSql(text);

  if (!sql) {
    return { sql: null, found: false, method: null };
  }

  // Determine extraction method
  let method = 'unknown';
  if (text.includes('```sql')) {
    method = 'fenced-sql';
  } else if (text.includes('```')) {
    method = 'fenced-generic';
  } else if (sql.toUpperCase().startsWith('SELECT')) {
    method = 'bare-select';
  } else if (sql.toUpperCase().startsWith('WITH')) {
    method = 'bare-with';
  }

  return { sql, found: true, method };
}
