-- Advanced Customer Clustering Analysis
-- Multi-dimensional customer segmentation for targeted marketing

WITH customer_behavior_metrics AS (
    SELECT 
        customer_id,
        COUNT(DISTINCT order_id) as total_orders,
        SUM(unit_price * quantity * (1 - discount_rate)) as total_spent,
        AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
        DATEDIFF(CURRENT_DATE, MAX(order_date)) as days_since_last_order,
        DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifespan_days,
        COUNT(DISTINCT DATE_TRUNC('month', order_date)) as active_months,
        AVG(CASE WHEN discount_rate > 0 THEN discount_rate ELSE 0 END) as avg_discount_used,
        COUNT(DISTINCT p.category_id) as product_categories_purchased,
        MAX(CASE WHEN order_date >= CURRENT_DATE - INTERVAL '30 days' THEN 1 ELSE 0 END) as active_last_30_days
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    GROUP BY customer_id
    HAVING COUNT(DISTINCT order_id) >= 2  -- Only customers with multiple orders
),
customer_percentiles AS (
    SELECT 
        *,
        NTILE(5) OVER (ORDER BY total_spent DESC) as spending_quintile,
        NTILE(5) OVER (ORDER BY total_orders DESC) as frequency_quintile,
        NTILE(5) OVER (ORDER BY avg_order_value DESC) as aov_quintile,
        NTILE(5) OVER (ORDER BY days_since_last_order ASC) as recency_quintile,
        NTILE(3) OVER (ORDER BY product_categories_purchased DESC) as diversity_tertile
    FROM customer_behavior_metrics
),
cluster_assignments AS (
    SELECT 
        *,
        -- Behavioral clustering based on multiple dimensions
        CASE 
            -- High Value Loyal Customers
            WHEN spending_quintile = 5 AND frequency_quintile >= 4 AND recency_quintile >= 4 THEN 'CHAMPIONS'
            -- High spenders but less frequent
            WHEN spending_quintile = 5 AND frequency_quintile <= 2 THEN 'BIG_SPENDERS'
            -- Frequent buyers with moderate spending
            WHEN frequency_quintile = 5 AND spending_quintile >= 3 THEN 'LOYAL_CUSTOMERS'
            -- Recent high activity
            WHEN recency_quintile = 5 AND (spending_quintile >= 4 OR frequency_quintile >= 4) THEN 'NEW_CHAMPIONS'
            -- Moderate on all dimensions
            WHEN spending_quintile = 3 AND frequency_quintile = 3 AND recency_quintile = 3 THEN 'POTENTIAL_LOYALISTS'
            -- High recency but low other metrics
            WHEN recency_quintile >= 4 AND spending_quintile <= 2 AND frequency_quintile <= 2 THEN 'NEW_CUSTOMERS'
            -- Low recency but historically good
            WHEN recency_quintile <= 2 AND (spending_quintile >= 4 OR frequency_quintile >= 4) THEN 'AT_RISK'
            -- Low on most dimensions
            WHEN spending_quintile <= 2 AND frequency_quintile <= 2 AND recency_quintile <= 2 THEN 'HIBERNATING'
            -- Price conscious customers
            WHEN avg_discount_used > 0.1 AND frequency_quintile >= 3 THEN 'PRICE_SENSITIVE'
            -- High diversity, moderate other metrics
            WHEN diversity_tertile = 3 AND spending_quintile >= 3 THEN 'EXPLORERS'
            ELSE 'UNDEFINED'
        END as behavioral_cluster,
        
        -- Value-based clustering
        CASE 
            WHEN total_spent >= 2000 THEN 'HIGH_VALUE'
            WHEN total_spent >= 1000 THEN 'MEDIUM_VALUE'
            WHEN total_spent >= 300 THEN 'LOW_VALUE'
            ELSE 'MINIMAL_VALUE'
        END as value_segment,
        
        -- Engagement clustering
        CASE 
            WHEN active_last_30_days = 1 AND total_orders >= 10 THEN 'HIGHLY_ENGAGED'
            WHEN active_last_30_days = 1 AND total_orders >= 3 THEN 'ENGAGED'
            WHEN days_since_last_order <= 90 THEN 'MODERATELY_ENGAGED'
            WHEN days_since_last_order <= 180 THEN 'LIGHTLY_ENGAGED'
            ELSE 'DISENGAGED'
        END as engagement_level
    FROM customer_percentiles
)
SELECT 
    behavioral_cluster,
    value_segment,
    engagement_level,
    COUNT(*) as customer_count,
    ROUND(AVG(total_spent), 2) as avg_total_spent,
    ROUND(AVG(total_orders), 1) as avg_total_orders,
    ROUND(AVG(avg_order_value), 2) as avg_order_value,
    ROUND(AVG(days_since_last_order), 1) as avg_days_since_last_order,
    ROUND(AVG(customer_lifespan_days), 1) as avg_customer_lifespan_days,
    ROUND(AVG(product_categories_purchased), 1) as avg_categories_purchased,
    ROUND(AVG(avg_discount_used) * 100, 2) as avg_discount_pct,
    ROUND(SUM(total_spent), 2) as cluster_total_revenue,
    ROUND((SUM(total_spent) / (SELECT SUM(total_spent) FROM cluster_assignments)) * 100, 2) as revenue_contribution_pct
FROM cluster_assignments
GROUP BY behavioral_cluster, value_segment, engagement_level
ORDER BY cluster_total_revenue DESC;