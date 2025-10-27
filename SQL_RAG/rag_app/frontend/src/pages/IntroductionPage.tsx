import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/IntroductionPage.css';

const IntroductionPage: React.FC = () => {
  const navigate = useNavigate();
  
  return (
    <div className="introduction-page">
      <div className="hero-section">
        <h1 className="hero-title">
          ⚡ Ask Data Questions Without SQL
        </h1>
        <p className="hero-subtitle">
          Get instant answers from your data in plain English—no SQL required. 
          For SQL experts: build queries 10x faster with AI-powered assistance.
        </p>
        
        <div className="cta-buttons">
          <button 
            className="primary-button"
            onClick={() => navigate('/chat')}
          >
            🚀 Start Chatting
          </button>
          <button 
            className="secondary-button"
            onClick={() => navigate('/search')}
          >
            🔍 Browse Queries
          </button>
        </div>
      </div>
      
      <div className="features-section">
        <h2>💡 Key Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>AI-Powered SQL Generation</h3>
            <p>Translate natural language questions into optimized SQL queries using advanced AI models.</p>
          </div>
          
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Real-time Data Execution</h3>
            <p>Execute generated queries safely against your BigQuery database with cost controls.</p>
          </div>
          
          <div className="feature-card">
            <div className="feature-icon">🗂️</div>
            <h3>Smart Schema Integration</h3>
            <p>Automatically inject relevant database schema information for more accurate results.</p>
          </div>
          
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>Conversational Context</h3>
            <p>Maintain context across conversations for follow-up questions and refinements.</p>
          </div>
          
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Specialized Agents</h3>
            <p>Use @create, @explain, @schema, and @longanswer agents for specific tasks.</p>
          </div>
          
          <div className="feature-card">
            <div className="feature-icon">📈</div>
            <h3>Query Catalog</h3>
            <p>Browse a searchable catalog of pre-built SQL queries with examples and explanations.</p>
          </div>
        </div>
      </div>
      
      <div className="how-it-works">
        <h2>🚀 How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h3>Ask in Plain English</h3>
              <p>"Show me top 10 customers by order total"</p>
            </div>
          </div>
          
          <div className="step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h3>AI Understands Context</h3>
              <p>System analyzes your intent and database schema</p>
            </div>
          </div>
          
          <div className="step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h3>Executes Safely</h3>
              <p>Runs optimized SQL query with cost limits</p>
            </div>
          </div>
          
          <div className="step">
            <div className="step-number">4</div>
            <div className="step-content">
              <h3>Get Results</h3>
              <p>Receive data, explanations, and related insights</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="getting-started">
        <h2>🎯 Getting Started</h2>
        <div className="quick-links">
          <div className="link-card" onClick={() => navigate('/chat')}>
            <h3>💬 Chat Interface</h3>
            <p>Start asking questions immediately</p>
            <span>→</span>
          </div>
          
          <div className="link-card" onClick={() => navigate('/search')}>
            <h3>🔍 Query Search</h3>
            <p>Browse pre-built SQL examples</p>
            <span>→</span>
          </div>
          
          <div className="link-card" onClick={() => navigate('/data')}>
            <h3>📊 Data Schema</h3>
            <p>Explore database structure</p>
            <span>→</span>
          </div>
          
          <div className="link-card" onClick={() => navigate('/analytics')}>
            <h3>📈 Analytics</h3>
            <p>View query statistics and insights</p>
            <span>→</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IntroductionPage;