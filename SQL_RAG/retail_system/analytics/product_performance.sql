-- Product Performance Analysis
-- Analyzes product sales performance across different dimensions

WITH product_metrics AS (
    SELECT 
        p.product_id,
        p.product_name,
        p.sku,
        p.unit_cost,
        pc.category_name,
        b.brand_name,
        COUNT(DISTINCT st.order_id) as order_count,
        SUM(st.quantity) as total_quantity_sold,
        SUM(st.unit_price * st.quantity) as gross_revenue,
        SUM(st.unit_price * st.quantity * st.discount_rate) as total_discounts,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_revenue,
        AVG(st.unit_price) as avg_selling_price,
        MAX(st.order_date) as last_sale_date,
        MIN(st.order_date) as first_sale_date
    FROM products p
    JOIN product_categories pc ON p.category_id = pc.category_id
    JOIN brands b ON p.brand_id = b.brand_id
    LEFT JOIN sales_transactions st ON p.product_id = st.product_id
        AND st.order_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY p.product_id, p.product_name, p.sku, p.unit_cost, pc.category_name, b.brand_name
),
category_totals AS (
    SELECT 
        category_name,
        SUM(net_revenue) as category_revenue,
        SUM(total_quantity_sold) as category_quantity
    FROM product_metrics
    GROUP BY category_name
),
performance_rankings AS (
    SELECT 
        pm.*,
        ct.category_revenue,
        pm.net_revenue / NULLIF(ct.category_revenue, 0) * 100 as category_revenue_share,
        pm.total_quantity_sold / NULLIF(ct.category_quantity, 0) * 100 as category_quantity_share,
        RANK() OVER (ORDER BY pm.net_revenue DESC) as revenue_rank,
        RANK() OVER (ORDER BY pm.total_quantity_sold DESC) as quantity_rank,
        RANK() OVER (PARTITION BY pm.category_name ORDER BY pm.net_revenue DESC) as category_revenue_rank
    FROM product_metrics pm
    JOIN category_totals ct ON pm.category_name = ct.category_name
)
SELECT 
    product_id,
    product_name,
    sku,
    category_name,
    brand_name,
    order_count,
    total_quantity_sold,
    net_revenue,
    avg_selling_price,
    unit_cost,
    ROUND((avg_selling_price - unit_cost) / NULLIF(avg_selling_price, 0) * 100, 2) as margin_percentage,
    ROUND(category_revenue_share, 2) as category_revenue_share_pct,
    revenue_rank,
    quantity_rank,
    category_revenue_rank,
    DATEDIFF(CURRENT_DATE, last_sale_date) as days_since_last_sale,
    CASE 
        WHEN total_quantity_sold = 0 THEN 'NO_SALES'
        WHEN revenue_rank <= 50 THEN 'TOP_PERFORMER'
        WHEN revenue_rank <= 200 THEN 'GOOD_PERFORMER'
        WHEN revenue_rank <= 500 THEN 'AVERAGE_PERFORMER'
        ELSE 'POOR_PERFORMER'
    END as performance_tier,
    CASE 
        WHEN DATEDIFF(CURRENT_DATE, last_sale_date) > 90 THEN 'STALE'
        WHEN DATEDIFF(CURRENT_DATE, last_sale_date) > 30 THEN 'SLOW_MOVING'
        ELSE 'ACTIVE'
    END as sales_velocity
FROM performance_rankings
ORDER BY net_revenue DESC; 