-- Supplier Performance Analysis
-- Evaluates supplier reliability, quality, and cost effectiveness

WITH supplier_metrics AS (
    SELECT 
        s.supplier_id,
        s.supplier_name,
        COUNT(DISTINCT po.purchase_order_id) as total_orders,
        COUNT(DISTINCT p.product_id) as products_supplied,
        SUM(po.order_total) as total_order_value,
        AVG(po.order_total) as avg_order_value,
        AVG(DATEDIFF(po.delivery_date, po.order_date)) as avg_delivery_days,
        AVG(DATEDIFF(po.promised_delivery_date, po.delivery_date)) as avg_delivery_variance_days
    FROM suppliers s
    JOIN products p ON s.supplier_id = p.supplier_id
    JOIN purchase_orders po ON s.supplier_id = po.supplier_id
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    AND po.order_status = 'COMPLETED'
    GROUP BY s.supplier_id, s.supplier_name
),
quality_metrics AS (
    SELECT 
        po.supplier_id,
        COUNT(*) as total_deliveries,
        SUM(CASE WHEN qc.quality_rating >= 4 THEN 1 ELSE 0 END) as good_quality_deliveries,
        AVG(qc.quality_rating) as avg_quality_rating,
        SUM(qc.defect_quantity) as total_defects,
        SUM(qc.received_quantity) as total_received_quantity
    FROM purchase_orders po
    JOIN quality_control qc ON po.purchase_order_id = qc.purchase_order_id
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY po.supplier_id
),
cost_analysis AS (
    SELECT 
        p.supplier_id,
        AVG(p.unit_cost) as avg_unit_cost,
        MIN(p.unit_cost) as min_unit_cost,
        MAX(p.unit_cost) as max_unit_cost,
        STDDEV(p.unit_cost) as cost_variability
    FROM products p
    WHERE p.is_active = TRUE
    GROUP BY p.supplier_id
),
delivery_performance AS (
    SELECT 
        po.supplier_id,
        COUNT(*) as total_deliveries,
        SUM(CASE WHEN po.delivery_date <= po.promised_delivery_date THEN 1 ELSE 0 END) as on_time_deliveries,
        SUM(CASE WHEN po.delivery_date > po.promised_delivery_date THEN 1 ELSE 0 END) as late_deliveries,
        AVG(CASE WHEN po.delivery_date > po.promised_delivery_date 
                 THEN DATEDIFF(po.delivery_date, po.promised_delivery_date) 
                 ELSE 0 END) as avg_late_days
    FROM purchase_orders po
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    AND po.delivery_date IS NOT NULL
    GROUP BY po.supplier_id
)
SELECT 
    sm.supplier_id,
    sm.supplier_name,
    sm.total_orders,
    sm.products_supplied,
    sm.total_order_value,
    sm.avg_order_value,
    sm.avg_delivery_days,
    
    -- Delivery Performance
    dp.total_deliveries,
    dp.on_time_deliveries,
    ROUND(dp.on_time_deliveries * 100.0 / dp.total_deliveries, 2) as on_time_delivery_rate,
    dp.late_deliveries,
    dp.avg_late_days,
    
    -- Quality Metrics
    qm.good_quality_deliveries,
    ROUND(qm.good_quality_deliveries * 100.0 / qm.total_deliveries, 2) as quality_rate,
    ROUND(qm.avg_quality_rating, 2) as avg_quality_rating,
    ROUND(qm.total_defects * 100.0 / qm.total_received_quantity, 4) as defect_rate,
    
    -- Cost Analysis
    ca.avg_unit_cost,
    ca.cost_variability,
    
    -- Overall Supplier Score (weighted composite)
    ROUND(
        (dp.on_time_deliveries * 100.0 / dp.total_deliveries) * 0.3 +  -- 30% weight on delivery
        (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) * 0.4 +  -- 40% weight on quality
        (100 - (qm.total_defects * 100.0 / qm.total_received_quantity)) * 0.2 +  -- 20% weight on defects
        GREATEST(0, 100 - sm.avg_delivery_variance_days * 2) * 0.1  -- 10% weight on delivery consistency
    , 2) as supplier_performance_score,
    
    -- Supplier Classification
    CASE 
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 95 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 90 
         AND (qm.total_defects * 100.0 / qm.total_received_quantity) <= 2 THEN 'PREFERRED'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 85 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 80 THEN 'APPROVED'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 70 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 70 THEN 'CONDITIONAL'
        ELSE 'UNDER_REVIEW'
    END as supplier_status,
    
    -- Risk Assessment
    CASE 
        WHEN sm.total_orders < 5 THEN 'NEW_SUPPLIER_RISK'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) < 75 THEN 'DELIVERY_RISK'
        WHEN (qm.total_defects * 100.0 / qm.total_received_quantity) > 5 THEN 'QUALITY_RISK'
        WHEN ca.cost_variability > (ca.avg_unit_cost * 0.2) THEN 'COST_VOLATILITY_RISK'
        ELSE 'LOW_RISK'
    END as risk_category

FROM supplier_metrics sm
LEFT JOIN quality_metrics qm ON sm.supplier_id = qm.supplier_id
LEFT JOIN cost_analysis ca ON sm.supplier_id = ca.supplier_id
LEFT JOIN delivery_performance dp ON sm.supplier_id = dp.supplier_id
ORDER BY 
    ROUND(
        (dp.on_time_deliveries * 100.0 / dp.total_deliveries) * 0.3 +
        (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) * 0.4 +
        (100 - (qm.total_defects * 100.0 / qm.total_received_quantity)) * 0.2 +
        GREATEST(0, 100 - sm.avg_delivery_variance_days * 2) * 0.1
    , 2) DESC; 