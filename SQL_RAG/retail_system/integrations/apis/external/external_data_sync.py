"""
External API Data Synchronization Module
SQL queries for syncing data from external systems and APIs
"""

def get_supplier_catalog_sync_query():
    """Returns SQL to sync product catalog data from supplier APIs"""
    return """
    WITH supplier_updates AS (
        SELECT 
            sp.supplier_product_id,
            sp.supplier_id,
            sp.supplier_sku,
            sp.supplier_price,
            sp.availability_status,
            sp.last_updated as supplier_last_updated,
            p.product_id,
            p.sku as internal_sku,
            p.unit_cost as current_cost,
            p.is_active as current_status,
            p.last_updated as internal_last_updated
        FROM external_supplier_products sp
        LEFT JOIN products p ON sp.supplier_sku = p.supplier_sku 
            AND sp.supplier_id = p.supplier_id
        WHERE sp.last_updated >= CURRENT_DATE - INTERVAL '7 days'
    ),
    price_changes AS (
        SELECT 
            supplier_id,
            supplier_sku,
            supplier_price,
            current_cost,
            ABS(supplier_price - current_cost) as price_diff,
            CASE 
                WHEN current_cost > 0 THEN 
                    ABS(supplier_price - current_cost) / current_cost * 100
                ELSE 0
            END as price_change_pct,
            availability_status,
            CASE 
                WHEN product_id IS NULL THEN 'NEW_PRODUCT'
                WHEN supplier_price != current_cost THEN 'PRICE_UPDATE'
                WHEN availability_status = 'DISCONTINUED' AND current_status = true THEN 'DISCONTINUE'
                WHEN availability_status = 'AVAILABLE' AND current_status = false THEN 'REACTIVATE'
                ELSE 'NO_CHANGE'
            END as sync_action
        FROM supplier_updates
    )
    SELECT 
        supplier_id,
        supplier_sku,
        supplier_price as new_cost,
        current_cost as old_cost,
        ROUND(price_diff, 2) as cost_difference,
        ROUND(price_change_pct, 2) as change_percentage,
        availability_status,
        sync_action,
        CASE 
            WHEN sync_action = 'NEW_PRODUCT' THEN 'High'
            WHEN sync_action = 'PRICE_UPDATE' AND price_change_pct > 20 THEN 'High'
            WHEN sync_action = 'DISCONTINUE' THEN 'High'
            WHEN sync_action = 'PRICE_UPDATE' AND price_change_pct > 5 THEN 'Medium'
            ELSE 'Low'
        END as priority,
        -- Generate update SQL for automation
        CASE 
            WHEN sync_action = 'PRICE_UPDATE' THEN 
                'UPDATE products SET unit_cost = ' || supplier_price || 
                ', last_updated = CURRENT_TIMESTAMP WHERE supplier_sku = ''' || supplier_sku || ''''
            WHEN sync_action = 'DISCONTINUE' THEN 
                'UPDATE products SET is_active = false, last_updated = CURRENT_TIMESTAMP WHERE supplier_sku = ''' || supplier_sku || ''''
            WHEN sync_action = 'REACTIVATE' THEN 
                'UPDATE products SET is_active = true, last_updated = CURRENT_TIMESTAMP WHERE supplier_sku = ''' || supplier_sku || ''''
            ELSE NULL
        END as suggested_sql
    FROM price_changes
    WHERE sync_action != 'NO_CHANGE'
    ORDER BY 
        CASE priority 
            WHEN 'High' THEN 1 
            WHEN 'Medium' THEN 2 
            ELSE 3 
        END,
        price_change_pct DESC;
    """

def get_customer_enrichment_sync_query():
    """Returns SQL to sync customer enrichment data from external marketing APIs"""
    return """
    WITH external_customer_data AS (
        SELECT 
            ecd.email,
            ecd.marketing_segment,
            ecd.income_bracket,
            ecd.demographic_cluster,
            ecd.social_media_presence,
            ecd.email_engagement_score,
            ecd.purchase_propensity_score,
            ecd.churn_risk_score,
            ecd.last_updated as external_last_updated,
            c.customer_id,
            c.email as customer_email,
            ce.marketing_segment as current_segment,
            ce.last_updated as current_last_updated
        FROM external_customer_demographics ecd
        JOIN customers c ON ecd.email = c.email
        LEFT JOIN customer_enrichment ce ON c.customer_id = ce.customer_id
        WHERE ecd.last_updated >= CURRENT_DATE - INTERVAL '30 days'
    ),
    enrichment_updates AS (
        SELECT 
            customer_id,
            customer_email,
            marketing_segment as new_segment,
            current_segment,
            income_bracket,
            demographic_cluster,
            social_media_presence,
            ROUND(email_engagement_score::NUMERIC, 2) as email_engagement_score,
            ROUND(purchase_propensity_score::NUMERIC, 2) as purchase_propensity_score,
            ROUND(churn_risk_score::NUMERIC, 2) as churn_risk_score,
            CASE 
                WHEN current_segment IS NULL THEN 'NEW_ENRICHMENT'
                WHEN marketing_segment != current_segment THEN 'SEGMENT_CHANGE'
                WHEN external_last_updated > current_last_updated THEN 'DATA_REFRESH'
                ELSE 'NO_CHANGE'
            END as update_type
        FROM external_customer_data
    ),
    segment_analysis AS (
        SELECT 
            new_segment,
            current_segment,
            COUNT(*) as customer_count,
            AVG(email_engagement_score) as avg_engagement,
            AVG(purchase_propensity_score) as avg_propensity,
            AVG(churn_risk_score) as avg_churn_risk
        FROM enrichment_updates
        WHERE update_type != 'NO_CHANGE'
        GROUP BY new_segment, current_segment
    )
    SELECT 
        'CUSTOMER_ENRICHMENT_SYNC' as sync_type,
        eu.customer_id,
        eu.customer_email,
        eu.new_segment,
        eu.current_segment,
        eu.income_bracket,
        eu.demographic_cluster,
        eu.email_engagement_score,
        eu.purchase_propensity_score,
        eu.churn_risk_score,
        eu.update_type,
        CASE 
            WHEN eu.churn_risk_score > 0.7 THEN 'HIGH_CHURN_RISK'
            WHEN eu.purchase_propensity_score > 0.8 THEN 'HIGH_PURCHASE_INTENT'
            WHEN eu.update_type = 'SEGMENT_CHANGE' THEN 'SEGMENT_MIGRATION'
            ELSE 'STANDARD_UPDATE'
        END as action_flag,
        CURRENT_TIMESTAMP as sync_timestamp
    FROM enrichment_updates eu
    WHERE eu.update_type != 'NO_CHANGE'
    
    UNION ALL
    
    SELECT 
        'SEGMENT_SUMMARY' as sync_type,
        NULL as customer_id,
        NULL as customer_email,
        sa.new_segment,
        sa.current_segment,
        NULL as income_bracket,
        NULL as demographic_cluster,
        sa.avg_engagement as email_engagement_score,
        sa.avg_propensity as purchase_propensity_score,
        sa.avg_churn_risk as churn_risk_score,
        'SUMMARY' as update_type,
        CONCAT('Updating ', sa.customer_count, ' customers') as action_flag,
        CURRENT_TIMESTAMP as sync_timestamp
    FROM segment_analysis sa
    ORDER BY sync_type, churn_risk_score DESC, purchase_propensity_score DESC;
    """

def get_inventory_replenishment_sync_query():
    """Returns SQL to sync inventory replenishment data from supplier systems"""
    return """
    WITH current_inventory AS (
        SELECT 
            product_id,
            current_stock,
            reorder_level,
            reorder_quantity,
            CASE 
                WHEN current_stock <= reorder_level THEN 'CRITICAL'
                WHEN current_stock <= reorder_level * 1.5 THEN 'LOW'
                ELSE 'ADEQUATE'
            END as stock_status
        FROM inventory_snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
    ),
    supplier_availability AS (
        SELECT 
            p.product_id,
            p.sku,
            s.supplier_id,
            s.supplier_name,
            esp.availability_status,
            esp.lead_time_days,
            esp.minimum_order_qty,
            esp.unit_price as supplier_unit_price,
            esp.last_updated as supplier_last_updated
        FROM products p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        LEFT JOIN external_supplier_products esp ON p.supplier_sku = esp.supplier_sku
            AND p.supplier_id = esp.supplier_id
    ),
    replenishment_needs AS (
        SELECT 
            ci.product_id,
            p.product_name,
            p.sku,
            ci.current_stock,
            ci.reorder_level,
            ci.reorder_quantity,
            ci.stock_status,
            sa.supplier_name,
            sa.availability_status,
            sa.lead_time_days,
            sa.minimum_order_qty,
            sa.supplier_unit_price,
            -- Calculate suggested order quantity
            CASE 
                WHEN ci.current_stock <= ci.reorder_level THEN
                    GREATEST(ci.reorder_quantity, sa.minimum_order_qty)
                ELSE 0
            END as suggested_order_qty,
            -- Calculate total order value
            CASE 
                WHEN ci.current_stock <= ci.reorder_level THEN
                    GREATEST(ci.reorder_quantity, sa.minimum_order_qty) * sa.supplier_unit_price
                ELSE 0
            END as estimated_order_value,
            -- Estimate delivery date
            CURRENT_DATE + INTERVAL '1 day' * COALESCE(sa.lead_time_days, 7) as estimated_delivery_date
        FROM current_inventory ci
        JOIN products p ON ci.product_id = p.product_id
        LEFT JOIN supplier_availability sa ON ci.product_id = sa.product_id
    )
    SELECT 
        product_id,
        product_name,
        sku,
        current_stock,
        reorder_level,
        stock_status,
        supplier_name,
        availability_status,
        suggested_order_qty,
        ROUND(estimated_order_value, 2) as estimated_order_value,
        estimated_delivery_date,
        lead_time_days,
        CASE 
            WHEN stock_status = 'CRITICAL' AND availability_status = 'AVAILABLE' THEN 'URGENT_ORDER'
            WHEN stock_status = 'CRITICAL' AND availability_status != 'AVAILABLE' THEN 'SUPPLIER_ISSUE'
            WHEN stock_status = 'LOW' AND availability_status = 'AVAILABLE' THEN 'STANDARD_ORDER'
            WHEN availability_status = 'DISCONTINUED' THEN 'FIND_ALTERNATIVE'
            ELSE 'NO_ACTION'
        END as recommended_action,
        CASE 
            WHEN stock_status = 'CRITICAL' THEN 1
            WHEN stock_status = 'LOW' THEN 2
            ELSE 3
        END as priority_order
    FROM replenishment_needs
    WHERE suggested_order_qty > 0 OR availability_status != 'AVAILABLE'
    ORDER BY priority_order, estimated_order_value DESC;
    """