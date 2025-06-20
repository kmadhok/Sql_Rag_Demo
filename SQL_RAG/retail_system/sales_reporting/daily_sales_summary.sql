-- Daily Sales Summary Report
-- Aggregates sales data by date, store, and product category

SELECT 
    DATE(order_date) as sale_date,
    store_id,
    category_name,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT customer_id) as unique_customers,
    SUM(quantity) as total_items_sold,
    SUM(unit_price * quantity) as gross_revenue,
    SUM(unit_price * quantity * discount_rate) as total_discounts,
    SUM(unit_price * quantity * (1 - discount_rate)) as net_revenue,
    AVG(unit_price * quantity) as avg_order_value
FROM sales_transactions st
JOIN products p ON st.product_id = p.product_id
JOIN product_categories pc ON p.category_id = pc.category_id
JOIN stores s ON st.store_id = s.store_id
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(order_date), store_id, category_name
ORDER BY sale_date DESC, net_revenue DESC; 