"""
Data Transformation Queries Module
ETL transformation logic for data warehouse processing
"""

def get_customer_dimension_transform():
    """Returns SQL to transform raw customer data into dimension table format"""
    return """
    WITH customer_enrichment AS (
        SELECT 
            c.customer_id,
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            c.registration_date,
            c.date_of_birth,
            EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM c.date_of_birth) as age,
            CASE 
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM c.date_of_birth) < 25 THEN 'Gen Z'
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM c.date_of_birth) < 40 THEN 'Millennial'
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM c.date_of_birth) < 55 THEN 'Gen X'
                ELSE 'Boomer'
            END as generation_segment,
            ca.address_line1,
            ca.city,
            ca.state,
            ca.postal_code,
            ca.country,
            -- Derived metrics from transaction history
            COALESCE(stats.total_orders, 0) as lifetime_orders,
            COALESCE(stats.total_spent, 0) as lifetime_value,
            COALESCE(stats.avg_order_value, 0) as avg_order_value,
            COALESCE(stats.first_order_date, c.registration_date) as first_order_date,
            stats.last_order_date,
            CASE 
                WHEN stats.last_order_date IS NULL THEN 'NEVER_PURCHASED'
                WHEN stats.last_order_date >= CURRENT_DATE - INTERVAL '30 days' THEN 'ACTIVE'
                WHEN stats.last_order_date >= CURRENT_DATE - INTERVAL '90 days' THEN 'RECENT'
                WHEN stats.last_order_date >= CURRENT_DATE - INTERVAL '365 days' THEN 'LAPSED'
                ELSE 'INACTIVE'
            END as customer_status,
            CURRENT_TIMESTAMP as last_updated
        FROM customers c
        LEFT JOIN customer_addresses ca ON c.customer_id = ca.customer_id 
            AND ca.is_primary = true
        LEFT JOIN (
            SELECT 
                customer_id,
                COUNT(DISTINCT order_id) as total_orders,
                SUM(unit_price * quantity * (1 - discount_rate)) as total_spent,
                AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
                MIN(order_date) as first_order_date,
                MAX(order_date) as last_order_date
            FROM sales_transactions
            GROUP BY customer_id
        ) stats ON c.customer_id = stats.customer_id
    )
    SELECT 
        customer_id,
        first_name,
        last_name,
        email,
        phone,
        registration_date,
        age,
        generation_segment,
        city,
        state,
        country,
        lifetime_orders,
        ROUND(lifetime_value, 2) as lifetime_value,
        ROUND(avg_order_value, 2) as avg_order_value,
        first_order_date,
        last_order_date,
        customer_status,
        last_updated
    FROM customer_enrichment;
    """

def get_product_dimension_transform():
    """Returns SQL to create enriched product dimension with performance metrics"""
    return """
    WITH product_performance AS (
        SELECT 
            p.product_id,
            COUNT(DISTINCT st.order_id) as total_orders,
            SUM(st.quantity) as total_units_sold,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as total_revenue,
            AVG(st.unit_price * st.quantity * (1 - st.discount_rate)) as avg_transaction_value,
            COUNT(DISTINCT st.customer_id) as unique_customers,
            AVG(st.discount_rate) as avg_discount_rate,
            MIN(st.order_date) as first_sale_date,
            MAX(st.order_date) as last_sale_date
        FROM products p
        LEFT JOIN sales_transactions st ON p.product_id = st.product_id
        WHERE st.order_date >= CURRENT_DATE - INTERVAL '365 days' OR st.order_date IS NULL
        GROUP BY p.product_id
    ),
    inventory_metrics AS (
        SELECT 
            product_id,
            current_stock,
            reorder_level,
            reorder_quantity,
            CASE 
                WHEN current_stock <= reorder_level THEN 'LOW_STOCK'
                WHEN current_stock <= reorder_level * 2 THEN 'NORMAL'
                ELSE 'OVERSTOCKED'
            END as stock_status
        FROM inventory_snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
    )
    SELECT 
        p.product_id,
        p.product_name,
        p.sku,
        p.unit_cost,
        p.unit_price,
        ROUND((p.unit_price - p.unit_cost) / p.unit_price * 100, 2) as margin_pct,
        pc.category_name,
        pc.category_id,
        s.supplier_name,
        s.supplier_id,
        COALESCE(pp.total_orders, 0) as orders_last_year,
        COALESCE(pp.total_units_sold, 0) as units_sold_last_year,
        COALESCE(pp.total_revenue, 0) as revenue_last_year,
        COALESCE(pp.unique_customers, 0) as customers_last_year,
        COALESCE(pp.avg_discount_rate, 0) as avg_discount_rate,
        im.current_stock,
        im.stock_status,
        CASE 
            WHEN pp.total_units_sold = 0 THEN 'NO_SALES'
            WHEN pp.total_units_sold <= 10 THEN 'SLOW_MOVING'
            WHEN pp.total_units_sold <= 100 THEN 'MODERATE'
            ELSE 'FAST_MOVING'
        END as velocity_category,
        pp.first_sale_date,
        pp.last_sale_date,
        CURRENT_TIMESTAMP as last_updated
    FROM products p
    JOIN product_categories pc ON p.category_id = pc.category_id
    LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
    LEFT JOIN product_performance pp ON p.product_id = pp.product_id
    LEFT JOIN inventory_metrics im ON p.product_id = im.product_id;
    """

def get_sales_fact_transform():
    """Returns SQL to create sales fact table with all necessary foreign keys and measures"""
    return """
    SELECT 
        st.order_id,
        st.customer_id,
        st.product_id,
        DATE(st.order_date) as order_date_key,
        EXTRACT(YEAR FROM st.order_date) as year,
        EXTRACT(QUARTER FROM st.order_date) as quarter,
        EXTRACT(MONTH FROM st.order_date) as month,
        EXTRACT(DOW FROM st.order_date) as day_of_week,
        st.quantity,
        st.unit_price,
        st.discount_rate,
        st.unit_price * st.quantity as gross_amount,
        st.unit_price * st.quantity * st.discount_rate as discount_amount,
        st.unit_price * st.quantity * (1 - st.discount_rate) as net_amount,
        p.unit_cost * st.quantity as cost_amount,
        (st.unit_price * st.quantity * (1 - st.discount_rate)) - (p.unit_cost * st.quantity) as profit_amount,
        CASE 
            WHEN st.unit_price * st.quantity > 0 THEN
                ((st.unit_price * st.quantity * (1 - st.discount_rate)) - (p.unit_cost * st.quantity)) / 
                (st.unit_price * st.quantity * (1 - st.discount_rate)) * 100
            ELSE 0
        END as profit_margin_pct,
        o.payment_method,
        o.shipping_method,
        o.order_status,
        CURRENT_TIMESTAMP as etl_created_at
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN orders o ON st.order_id = o.order_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '2 years';
    """