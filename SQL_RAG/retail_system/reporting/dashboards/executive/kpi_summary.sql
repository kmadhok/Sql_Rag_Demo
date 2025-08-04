-- Executive KPI Summary Dashboard
-- High-level business metrics for executive decision making

WITH monthly_metrics AS (
    SELECT 
        DATE_TRUNC('month', order_date) as reporting_month,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT customer_id) as active_customers,
        SUM(unit_price * quantity * (1 - discount_rate)) as gross_revenue,
        SUM(unit_price * quantity * discount_rate) as total_discounts,
        AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
        COUNT(DISTINCT CASE WHEN customer_id IN (
            SELECT customer_id FROM sales_transactions st2 
            WHERE st2.order_date < DATE_TRUNC('month', st.order_date)
        ) THEN NULL ELSE customer_id END) as new_customers
    FROM sales_transactions st
    WHERE order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY DATE_TRUNC('month', order_date)
),
growth_calculations AS (
    SELECT 
        *,
        LAG(gross_revenue, 1) OVER (ORDER BY reporting_month) as prev_month_revenue,
        LAG(active_customers, 1) OVER (ORDER BY reporting_month) as prev_month_customers,
        LAG(avg_order_value, 1) OVER (ORDER BY reporting_month) as prev_month_aov
    FROM monthly_metrics
)
SELECT 
    reporting_month,
    total_orders,
    active_customers,
    new_customers,
    ROUND(gross_revenue, 2) as gross_revenue,
    ROUND(total_discounts, 2) as total_discounts,
    ROUND(avg_order_value, 2) as avg_order_value,
    ROUND(gross_revenue - total_discounts, 2) as net_revenue,
    CASE 
        WHEN prev_month_revenue > 0 THEN 
            ROUND(((gross_revenue - prev_month_revenue) / prev_month_revenue) * 100, 2)
        ELSE NULL 
    END as revenue_growth_pct,
    CASE 
        WHEN prev_month_customers > 0 THEN 
            ROUND(((active_customers - prev_month_customers) / prev_month_customers::FLOAT) * 100, 2)
        ELSE NULL 
    END as customer_growth_pct,
    CASE 
        WHEN prev_month_aov > 0 THEN 
            ROUND(((avg_order_value - prev_month_aov) / prev_month_aov) * 100, 2)
        ELSE NULL 
    END as aov_growth_pct,
    ROUND((new_customers::FLOAT / active_customers) * 100, 2) as new_customer_pct
FROM growth_calculations
ORDER BY reporting_month DESC;