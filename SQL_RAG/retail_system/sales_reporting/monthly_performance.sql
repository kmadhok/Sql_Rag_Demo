-- Monthly Sales Performance Analysis
-- Compares current month performance with previous months

WITH monthly_sales AS (
    SELECT 
        EXTRACT(YEAR FROM order_date) as sale_year,
        EXTRACT(MONTH FROM order_date) as sale_month,
        store_id,
        SUM(unit_price * quantity * (1 - discount_rate)) as monthly_revenue,
        COUNT(DISTINCT order_id) as monthly_orders,
        COUNT(DISTINCT customer_id) as monthly_customers
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date), store_id
),
performance_metrics AS (
    SELECT 
        *,
        LAG(monthly_revenue, 1) OVER (PARTITION BY store_id ORDER BY sale_year, sale_month) as prev_month_revenue,
        LAG(monthly_orders, 1) OVER (PARTITION BY store_id ORDER BY sale_year, sale_month) as prev_month_orders
    FROM monthly_sales
)
SELECT 
    sale_year,
    sale_month,
    store_id,
    monthly_revenue,
    monthly_orders,
    monthly_customers,
    ROUND(((monthly_revenue - prev_month_revenue) / prev_month_revenue * 100), 2) as revenue_growth_pct,
    ROUND(((monthly_orders - prev_month_orders) / prev_month_orders * 100), 2) as order_growth_pct,
    ROUND(monthly_revenue / monthly_orders, 2) as avg_order_value
FROM performance_metrics
WHERE prev_month_revenue IS NOT NULL
ORDER BY sale_year DESC, sale_month DESC, store_id; 