import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import { setAgentType } from '../../store/chatSlice';
import './AgentSelector.css';

interface AgentSelectorProps {
  disabled?: boolean;
}

const AgentSelector: React.FC<AgentSelectorProps> = ({ disabled = false }) => {
  const { agentType } = useSelector((state: RootState) => state.chat);
  const dispatch = useDispatch<AppDispatch>();

  const agentOptions = [
    { value: 'normal', label: 'Normal' },
    { value: 'create', label: 'Create' },
    { value: 'explain', label: 'Explain' },
    { value: 'schema', label: 'Schema' },
    { value: 'longanswer', label: 'Long Answer' },
  ];

  return (
    <div className="agent-selector">
      <label>Agent Mode:</label>
      <select
        value={agentType}
        onChange={(e) => dispatch(setAgentType(e.target.value))}
        disabled={disabled}
        className="agent-select"
      >
        {agentOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default AgentSelector;