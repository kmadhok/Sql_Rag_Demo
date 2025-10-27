import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { 
  fetchQueries, 
  setSearchQuery, 
  setFilterOptions 
} from '../store/dataSlice';
import { FilterOptions } from '../types/data';
import { SearchBar } from '../components/search/SearchBar';
import { FilterPanel } from '../components/search/FilterPanel';
import { QueryCard } from '../components/search/QueryCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import '../styles/SearchPage.css';

const SearchPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { 
    queries, 
    queryStats, 
    isLoading, 
    searchQuery,
    filterOptions 
  } = useSelector((state: RootState) => state.data);
  
  const [filtersVisible, setFiltersVisible] = useState(false);
  
  useEffect(() => {
    dispatch(fetchQueries({ 
      search: searchQuery, 
      page: 1,
      filters: filterOptions 
    }));
  }, [dispatch, searchQuery, filterOptions]);
  
  const handleSearch = (query: string) => {
    dispatch(setSearchQuery(query));
  };
  
  const handleFilter = (filters: FilterOptions) => {
    dispatch(setFilterOptions(filters));
  };
  
  const handlePageChange = (page: number) => {
    dispatch(fetchQueries({ 
      search: searchQuery, 
      page,
      filters: filterOptions 
    }));
  };
  
  const totalPages = Math.ceil(queryStats.total / queryStats.pageSize);
  
  return (
    <div className="search-page">
      <div className="search-header">
        <h1>🔍 Query Search</h1>
        <p>Search through {queryStats.total} SQL queries with examples</p>
      </div>
      
      <div className="search-controls">
        <SearchBar 
          onSearch={handleSearch}
          placeholder="Search queries, tables, or descriptions..."
          initialValue={searchQuery}
        />
        
        <button
          onClick={() => setFiltersVisible(!filtersVisible)}
          className="filters-toggle"
        >
          {filtersVisible ? '📋 Hide Filters' : '🎛️ Show Filters'}
        </button>
      </div>
      
      {filtersVisible && (
        <FilterPanel 
          onFilterChange={handleFilter}
          filters={filterOptions}
        />
      )}
      
      <div className="search-stats">
        <span>Found {queryStats.total} queries</span>
        <span>Page {queryStats.page} of {totalPages}</span>
      </div>
      
      {isLoading ? (
        <LoadingSpinner message="Searching queries..." />
      ) : (
        <>
          <div className="query-grid">
            {queries.map((query) => (
              <QueryCard
                key={query.id}
                query={query}
                onCopy={(sql) => navigator.clipboard.writeText(sql)}
              />
            ))}
          </div>
          
          {totalPages > 1 && (
            <div className="pagination">
              {queryStats.page > 1 && (
                <button
                  onClick={() => handlePageChange(queryStats.page - 1)}
                  disabled={isLoading}
                >
                  ← Previous
                </button>
              )}
              
              <span className="page-info">
                Page {queryStats.page} of {totalPages}
              </span>
              
              {queryStats.page < totalPages && (
                <button
                  onClick={() => handlePageChange(queryStats.page + 1)}
                  disabled={isLoading}
                >
                  Next →
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SearchPage;