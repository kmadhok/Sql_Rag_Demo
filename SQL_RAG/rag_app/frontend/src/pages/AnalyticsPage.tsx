import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { fetchQueries } from '../store/dataSlice';
import { QueryItem } from '../types/api';

const AnalyticsPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { analytics, queries, isLoading, error } = useSelector((state: RootState) => state.data);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    // Mock analytics data for now
    dispatch(fetchQueries({}));
  }, [dispatch, timeRange]);

  const mockAnalyticsData = {
    queryStats: {
      totalQueries: queries.length,
      averageExecutionTime: 0.5,
      successRate: 95.5,
      popularQueries: queries.slice(0, 5)
    },
    sessionStats: {
      totalSessions: 42,
      averageMessagesPerSession: 3.8,
      sessionDuration: 15.2,
      topUsers: []
    },
    performanceMetrics: {
      currentLoad: 65,
      responseTime: 0.234,
      errorRate: 2.1,
      uptime: 99.98
    }
  };

  const currentAnalytics = analytics || mockAnalyticsData;

  const styles = {
    analyticsPage: {
      padding: '20px',
      maxWidth: '1200px',
      margin: '0 auto'
    },
    pageHeader: {
      marginBottom: '30px',
      textAlign: 'center' as const
    },
    metricsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '20px',
      marginBottom: '30px'
    },
    metricCard: {
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      textAlign: 'center' as const
    },
    metricValue: {
      fontSize: '2rem',
      fontWeight: 'bold',
      margin: '10px 0'
    },
    metricLabel: {
      color: '#666',
      fontSize: '0.9rem'
    },
    chartsSection: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '20px',
      marginBottom: '30px'
    },
    chartContainer: {
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    tableContainer: {
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse' as const
    },
    tableHeader: {
      backgroundColor: '#f8f9fa',
      textAlign: 'left' as const,
      padding: '10px',
      borderBottom: '2px solid #dee2e6'
    },
    tableCell: {
      padding: '10px',
      borderBottom: '1px solid #dee2e6'
    }
  };

  return (
    <div style={styles.analyticsPage}>
      <div style={styles.pageHeader}>
        <h1>📊 Analytics Dashboard</h1>
        <p>Monitor usage patterns, query performance, and system health</p>
      </div>

      {/* Time Range Selector */}
      <div style={{ marginBottom: '20px', textAlign: 'center' }}>
        <select 
          value={timeRange} 
          onChange={(e) => setTimeRange(e.target.value)}
          style={{ padding: '8px 16px', borderRadius: '4px', border: '1px solid #ddd' }}
        >
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <h3>Total Queries</h3>
          <div style={styles.metricValue}>
            {currentAnalytics.queryStats.totalQueries}
          </div>
          <div style={styles.metricLabel}>Executed queries</div>
        </div>
        
        <div style={styles.metricCard}>
          <h3>Success Rate</h3>
          <div style={styles.metricValue}>
            {currentAnalytics.queryStats.successRate}%
          </div>
          <div style={styles.metricLabel}>Query success rate</div>
        </div>
        
        <div style={styles.metricCard}>
          <h3>Avg Response Time</h3>
          <div style={styles.metricValue}>
            {currentAnalytics.performanceMetrics.responseTime}s
          </div>
          <div style={styles.metricLabel}>Average response time</div>
        </div>
        
        <div style={styles.metricCard}>
          <h3>System Uptime</h3>
          <div style={styles.metricValue}>
            {currentAnalytics.performanceMetrics.uptime}%
          </div>
          <div style={styles.metricLabel}>System uptime</div>
        </div>
      </div>

      {/* Charts */}
      <div style={styles.chartsSection}>
        <div style={styles.chartContainer}>
          <h3>Query Volume Over Time</h3>
          <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
            📈 Chart visualization would go here
          </div>
        </div>
        
        <div style={styles.chartContainer}>
          <h3>Query Categories Distribution</h3>
          <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
            🥧 Pie chart would go here
          </div>
        </div>
      </div>

      {/* Popular Queries Table */}
      <div style={styles.tableContainer}>
        <h3>Most Popular Queries</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.tableHeader}>Query</th>
              <th style={styles.tableHeader}>Category</th>
              <th style={styles.tableHeader}>Usage Count</th>
              <th style={styles.tableHeader}>Avg Time (s)</th>
            </tr>
          </thead>
          <tbody>
            {currentAnalytics.queryStats.popularQueries.map((query: QueryItem, index: number) => (
              <tr key={index}>
                <td style={styles.tableCell}>{query.title}</td>
                <td style={styles.tableCell}>{query.category}</td>
                <td style={styles.tableCell}>{query.complexity}</td>
                <td style={styles.tableCell}>0.{Math.floor(Math.random() * 9) + 1}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isLoading && <div>Loading analytics...</div>}
      {error && <div>Error: {error}</div>}
    </div>
  );
};

export default AnalyticsPage;