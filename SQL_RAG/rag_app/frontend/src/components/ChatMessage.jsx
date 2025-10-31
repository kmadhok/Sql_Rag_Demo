import { useState, useMemo } from "react";
import Button from "./Button.jsx";
import Card from "./Card.jsx";

function MessageContainer({ align, children }) {
  return (
    <div className={`flex ${align === "end" ? "justify-end" : "justify-start"} mb-3 animate-fade-in-up`}>
      {children}
    </div>
  );
}

function UsageChips({ usage }) {
  if (!usage) {
    return null;
  }

  const chips = [
    usage.total_tokens != null && {
      label: `${usage.total_tokens.toLocaleString()} tokens`,
      color: 'blue'
    },
    usage.retrieval_time != null && {
      label: `${usage.retrieval_time.toFixed(2)}s retrieval`,
      color: 'green'
    },
    usage.generation_time != null && {
      label: `${usage.generation_time.toFixed(2)}s generation`,
      color: 'purple'
    },
    usage.documents_retrieved != null && {
      label: `${usage.documents_retrieved} docs`,
      color: 'orange'
    },
    usage.search_method && {
      label: usage.search_method,
      color: 'gray'
    },
  ].filter(Boolean);

  if (chips.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {chips.map((chip, index) => (
        <span
          key={index}
          className="badge-soft"
          style={{
            backgroundColor:
              chip.color === 'blue' ? 'rgba(59, 130, 246, 0.18)' :
              chip.color === 'green' ? 'rgba(34, 197, 94, 0.18)' :
              chip.color === 'purple' ? 'rgba(168, 85, 247, 0.18)' :
              chip.color === 'orange' ? 'rgba(249, 115, 22, 0.18)' :
              'rgba(148, 163, 184, 0.18)',
            color:
              chip.color === 'blue' ? 'rgba(191, 219, 254, 0.95)' :
              chip.color === 'green' ? 'rgba(187, 247, 208, 0.95)' :
              chip.color === 'purple' ? 'rgba(233, 213, 255, 0.95)' :
              chip.color === 'orange' ? 'rgba(255, 237, 213, 0.95)' :
              'rgba(226, 232, 240, 0.9)'
          }}
        >
          {chip.label}
        </span>
      ))}
    </div>
  );
}

function SourceList({ sources }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Card className="mt-3 card-muted" padding="md">
      <div className="flex items-center justify-between">
        <h4 className="typography-subheading text-xs">Sources ({sources.length})</h4>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="typography-caption text-blue-400 hover:text-blue-300 transition-colors text-xs"
        >
          {isExpanded ? 'Hide' : 'Show'}
        </button>
      </div>
      
      {isExpanded && (
        <div className="mt-2 space-y-1">
          {sources.map((source, index) => (
            <div key={index} className="surface-item">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="typography-body text-xs mb-1">
                    {source.content?.substring(0, 150)}
                    {source.content?.length > 150 && '...'}
                  </p>
                  {source.metadata && (
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(source.metadata).slice(0, 3).map(([key, value]) => (
                        <span
                          key={key}
                          className="badge-meta"
                        >
                          {key}: {String(value).substring(0, 20)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <span className="typography-caption text-gray-500 ml-2 text-xs">
                  #{index + 1}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ExecutionPanel({ execution, onExecute, onSave }) {
  const [isSqlExpanded, setIsSqlExpanded] = useState(false);
  
  if (!execution) {
    return null;
  }

  const renderStatusIndicator = () => {
    switch (execution.status) {
      case "loading":
        return (
          <div className="flex items-center space-x-2">
            <div className="animate-pulse flex space-x-0.5">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
            </div>
            <span className="typography-caption text-blue-400 text-xs">
              {execution.dryRun ? 'Validating...' : 'Executing...'}
            </span>
          </div>
        );
      case "success":
        return (
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${execution.dryRun ? 'bg-green-500' : 'bg-blue-500'}`}></div>
            <span className="typography-caption text-green-400 text-xs">
              {execution.dryRun ? 'Valid' : `${execution.result?.row_count || 0} rows`}
            </span>
          </div>
        );
      case "error":
        return (
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span className="typography-caption text-red-400 text-xs">
              {execution.error || 'Failed'}
            </span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="mt-3 space-y-2">
      {/* Status and Actions */}
      <div className="flex items-center justify-between">
        {renderStatusIndicator()}
        
        <div className="flex space-x-2">
          {execution.status === "success" && !execution.dryRun && (
            <Button
              variant="accent"
              size="sm"
              disabled={execution.saving === "pending"}
              onClick={() => onSave?.()}
            >
              {execution.saving === "pending" ? "Saving..." : "Save"}
            </Button>
          )}
          
          {execution.sql && (
            <button
              onClick={() => navigator.clipboard.writeText(execution.sql)}
              className="typography-caption text-blue-400 hover:text-blue-300 transition-colors text-xs"
            >
              Copy
            </button>
          )}
        </div>
      </div>

      {/* SQL Preview */}
      {execution.sql && (
        <Card className="card-muted" padding="md">
          <div className="flex items-center justify-between mb-1">
            <h4 className="typography-subheading text-xs">SQL</h4>
            <button
              onClick={() => setIsSqlExpanded(!isSqlExpanded)}
              className="typography-caption text-blue-400 hover:text-blue-300 transition-colors text-xs"
            >
              {isSqlExpanded ? 'Collapse' : 'Expand'}
            </button>
          </div>
          
          <pre className={`text-xs font-mono surface-item overflow-x-auto whitespace-pre-wrap ${!isSqlExpanded ? 'max-h-24 overflow-y-auto' : ''}`}>
            <code className="text-green-200">{execution.sql}</code>
          </pre>
        </Card>
      )}

      {/* Results Preview */}
      {execution.status === "success" && execution.result?.data && (
        <Card className="card-muted" padding="md">
          <h4 className="typography-subheading text-xs mb-2">
            Results ({execution.result.row_count || 0} rows)
          </h4>
          
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="table-header">
                  {execution.result.columns?.map((col, index) => (
                    <th key={index} className="text-left table-cell">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {execution.result.data.slice(0, 3).map((row, rowIndex) => (
                  <tr key={rowIndex} className="table-row">
                    {execution.result.columns?.map((col, colIndex) => (
                      <td key={colIndex} className="table-cell">
                        {row[col]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            
            {execution.result.data.length > 3 && (
              <p className="typography-caption text-center mt-2 text-gray-500 text-xs">
                ... and {execution.result.data.length - 3} more rows
              </p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

export default function ChatMessage({ message, onExecute, onSave }) {
  const isUser = message.role === "user";

  const messageBubble = useMemo(() => {
    return (
      <div className={`
        max-w-xl rounded-xl p-3 shadow-md
        ${isUser 
          ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white' 
          : 'bg-gray-900 border border-gray-700 text-gray-100'
        }
        backdrop-blur-sm
      `}>
        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </p>
        
        {/* Message metadata */}
        <div className="flex items-center justify-between mt-2">
          <span className="typography-caption opacity-70 text-xs">
            {isUser ? 'You' : 'Assistant'}
          </span>
          {message.timestamp && (
            <span className="typography-caption opacity-70 text-xs">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    );
  }, [message.content, isUser, message.timestamp]);

  return (
    <MessageContainer align={isUser ? "end" : "start"}>
      <div className={`flex ${isUser ? "flex-row-reverse" : "flex-row"} items-start space-x-2`}>
        {/* Simple Avatar - No Icon */}
        <div className={`
          w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold
          ${isUser 
            ? 'bg-blue-600 text-white ml-2' 
            : 'bg-gray-700 text-gray-300 mr-2'
          }
        `}>
          {isUser ? 'U' : 'A'}
        </div>
        
        {/* Message Content */}
        <div className="flex flex-col space-y-2">
          {messageBubble}
          
          {/* Non-user message enhancements */}
          {!isUser && (
            <>
              <UsageChips usage={message.usage} />
              <SourceList sources={message.sources} />
              <ExecutionPanel 
                execution={message.execution} 
                onExecute={() => onExecute?.(message.id, { dryRun: false })}
                onSave={() => onSave?.(message.id)}
              />
            </>
          )}
        </div>
      </div>
    </MessageContainer>
  );
}
