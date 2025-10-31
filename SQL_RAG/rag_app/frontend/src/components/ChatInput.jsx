import { useState } from "react";
import Button from "./Button.jsx";
import Card from "./Card.jsx";

const DEFAULT_OPTIONS = {
  k: 20,
  gemini_mode: false,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

function ChatInput({ onSend, isLoading, options, onOptionsChange }) {
  const [message, setMessage] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isLoading) {
      return;
    }
    onSend(trimmed, mergedOptions);
    setMessage("");
  };

  const handleToggle = (field) => () => {
    const nextOptions = { ...mergedOptions, [field]: !mergedOptions[field] };
    onOptionsChange(nextOptions);
  };

  const handleSlider = (value) => {
    const nextOptions = { ...mergedOptions, k: value };
    onOptionsChange(nextOptions);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  return (
    <div className="space-y-md">
      {/* Main Input */}
      <Card className="card-muted" padding="lg">
        <form onSubmit={handleSubmit} className="space-y-md">
          <div className="flex space-x-2">
            <div className="flex-1 relative">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything... (use @create for SQL)"
                className="input textarea resize-none"
                disabled={isLoading}
                rows={1}
              />
              
              {/* Character count */}
              {message.length > 0 && (
                <div className="absolute bottom-1.5 right-2 text-xs text-gray-500">
                  {message.length}
                </div>
              )}
            </div>
            
            {/* Send Button - No Icon */}
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={isLoading || !message.trim()}
              className="px-4"
            >
              {isLoading ? (
                <span className="text-sm">Sending...</span>
              ) : (
                <span className="text-sm">Send</span>
              )}
            </Button>
          </div>
          
          {/* Quick Actions */}
          <div className="flex items-center justify-between">
            <div className="flex space-x-sm">
              <button
                type="button"
                onClick={() => setMessage("@create Top users by order value")}
                className="chip-button"
              >
                Top users
              </button>
              <button
                type="button"
                onClick={() => setMessage("Popular products?")}
                className="chip-button"
              >
                Products
              </button>
            </div>
            
            <button
              type="button"
              onClick={() => setShowOptions(!showOptions)}
              className="flex items-center space-x-1 typography-caption"
            >
              <span>Options</span>
              <span className={`transition-transform ${showOptions ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
          </div>
        </form>
      </Card>

      {/* Advanced Options */}
      <div className={`transition-all duration-200 ${showOptions ? 'opacity-100 max-h-64' : 'opacity-0 max-h-0 overflow-hidden'}`}>
        <Card className="card-muted" padding="lg">
          <h3 className="typography-subheading mb-4 text-sm">Options</h3>
          
          <div className="options-grid">
            {/* Left Column */}
            <div className="space-y-md">
              {/* Document Count Slider */}
              <div>
                <label className="typography-label text-xs">
                  Documents: {mergedOptions.k}
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={mergedOptions.k}
                  onChange={(e) => handleSlider(parseInt(e.target.value))}
                  className="range mt-1"
                />
                <div className="flex justify-between typography-caption mt-0.5 text-xs">
                  <span>5</span>
                  <span>50</span>
                </div>
              </div>

              {/* Gemini Mode */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="typography-body text-sm">Gemini Mode</p>
                  <p className="typography-caption text-xs">Advanced language</p>
                </div>
                <button
                  type="button"
                  onClick={handleToggle('gemini_mode')}
                  className={`toggle ${mergedOptions.gemini_mode ? 'active' : ''}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>

              {/* Hybrid Search */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="typography-body text-sm">Hybrid Search</p>
                  <p className="typography-caption text-xs">Semantic + keyword</p>
                </div>
                <button
                  type="button"
                  onClick={handleToggle('hybrid_search')}
                  className={`toggle ${mergedOptions.hybrid_search ? 'active' : ''}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-md">
              {/* Auto Adjust Weights */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="typography-body text-sm">Auto Weights</p>
                  <p className="typography-caption text-xs">Optimize search</p>
                </div>
                <button
                  type="button"
                  onClick={handleToggle('auto_adjust_weights')}
                  className={`toggle ${mergedOptions.auto_adjust_weights ? 'active' : ''}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>

              {/* Query Rewriting */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="typography-body text-sm">Query Rewrite</p>
                  <p className="typography-caption text-xs">Improve understanding</p>
                </div>
                <button
                  type="button"
                  onClick={handleToggle('query_rewriting')}
                  className={`toggle ${mergedOptions.query_rewriting ? 'active' : ''}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>

              {/* SQL Validation */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="typography-body text-sm">SQL Validate</p>
                  <p className="typography-caption text-xs">Security check</p>
                </div>
                <button
                  type="button"
                  onClick={handleToggle('sql_validation')}
                  className={`toggle ${mergedOptions.sql_validation ? 'active' : ''}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default ChatInput;
