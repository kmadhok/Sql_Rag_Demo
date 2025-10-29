import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import { useSelector } from 'react-redux';
import { RootState } from './store';

// Pages
import IntroductionPage from './pages/IntroductionPage';
import ChatPage from './pages/ChatPage';
import SearchPage from './pages/SearchPage';
import DataPage from './pages/DataPage';
import AnalyticsPage from './pages/AnalyticsPage';

// Components
import Navigation from './components/common/Navigation';
import Notifications from './components/common/Notifications';

// Styles
import './App.css';

const AppContent: React.FC = () => {
  const { darkMode } = useSelector((state: RootState) => state.ui);

  return (
    <div className={`app ${darkMode ? 'dark' : 'light'}`}>
      <Router>
        <div className="app-layout">
          <Navigation />
          
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Navigate to="/introduction" replace />} />
              <Route path="/introduction" element={<IntroductionPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/data" element={<DataPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="*" element={<Navigate to="/introduction" replace />} />
            </Routes>
          </main>
          
          <Notifications />
        </div>
      </Router>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
};

export default App;