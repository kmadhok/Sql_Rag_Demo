import { useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';

/**
 * SQL Editor component using Monaco Editor
 * Provides syntax highlighting, keyboard shortcuts, and auto-completion
 */
export default function SqlEditor({
  value,
  onChange,
  onExecute,
  theme = 'vs-dark',
  readOnly = false,
  height = '400px'
}) {
  const editorRef = useRef(null);

  /**
   * Called when editor is mounted
   */
  function handleEditorDidMount(editor, monaco) {
    editorRef.current = editor;

    // Add Cmd/Ctrl+Enter keyboard shortcut to execute query
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        if (onExecute) {
          onExecute();
        }
      }
    );

    // Add Cmd/Ctrl+K keyboard shortcut to format SQL (future enhancement)
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK,
      () => {
        editor.getAction('editor.action.formatDocument')?.run();
      }
    );

    // Focus editor on mount
    editor.focus();
  }

  /**
   * Editor configuration options
   */
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
    // Enable suggestions (autocomplete)
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
    <div className="sql-editor-container" style={{ height }}>
      <Editor
        height={height}
        defaultLanguage="sql"
        value={value}
        onChange={onChange}
        onMount={handleEditorDidMount}
        theme={theme}
        options={editorOptions}
      />
    </div>
  );
}
