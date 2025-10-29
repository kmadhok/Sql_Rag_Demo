import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { QueryItem, DatabaseSchema } from '../types/api';
import { dataService } from '../services/dataService';

interface DataState {
  schema: DatabaseSchema | null;
  queries: QueryItem[];
  analytics: any;
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  filters: {
    search: string;
    tables: string[];
    hasJoins: boolean | null;
  };
}

const initialState: DataState = {
  schema: null,
  queries: [],
  analytics: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0
  },
  filters: {
    search: '',
    tables: [],
    hasJoins: null
  }
};

// Async thunks
export const fetchSchema = createAsyncThunk(
  'data/fetchSchema',
  async () => {
    const response = await dataService.getDatabaseSchema();
    return response;
  }
);

export const fetchQueries = createAsyncThunk(
  'data/fetchQueries',
  async (params: { search?: string; limit?: number }) => {
    const response = await dataService.getQueries(params);
    return response;
  }
);

export const executeQuery = createAsyncThunk(
  'data/executeQuery',
  async (params: { sql: string; dryRun?: boolean }) => {
    const response = await dataService.executeQuery(params);
    return response;
  }
);

const dataSlice = createSlice({
  name: 'data',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<Partial<DataState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setPagination: (state, action: PayloadAction<Partial<DataState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    // fetchSchema
    builder
      .addCase(fetchSchema.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchSchema.fulfilled, (state, action) => {
        state.isLoading = false;
        state.schema = action.payload;
      })
      .addCase(fetchSchema.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch schema';
      });
    
    // fetchQueries
    builder
      .addCase(fetchQueries.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchQueries.fulfilled, (state, action) => {
        state.isLoading = false;
        state.queries = action.payload.queries;
        state.pagination.total = action.payload.count;
      })
      .addCase(fetchQueries.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch queries';
      });
    
    // executeQuery
    builder
      .addCase(executeQuery.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(executeQuery.fulfilled, (state, action) => {
        state.isLoading = false;
        // Handle query results if needed
      })
      .addCase(executeQuery.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to execute query';
      });
  }
});

export const { setFilters, setPagination, clearError } = dataSlice.actions;
export default dataSlice.reducer;