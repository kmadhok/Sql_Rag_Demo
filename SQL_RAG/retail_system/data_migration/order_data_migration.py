"""
Order Data Migration Module
Scripts for migrating order data between systems or during upgrades
"""

def get_legacy_order_migration_query():
    """Returns SQL query to migrate orders from legacy system"""
    return """
    INSERT INTO sales_transactions (
        order_id, customer_id, store_id, product_id, quantity,
        unit_price, discount_rate, tax_rate, order_date, 
        payment_method, created_at
    )
    SELECT 
        lo.legacy_order_id as order_id,
        cm.new_customer_id as customer_id,
        sm.new_store_id as store_id,
        pm.new_product_id as product_id,
        lo.quantity,
        lo.price as unit_price,
        COALESCE(lo.discount_percent / 100, 0) as discount_rate,
        COALESCE(lo.tax_percent / 100, 0.08) as tax_rate,
        STR_TO_DATE(lo.order_date, '%Y-%m-%d %H:%i:%s') as order_date,
        CASE lo.payment_type
            WHEN 'CC' THEN 'CREDIT_CARD'
            WHEN 'DC' THEN 'DEBIT_CARD'
            WHEN 'CA' THEN 'CASH'
            ELSE 'CASH'
        END as payment_method,
        CURRENT_TIMESTAMP as created_at
    FROM legacy_orders lo
    JOIN customer_mapping cm ON lo.customer_code = cm.legacy_customer_code
    JOIN store_mapping sm ON lo.store_code = sm.legacy_store_code
    JOIN product_mapping pm ON lo.product_sku = pm.legacy_sku
    WHERE lo.migrated = 0
    AND lo.order_date >= '2020-01-01'
    ORDER BY lo.order_date;
    """

def get_data_validation_query():
    """Returns SQL query to validate migrated data integrity"""
    return """
    WITH migration_summary AS (
        SELECT 
            'ORDERS' as table_name,
            COUNT(*) as total_records,
            MIN(order_date) as earliest_date,
            MAX(order_date) as latest_date,
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(DISTINCT product_id) as unique_products,
            SUM(unit_price * quantity * (1 - discount_rate)) as total_revenue
        FROM sales_transactions
        WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
        
        UNION ALL
        
        SELECT 
            'CUSTOMERS' as table_name,
            COUNT(*) as total_records,
            MIN(registration_date) as earliest_date,
            MAX(registration_date) as latest_date,
            NULL as unique_customers,
            NULL as unique_products,
            NULL as total_revenue
        FROM customers
        WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
    ),
    data_quality_checks AS (
        SELECT 
            'DUPLICATE_ORDERS' as check_name,
            COUNT(*) as issues_found
        FROM (
            SELECT order_id, customer_id, product_id, order_date
            FROM sales_transactions
            GROUP BY order_id, customer_id, product_id, order_date
            HAVING COUNT(*) > 1
        ) duplicates
        
        UNION ALL
        
        SELECT 
            'NEGATIVE_PRICES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE unit_price < 0
        
        UNION ALL
        
        SELECT 
            'ZERO_QUANTITIES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE quantity <= 0
        
        UNION ALL
        
        SELECT 
            'INVALID_DISCOUNT_RATES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE discount_rate < 0 OR discount_rate > 1
    )
    SELECT 
        'MIGRATION_SUMMARY' as report_section,
        table_name,
        total_records,
        earliest_date,
        latest_date,
        unique_customers,
        unique_products,
        total_revenue,
        NULL as issues_found
    FROM migration_summary
    
    UNION ALL
    
    SELECT 
        'DATA_QUALITY_CHECKS' as report_section,
        check_name as table_name,
        NULL as total_records,
        NULL as earliest_date,
        NULL as latest_date,
        NULL as unique_customers,
        NULL as unique_products,
        NULL as total_revenue,
        issues_found
    FROM data_quality_checks
    ORDER BY report_section, table_name;
    """

def get_incremental_sync_query(last_sync_timestamp):
    """Returns SQL query for incremental data synchronization"""
    return f"""
    WITH new_orders AS (
        SELECT 
            order_id,
            customer_id,
            store_id,
            order_date,
            total_amount,
            order_status,
            updated_at
        FROM source_orders
        WHERE updated_at > '{last_sync_timestamp}'
    ),
    order_items AS (
        SELECT 
            oi.order_id,
            oi.product_id,
            oi.quantity,
            oi.unit_price,
            oi.discount_amount,
            p.unit_cost
        FROM source_order_items oi
        JOIN source_products p ON oi.product_id = p.product_id
        JOIN new_orders no ON oi.order_id = no.order_id
    )
    INSERT INTO sales_transactions (
        order_id, customer_id, store_id, product_id, quantity,
        unit_price, discount_rate, order_date, created_at
    )
    SELECT 
        no.order_id,
        no.customer_id,
        no.store_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        CASE 
            WHEN oi.unit_price > 0 THEN oi.discount_amount / (oi.unit_price * oi.quantity)
            ELSE 0
        END as discount_rate,
        no.order_date,
        CURRENT_TIMESTAMP
    FROM new_orders no
    JOIN order_items oi ON no.order_id = oi.order_id
    WHERE NOT EXISTS (
        SELECT 1 FROM sales_transactions st 
        WHERE st.order_id = no.order_id 
        AND st.product_id = oi.product_id
    );
    """

def get_cleanup_temp_tables_query():
    """Returns SQL query to cleanup temporary migration tables"""
    return """
    -- Drop temporary mapping tables
    DROP TABLE IF EXISTS customer_mapping;
    DROP TABLE IF EXISTS product_mapping;
    DROP TABLE IF EXISTS store_mapping;
    
    -- Drop staging tables
    DROP TABLE IF EXISTS staging_orders;
    DROP TABLE IF EXISTS staging_customers;
    DROP TABLE IF EXISTS staging_products;
    
    -- Mark legacy data as migrated
    UPDATE legacy_orders SET migrated = 1 WHERE migrated = 0;
    UPDATE legacy_customers SET migrated = 1 WHERE migrated = 0;
    UPDATE legacy_products SET migrated = 1 WHERE migrated = 0;
    
    -- Create migration log entry
    INSERT INTO migration_log (
        migration_type, 
        start_time, 
        end_time, 
        records_processed, 
        status
    ) VALUES (
        'ORDER_DATA_MIGRATION',
        @migration_start_time,
        CURRENT_TIMESTAMP,
        @records_processed,
        'COMPLETED'
    );
    """ 