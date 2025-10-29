import api from './api';
import { DatabaseSchema, TableSchema, QueryItem, ExecuteSQLRequest, ExecuteSQLResponse } from '../types/api';

export const dataService = {
  // Get database schema
  async getDatabaseSchema(): Promise<DatabaseSchema> {
    try {
      const response = await api.get<DatabaseSchema>('/data/schema');
      return response.data;
    } catch (error: any) {
      console.error('Error fetching database schema:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to fetch database schema'
      );
    }
  },

  // Get table schema
  async getTableSchema(tableName: string): Promise<TableSchema> {
    try {
      const response = await api.get<TableSchema>(`/data/tables/${tableName}`);
      return response.data;
    } catch (error: any) {
      console.error(`Error fetching table schema for ${tableName}:`, error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to fetch table schema'
      );
    }
  },

  // Get all table names
  async getTableNames(): Promise<{ tables: string[]; count: number }> {
    try {
      const response = await api.get('/data/tables');
      return response.data;
    } catch (error: any) {
      console.error('Error fetching table names:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to fetch table names'
      );
    }
  },

  // Get query catalog
  async getQueries(options?: {
    search?: string;
    limit?: number;
  }): Promise<{ queries: QueryItem[]; count: number }> {
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

  // Execute SQL query
  async executeQuery(request: ExecuteSQLRequest): Promise<ExecuteSQLResponse> {
    try {
      const response = await api.post<ExecuteSQLResponse>('/sql/execute', {
        sql: request.sql,
        dry_run: request.dryRun,
        session_id: request.sessionId
      });
      return response.data;
    } catch (error: any) {
      console.error('Error executing query:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to execute query'
      );
    }
  },

  // Search queries
  async searchQueries(
    search: string, 
    limit: number = 20
  ): Promise<{ queries: QueryItem[]; count: number }> {
    return this.getQueries({ search, limit });
  }
};