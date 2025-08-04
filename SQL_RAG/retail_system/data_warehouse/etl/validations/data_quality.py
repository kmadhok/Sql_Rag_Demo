"""
Data Quality Validation Queries Module
SQL queries for validating data integrity and quality in ETL processes
"""

def get_customer_data_quality_checks():
    """Returns SQL query to validate customer data quality"""
    return """
    WITH quality_checks AS (
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'NULL_EMAIL' as check_type,
            COUNT(*) as failing_records,
            'Critical: Customers without email addresses' as description
        FROM customers 
        WHERE email IS NULL OR email = ''
        
        UNION ALL
        
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'INVALID_EMAIL_FORMAT' as check_type,
            COUNT(*) as failing_records,
            'Critical: Customers with invalid email format' as description
        FROM customers 
        WHERE email IS NOT NULL 
            AND email NOT LIKE '%@%.%'
        
        UNION ALL
        
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'DUPLICATE_EMAILS' as check_type,
            COUNT(*) - COUNT(DISTINCT email) as failing_records,
            'High: Duplicate email addresses found' as description
        FROM customers 
        WHERE email IS NOT NULL
        
        UNION ALL
        
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'MISSING_NAMES' as check_type,
            COUNT(*) as failing_records,
            'Medium: Customers missing first or last name' as description
        FROM customers 
        WHERE first_name IS NULL OR last_name IS NULL 
            OR first_name = '' OR last_name = ''
        
        UNION ALL
        
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'FUTURE_REGISTRATION_DATE' as check_type,
            COUNT(*) as failing_records,
            'Critical: Registration dates in the future' as description
        FROM customers 
        WHERE registration_date > CURRENT_DATE
        
        UNION ALL
        
        SELECT 
            'CUSTOMER_DATA' as table_name,
            'INVALID_BIRTH_DATE' as check_type,
            COUNT(*) as failing_records,
            'Medium: Invalid birth dates (future or too old)' as description
        FROM customers 
        WHERE date_of_birth > CURRENT_DATE 
            OR date_of_birth < CURRENT_DATE - INTERVAL '120 years'
    )
    SELECT 
        table_name,
        check_type,
        failing_records,
        description,
        CASE 
            WHEN failing_records = 0 THEN 'PASS'
            WHEN description LIKE 'Critical:%' AND failing_records > 0 THEN 'CRITICAL_FAIL'
            WHEN description LIKE 'High:%' AND failing_records > 10 THEN 'HIGH_FAIL'
            WHEN description LIKE 'Medium:%' AND failing_records > 50 THEN 'MEDIUM_FAIL'
            ELSE 'LOW_CONCERN'
        END as status,
        CURRENT_TIMESTAMP as check_timestamp
    FROM quality_checks
    ORDER BY 
        CASE 
            WHEN status = 'CRITICAL_FAIL' THEN 1
            WHEN status = 'HIGH_FAIL' THEN 2
            WHEN status = 'MEDIUM_FAIL' THEN 3
            WHEN status = 'LOW_CONCERN' THEN 4
            ELSE 5
        END,
        failing_records DESC;
    """

def get_sales_data_integrity_checks():
    """Returns SQL query to validate sales transaction data integrity"""
    return """
    WITH integrity_checks AS (
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'NEGATIVE_QUANTITIES' as check_type,
            COUNT(*) as failing_records,
            'Critical: Negative quantities in sales transactions' as description
        FROM sales_transactions 
        WHERE quantity < 0
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'NEGATIVE_PRICES' as check_type,
            COUNT(*) as failing_records,
            'Critical: Negative unit prices in sales transactions' as description
        FROM sales_transactions 
        WHERE unit_price < 0
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'INVALID_DISCOUNT_RATES' as check_type,
            COUNT(*) as failing_records,
            'High: Invalid discount rates (negative or >100%)' as description
        FROM sales_transactions 
        WHERE discount_rate < 0 OR discount_rate > 1
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'ORPHANED_CUSTOMER_REFERENCES' as check_type,
            COUNT(*) as failing_records,
            'Critical: Sales transactions with invalid customer references' as description
        FROM sales_transactions st
        LEFT JOIN customers c ON st.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'ORPHANED_PRODUCT_REFERENCES' as check_type,
            COUNT(*) as failing_records,
            'Critical: Sales transactions with invalid product references' as description
        FROM sales_transactions st
        LEFT JOIN products p ON st.product_id = p.product_id
        WHERE p.product_id IS NULL
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'FUTURE_ORDER_DATES' as check_type,
            COUNT(*) as failing_records,
            'Critical: Order dates in the future' as description
        FROM sales_transactions 
        WHERE order_date > CURRENT_TIMESTAMP
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'ZERO_VALUE_TRANSACTIONS' as check_type,
            COUNT(*) as failing_records,
            'Medium: Transactions with zero monetary value' as description
        FROM sales_transactions 
        WHERE unit_price * quantity * (1 - discount_rate) = 0
        
        UNION ALL
        
        SELECT 
            'SALES_TRANSACTIONS' as table_name,
            'DUPLICATE_TRANSACTIONS' as check_type,
            COUNT(*) - COUNT(DISTINCT order_id, product_id, customer_id, order_date) as failing_records,
            'High: Potential duplicate transactions' as description
        FROM sales_transactions
    )
    SELECT 
        table_name,
        check_type,
        failing_records,
        description,
        CASE 
            WHEN failing_records = 0 THEN 'PASS'
            WHEN description LIKE 'Critical:%' AND failing_records > 0 THEN 'CRITICAL_FAIL'
            WHEN description LIKE 'High:%' AND failing_records > 5 THEN 'HIGH_FAIL'
            WHEN description LIKE 'Medium:%' AND failing_records > 20 THEN 'MEDIUM_FAIL'
            ELSE 'LOW_CONCERN'
        END as status,
        ROUND(failing_records * 100.0 / (SELECT COUNT(*) FROM sales_transactions), 4) as failure_rate_pct,
        CURRENT_TIMESTAMP as check_timestamp
    FROM integrity_checks
    ORDER BY 
        CASE 
            WHEN status = 'CRITICAL_FAIL' THEN 1
            WHEN status = 'HIGH_FAIL' THEN 2
            WHEN status = 'MEDIUM_FAIL' THEN 3
            WHEN status = 'LOW_CONCERN' THEN 4
            ELSE 5
        END,
        failing_records DESC;
    """

def get_inventory_consistency_checks():
    """Returns SQL query to validate inventory data consistency"""
    return """
    WITH consistency_checks AS (
        SELECT 
            'INVENTORY' as table_name,
            'NEGATIVE_STOCK_LEVELS' as check_type,
            COUNT(*) as failing_records,
            'Critical: Products with negative stock levels' as description
        FROM inventory_snapshots
        WHERE current_stock < 0
            AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
        
        UNION ALL
        
        SELECT 
            'INVENTORY' as table_name,
            'MISSING_REORDER_LEVELS' as check_type,
            COUNT(*) as failing_records,
            'Medium: Products without defined reorder levels' as description
        FROM inventory_snapshots
        WHERE reorder_level IS NULL OR reorder_level <= 0
            AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
        
        UNION ALL
        
        SELECT 
            'INVENTORY' as table_name,
            'PRODUCTS_NOT_IN_INVENTORY' as check_type,
            COUNT(*) as failing_records,
            'High: Active products not tracked in inventory' as description
        FROM products p
        LEFT JOIN inventory_snapshots inv ON p.product_id = inv.product_id
            AND inv.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
        WHERE inv.product_id IS NULL
            AND p.is_active = true
        
        UNION ALL
        
        SELECT 
            'INVENTORY' as table_name,
            'STOCK_VS_SALES_MISMATCH' as check_type,
            COUNT(*) as failing_records,
            'Medium: High sales volume but zero stock recorded' as description
        FROM (
            SELECT 
                st.product_id,
                SUM(st.quantity) as units_sold_last_30_days,
                COALESCE(inv.current_stock, 0) as current_stock
            FROM sales_transactions st
            LEFT JOIN inventory_snapshots inv ON st.product_id = inv.product_id
                AND inv.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
            WHERE st.order_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY st.product_id, inv.current_stock
            HAVING SUM(st.quantity) > 50 AND COALESCE(inv.current_stock, 0) = 0
        ) stock_mismatches
    )
    SELECT 
        table_name,
        check_type,
        failing_records,
        description,
        CASE 
            WHEN failing_records = 0 THEN 'PASS'
            WHEN description LIKE 'Critical:%' AND failing_records > 0 THEN 'CRITICAL_FAIL'
            WHEN description LIKE 'High:%' AND failing_records > 3 THEN 'HIGH_FAIL'
            WHEN description LIKE 'Medium:%' AND failing_records > 10 THEN 'MEDIUM_FAIL'
            ELSE 'LOW_CONCERN'
        END as status,
        CURRENT_TIMESTAMP as check_timestamp
    FROM consistency_checks
    ORDER BY 
        CASE 
            WHEN status = 'CRITICAL_FAIL' THEN 1
            WHEN status = 'HIGH_FAIL' THEN 2
            WHEN status = 'MEDIUM_FAIL' THEN 3
            WHEN status = 'LOW_CONCERN' THEN 4
            ELSE 5
        END,
        failing_records DESC;
    """