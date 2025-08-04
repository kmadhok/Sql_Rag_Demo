"""
Internal Service API Queries Module
SQL queries for internal microservices and API endpoints
"""

def get_user_authentication_query(user_id):
    """Returns SQL query to validate user authentication and permissions"""
    return f"""
    WITH user_session_data AS (
        SELECT 
            u.user_id,
            u.username,
            u.email,
            u.role,
            u.is_active,
            u.last_login,
            u.created_at,
            us.session_id,
            us.session_token,
            us.expires_at,
            us.ip_address,
            us.user_agent,
            CASE 
                WHEN us.expires_at > CURRENT_TIMESTAMP THEN 'ACTIVE'
                WHEN us.expires_at <= CURRENT_TIMESTAMP THEN 'EXPIRED'
                ELSE 'NO_SESSION'
            END as session_status
        FROM users u
        LEFT JOIN user_sessions us ON u.user_id = us.user_id
            AND us.expires_at > CURRENT_TIMESTAMP
        WHERE u.user_id = '{user_id}'
    ),
    user_permissions AS (
        SELECT 
            usd.user_id,
            array_agg(DISTINCT p.permission_name) as permissions,
            array_agg(DISTINCT r.role_name) as roles
        FROM user_session_data usd
        LEFT JOIN user_roles ur ON usd.user_id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.role_id
        LEFT JOIN role_permissions rp ON r.role_id = rp.role_id
        LEFT JOIN permissions p ON rp.permission_id = p.permission_id
        WHERE usd.user_id IS NOT NULL
        GROUP BY usd.user_id
    )
    SELECT 
        usd.user_id,
        usd.username,
        usd.email,
        usd.role,
        usd.is_active,
        usd.session_status,
        usd.session_id,
        usd.expires_at,
        up.permissions,
        up.roles,
        CASE 
            WHEN NOT usd.is_active THEN 'USER_INACTIVE'
            WHEN usd.session_status = 'EXPIRED' THEN 'SESSION_EXPIRED'
            WHEN usd.session_status = 'NO_SESSION' THEN 'NO_ACTIVE_SESSION'
            WHEN usd.session_status = 'ACTIVE' THEN 'AUTHENTICATED'
            ELSE 'UNKNOWN_STATUS'
        END as auth_status,
        CURRENT_TIMESTAMP as check_timestamp
    FROM user_session_data usd
    LEFT JOIN user_permissions up ON usd.user_id = up.user_id;
    """

def get_order_processing_service_query(order_status_filter=None):
    """Returns SQL query for order processing service API endpoints"""
    status_condition = f"AND o.order_status = '{order_status_filter}'" if order_status_filter else ""
    
    return f"""
    WITH order_details AS (
        SELECT 
            o.order_id,
            o.customer_id,
            c.first_name,
            c.last_name,
            c.email,
            o.order_date,
            o.order_status,
            o.payment_method,
            o.shipping_method,
            o.shipping_address,
            o.billing_address,
            COUNT(st.product_id) as total_items,
            SUM(st.quantity) as total_quantity,
            SUM(st.unit_price * st.quantity) as gross_amount,
            SUM(st.unit_price * st.quantity * st.discount_rate) as total_discount,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN sales_transactions st ON o.order_id = st.order_id
        WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days'
        {status_condition}
        GROUP BY 
            o.order_id, o.customer_id, c.first_name, c.last_name, c.email,
            o.order_date, o.order_status, o.payment_method, o.shipping_method,
            o.shipping_address, o.billing_address
    ),
    order_processing_status AS (
        SELECT 
            od.*,
            CASE 
                WHEN od.order_status = 'PENDING' THEN 'Awaiting payment confirmation'
                WHEN od.order_status = 'CONFIRMED' THEN 'Order confirmed, preparing for shipment'
                WHEN od.order_status = 'PROCESSING' THEN 'Items being picked and packed'
                WHEN od.order_status = 'SHIPPED' THEN 'Order shipped, tracking available'
                WHEN od.order_status = 'DELIVERED' THEN 'Order successfully delivered'
                WHEN od.order_status = 'CANCELLED' THEN 'Order has been cancelled'
                WHEN od.order_status = 'RETURNED' THEN 'Order returned by customer'
                ELSE 'Unknown status'
            END as status_description,
            CASE 
                WHEN od.order_status IN ('PENDING', 'CONFIRMED') THEN 'ACTIONABLE'
                WHEN od.order_status IN ('PROCESSING', 'SHIPPED') THEN 'IN_PROGRESS'
                WHEN od.order_status IN ('DELIVERED', 'CANCELLED', 'RETURNED') THEN 'COMPLETED'
                ELSE 'UNKNOWN'
            END as processing_category,
            -- Calculate estimated processing time
            CASE 
                WHEN od.order_status = 'PENDING' THEN CURRENT_TIMESTAMP + INTERVAL '2 hours'
                WHEN od.order_status = 'CONFIRMED' THEN CURRENT_TIMESTAMP + INTERVAL '1 day'
                WHEN od.order_status = 'PROCESSING' THEN CURRENT_TIMESTAMP + INTERVAL '2 days'
                ELSE NULL
            END as estimated_next_update
        FROM order_details od
    )
    SELECT 
        order_id,
        customer_id,
        CONCAT(first_name, ' ', last_name) as customer_name,
        email as customer_email,
        order_date,
        order_status,
        status_description,
        processing_category,
        payment_method,
        shipping_method,
        total_items,
        total_quantity,
        ROUND(gross_amount, 2) as gross_amount,
        ROUND(total_discount, 2) as total_discount,
        ROUND(net_amount, 2) as net_amount,
        estimated_next_update,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - order_date)) / 3600 as hours_since_order,
        -- API response formatting
        json_build_object(
            'orderId', order_id,
            'customerId', customer_id,
            'status', order_status,
            'totalAmount', ROUND(net_amount, 2),
            'itemCount', total_items,
            'orderDate', order_date,
            'estimatedUpdate', estimated_next_update
        ) as api_response_json
    FROM order_processing_status
    ORDER BY 
        CASE processing_category
            WHEN 'ACTIONABLE' THEN 1
            WHEN 'IN_PROGRESS' THEN 2
            ELSE 3
        END,
        order_date DESC;
    """

def get_inventory_service_query(product_id=None):
    """Returns SQL query for inventory management service endpoints"""
    product_filter = f"AND p.product_id = '{product_id}'" if product_id else ""
    
    return f"""
    WITH current_inventory AS (
        SELECT 
            product_id,
            current_stock,
            reorder_level,
            reorder_quantity,
            last_restocked_date,
            snapshot_date
        FROM inventory_snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
    ),
    recent_movements AS (
        SELECT 
            product_id,
            SUM(CASE WHEN movement_type = 'SALE' THEN -quantity ELSE quantity END) as net_movement_7d,
            SUM(CASE WHEN movement_type = 'SALE' THEN quantity ELSE 0 END) as units_sold_7d,
            SUM(CASE WHEN movement_type = 'RESTOCK' THEN quantity ELSE 0 END) as units_restocked_7d,
            COUNT(CASE WHEN movement_type = 'SALE' THEN 1 END) as sale_transactions_7d
        FROM inventory_movements
        WHERE movement_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY product_id
    ),
    inventory_status AS (
        SELECT 
            p.product_id,
            p.product_name,
            p.sku,
            pc.category_name,
            p.unit_price,
            ci.current_stock,
            ci.reorder_level,
            ci.reorder_quantity,
            COALESCE(rm.units_sold_7d, 0) as units_sold_last_7_days,
            COALESCE(rm.units_restocked_7d, 0) as units_restocked_last_7_days,
            COALESCE(rm.sale_transactions_7d, 0) as transactions_last_7_days,
            CASE 
                WHEN ci.current_stock <= 0 THEN 'OUT_OF_STOCK'
                WHEN ci.current_stock <= ci.reorder_level THEN 'LOW_STOCK'
                WHEN ci.current_stock <= ci.reorder_level * 2 THEN 'NORMAL'
                ELSE 'OVERSTOCKED'
            END as stock_status,
            CASE 
                WHEN ci.current_stock <= 0 THEN 'CRITICAL'
                WHEN ci.current_stock <= ci.reorder_level THEN 'HIGH'
                WHEN ci.current_stock <= ci.reorder_level * 1.5 THEN 'MEDIUM'
                ELSE 'LOW'
            END as reorder_priority,
            -- Calculate days of inventory remaining
            CASE 
                WHEN COALESCE(rm.units_sold_7d, 0) > 0 THEN
                    ROUND(ci.current_stock / (rm.units_sold_7d / 7.0))
                ELSE 999
            END as days_of_inventory_remaining,
            ci.last_restocked_date
        FROM products p
        JOIN product_categories pc ON p.category_id = pc.category_id
        LEFT JOIN current_inventory ci ON p.product_id = ci.product_id
        LEFT JOIN recent_movements rm ON p.product_id = rm.product_id
        WHERE p.is_active = true
        {product_filter}
    )
    SELECT 
        product_id,
        product_name,
        sku,
        category_name,
        ROUND(unit_price, 2) as unit_price,
        COALESCE(current_stock, 0) as current_stock,
        COALESCE(reorder_level, 0) as reorder_level,
        stock_status,
        reorder_priority,
        units_sold_last_7_days,
        transactions_last_7_days,
        CASE 
            WHEN days_of_inventory_remaining = 999 THEN 'No recent sales'
            WHEN days_of_inventory_remaining <= 7 THEN CONCAT(days_of_inventory_remaining, ' days (Critical)')
            WHEN days_of_inventory_remaining <= 30 THEN CONCAT(days_of_inventory_remaining, ' days (Monitor)')
            ELSE CONCAT(days_of_inventory_remaining, ' days (Healthy)')
        END as inventory_runway,
        last_restocked_date,
        -- API response formatting for mobile/web apps
        json_build_object(
            'productId', product_id,
            'sku', sku,
            'name', product_name,
            'currentStock', COALESCE(current_stock, 0),
            'status', stock_status,
            'priority', reorder_priority,
            'daysRemaining', CASE WHEN days_of_inventory_remaining = 999 THEN null ELSE days_of_inventory_remaining END,
            'recentSales', units_sold_last_7_days
        ) as api_response_json
    FROM inventory_status
    ORDER BY 
        CASE reorder_priority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            ELSE 4
        END,
        days_of_inventory_remaining ASC;
    """