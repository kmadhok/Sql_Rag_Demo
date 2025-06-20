-- Customer Behavior Analysis
-- Comprehensive analysis of customer purchasing patterns and lifetime value

WITH customer_purchase_history AS (
    SELECT 
        customer_id,
        MIN(order_date) as first_purchase_date,
        MAX(order_date) as last_purchase_date,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT DATE(order_date)) as shopping_days,
        SUM(unit_price * quantity * (1 - discount_rate)) as total_spent,
        AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
        DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifespan_days
    FROM sales_transactions
    GROUP BY customer_id
),
customer_categories AS (
    SELECT 
        st.customer_id,
        pc.category_name,
        COUNT(DISTINCT st.order_id) as category_orders,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as category_spent
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    GROUP BY st.customer_id, pc.category_name
),
preferred_categories AS (
    SELECT 
        customer_id,
        category_name as preferred_category,
        category_spent,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY category_spent DESC) as category_rank
    FROM customer_categories
)
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.registration_date,
    cph.first_purchase_date,
    cph.last_purchase_date,
    cph.total_orders,
    cph.shopping_days,
    cph.total_spent,
    cph.avg_order_value,
    cph.customer_lifespan_days,
    CASE 
        WHEN cph.customer_lifespan_days > 0 THEN 
            cph.total_orders / (cph.customer_lifespan_days / 365.0)
        ELSE 0
    END as orders_per_year,
    pc.preferred_category,
    DATEDIFF(CURRENT_DATE, cph.last_purchase_date) as days_since_last_order,
    CASE 
        WHEN cph.total_spent >= 1000 AND cph.total_orders >= 10 THEN 'VIP'
        WHEN cph.total_spent >= 500 AND cph.total_orders >= 5 THEN 'GOLD'
        WHEN cph.total_spent >= 200 AND cph.total_orders >= 3 THEN 'SILVER'
        ELSE 'BRONZE'
    END as customer_tier,
    CASE 
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 365 THEN 'INACTIVE'
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 180 THEN 'AT_RISK'
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 90 THEN 'DORMANT'
        ELSE 'ACTIVE'
    END as customer_status
FROM customers c
JOIN customer_purchase_history cph ON c.customer_id = cph.customer_id
LEFT JOIN preferred_categories pc ON c.customer_id = pc.customer_id AND pc.category_rank = 1
ORDER BY cph.total_spent DESC; 