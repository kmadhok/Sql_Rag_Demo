import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import { toggleSidebar, setCurrentPage } from '../../store/uiSlice';
import './Navigation.css';

const Navigation: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { sidebarOpen } = useSelector((state: RootState) => state.ui);
  const location = useLocation();

  const navigationItems = [
    { path: '/introduction', label: '🏠 Introduction', icon: '🏠' },
    { path: '/chat', label: '💬 Chat', icon: '💬' },
    { path: '/search', label: '🔍 Search', icon: '🔍' },
    { path: '/data', label: '📊 Data', icon: '📊' },
    { path: '/analytics', label: '📈 Analytics', icon: '📈' },
  ];

  React.useEffect(() => {
    const currentPage = location.pathname.split('/')[1] || 'introduction';
    dispatch(setCurrentPage(currentPage));
  }, [location.pathname, dispatch]);

  return (
    <nav className={`navigation ${sidebarOpen ? 'open' : 'closed'}`}>
      <div className="nav-header">
        <h2>SQL RAG</h2>
        <button 
          className="sidebar-toggle"
          onClick={() => dispatch(toggleSidebar())}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
      </div>

      <div className="nav-menu">
        {navigationItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => 
              `nav-item ${isActive ? 'active' : ''}`
            }
            onClick={() => dispatch(setCurrentPage(item.path.replace('/', '')))}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="nav-footer">
        <div className="app-info">
          <p>SQL RAG Assistant</p>
          <p className="version">v2.0.0</p>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;