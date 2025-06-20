-- Dynamic Pricing Analysis
-- Analyzes price elasticity and optimal pricing strategies

WITH price_history AS (
    SELECT 
        product_id,
        DATE(order_date) as price_date,
        AVG(unit_price) as avg_price,
        SUM(quantity) as daily_quantity,
        COUNT(DISTINCT order_id) as daily_orders,
        SUM(unit_price * quantity * (1 - discount_rate)) as daily_revenue
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY product_id, DATE(order_date)
),
price_elasticity AS (
    SELECT 
        ph1.product_id,
        ph1.price_date,
        ph1.avg_price,
        ph1.daily_quantity,
        ph1.daily_revenue,
        LAG(ph1.avg_price, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) as prev_price,
        LAG(ph1.daily_quantity, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) as prev_quantity,
        -- Calculate price change percentage
        CASE 
            WHEN LAG(ph1.avg_price, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) > 0 THEN
                (ph1.avg_price - LAG(ph1.avg_price, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date)) / 
                LAG(ph1.avg_price, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) * 100
            ELSE 0
        END as price_change_pct,
        -- Calculate quantity change percentage
        CASE 
            WHEN LAG(ph1.daily_quantity, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) > 0 THEN
                (ph1.daily_quantity - LAG(ph1.daily_quantity, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date)) / 
                LAG(ph1.daily_quantity, 1) OVER (PARTITION BY ph1.product_id ORDER BY ph1.price_date) * 100
            ELSE 0
        END as quantity_change_pct
    FROM price_history ph1
),
elasticity_calculation AS (
    SELECT 
        pe.product_id,
        p.product_name,
        pc.category_name,
        AVG(pe.avg_price) as avg_selling_price,
        SUM(pe.daily_quantity) as total_quantity_sold,
        SUM(pe.daily_revenue) as total_revenue,
        -- Price elasticity of demand
        CASE 
            WHEN AVG(ABS(pe.price_change_pct)) > 0 THEN
                AVG(pe.quantity_change_pct) / AVG(pe.price_change_pct)
            ELSE 0
        END as price_elasticity,
        STDDEV(pe.avg_price) as price_volatility,
        COUNT(DISTINCT pe.price_date) as observation_days
    FROM price_elasticity pe
    JOIN products p ON pe.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    WHERE pe.prev_price IS NOT NULL
    AND ABS(pe.price_change_pct) > 1  -- Only consider meaningful price changes
    GROUP BY pe.product_id, p.product_name, pc.category_name
    HAVING COUNT(DISTINCT pe.price_date) >= 10  -- Minimum observations for reliability
),
competitor_pricing AS (
    SELECT 
        product_id,
        AVG(competitor_price) as avg_competitor_price,
        MIN(competitor_price) as min_competitor_price,
        MAX(competitor_price) as max_competitor_price
    FROM competitor_prices
    WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY product_id
)
SELECT 
    ec.product_id,
    ec.product_name,
    ec.category_name,
    ec.avg_selling_price,
    ec.total_quantity_sold,
    ec.total_revenue,
    ROUND(ec.price_elasticity, 3) as price_elasticity,
    ROUND(ec.price_volatility, 2) as price_volatility,
    cp.avg_competitor_price,
    cp.min_competitor_price,
    cp.max_competitor_price,
    ROUND(ec.avg_selling_price - cp.avg_competitor_price, 2) as price_gap_vs_competition,
    CASE 
        WHEN ec.price_elasticity > -0.5 THEN 'INELASTIC'
        WHEN ec.price_elasticity > -1.5 THEN 'MODERATE_ELASTIC'
        ELSE 'HIGHLY_ELASTIC'
    END as demand_elasticity_category,
    CASE 
        WHEN ec.avg_selling_price > cp.max_competitor_price THEN 'PREMIUM_PRICING'
        WHEN ec.avg_selling_price < cp.min_competitor_price THEN 'DISCOUNT_PRICING'
        ELSE 'COMPETITIVE_PRICING'
    END as pricing_position,
    -- Optimization recommendations
    CASE 
        WHEN ec.price_elasticity > -0.5 AND ec.avg_selling_price < cp.avg_competitor_price THEN 'INCREASE_PRICE'
        WHEN ec.price_elasticity < -1.5 AND ec.avg_selling_price > cp.avg_competitor_price THEN 'DECREASE_PRICE'
        WHEN ec.price_volatility > 5 THEN 'STABILIZE_PRICING'
        ELSE 'MAINTAIN_CURRENT_PRICE'
    END as pricing_recommendation
FROM elasticity_calculation ec
LEFT JOIN competitor_pricing cp ON ec.product_id = cp.product_id
ORDER BY ec.total_revenue DESC; 