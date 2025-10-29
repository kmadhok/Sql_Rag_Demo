import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import { removeNotification } from '../../store/uiSlice';
import './Notifications.css';

const Notifications: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { notifications } = useSelector((state: RootState) => state.ui);

  React.useEffect(() => {
    if (notifications.length > 0) {
      const timer = setTimeout(() => {
        dispatch(removeNotification(notifications[0].id));
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notifications, dispatch]);

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="notifications-container">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`notification ${notification.type}`}
          onClick={() => dispatch(removeNotification(notification.id))}
        >
          <div className="notification-content">
            <span className="notification-icon">
              {notification.type === 'success' && '✓'}
              {notification.type === 'error' && '✗'}
              {notification.type === 'warning' && '⚠'}
              {notification.type === 'info' && 'ℹ'}
            </span>
            <span className="notification-message">
              {notification.message}
            </span>
          </div>
          <button 
            className="notification-close"
            onClick={() => dispatch(removeNotification(notification.id))}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};

export default Notifications;