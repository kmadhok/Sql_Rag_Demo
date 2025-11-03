import { useState, useRef } from 'react';
import SqlEditor from './playground/SqlEditor.jsx';
import ResultsDataGrid from './playground/ResultsDataGrid.jsx';
import SchemaExplorerSidebar from './playground/SchemaExplorerSidebar.jsx';
import AiSuggestionPanel from './playground/AiSuggestionPanel.jsx';
import DiffViewModal from './playground/DiffViewModal.jsx';
import Button from './Button.jsx';
import Card from './Card.jsx';
import { executeSql, explainSql, fixSql } from '../services/ragClient.js';

/**
 * SQL Playground - Interactive SQL editor with AI assistance
 * Allows users to write, execute, and analyze SQL queries
 */
export default function Playground({ theme }) {
  const [sql, setSql] = useState('SELECT * FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 10;');
  const [result, setResult] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [maxBytes, setMaxBytes] = useState(100_000_000); // 100MB default
  const [showSchema, setShowSchema] = useState(true);

  // Week 4: AI Features State
  const [aiPanel, setAiPanel] = useState({
    visible: false,
    explanation: null,
    isLoading: false
  });
  const [isFixing, setIsFixing] = useState(false);
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [diffData, setDiffData] = useState(null);

  const editorRef = useRef(null);

  const handleExecute = async (dryRun = false) => {
    console.log('🚀 Execute button clicked', { dryRun, sqlLength: sql.length });

    if (!sql.trim()) {
      console.warn('⚠️ Empty SQL query');
      setResult({
        success: false,
        error_message: 'Please enter a SQL query'
      });
      return;
    }

    setIsExecuting(true);
    setResult(null);

    try {
      console.log('📡 Calling executeSql API...', {
        sql: sql.trim().substring(0, 100) + (sql.trim().length > 100 ? '...' : ''),
        dry_run: dryRun,
        max_bytes_billed: maxBytes
      });

      const response = await executeSql({
        sql: sql.trim(),
        dry_run: dryRun,
        max_bytes_billed: maxBytes
      });

      console.log('✅ API Response received:', response);

      const transformedResult = {
        success: response.success || false,
        data: response.data || [],
        row_count: response.total_rows || response.row_count || 0,
        execution_time: response.execution_time,
        bytes_processed: response.bytes_processed,
        bytes_billed: response.bytes_billed,
        cache_hit: response.cache_hit,
        dry_run: response.dry_run,
        job_id: response.job_id,
        error_message: response.error_message,
        validation_message: response.validation_message
      };

      setResult(transformedResult);

      if (response.validation_message) {
        console.warn('Validation warning:', response.validation_message);
      }
    } catch (error) {
      console.error('❌ Execution failed:', error);
      console.error('Error details:', { message: error.message, stack: error.stack });
      setResult({
        success: false,
        error_message: error.message || 'Failed to execute query'
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const handleClear = () => {
    setResult(null);
  };

  const handleInsert = (text) => {
    if (!text || !editorRef.current) {
      return;
    }

    const position = editorRef.current.getPosition?.();
    if (!position) {
      return;
    }

    editorRef.current.executeEdits?.('', [
      {
        range: {
          startLineNumber: position.lineNumber,
          startColumn: position.column,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        },
        text,
        forceMoveMarkers: true,
      },
    ]);

    editorRef.current.focus?.();
  };

  const loadExample = (exampleSql) => {
    setSql(exampleSql);
    setResult(null);
  };

  // Week 4: AI Feature Handlers
  const handleExplain = async () => {
    console.log('✨ Explain with AI clicked');

    // Get selected text or full SQL
    const selection = editorRef.current?.getSelection?.();
    const model = editorRef.current?.getModel?.();
    let sqlToExplain = sql;

    if (selection && model) {
      const selectedText = model.getValueInRange(selection);
      if (selectedText && selectedText.trim()) {
        sqlToExplain = selectedText.trim();
      }
    }

    if (!sqlToExplain.trim()) {
      alert('No SQL to explain');
      return;
    }

    // Show AI panel with loading state
    setAiPanel({ visible: true, explanation: null, isLoading: true });

    try {
      console.log('🤖 Calling explainSql API...');
      const response = await explainSql({ sql: sqlToExplain });

      if (response.success) {
        setAiPanel({
          visible: true,
          explanation: response.explanation,
          isLoading: false
        });
        console.log('✅ Explanation generated');
      } else {
        throw new Error(response.error || 'Failed to generate explanation');
      }
    } catch (error) {
      console.error('❌ Explain failed:', error);
      setAiPanel({
        visible: true,
        explanation: `Error: ${error.message}`,
        isLoading: false
      });
    }
  };

  const handleFixWithAI = async () => {
    if (!result || result.success || !result.error_message) {
      return;
    }

    console.log('🤖 Fix with AI clicked');
    setIsFixing(true);

    try {
      console.log('🔧 Calling fixSql API...');
      const response = await fixSql({
        sql: sql,
        error_message: result.error_message
      });

      if (response.success) {
        setDiffData({
          original: sql,
          fixed: response.fixed_sql,
          diagnosis: response.diagnosis,
          changes: response.changes
        });
        setShowDiffModal(true);
        console.log('✅ Fix generated');
      } else {
        throw new Error(response.error || 'Failed to fix SQL');
      }
    } catch (error) {
      console.error('❌ Fix failed:', error);
      alert(`AI fix failed: ${error.message}`);
    } finally {
      setIsFixing(false);
    }
  };

  const handleApplyFix = (fixedSql) => {
    console.log('✅ Applying fix');
    setSql(fixedSql);
    setShowDiffModal(false);
    setDiffData(null);
    setResult(null); // Clear error so user can re-run
  };

  return (
    <div className="flex flex-col h-full gap-4 p-4 overflow-hidden">
      <div className="flex justify-between items-center flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">SQL Playground</h2>
          <p className="text-sm text-gray-400 mt-1">
            Write and execute SQL queries against BigQuery
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowSchema((prev) => !prev)}
            className={`px-3 py-2 text-sm rounded transition-colors ${
              showSchema
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {showSchema ? '📋 Hide Schema' : '📋 Show Schema'}
          </button>

          <select
            onChange={(event) => {
              if (event.target.value) {
                loadExample(event.target.value);
                event.target.value = '';
              }
            }}
            className="px-3 py-2 text-sm bg-gray-700 text-gray-200 border border-gray-600 rounded hover:bg-gray-600 transition-colors"
          >
            <option value="">Load Example...</option>
            <option value="SELECT * FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 10;">
              Simple SELECT
            </option>
            <option value="SELECT category, COUNT(*) as count\nFROM `bigquery-public-data.thelook_ecommerce.products`\nGROUP BY category\nORDER BY count DESC;">
              GROUP BY Example
            </option>
            <option value="SELECT u.id, u.email, COUNT(o.id) as order_count\nFROM `bigquery-public-data.thelook_ecommerce.users` u\nLEFT JOIN `bigquery-public-data.thelook_ecommerce.orders` o ON u.id = o.user_id\nGROUP BY u.id, u.email\nORDER BY order_count DESC\nLIMIT 10;">
              JOIN Example
            </option>
          </select>
        </div>
      </div>

      <div className="flex gap-4 flex-1 overflow-hidden">
        <SchemaExplorerSidebar
          onInsert={handleInsert}
          isVisible={showSchema}
          onToggle={() => setShowSchema(false)}
        />

        <div className="flex-1 flex flex-col gap-4 overflow-hidden">
          <Card className="flex-shrink-0">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-200">Query Editor</h3>
                <div className="text-xs text-gray-400">
                  Tip: Press <kbd className="px-1 py-0.5 bg-gray-700 rounded">Cmd+Enter</kbd> to execute
                </div>
              </div>

              <SqlEditor
                ref={editorRef}
                value={sql}
                onChange={(value) => setSql(value || '')}
                onExecute={() => handleExecute(false)}
                theme={theme === 'dark' ? 'vs-dark' : 'vs-light'}
                height="300px"
              />

              <div className="flex justify-between items-center pt-2 border-t border-gray-700">
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-400">
                    Max bytes:
                    <input
                      type="number"
                      value={maxBytes}
                      onChange={(event) => setMaxBytes(parseInt(event.target.value, 10) || 100_000_000)}
                      className="ml-2 px-2 py-1 w-32 text-sm bg-gray-700 text-gray-200 border border-gray-600 rounded"
                    />
                    <span className="ml-1 text-xs">({formatBytes(maxBytes)})</span>
                  </label>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={handleExplain}
                    disabled={!sql.trim() || aiPanel.isLoading}
                    className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Explain SQL with AI"
                  >
                    ✨ Explain with AI
                  </Button>
                  <Button
                    onClick={() => handleExecute(true)}
                    disabled={isExecuting || !sql.trim()}
                    className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isExecuting ? 'Checking...' : 'Dry Run'}
                  </Button>
                  <Button
                    onClick={() => handleExecute(false)}
                    disabled={isExecuting || !sql.trim()}
                    className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isExecuting ? 'Executing...' : 'Execute Query'}
                  </Button>
                  {result && (
                    <Button
                      onClick={handleClear}
                      className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600"
                    >
                      Clear Results
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {isExecuting && (
            <Card className="text-center py-8">
              <div className="text-gray-400">
                <div className="flex items-center justify-center gap-3">
                  <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <div>Executing query...</div>
                </div>
              </div>
            </Card>
          )}

          {/* Week 4: Error Card with Fix with AI Button */}
          {result && !result.success && result.error_message && (
            <Card className="border-l-4 border-red-500 bg-red-900/20">
              <div className="flex items-start gap-3">
                <span className="text-2xl">⚠️</span>
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-red-400 mb-2">Query Error</h4>
                  <pre className="text-sm text-gray-300 whitespace-pre-wrap mb-3 font-mono bg-gray-800/50 p-3 rounded">
                    {result.error_message}
                  </pre>
                  <Button
                    onClick={handleFixWithAI}
                    disabled={isFixing}
                    className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isFixing ? '🤖 Analyzing...' : '🤖 Fix with AI'}
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {result && result.success && (
            <Card className="flex-1 flex flex-col overflow-hidden">
              <div className="mb-2 flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-200">
                  {result.dry_run ? 'Dry Run Results' : 'Query Results'}
                </h3>
              </div>
              <div className="flex-1 overflow-auto">
                <ResultsDataGrid result={result} sql={sql} />
              </div>
            </Card>
          )}

          {!result && !isExecuting && (
            <Card className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-400">
                <div className="text-4xl mb-4">⚡</div>
                <div className="text-lg mb-2">Ready to execute your query</div>
                <div className="text-sm">
                  Write your SQL query above and press Execute or <kbd className="px-1 py-0.5 bg-gray-700 rounded">Cmd+Enter</kbd>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Week 4: AI Suggestion Panel */}
        {aiPanel.visible && (
          <AiSuggestionPanel
            explanation={aiPanel.explanation}
            suggestions={[]}
            isLoading={aiPanel.isLoading}
            onClose={() => setAiPanel({ visible: false, explanation: null, isLoading: false })}
          />
        )}
      </div>

      {/* Week 4: Diff View Modal */}
      {showDiffModal && diffData && (
        <DiffViewModal
          diffData={diffData}
          onApply={handleApplyFix}
          onClose={() => {
            setShowDiffModal(false);
            setDiffData(null);
          }}
        />
      )}
    </div>
  );
}
