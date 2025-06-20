"""
Warehouse Operations Module
SQL queries for warehouse management and inventory operations
"""

def get_receiving_report_query(date_from, date_to):
    """Returns SQL query for warehouse receiving report"""
    return f"""
    SELECT 
        r.receiving_date,
        r.purchase_order_id,
        s.supplier_name,
        p.product_name,
        p.sku,
        r.quantity_ordered,
        r.quantity_received,
        r.quantity_damaged,
        r.unit_cost,
        r.quantity_received * r.unit_cost as total_value,
        CASE 
            WHEN r.quantity_received = r.quantity_ordered THEN 'COMPLETE'
            WHEN r.quantity_received > 0 THEN 'PARTIAL'
            ELSE 'NOT_RECEIVED'
        END as receiving_status
    FROM receiving_log r
    JOIN purchase_orders po ON r.purchase_order_id = po.purchase_order_id
    JOIN suppliers s ON po.supplier_id = s.supplier_id
    JOIN products p ON r.product_id = p.product_id
    WHERE r.receiving_date BETWEEN '{date_from}' AND '{date_to}'
    ORDER BY r.receiving_date DESC, s.supplier_name;
    """

def get_picking_efficiency_query():
    """Returns SQL query for warehouse picking efficiency analysis"""
    return """
    WITH picking_metrics AS (
        SELECT 
            picker_id,
            pick_date,
            COUNT(DISTINCT order_id) as orders_picked,
            SUM(quantity_picked) as total_items_picked,
            AVG(TIMESTAMPDIFF(MINUTE, pick_start_time, pick_end_time)) as avg_pick_time_minutes,
            SUM(TIMESTAMPDIFF(MINUTE, pick_start_time, pick_end_time)) as total_pick_time_minutes
        FROM picking_log
        WHERE pick_date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY picker_id, pick_date
    ),
    daily_averages AS (
        SELECT 
            picker_id,
            AVG(orders_picked) as avg_orders_per_day,
            AVG(total_items_picked) as avg_items_per_day,
            AVG(total_pick_time_minutes) as avg_total_time_per_day,
            AVG(total_items_picked / NULLIF(total_pick_time_minutes, 0)) as items_per_minute
        FROM picking_metrics
        GROUP BY picker_id
    )
    SELECT 
        p.picker_id,
        p.picker_name,
        da.avg_orders_per_day,
        da.avg_items_per_day,
        da.avg_total_time_per_day,
        ROUND(da.items_per_minute * 60, 2) as items_per_hour,
        RANK() OVER (ORDER BY da.items_per_minute DESC) as efficiency_rank
    FROM pickers p
    JOIN daily_averages da ON p.picker_id = da.picker_id
    ORDER BY da.items_per_minute DESC;
    """

def get_warehouse_capacity_query():
    """Returns SQL query for warehouse capacity analysis"""
    return """
    SELECT 
        wl.location_zone,
        wl.location_type,
        COUNT(*) as total_locations,
        COUNT(CASE WHEN i.product_id IS NOT NULL THEN 1 END) as occupied_locations,
        COUNT(*) - COUNT(CASE WHEN i.product_id IS NOT NULL THEN 1 END) as available_locations,
        ROUND((COUNT(CASE WHEN i.product_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*)), 2) as occupancy_rate,
        SUM(COALESCE(i.current_stock * p.unit_volume, 0)) as total_volume_used,
        SUM(wl.max_volume) as total_volume_capacity,
        ROUND((SUM(COALESCE(i.current_stock * p.unit_volume, 0)) * 100.0 / SUM(wl.max_volume)), 2) as volume_utilization
    FROM warehouse_locations wl
    LEFT JOIN inventory i ON wl.location_id = i.location_id
    LEFT JOIN products p ON i.product_id = p.product_id
    GROUP BY wl.location_zone, wl.location_type
    ORDER BY occupancy_rate DESC;
    """

def get_cycle_count_query():
    """Returns SQL query for cycle count variance analysis"""
    return """
    WITH count_variances AS (
        SELECT 
            cc.product_id,
            p.product_name,
            p.sku,
            cc.count_date,
            cc.system_quantity,
            cc.physical_quantity,
            cc.physical_quantity - cc.system_quantity as variance_quantity,
            (cc.physical_quantity - cc.system_quantity) * p.unit_cost as variance_value,
            ABS(cc.physical_quantity - cc.system_quantity) / NULLIF(cc.system_quantity, 0) * 100 as variance_percentage
        FROM cycle_counts cc
        JOIN products p ON cc.product_id = p.product_id
        WHERE cc.count_date >= CURRENT_DATE - INTERVAL '90 days'
    )
    SELECT 
        product_id,
        product_name,
        sku,
        COUNT(*) as count_cycles,
        AVG(variance_quantity) as avg_variance_qty,
        SUM(variance_value) as total_variance_value,
        AVG(ABS(variance_percentage)) as avg_accuracy_variance,
        CASE 
            WHEN AVG(ABS(variance_percentage)) > 10 THEN 'HIGH_VARIANCE'
            WHEN AVG(ABS(variance_percentage)) > 5 THEN 'MEDIUM_VARIANCE'
            ELSE 'LOW_VARIANCE'
        END as variance_category
    FROM count_variances
    GROUP BY product_id, product_name, sku
    HAVING COUNT(*) >= 2
    ORDER BY AVG(ABS(variance_percentage)) DESC;
    """ 