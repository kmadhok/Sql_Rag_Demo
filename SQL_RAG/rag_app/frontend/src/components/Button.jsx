import React from 'react';

/**
 * Framer-inspired Button Component
 * Supports multiple variants: primary, secondary, accent
 * Multiple sizes: sm, md, lg
 */
const Button = ({ 
  variant = 'primary', 
  size = 'md', 
  children, 
  className = '',
  disabled = false,
  icon = null,
  iconPosition = 'left',
  ...props 
}) => {
  const baseClasses = 'btn';
  
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary', 
    accent: 'btn-accent'
  };
  
  const sizeClasses = {
    sm: 'btn-sm',
    md: 'btn-md', 
    lg: 'btn-lg'
  };

  const renderIcon = () => {
    if (!icon) return null;
    return (
      <span className="btn-icon" style={{ 
        marginRight: iconPosition === 'left' ? '8px' : '0',
        marginLeft: iconPosition === 'right' ? '8px' : '0'
      }}>
        {icon}
      </span>
    );
  };

  return (
    <button 
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {iconPosition === 'left' && renderIcon()}
      {children}
      {iconPosition === 'right' && renderIcon()}
    </button>
  );
};

export default Button;