  // Get query catalog
  async getQueries(options?: {
    search?: string;
    limit?: number;
    category?: string;
    complexity?: string;
    min_joins?: number;
    has_aggregation?: boolean;
    has_window_function?: boolean;
    has_subquery?: boolean;
  }): Promise<{ queries: QueryItem[]; count: number; total_count: number }> {
    try {
      const response = await api.get('/data/queries', {
        params: options
      });
      return response.data;
    } catch (error: any) {
      console.error('Error fetching queries:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to fetch queries'
      );
    }
  },