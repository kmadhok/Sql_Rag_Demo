import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { fetchSchema, fetchQueries } from '../store/dataSlice';
import { ExecuteSQLResponse } from '../types/api';
import SchemasTree from '../components/data/SchemasTree';
import DataTable from '../components/data/DataTable';
import QueryCard from '../components/search/QueryCard';
import LoadingSpinner from '../components/common/LoadingSpinner';

const DataPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { schema, queries, isLoading, error } = useSelector((state: RootState) => state.data);
  const [activeTab, setActiveTab] = useState<'schema' | 'queries' | 'results'>('schema');
  const [queryResult, setQueryResult] = useState<ExecuteSQLResponse | null>(null);
  const [executingQuery, setExecutingQuery] = useState(false);

  useEffect(() => {
    dispatch(fetchSchema());
    dispatch(fetchQueries({}));
  }, [dispatch]);

  const handleExecuteQuery = async (sql: string) => {
    try {
      setExecutingQuery(true);
      // This would call the SQL execution API
      console.log('Executing query:', sql);
      // Mock execution for now
      setQueryResult({ success: true, data: [], columns: [], timestamp: new Date().toISOString() });
      setActiveTab('results');
    } catch (error) {
      console.error('Error executing query:', error);
    } finally {
      setExecutingQuery(false);
    }
  };

  const styles = {
    dataPage: {
      padding: '20px',
      maxWidth: '1200px',
      margin: '0 auto'
    },
    pageHeader: {
      marginBottom: '30px',
      textAlign: 'center' as const
    },
    tabNavigation: {
      display: 'flex',
      marginBottom: '20px',
      borderBottom: '1px solid #ddd'
    },
    tabButton: {
      padding: '12px 24px',
      border: 'none',
      backgroundColor: 'transparent',
      cursor: 'pointer',
      borderBottom: '2px solid transparent',
      marginRight: '10px'
    },
    activeTab: {
      borderBottom: '2px solid #007bff',
      color: '#007bff'
    },
    dataContent: {
      marginTop: '20px'
    },
    queryHeader: {
      marginBottom: '20px'
    },
    queriesList: {
      display: 'grid',
      gap: '16px'
    }
  };

  return (
    <div style={styles.dataPage}>
      <div style={styles.pageHeader}>
        <h1>🗃️ Data Explorer</h1>
        <p>Explore your database schema, understand table relationships,
          and execute SQL queries with our powerful data exploration tools.</p>
      </div>

      <div style={styles.tabNavigation}>
        <button
          style={{...styles.tabButton, ...(activeTab === 'schema' ? styles.activeTab : {})}}
          onClick={() => setActiveTab('schema')}
        >
          📊 Schema
        </button>
        <button
          style={{...styles.tabButton, ...(activeTab === 'queries' ? styles.activeTab : {})}}
          onClick={() => setActiveTab('queries')}
        >
          🔍 Query Catalog
        </button>
        <button
          style={{...styles.tabButton, ...(activeTab === 'results' ? styles.activeTab : {})}}
          onClick={() => setActiveTab('results')}
        >
          📋 Results
        </button>
      </div>

      <div style={styles.dataContent}>
        {activeTab === 'schema' && (
          <div className="schema-panel">
            <SchemasTree 
              schema={schema} 
              isLoading={isLoading}
              error={error}
            />
          </div>
        )}

        {activeTab === 'queries' && (
          <div className="query-panel">
            <div style={styles.queryHeader}>
              <h2>Query Catalog</h2>
              <p>Browse pre-built SQL queries and execute them instantly</p>
            </div>
            
            <div style={styles.queriesList}>
              {queries.map((query) => (
                <QueryCard
                  key={query.id}
                  query={query}
                  onExecute={handleExecuteQuery}
                />
              ))}
            </div>
            
            {isLoading && <LoadingSpinner message="Loading queries..." />}
            {error && <div className="error-message">{error}</div>}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="results-panel">
            <DataTable 
              data={queryResult} 
              isLoading={executingQuery}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default DataPage;