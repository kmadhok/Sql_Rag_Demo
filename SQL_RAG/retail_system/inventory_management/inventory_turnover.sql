-- Inventory Turnover Analysis
-- Calculates inventory turnover ratios and identifies slow-moving stock

WITH inventory_movements AS (
    SELECT 
        product_id,
        SUM(CASE WHEN movement_type = 'SALE' THEN -quantity ELSE quantity END) as net_movement,
        SUM(CASE WHEN movement_type = 'SALE' THEN quantity ELSE 0 END) as total_sold,
        COUNT(CASE WHEN movement_type = 'SALE' THEN 1 END) as sale_transactions
    FROM inventory_movements
    WHERE movement_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY product_id
),
average_inventory AS (
    SELECT 
        product_id,
        AVG(current_stock) as avg_stock_level
    FROM inventory_snapshots
    WHERE snapshot_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY product_id
),
cost_analysis AS (
    SELECT 
        st.product_id,
        SUM(st.quantity * p.unit_cost) as cogs_annual
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY st.product_id
)
SELECT 
    p.product_id,
    p.product_name,
    p.sku,
    pc.category_name,
    COALESCE(im.total_sold, 0) as units_sold_ytd,
    COALESCE(ai.avg_stock_level, 0) as avg_inventory_level,
    COALESCE(ca.cogs_annual, 0) as cogs_annual,
    p.unit_cost * COALESCE(ai.avg_stock_level, 0) as avg_inventory_value,
    CASE 
        WHEN ai.avg_stock_level > 0 AND ca.cogs_annual > 0 THEN 
            ca.cogs_annual / (p.unit_cost * ai.avg_stock_level)
        ELSE 0
    END as inventory_turnover_ratio,
    CASE 
        WHEN im.total_sold > 0 AND ai.avg_stock_level > 0 THEN
            365.0 / (ca.cogs_annual / (p.unit_cost * ai.avg_stock_level))
        ELSE NULL
    END as days_to_sell_inventory,
    CASE 
        WHEN COALESCE(im.total_sold, 0) = 0 THEN 'NO_SALES'
        WHEN ca.cogs_annual / (p.unit_cost * ai.avg_stock_level) < 2 THEN 'SLOW_MOVING'
        WHEN ca.cogs_annual / (p.unit_cost * ai.avg_stock_level) > 12 THEN 'FAST_MOVING'
        ELSE 'NORMAL'
    END as movement_category
FROM products p
JOIN product_categories pc ON p.category_id = pc.category_id
LEFT JOIN inventory_movements im ON p.product_id = im.product_id
LEFT JOIN average_inventory ai ON p.product_id = ai.product_id
LEFT JOIN cost_analysis ca ON p.product_id = ca.product_id
ORDER BY inventory_turnover_ratio DESC; 