-- Daily Operations Dashboard
-- Real-time operational metrics for day-to-day business monitoring

WITH daily_summary AS (
    SELECT 
        CURRENT_DATE as report_date,
        COUNT(DISTINCT order_id) as todays_orders,
        COUNT(DISTINCT customer_id) as todays_customers,
        SUM(unit_price * quantity * (1 - discount_rate)) as todays_revenue,
        AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
        SUM(quantity) as total_units_sold
    FROM sales_transactions
    WHERE DATE(order_date) = CURRENT_DATE
),
hourly_trends AS (
    SELECT 
        EXTRACT(HOUR FROM order_date) as hour_of_day,
        COUNT(DISTINCT order_id) as hourly_orders,
        SUM(unit_price * quantity * (1 - discount_rate)) as hourly_revenue
    FROM sales_transactions
    WHERE DATE(order_date) = CURRENT_DATE
    GROUP BY EXTRACT(HOUR FROM order_date)
),
inventory_alerts AS (
    SELECT 
        p.product_name,
        p.sku,
        inv.current_stock,
        inv.reorder_level,
        CASE 
            WHEN inv.current_stock <= inv.reorder_level THEN 'CRITICAL'
            WHEN inv.current_stock <= inv.reorder_level * 1.5 THEN 'LOW'
            ELSE 'OK'
        END as stock_status
    FROM products p
    JOIN (
        SELECT 
            product_id,
            current_stock,
            reorder_level
        FROM inventory_snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
    ) inv ON p.product_id = inv.product_id
    WHERE inv.current_stock <= inv.reorder_level * 1.5
),
payment_methods AS (
    SELECT 
        payment_method,
        COUNT(*) as transaction_count,
        SUM(unit_price * quantity * (1 - discount_rate)) as method_revenue
    FROM sales_transactions st
    JOIN orders o ON st.order_id = o.order_id
    WHERE DATE(st.order_date) = CURRENT_DATE
    GROUP BY payment_method
)
SELECT 
    'DAILY_SUMMARY' as metric_type,
    CAST(ds.report_date AS VARCHAR) as metric_name,
    ds.todays_orders as metric_value,
    'orders' as metric_unit,
    NULL as additional_info
FROM daily_summary ds

UNION ALL

SELECT 
    'DAILY_SUMMARY' as metric_type,
    'Revenue' as metric_name,
    ds.todays_revenue as metric_value,
    'currency' as metric_unit,
    NULL as additional_info
FROM daily_summary ds

UNION ALL

SELECT 
    'HOURLY_TREND' as metric_type,
    CONCAT('Hour_', ht.hour_of_day) as metric_name,
    ht.hourly_orders as metric_value,
    'orders' as metric_unit,
    CAST(ht.hourly_revenue AS VARCHAR) as additional_info
FROM hourly_trends ht

UNION ALL

SELECT 
    'INVENTORY_ALERT' as metric_type,
    ia.product_name as metric_name,
    ia.current_stock as metric_value,
    'units' as metric_unit,
    ia.stock_status as additional_info
FROM inventory_alerts ia

UNION ALL

SELECT 
    'PAYMENT_METHOD' as metric_type,
    pm.payment_method as metric_name,
    pm.transaction_count as metric_value,
    'transactions' as metric_unit,
    CAST(pm.method_revenue AS VARCHAR) as additional_info
FROM payment_methods pm
ORDER BY metric_type, metric_name;