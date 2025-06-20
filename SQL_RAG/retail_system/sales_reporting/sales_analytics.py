"""
Sales Analytics Module
Contains SQL queries for various sales reporting and analytics tasks
"""

def get_top_selling_products_query(limit=10, days=30):
    """Returns SQL query to get top selling products"""
    return f"""
    SELECT 
        p.product_id,
        p.product_name,
        p.sku,
        pc.category_name,
        SUM(st.quantity) as total_quantity_sold,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as total_revenue,
        COUNT(DISTINCT st.order_id) as order_count,
        AVG(st.unit_price) as avg_selling_price
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '{days} days'
    GROUP BY p.product_id, p.product_name, p.sku, pc.category_name
    ORDER BY total_revenue DESC
    LIMIT {limit};
    """

def get_customer_segmentation_query():
    """Returns SQL query for RFM customer segmentation"""
    return """
    WITH customer_metrics AS (
        SELECT 
            customer_id,
            MAX(order_date) as last_order_date,
            COUNT(DISTINCT order_id) as frequency,
            SUM(unit_price * quantity * (1 - discount_rate)) as monetary_value,
            DATEDIFF(CURRENT_DATE, MAX(order_date)) as recency_days
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '365 days'
        GROUP BY customer_id
    ),
    rfm_scores AS (
        SELECT 
            customer_id,
            recency_days,
            frequency,
            monetary_value,
            NTILE(5) OVER (ORDER BY recency_days ASC) as recency_score,
            NTILE(5) OVER (ORDER BY frequency DESC) as frequency_score,
            NTILE(5) OVER (ORDER BY monetary_value DESC) as monetary_score
        FROM customer_metrics
    )
    SELECT 
        customer_id,
        recency_days,
        frequency,
        monetary_value,
        recency_score,
        frequency_score,
        monetary_score,
        CASE 
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
            WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Loyal Customers'
            WHEN recency_score >= 3 AND frequency_score <= 2 THEN 'Potential Loyalists'
            WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk'
            WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Lost Customers'
            ELSE 'New Customers'
        END as customer_segment
    FROM rfm_scores
    ORDER BY monetary_value DESC;
    """

def get_sales_trend_analysis_query():
    """Returns SQL query for sales trend analysis"""
    return """
    SELECT 
        DATE_TRUNC('week', order_date) as week_start,
        COUNT(DISTINCT order_id) as weekly_orders,
        SUM(unit_price * quantity * (1 - discount_rate)) as weekly_revenue,
        COUNT(DISTINCT customer_id) as weekly_customers,
        AVG(unit_price * quantity) as avg_order_value,
        LAG(SUM(unit_price * quantity * (1 - discount_rate)), 1) 
            OVER (ORDER BY DATE_TRUNC('week', order_date)) as prev_week_revenue
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '12 weeks'
    GROUP BY DATE_TRUNC('week', order_date)
    ORDER BY week_start DESC;
    """ 