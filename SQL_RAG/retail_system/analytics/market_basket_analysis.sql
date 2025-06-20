-- Market Basket Analysis
-- Identifies products frequently bought together for cross-selling opportunities

WITH order_products AS (
    SELECT 
        st.order_id,
        st.product_id,
        p.product_name,
        pc.category_name,
        st.quantity,
        st.unit_price * st.quantity * (1 - st.discount_rate) as item_revenue
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '180 days'
),
product_pairs AS (
    SELECT 
        op1.product_id as product_a_id,
        op1.product_name as product_a_name,
        op1.category_name as category_a,
        op2.product_id as product_b_id,
        op2.product_name as product_b_name,
        op2.category_name as category_b,
        COUNT(DISTINCT op1.order_id) as orders_together,
        AVG(op1.item_revenue + op2.item_revenue) as avg_combined_revenue
    FROM order_products op1
    JOIN order_products op2 ON op1.order_id = op2.order_id
    WHERE op1.product_id < op2.product_id  -- Avoid duplicates and self-pairs
    GROUP BY op1.product_id, op1.product_name, op1.category_name,
             op2.product_id, op2.product_name, op2.category_name
    HAVING COUNT(DISTINCT op1.order_id) >= 5  -- Minimum threshold
),
product_totals AS (
    SELECT 
        product_id,
        product_name,
        COUNT(DISTINCT order_id) as total_orders_with_product
    FROM order_products
    GROUP BY product_id, product_name
),
association_metrics AS (
    SELECT 
        pp.*,
        pt1.total_orders_with_product as orders_with_a,
        pt2.total_orders_with_product as orders_with_b,
        (SELECT COUNT(DISTINCT order_id) FROM order_products) as total_orders,
        -- Support: Probability of both products being bought together
        pp.orders_together / (SELECT COUNT(DISTINCT order_id) FROM order_products)::FLOAT as support,
        -- Confidence A->B: Probability of B given A
        pp.orders_together / pt1.total_orders_with_product::FLOAT as confidence_a_to_b,
        -- Confidence B->A: Probability of A given B
        pp.orders_together / pt2.total_orders_with_product::FLOAT as confidence_b_to_a,
        -- Lift: How much more likely B is bought when A is bought vs randomly
        (pp.orders_together / pt1.total_orders_with_product::FLOAT) / 
        (pt2.total_orders_with_product / (SELECT COUNT(DISTINCT order_id) FROM order_products)::FLOAT) as lift_a_to_b
    FROM product_pairs pp
    JOIN product_totals pt1 ON pp.product_a_id = pt1.product_id
    JOIN product_totals pt2 ON pp.product_b_id = pt2.product_id
)
SELECT 
    product_a_id,
    product_a_name,
    category_a,
    product_b_id,
    product_b_name,
    category_b,
    orders_together,
    orders_with_a,
    orders_with_b,
    ROUND(support * 100, 3) as support_pct,
    ROUND(confidence_a_to_b * 100, 2) as confidence_a_to_b_pct,
    ROUND(confidence_b_to_a * 100, 2) as confidence_b_to_a_pct,
    ROUND(lift_a_to_b, 2) as lift_a_to_b,
    ROUND(avg_combined_revenue, 2) as avg_combined_revenue,
    CASE 
        WHEN lift_a_to_b >= 2.0 AND confidence_a_to_b >= 0.3 THEN 'STRONG_ASSOCIATION'
        WHEN lift_a_to_b >= 1.5 AND confidence_a_to_b >= 0.2 THEN 'MODERATE_ASSOCIATION'
        WHEN lift_a_to_b >= 1.2 AND confidence_a_to_b >= 0.1 THEN 'WEAK_ASSOCIATION'
        ELSE 'NO_SIGNIFICANT_ASSOCIATION'
    END as association_strength
FROM association_metrics
WHERE lift_a_to_b > 1.0  -- Only show positive associations
ORDER BY lift_a_to_b DESC, confidence_a_to_b DESC; 