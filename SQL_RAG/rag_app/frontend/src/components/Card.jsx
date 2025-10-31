import React from 'react';

/**
 * Framer-inspired Card Component
 * Supports hover effects and different layouts
 */
const Card = ({ 
  children, 
  className = '', 
  hover = false,
  padding = 'lg',
  shadow = false,
  ...props 
}) => {
  const baseClasses = 'card';
  
  const hoverClasses = hover ? 'card-hover' : '';
  const shadowClasses = shadow ? 'card-shadow' : '';
  
  const paddingClasses = {
    sm: 'card-padding-sm',
    md: 'card-padding-md', 
    lg: 'card-padding-lg',
    xl: 'card-padding-xl'
  };

  return (
    <div 
      className={`${baseClasses} ${hoverClasses} ${shadowClasses} ${paddingClasses[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

/**
 * Stat Card Component for Dashboard
 */
export const StatCard = ({ 
  title, 
  value, 
  change, 
  changeType = 'neutral',
  icon = null,
  loading = false 
}) => {
  const changeColor = {
    positive: 'text-green-500',
    negative: 'text-red-500',
    neutral: 'text-gray-400'
  }[changeType];

  if (loading) {
    return (
      <Card hover className="animate-pulse">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-4 bg-gray-700 rounded w-20 mb-2"></div>
            <div className="h-8 bg-gray-700 rounded w-16"></div>
          </div>
          <div className="h-8 w-8 bg-gray-700 rounded-full"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card hover>
      <div className="flex items-center justify-between">
        <div>
          <p className="typography-caption">{title}</p>
          <p className="typography-heading text-2xl">{value}</p>
          {change && (
            <p className={`typography-caption font-medium ${changeColor}`}>
              {change.startsWith('+') ? '↑' : change.startsWith('-') ? '↓' : '→'} {change}
            </p>
          )}
        </div>
        {icon && (
          <div className="flex-shrink-0 ml-4">
            <div className="p-2 bg-gray-800 rounded-lg">
              {icon}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

/**
 * Feature Card Component
 */
export const FeatureCard = ({ 
  title, 
  description, 
  icon = null,
  action = null,
  ...props 
}) => {
  return (
    <Card hover {...props}>
      {icon && (
        <div className="mb-4">
          <div className="p-3 bg-blue-900/20 border border-blue-800/30 rounded-lg inline-block">
            {icon}
          </div>
        </div>
      )}
      <h3 className="typography-subheading mb-2">{title}</h3>
      <p className="typography-body mb-4">{description}</p>
      {action && (
        <div className="mt-auto">
          {action}
        </div>
      )}
    </Card>
  );
};

export default Card;