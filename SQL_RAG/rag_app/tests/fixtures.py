"""
Test fixtures and sample data for SQL RAG testing
"""
import pandas as pd
from typing import List, Dict, Any
from unittest.mock import Mock
import json


class TestDataFixtures:
    """Collection of test data fixtures for different testing scenarios"""
    
    @staticmethod
    def create_minimal_query_data() -> pd.DataFrame:
        """Create minimal query data for basic testing"""
        return pd.DataFrame({
            'query': [
                'SELECT * FROM customers',
                'SELECT * FROM orders'
            ],
            'description': [
                'Get all customers',
                'Get all orders'
            ]
        })
    
    @staticmethod
    def create_basic_query_data() -> pd.DataFrame:
        """Create basic query data with tables and joins"""
        return pd.DataFrame({
            'query': [
                'SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id',
                'SELECT p.name, c.category FROM products p JOIN categories c ON p.category_id = c.id',
                'SELECT * FROM customers WHERE city = "New York"',
                'SELECT o.id, c.name, p.name FROM orders o JOIN customers c ON o.customer_id = c.id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id',
                'UPDATE customers SET last_login = NOW() WHERE id = ?'
            ],
            'description': [
                'Count orders per customer',
                'Get product names with categories',
                'Find customers in New York',
                'Complex join across multiple tables',
                'Update customer last login'
            ],
            'tables': [
                'orders',
                'products,categories',
                'customers',
                'orders,customers,order_items,products',
                'customers'
            ],
            'joins': [
                '',
                'products.category_id = categories.id',
                '',
                'orders.customer_id = customers.id,orders.id = order_items.order_id,order_items.product_id = products.id',
                ''
            ]
        })
    
    @staticmethod
    def create_parsed_query_data() -> pd.DataFrame:
        """Create query data with pre-parsed tables and joins"""
        return pd.DataFrame({
            'query': [
                'SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id',
                'SELECT p.name, c.category FROM products p JOIN categories c ON p.category_id = c.id',
                'SELECT o.id, c.name FROM orders o LEFT JOIN customers c ON o.customer_id = c.id'
            ],
            'description': [
                'Calculate total order amount per customer',
                'Get product names with categories using JOIN',
                'Get orders with optional customer names'
            ],
            'tables': [
                'orders',
                'products,categories',
                'orders,customers'
            ],
            'joins': [
                '',
                'products.category_id = categories.id',
                'orders.customer_id = customers.id'
            ],
            'tables_parsed': [
                ['orders'],
                ['products', 'categories'],
                ['orders', 'customers']
            ],
            'joins_parsed': [
                [],
                [
                    {
                        'left_table': 'products',
                        'right_table': 'categories',
                        'left_column': 'category_id',
                        'right_column': 'id',
                        'join_type': 'INNER JOIN',
                        'condition': 'products.category_id = categories.id'
                    }
                ],
                [
                    {
                        'left_table': 'orders',
                        'right_table': 'customers',
                        'left_column': 'customer_id',
                        'right_column': 'id',
                        'join_type': 'LEFT JOIN',
                        'condition': 'orders.customer_id = customers.id'
                    }
                ]
            ]
        })
    
    @staticmethod
    def create_large_query_dataset(num_queries: int = 100) -> pd.DataFrame:
        """Create a large dataset for pagination testing"""
        data = {
            'query': [],
            'description': [],
            'tables': [],
            'joins': [],
            'tables_parsed': [],
            'joins_parsed': []
        }
        
        for i in range(num_queries):
            if i % 3 == 0:
                # Simple SELECT
                data['query'].append(f'SELECT * FROM table_{i}')
                data['description'].append(f'Get all data from table {i}')
                data['tables'].append(f'table_{i}')
                data['joins'].append('')
                data['tables_parsed'].append([f'table_{i}'])
                data['joins_parsed'].append([])
            elif i % 3 == 1:
                # JOIN query
                data['query'].append(f'SELECT a.*, b.* FROM table_{i} a JOIN table_{i+1} b ON a.id = b.table_{i}_id')
                data['description'].append(f'Join table {i} with table {i+1}')
                data['tables'].append(f'table_{i},table_{i+1}')
                data['joins'].append(f'table_{i}.id = table_{i+1}.table_{i}_id')
                data['tables_parsed'].append([f'table_{i}', f'table_{i+1}'])
                data['joins_parsed'].append([
                    {
                        'left_table': f'table_{i}',
                        'right_table': f'table_{i+1}',
                        'join_type': 'INNER JOIN'
                    }
                ])
            else:
                # Aggregation query
                data['query'].append(f'SELECT category, COUNT(*) FROM table_{i} GROUP BY category')
                data['description'].append(f'Count by category in table {i}')
                data['tables'].append(f'table_{i}')
                data['joins'].append('')
                data['tables_parsed'].append([f'table_{i}'])
                data['joins_parsed'].append([])
        
        return pd.DataFrame(data)
    
    @staticmethod
    def create_search_test_data() -> pd.DataFrame:
        """Create data specifically designed for search testing"""
        return pd.DataFrame({
            'query': [
                'SELECT customer_id, name FROM customers WHERE status = "active"',
                'SELECT product_id, price FROM products WHERE category = "electronics"',
                'SELECT order_id, total FROM orders WHERE customer_id = 123',
                'SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id',
                'SELECT p.name, COUNT(*) FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.name'
            ],
            'description': [
                'Find active customers',
                'Get electronics products',
                'Orders for specific customer',
                'Customer names with order totals',
                'Product popularity analysis'
            ],
            'tables': [
                'customers',
                'products',
                'orders',
                'customers,orders',
                'products,order_items'
            ],
            'joins': [
                '',
                '',
                '',
                'customers.id = orders.customer_id',
                'products.id = order_items.product_id'
            ],
            'tables_parsed': [
                ['customers'],
                ['products'],
                ['orders'],
                ['customers', 'orders'],
                ['products', 'order_items']
            ],
            'joins_parsed': [
                [],
                [],
                [],
                [{'left_table': 'customers', 'right_table': 'orders', 'join_type': 'INNER JOIN'}],
                [{'left_table': 'products', 'right_table': 'order_items', 'join_type': 'INNER JOIN'}]
            ]
        })


class MockDataFixtures:
    """Collection of mock objects for testing"""
    
    @staticmethod
    def create_mock_document(content: str, metadata: Dict[str, Any] = None):
        """Create a mock document object"""
        mock_doc = Mock()
        mock_doc.page_content = content
        mock_doc.metadata = metadata or {}
        return mock_doc
    
    @staticmethod
    def create_mock_documents_list(contents: List[str], metadatas: List[Dict] = None):
        """Create a list of mock documents"""
        if metadatas is None:
            metadatas = [{}] * len(contents)
        
        return [
            MockDataFixtures.create_mock_document(content, metadata)
            for content, metadata in zip(contents, metadatas)
        ]
    
    @staticmethod
    def create_mock_rag_response():
        """Create a mock RAG engine response"""
        answer = "This is a sample answer explaining how to calculate customer lifetime value using SQL."
        sources = MockDataFixtures.create_mock_documents_list([
            "SELECT customer_id, SUM(order_total) FROM orders GROUP BY customer_id",
            "SELECT AVG(order_value) FROM orders WHERE customer_id = ?",
            "WITH customer_metrics AS (SELECT customer_id, COUNT(*) as order_count FROM orders)"
        ], [
            {'source': 'customer_analysis.sql', 'description': 'Customer order totals'},
            {'source': 'customer_metrics.sql', 'description': 'Average order value'},
            {'source': 'advanced_analytics.sql', 'description': 'Customer metrics CTE'}
        ])
        token_usage = {
            'total_tokens': 250,
            'prompt_tokens': 180,
            'completion_tokens': 70,
            'retrieval_time': 0.45,
            'documents_processed': 3,
            'search_method': 'vector'
        }
        return answer, sources, token_usage
    
    @staticmethod
    def create_mock_token_usage(
        total: int = 150,
        prompt: int = 100,
        completion: int = 50,
        include_extras: bool = False
    ):
        """Create mock token usage data"""
        usage = {
            'total_tokens': total,
            'prompt_tokens': prompt,
            'completion_tokens': completion
        }
        
        if include_extras:
            usage.update({
                'retrieval_time': 0.35,
                'documents_processed': 4,
                'search_method': 'vector',
                'query_rewriting': {
                    'enabled': True,
                    'rewritten_query': 'Enhanced version of the original query',
                    'query_changed': True,
                    'confidence': 0.85,
                    'rewrite_time': 0.12,
                    'model_used': 'gemini-2.5-flash'
                },
                'schema_filtering': {
                    'enabled': True,
                    'relevant_tables': 3,
                    'schema_coverage': '3/15',
                    'schema_tokens': 450,
                    'total_schema_tables': 15,
                    'schema_available': True
                },
                'hybrid_search_breakdown': {
                    'hybrid': 2,
                    'vector': 1,
                    'keyword': 1
                },
                'search_weights': {
                    'vector_weight': 0.7,
                    'keyword_weight': 0.3
                }
            })
        
        return usage


class AnalyticsFixtures:
    """Collection of analytics data fixtures"""
    
    @staticmethod
    def create_comprehensive_analytics():
        """Create comprehensive analytics data for testing"""
        return {
            'total_queries': 150,
            'queries_with_descriptions': 145,
            'queries_with_tables': 140,
            'queries_with_joins': 85,
            'total_individual_joins': 180,
            'max_joins_per_query': 6,
            'join_count_distribution': {
                0: 65,  # No joins
                1: 35,  # 1 join
                2: 25,  # 2 joins
                3: 15,  # 3 joins
                4: 7,   # 4 joins
                5: 2,   # 5 joins
                6: 1    # 6 joins
            },
            'json_format_count': 120,
            'string_format_count': 60,
            'join_types': {
                'INNER JOIN': 85,
                'LEFT JOIN': 45,
                'RIGHT JOIN': 12,
                'FULL OUTER JOIN': 8,
                'CROSS JOIN': 3
            },
            'table_usage': {
                'customers': 65,
                'orders': 55,
                'products': 48,
                'order_items': 42,
                'categories': 35,
                'suppliers': 28,
                'inventory': 22,
                'reviews': 18,
                'payments': 15,
                'shipping': 12
            },
            'relationships': [
                {
                    'left_table': 'customers',
                    'right_table': 'orders',
                    'join_type': 'INNER JOIN',
                    'condition': 'customers.id = orders.customer_id',
                    'frequency': 45
                },
                {
                    'left_table': 'orders',
                    'right_table': 'order_items',
                    'join_type': 'INNER JOIN',
                    'condition': 'orders.id = order_items.order_id',
                    'frequency': 35
                },
                {
                    'left_table': 'products',
                    'right_table': 'categories',
                    'join_type': 'INNER JOIN',
                    'condition': 'products.category_id = categories.id',
                    'frequency': 30
                },
                {
                    'left_table': 'products',
                    'right_table': 'order_items',
                    'join_type': 'INNER JOIN',
                    'condition': 'products.id = order_items.product_id',
                    'frequency': 28
                },
                {
                    'left_table': 'customers',
                    'right_table': 'reviews',
                    'join_type': 'LEFT JOIN',
                    'condition': 'customers.id = reviews.customer_id',
                    'frequency': 18
                }
            ]
        }
    
    @staticmethod
    def create_minimal_analytics():
        """Create minimal analytics data for simple testing"""
        return {
            'total_queries': 5,
            'queries_with_descriptions': 4,
            'queries_with_tables': 5,
            'queries_with_joins': 2,
            'total_individual_joins': 3,
            'max_joins_per_query': 2,
            'join_count_distribution': {0: 3, 1: 1, 2: 1},
            'json_format_count': 2,
            'string_format_count': 1,
            'join_types': {'INNER JOIN': 2, 'LEFT JOIN': 1},
            'table_usage': {'customers': 3, 'orders': 2, 'products': 1},
            'relationships': [
                {
                    'left_table': 'customers',
                    'right_table': 'orders',
                    'join_type': 'INNER JOIN',
                    'condition': 'customers.id = orders.customer_id'
                }
            ]
        }
    
    @staticmethod
    def create_no_joins_analytics():
        """Create analytics data for dataset with no joins"""
        return {
            'total_queries': 10,
            'queries_with_descriptions': 8,
            'queries_with_tables': 10,
            'queries_with_joins': 0,
            'total_individual_joins': 0,
            'max_joins_per_query': 0,
            'join_count_distribution': {0: 10},
            'json_format_count': 0,
            'string_format_count': 0,
            'join_types': {},
            'table_usage': {'table1': 3, 'table2': 4, 'table3': 3},
            'relationships': []
        }


class ConfigurationFixtures:
    """Collection of configuration fixtures for testing"""
    
    @staticmethod
    def create_default_search_config():
        """Create default search configuration"""
        return {
            'selected_index': 'test_index',
            'k': 4,
            'gemini_mode': True,
            'schema_injection': True,
            'show_full_queries': False,
            'query_rewriting': False,
            'hybrid_search': False,
            'auto_adjust_weights': True,
            'search_weights': None
        }
    
    @staticmethod
    def create_advanced_search_config():
        """Create advanced search configuration with all features enabled"""
        return {
            'selected_index': 'advanced_index',
            'k': 8,
            'gemini_mode': True,
            'schema_injection': True,
            'show_full_queries': True,
            'query_rewriting': True,
            'hybrid_search': True,
            'auto_adjust_weights': False,
            'search_weights': {
                'vector_weight': 0.7,
                'keyword_weight': 0.3
            }
        }
    
    @staticmethod
    def create_minimal_search_config():
        """Create minimal search configuration"""
        return {
            'selected_index': 'minimal_index',
            'k': 2,
            'gemini_mode': False,
            'schema_injection': False,
            'show_full_queries': False,
            'query_rewriting': False,
            'hybrid_search': False,
            'auto_adjust_weights': False,
            'search_weights': None
        }


# Convenience functions for easy access to fixtures
def get_sample_query_data(data_type: str = 'basic') -> pd.DataFrame:
    """Get sample query data by type"""
    if data_type == 'minimal':
        return TestDataFixtures.create_minimal_query_data()
    elif data_type == 'basic':
        return TestDataFixtures.create_basic_query_data()
    elif data_type == 'parsed':
        return TestDataFixtures.create_parsed_query_data()
    elif data_type == 'search':
        return TestDataFixtures.create_search_test_data()
    else:
        return TestDataFixtures.create_basic_query_data()


def get_sample_analytics(analytics_type: str = 'comprehensive') -> Dict[str, Any]:
    """Get sample analytics data by type"""
    if analytics_type == 'minimal':
        return AnalyticsFixtures.create_minimal_analytics()
    elif analytics_type == 'no_joins':
        return AnalyticsFixtures.create_no_joins_analytics()
    else:
        return AnalyticsFixtures.create_comprehensive_analytics()


def get_mock_rag_response() -> tuple:
    """Get a complete mock RAG response"""
    return MockDataFixtures.create_mock_rag_response()


def get_search_config(config_type: str = 'default') -> Dict[str, Any]:
    """Get search configuration by type"""
    if config_type == 'advanced':
        return ConfigurationFixtures.create_advanced_search_config()
    elif config_type == 'minimal':
        return ConfigurationFixtures.create_minimal_search_config()
    else:
        return ConfigurationFixtures.create_default_search_config()