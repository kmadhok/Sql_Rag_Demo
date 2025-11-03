import { useRef, useState, forwardRef, useImperativeHandle } from 'react';
import Editor from '@monaco-editor/react';
import { completeSql } from '../../services/ragClient.js';

/**
 * SQL Editor component using Monaco Editor
 * Provides syntax highlighting, keyboard shortcuts, and AI-powered auto-completion.
 */
const SqlEditor = forwardRef(function SqlEditor(
  {
    value,
    onChange,
    onExecute,
    theme = 'vs-dark',
    readOnly = false,
    height = '400px'
  },
  ref
) {
  const editorRef = useRef(null);
  const [isLoadingCompletions, setIsLoadingCompletions] = useState(false);
  const completionTimeoutRef = useRef(null);

  useImperativeHandle(
    ref,
    () => ({
      getInstance: () => editorRef.current,
      getValue: () => editorRef.current?.getValue(),
      getModel: () => editorRef.current?.getModel(),
      getPosition: () => editorRef.current?.getPosition(),
      getSelection: () => editorRef.current?.getSelection?.(),
      executeEdits: (...args) => editorRef.current?.executeEdits(...args),
      focus: () => editorRef.current?.focus(),
      setValue: (newValue) => editorRef.current?.setValue(newValue),
    }),
    []
  );

  // Static fallback suggestions when AI is unavailable or too slow
  function getStaticSuggestions(monaco, partial) {
    const partialUpper = partial.toUpperCase().trim();
    const keywords = [];

    if (!partialUpper.includes('SELECT')) {
      keywords.push({ label: 'SELECT', detail: 'Start a SELECT query' });
      keywords.push({ label: 'WITH', detail: 'Start a CTE' });
    } else if (!partialUpper.includes('FROM')) {
      keywords.push({ label: 'FROM', detail: 'Specify source table' });
      keywords.push({ label: '* FROM', detail: 'Select all columns' });
    } else if (!partialUpper.includes('WHERE')) {
      keywords.push({ label: 'WHERE', detail: 'Add filter conditions' });
      keywords.push({ label: 'GROUP BY', detail: 'Group results' });
      keywords.push({ label: 'ORDER BY', detail: 'Sort results' });
    } else {
      keywords.push({ label: 'LIMIT', detail: 'Limit results' });
      keywords.push({ label: 'ORDER BY', detail: 'Sort results' });
    }

    return keywords.map(kw => ({
      label: kw.label,
      kind: monaco.languages.CompletionItemKind.Keyword,
      insertText: kw.label,
      detail: kw.detail,
    }));
  }

  function handleEditorDidMount(editor, monaco) {
    editorRef.current = editor;

    // Register keyboard shortcuts
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        if (onExecute) {
          onExecute();
        }
      }
    );

    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK,
      () => {
        editor.getAction('editor.action.formatDocument')?.run();
      }
    );

    // Week 4: Register AI-powered completion provider
    monaco.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: ['.', ' ', '('],

      provideCompletionItems: async (model, position) => {
        // Get text before cursor
        const textBefore = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        });

        // Debounce: only call AI for substantial queries
        if (textBefore.length < 10) {
          return { suggestions: getStaticSuggestions(monaco, textBefore) };
        }

        // Clear existing timeout
        if (completionTimeoutRef.current) {
          clearTimeout(completionTimeoutRef.current);
        }

        // Return promise that resolves after debounce
        return new Promise((resolve) => {
          completionTimeoutRef.current = setTimeout(async () => {
            try {
              setIsLoadingCompletions(true);

              // Call AI completion endpoint
              const response = await completeSql({
                partial_sql: textBefore,
                cursor_position: {
                  line: position.lineNumber,
                  column: position.column,
                },
              });

              if (response.success && response.suggestions && response.suggestions.length > 0) {
                const aiSuggestions = response.suggestions.map((s, idx) => ({
                  label: s.completion,
                  kind: monaco.languages.CompletionItemKind.Snippet,
                  detail: s.explanation,
                  insertText: s.completion,
                  range: {
                    startLineNumber: position.lineNumber,
                    startColumn: position.column,
                    endLineNumber: position.lineNumber,
                    endColumn: position.column,
                  },
                  sortText: String(idx).padStart(3, '0'), // Preserve AI ranking
                }));

                resolve({ suggestions: aiSuggestions });
              } else {
                // Fallback to static suggestions
                resolve({ suggestions: getStaticSuggestions(monaco, textBefore) });
              }
            } catch (error) {
              console.error('AI completion error:', error);
              // Fallback to static suggestions
              resolve({ suggestions: getStaticSuggestions(monaco, textBefore) });
            } finally {
              setIsLoadingCompletions(false);
            }
          }, 500); // 500ms debounce delay
        });
      },
    });

    editor.focus();
  }

  const editorOptions = {
    selectOnLineNumbers: true,
    roundedSelection: false,
    readOnly: readOnly,
    cursorStyle: 'line',
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: 14,
    lineNumbers: 'on',
    glyphMargin: false,
    folding: true,
    lineDecorationsWidth: 10,
    lineNumbersMinChars: 3,
    renderLineHighlight: 'all',
    scrollbar: {
      verticalScrollbarSize: 10,
      horizontalScrollbarSize: 10,
    },
    quickSuggestions: {
      other: true,
      comments: false,
      strings: false,
    },
    suggestOnTriggerCharacters: true,
    acceptSuggestionOnCommitCharacter: true,
    acceptSuggestionOnEnter: 'on',
    wordBasedSuggestions: true,
  };

  return (
    <div className="sql-editor-container" style={{ height, position: 'relative' }}>
      <Editor
        height={height}
        defaultLanguage="sql"
        value={value}
        onChange={onChange}
        onMount={handleEditorDidMount}
        theme={theme}
        options={editorOptions}
      />
      {isLoadingCompletions && (
        <div
          style={{
            position: 'absolute',
            bottom: '10px',
            right: '10px',
            padding: '6px 12px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: '#fff',
            borderRadius: '4px',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              width: '12px',
              height: '12px',
              border: '2px solid #fff',
              borderTop: '2px solid transparent',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }}
          ></div>
          Getting AI suggestions...
        </div>
      )}
    </div>
  );
});

export default SqlEditor;
