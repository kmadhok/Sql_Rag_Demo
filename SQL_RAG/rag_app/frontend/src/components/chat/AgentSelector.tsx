import React from 'react';
import { AgentType } from '../../types/api';
import '../styles/AgentSelector.css';

interface AgentSelectorProps {
  selectedAgent: AgentType;
  onAgentChange: (agent: AgentType) => void;
}

const AgentSelector: React.FC<AgentSelectorProps> = ({
  selectedAgent,
  onAgentChange,
}) => {
  const agents = [
    {
      type: AgentType.NORMAL,
      name: 'Normal',
      description: 'Standard question answering',
      icon: '💬',
    },
    {
      type: AgentType.CREATE,
      name: '@create',
      description: 'Generate SQL queries',
      icon: '🔨',
    },
    {
      type: AgentType.EXPLAIN,
      name: '@explain',
      description: 'Explain SQL queries',
      icon: '📖',
    },
    {
      type: AgentType.SCHEMA,
      name: '@schema',
      description: 'Explore database schema',
      icon: '🗂️',
    },
    {
      type: AgentType.LONGANSWER,
      name: '@longanswer',
      description: 'Detailed explanations',
      icon: '📝',
    },
  ];
  
  return (
    <div className="agent-selector">
      <label className="agent-label">Agent Mode:</label>
      <div className="agent-options">
        {agents.map((agent) => (
          <button
            key={agent.type}
            className={`agent-option ${
              selectedAgent === agent.type ? 'selected' : ''
            }`}
            onClick={() => onAgentChange(agent.type)}
            title={agent.description}
          >
            <span className="agent-icon">{agent.icon}</span>
            <span className="agent-name">{agent.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default AgentSelector;