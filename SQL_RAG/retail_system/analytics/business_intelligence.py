"""
Business Intelligence Module
SQL queries for executive dashboards and KPI reporting
"""

def get_executive_dashboard_query():
    """Returns SQL query for high-level executive dashboard metrics"""
    return """
    WITH current_period AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_today,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_today,
            COUNT(DISTINCT customer_id) as customers_today
        FROM sales_transactions
        WHERE DATE(order_date) = CURRENT_DATE
    ),
    previous_period AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_yesterday,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_yesterday,
            COUNT(DISTINCT customer_id) as customers_yesterday
        FROM sales_transactions
        WHERE DATE(order_date) = CURRENT_DATE - INTERVAL '1 day'
    ),
    month_to_date AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_mtd,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_mtd,
            COUNT(DISTINCT customer_id) as customers_mtd,
            AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value_mtd
        FROM sales_transactions
        WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        AND EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE)
    ),
    year_to_date AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_ytd,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_ytd,
            COUNT(DISTINCT customer_id) as customers_ytd
        FROM sales_transactions
        WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    )
    SELECT 
        -- Today's metrics
        cp.orders_today,
        cp.revenue_today,
        cp.customers_today,
        
        -- Day-over-day changes
        ROUND(((cp.orders_today - pp.orders_yesterday) / NULLIF(pp.orders_yesterday, 0) * 100), 2) as orders_change_pct,
        ROUND(((cp.revenue_today - pp.revenue_yesterday) / NULLIF(pp.revenue_yesterday, 0) * 100), 2) as revenue_change_pct,
        
        -- Month to date
        mtd.orders_mtd,
        mtd.revenue_mtd,
        mtd.customers_mtd,
        mtd.avg_order_value_mtd,
        
        -- Year to date
        ytd.orders_ytd,
        ytd.revenue_ytd,
        ytd.customers_ytd,
        
        CURRENT_TIMESTAMP as report_generated_at
    FROM current_period cp
    CROSS JOIN previous_period pp
    CROSS JOIN month_to_date mtd
    CROSS JOIN year_to_date ytd;
    """

def get_conversion_funnel_query():
    """Returns SQL query for e-commerce conversion funnel analysis"""
    return """
    WITH funnel_metrics AS (
        SELECT 
            COUNT(DISTINCT session_id) as total_sessions,
            COUNT(DISTINCT CASE WHEN page_views > 1 THEN session_id END) as engaged_sessions,
            COUNT(DISTINCT CASE WHEN product_views > 0 THEN session_id END) as product_view_sessions,
            COUNT(DISTINCT CASE WHEN cart_additions > 0 THEN session_id END) as cart_addition_sessions,
            COUNT(DISTINCT CASE WHEN checkout_starts > 0 THEN session_id END) as checkout_start_sessions,
            COUNT(DISTINCT CASE WHEN orders > 0 THEN session_id END) as converted_sessions
        FROM (
            SELECT 
                w.session_id,
                COUNT(w.page_view_id) as page_views,
                COUNT(CASE WHEN w.event_type = 'product_view' THEN 1 END) as product_views,
                COUNT(CASE WHEN w.event_type = 'add_to_cart' THEN 1 END) as cart_additions,
                COUNT(CASE WHEN w.event_type = 'checkout_start' THEN 1 END) as checkout_starts,
                COUNT(DISTINCT o.order_id) as orders
            FROM website_events w
            LEFT JOIN orders o ON w.session_id = o.session_id
            WHERE w.event_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY w.session_id
        ) session_summary
    )
    SELECT 
        total_sessions,
        engaged_sessions,
        product_view_sessions,
        cart_addition_sessions,
        checkout_start_sessions,
        converted_sessions,
        
        -- Conversion rates at each step
        ROUND(engaged_sessions * 100.0 / NULLIF(total_sessions, 0), 2) as engagement_rate,
        ROUND(product_view_sessions * 100.0 / NULLIF(engaged_sessions, 0), 2) as product_view_rate,
        ROUND(cart_addition_sessions * 100.0 / NULLIF(product_view_sessions, 0), 2) as cart_addition_rate,
        ROUND(checkout_start_sessions * 100.0 / NULLIF(cart_addition_sessions, 0), 2) as checkout_start_rate,
        ROUND(converted_sessions * 100.0 / NULLIF(checkout_start_sessions, 0), 2) as checkout_completion_rate,
        ROUND(converted_sessions * 100.0 / NULLIF(total_sessions, 0), 2) as overall_conversion_rate
    FROM funnel_metrics;
    """

def get_cohort_analysis_query():
    """Returns SQL query for customer cohort retention analysis"""
    return """
    WITH customer_cohorts AS (
        SELECT 
            customer_id,
            DATE_TRUNC('month', MIN(order_date)) as cohort_month,
            MIN(order_date) as first_order_date
        FROM sales_transactions
        GROUP BY customer_id
    ),
    customer_activities AS (
        SELECT 
            cc.customer_id,
            cc.cohort_month,
            DATE_TRUNC('month', st.order_date) as activity_month,
            EXTRACT(EPOCH FROM (DATE_TRUNC('month', st.order_date) - cc.cohort_month)) / (30 * 24 * 60 * 60) as months_since_first_order
        FROM customer_cohorts cc
        JOIN sales_transactions st ON cc.customer_id = st.customer_id
    ),
    cohort_data AS (
        SELECT 
            cohort_month,
            months_since_first_order,
            COUNT(DISTINCT customer_id) as active_customers
        FROM customer_activities
        GROUP BY cohort_month, months_since_first_order
    ),
    cohort_sizes AS (
        SELECT 
            cohort_month,
            COUNT(DISTINCT customer_id) as cohort_size
        FROM customer_cohorts
        GROUP BY cohort_month
    )
    SELECT 
        cd.cohort_month,
        cs.cohort_size,
        cd.months_since_first_order,
        cd.active_customers,
        ROUND(cd.active_customers * 100.0 / cs.cohort_size, 2) as retention_rate
    FROM cohort_data cd
    JOIN cohort_sizes cs ON cd.cohort_month = cs.cohort_month
    WHERE cd.cohort_month >= CURRENT_DATE - INTERVAL '12 months'
    AND cd.months_since_first_order <= 12
    ORDER BY cd.cohort_month, cd.months_since_first_order;
    """

def get_profitability_analysis_query():
    """Returns SQL query for product and category profitability analysis"""
    return """
    WITH product_profitability AS (
        SELECT 
            p.product_id,
            p.product_name,
            pc.category_name,
            b.brand_name,
            p.unit_cost,
            AVG(st.unit_price) as avg_selling_price,
            SUM(st.quantity) as total_units_sold,
            SUM(st.unit_price * st.quantity) as gross_revenue,
            SUM(st.unit_price * st.quantity * st.discount_rate) as total_discounts,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_revenue,
            SUM(p.unit_cost * st.quantity) as total_cost,
            SUM((st.unit_price * (1 - st.discount_rate) - p.unit_cost) * st.quantity) as gross_profit
        FROM products p
        JOIN product_categories pc ON p.category_id = pc.category_id
        JOIN brands b ON p.brand_id = b.brand_id
        LEFT JOIN sales_transactions st ON p.product_id = st.product_id
            AND st.order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY p.product_id, p.product_name, pc.category_name, b.brand_name, p.unit_cost
        HAVING SUM(st.quantity) > 0
    )
    SELECT 
        product_id,
        product_name,
        category_name,
        brand_name,
        total_units_sold,
        net_revenue,
        total_cost,
        gross_profit,
        ROUND((avg_selling_price - unit_cost) / NULLIF(avg_selling_price, 0) * 100, 2) as margin_percentage,
        ROUND(gross_profit / NULLIF(net_revenue, 0) * 100, 2) as profit_margin_pct,
        ROUND(gross_profit / NULLIF(total_units_sold, 0), 2) as profit_per_unit,
        CASE 
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.3 THEN 'HIGH_MARGIN'
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.15 THEN 'MEDIUM_MARGIN'
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.05 THEN 'LOW_MARGIN'
            ELSE 'UNPROFITABLE'
        END as profitability_tier
    FROM product_profitability
    ORDER BY gross_profit DESC;
    """ 