import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { fetchQueries } from '../store/dataSlice';
import { QueryItem } from '../types/api';
import QueryCard from '../components/search/QueryCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import '../styles/SearchPage.css';

const SearchPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { queries, isLoading, error } = useSelector((state: RootState) => state.data);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    dispatch(fetchQueries({ search: searchQuery }));
  }, [dispatch, searchQuery]);

  return (
    <div className="search-page">
      <div className="search-header">
        <h1>🔍 Query Catalog</h1>
        <p>Browse and search through pre-built SQL queries</p>
      </div>

      <div className="search-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Search queries..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button className="filter-button">
          Filters
        </button>
      </div>

      {isLoading && queries.length === 0 && (
        <div className="loading-state">
          <LoadingSpinner message="Loading queries..." />
        </div>
      )}

      {error && (
        <div className="error-state">
          <p>Error loading queries: {error}</p>
        </div>
      )}

      <div className="queries-grid">
        {queries.map((query: QueryItem) => (
          <QueryCard key={query.id} query={query} />
        ))}
      </div>

      {!isLoading && !error && queries.length === 0 && (
        <div className="empty-state">
          <p>No queries found. Try adjusting your search.</p>
        </div>
      )}
    </div>
  );
};

export default SearchPage;