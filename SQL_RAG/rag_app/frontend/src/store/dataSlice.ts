export const fetchQueries = createAsyncThunk(
  'data/fetchQueries',
  async (params: { 
    search?: string; 
    limit?: number;
    category?: string;
    complexity?: string;
    min_joins?: number;
    has_aggregation?: boolean;
    has_window_function?: boolean;
    has_subquery?: boolean;
  }) => {
    const response = await dataService.getQueries(params);
    return response;
  }
);