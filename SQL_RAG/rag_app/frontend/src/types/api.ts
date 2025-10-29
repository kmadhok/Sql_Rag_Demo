export interface QueryItem {
  id: string;
  title: string;
  description: string;
  sql: string;
  category: string;
  complexity: 'Easy' | 'Medium' | 'Hard';
  tags?: string[];
  usage_count?: number;
  last_used?: string;
  // Enhanced fields from original app
  tables?: string[];
  join_count?: number;
  has_aggregation?: boolean;
  has_subquery?: boolean;
  has_window_function?: boolean;
  execution_time?: number;
  created_at?: string;
  difficulty_score?: number;
  performance_rating?: number;
  author?: string;
  validated?: boolean;
  notes?: string;
  examples?: string[];
  related_queries?: string[];
}