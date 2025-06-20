-- Current Stock Levels and Reorder Analysis
-- Identifies products that need restocking based on current inventory and sales velocity

WITH sales_velocity AS (
    SELECT 
        product_id,
        AVG(daily_sales) as avg_daily_sales,
        STDDEV(daily_sales) as sales_stddev
    FROM (
        SELECT 
            product_id,
            DATE(order_date) as sale_date,
            SUM(quantity) as daily_sales
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY product_id, DATE(order_date)
    ) daily_totals
    GROUP BY product_id
),
current_inventory AS (
    SELECT 
        i.product_id,
        p.product_name,
        p.sku,
        i.current_stock,
        i.reserved_stock,
        i.available_stock,
        i.reorder_point,
        i.max_stock_level,
        p.unit_cost,
        pc.category_name
    FROM inventory i
    JOIN products p ON i.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
)
SELECT 
    ci.product_id,
    ci.product_name,
    ci.sku,
    ci.category_name,
    ci.current_stock,
    ci.available_stock,
    ci.reorder_point,
    ci.max_stock_level,
    COALESCE(sv.avg_daily_sales, 0) as avg_daily_sales,
    CASE 
        WHEN sv.avg_daily_sales > 0 THEN ci.available_stock / sv.avg_daily_sales
        ELSE NULL
    END as days_of_stock,
    CASE 
        WHEN ci.available_stock <= ci.reorder_point THEN 'REORDER_NOW'
        WHEN ci.available_stock <= ci.reorder_point * 1.2 THEN 'LOW_STOCK'
        WHEN ci.available_stock >= ci.max_stock_level * 0.9 THEN 'OVERSTOCK'
        ELSE 'NORMAL'
    END as stock_status,
    ci.unit_cost * ci.available_stock as inventory_value
FROM current_inventory ci
LEFT JOIN sales_velocity sv ON ci.product_id = sv.product_id
ORDER BY 
    CASE 
        WHEN ci.available_stock <= ci.reorder_point THEN 1
        WHEN ci.available_stock <= ci.reorder_point * 1.2 THEN 2
        ELSE 3
    END,
    ci.available_stock / NULLIF(sv.avg_daily_sales, 0) ASC; 