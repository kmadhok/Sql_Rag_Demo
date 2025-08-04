-- Executive Revenue Breakdown Analysis
-- Detailed revenue analysis by various dimensions for executive reporting

WITH revenue_by_category AS (
    SELECT 
        pc.category_name,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as category_revenue,
        COUNT(DISTINCT st.order_id) as category_orders,
        COUNT(DISTINCT st.customer_id) as category_customers,
        AVG(st.unit_price * st.quantity * (1 - st.discount_rate)) as avg_transaction_value
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY pc.category_name
),
revenue_by_customer_segment AS (
    SELECT 
        CASE 
            WHEN customer_total_spent >= 1000 THEN 'VIP'
            WHEN customer_total_spent >= 500 THEN 'Premium'
            WHEN customer_total_spent >= 200 THEN 'Regular'
            ELSE 'New'
        END as customer_segment,
        SUM(customer_total_spent) as segment_revenue,
        COUNT(*) as customers_in_segment,
        AVG(customer_total_spent) as avg_customer_value
    FROM (
        SELECT 
            customer_id,
            SUM(unit_price * quantity * (1 - discount_rate)) as customer_total_spent
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY customer_id
    ) customer_spending
    GROUP BY 
        CASE 
            WHEN customer_total_spent >= 1000 THEN 'VIP'
            WHEN customer_total_spent >= 500 THEN 'Premium'
            WHEN customer_total_spent >= 200 THEN 'Regular'
            ELSE 'New'
        END
),
total_revenue AS (
    SELECT SUM(unit_price * quantity * (1 - discount_rate)) as total_company_revenue
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT 
    'CATEGORY' as breakdown_type,
    category_name as breakdown_value,
    ROUND(category_revenue, 2) as revenue,
    ROUND((category_revenue / tr.total_company_revenue) * 100, 2) as revenue_percentage,
    category_orders as transaction_count,
    category_customers as unique_customers,
    ROUND(avg_transaction_value, 2) as avg_transaction_value
FROM revenue_by_category rbc
CROSS JOIN total_revenue tr

UNION ALL

SELECT 
    'CUSTOMER_SEGMENT' as breakdown_type,
    customer_segment as breakdown_value,
    ROUND(segment_revenue, 2) as revenue,
    ROUND((segment_revenue / tr.total_company_revenue) * 100, 2) as revenue_percentage,
    NULL as transaction_count,
    customers_in_segment as unique_customers,
    ROUND(avg_customer_value, 2) as avg_transaction_value
FROM revenue_by_customer_segment rbcs
CROSS JOIN total_revenue tr
ORDER BY breakdown_type, revenue DESC;