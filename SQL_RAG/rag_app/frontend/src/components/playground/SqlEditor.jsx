import { useRef, forwardRef, useImperativeHandle } from 'react';
import Editor from '@monaco-editor/react';

/**
 * SQL Editor component using Monaco Editor
 * Provides syntax highlighting, keyboard shortcuts, and auto-completion.
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

  function handleEditorDidMount(editor, monaco) {
    editorRef.current = editor;

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
});

export default SqlEditor;
