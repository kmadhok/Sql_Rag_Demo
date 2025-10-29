import React from 'react';
import './LoadingSpinner.css';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
  inline?: boolean;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'medium', 
  message, 
  inline = false 
}) => {
  return (
    <div className={`loading-spinner ${size} ${inline ? 'inline' : ''}`}>
      <div className="spinner" />
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
};

export default LoadingSpinner;