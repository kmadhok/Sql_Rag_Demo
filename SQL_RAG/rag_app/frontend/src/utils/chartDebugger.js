/**
 * Centralized Chart Debugging Utility
 *
 * Provides structured logging for chart loading, rendering, and error tracking.
 * Enable debug mode via environment variable: VITE_DEBUG_CHARTS=true
 */

const isDebugEnabled = import.meta.env.VITE_DEBUG_CHARTS === 'true' ||
                       localStorage.getItem('debug_charts') === 'true';

const LOG_STYLES = {
  info: 'background: #2563eb; color: white; padding: 2px 4px; border-radius: 2px;',
  success: 'background: #10b981; color: white; padding: 2px 4px; border-radius: 2px;',
  error: 'background: #ef4444; color: white; padding: 2px 4px; border-radius: 2px;',
  warn: 'background: #f59e0b; color: white; padding: 2px 4px; border-radius: 2px;',
};

class ChartDebugger {
  constructor() {
    this.logs = [];
    this.maxLogs = 100;
  }

  /**
   * Format timestamp for logs
   */
  getTimestamp() {
    return new Date().toISOString().split('T')[1].slice(0, -1);
  }

  /**
   * Store log entry for later retrieval
   */
  storeLog(level, context, message, data) {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      context,
      message,
      data,
    };

    this.logs.push(entry);

    // Keep only last N logs
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }

  /**
   * Log info message
   */
  info(context, message, data = null) {
    this.storeLog('info', context, message, data);

    if (isDebugEnabled) {
      console.log(
        `%c[CHART:${context}]%c ${this.getTimestamp()} - ${message}`,
        LOG_STYLES.info,
        '',
        data || ''
      );
    }
  }

  /**
   * Log success message
   */
  success(context, message, data = null) {
    this.storeLog('success', context, message, data);

    if (isDebugEnabled) {
      console.log(
        `%c[CHART:${context}]%c ${this.getTimestamp()} - ✅ ${message}`,
        LOG_STYLES.success,
        '',
        data || ''
      );
    }
  }

  /**
   * Log warning message
   */
  warn(context, message, data = null) {
    this.storeLog('warn', context, message, data);

    if (isDebugEnabled) {
      console.warn(
        `%c[CHART:${context}]%c ${this.getTimestamp()} - ⚠️ ${message}`,
        LOG_STYLES.warn,
        '',
        data || ''
      );
    }
  }

  /**
   * Log error message (always shown, even if debug disabled)
   */
  error(context, message, error = null) {
    const errorData = error ? {
      message: error.message,
      stack: error.stack,
      name: error.name,
      ...error,
    } : null;

    this.storeLog('error', context, message, errorData);

    // Always log errors, even if debug is disabled
    console.error(
      `%c[CHART:${context}]%c ${this.getTimestamp()} - ❌ ${message}`,
      LOG_STYLES.error,
      '',
      errorData || ''
    );
  }

  /**
   * Log API request
   */
  apiRequest(method, url, savedQueryId = null) {
    this.info('API', `${method} ${url}`, { savedQueryId });
  }

  /**
   * Log API response
   */
  apiResponse(method, url, status, data = null) {
    if (status >= 200 && status < 300) {
      this.success('API', `${method} ${url} - ${status}`, data);
    } else {
      this.error('API', `${method} ${url} - ${status}`, { status, data });
    }
  }

  /**
   * Log chart lifecycle event
   */
  lifecycle(chartId, event, data = null) {
    this.info('LIFECYCLE', `Chart ${chartId}: ${event}`, data);
  }

  /**
   * Log data transformation
   */
  transform(chartId, input, output) {
    if (isDebugEnabled) {
      this.info('TRANSFORM', `Chart ${chartId} data transformation`, {
        inputRows: input?.length || 0,
        outputRows: output?.length || 0,
        inputSample: input?.slice(0, 2),
        outputSample: output?.slice(0, 2),
      });
    }
  }

  /**
   * Get all stored logs
   */
  getLogs(level = null) {
    if (level) {
      return this.logs.filter(log => log.level === level);
    }
    return this.logs;
  }

  /**
   * Export logs as JSON
   */
  exportLogs() {
    const blob = new Blob([JSON.stringify(this.logs, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chart-debug-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Clear all logs
   */
  clearLogs() {
    this.logs = [];
    console.log('%c[CHART:DEBUG]%c Logs cleared', LOG_STYLES.info, '');
  }

  /**
   * Get error logs only
   */
  getErrors() {
    return this.getLogs('error');
  }

  /**
   * Check if debug mode is enabled
   */
  isDebugEnabled() {
    return isDebugEnabled;
  }

  /**
   * Enable debug mode
   */
  enableDebug() {
    localStorage.setItem('debug_charts', 'true');
    console.log('%c[CHART:DEBUG]%c Debug mode enabled. Refresh page to apply.', LOG_STYLES.success, '');
  }

  /**
   * Disable debug mode
   */
  disableDebug() {
    localStorage.removeItem('debug_charts');
    console.log('%c[CHART:DEBUG]%c Debug mode disabled. Refresh page to apply.', LOG_STYLES.info, '');
  }
}

// Create singleton instance
const chartDebugger = new ChartDebugger();

// Expose to window for console access
if (typeof window !== 'undefined') {
  window.chartDebugger = chartDebugger;

  // Log initialization
  if (isDebugEnabled) {
    console.log(
      '%c[CHART:DEBUG]%c Debug mode is ENABLED',
      LOG_STYLES.success,
      ''
    );
    console.log(
      '%c[CHART:DEBUG]%c Available commands:',
      LOG_STYLES.info,
      '',
      '\n  - window.chartDebugger.getLogs() - Get all logs',
      '\n  - window.chartDebugger.getErrors() - Get error logs only',
      '\n  - window.chartDebugger.exportLogs() - Export logs to file',
      '\n  - window.chartDebugger.clearLogs() - Clear all logs',
      '\n  - window.chartDebugger.disableDebug() - Disable debug mode'
    );
  }
}

export default chartDebugger;
