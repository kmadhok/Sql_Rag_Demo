-- Loyalty Program Management
-- Tracks customer loyalty points, redemptions, and program effectiveness

WITH loyalty_earnings AS (
    SELECT 
        customer_id,
        SUM(points_earned) as total_points_earned,
        COUNT(*) as earning_transactions
    FROM loyalty_transactions
    WHERE transaction_type = 'EARN'
    GROUP BY customer_id
),
loyalty_redemptions AS (
    SELECT 
        customer_id,
        SUM(ABS(points_earned)) as total_points_redeemed,
        COUNT(*) as redemption_transactions
    FROM loyalty_transactions
    WHERE transaction_type = 'REDEEM'
    GROUP BY customer_id
),
current_balances AS (
    SELECT 
        customer_id,
        SUM(points_earned) as current_point_balance
    FROM loyalty_transactions
    GROUP BY customer_id
),
tier_analysis AS (
    SELECT 
        customer_id,
        tier_name,
        tier_start_date,
        tier_end_date,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY tier_start_date DESC) as tier_rank
    FROM customer_tiers
    WHERE tier_end_date IS NULL OR tier_end_date >= CURRENT_DATE
)
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    ta.tier_name as current_tier,
    ta.tier_start_date,
    COALESCE(le.total_points_earned, 0) as total_points_earned,
    COALESCE(lr.total_points_redeemed, 0) as total_points_redeemed,
    COALESCE(cb.current_point_balance, 0) as current_point_balance,
    COALESCE(le.earning_transactions, 0) as earning_transactions,
    COALESCE(lr.redemption_transactions, 0) as redemption_transactions,
    CASE 
        WHEN COALESCE(le.total_points_earned, 0) > 0 THEN
            COALESCE(lr.total_points_redeemed, 0) / le.total_points_earned * 100
        ELSE 0
    END as redemption_rate_pct,
    CASE 
        WHEN COALESCE(cb.current_point_balance, 0) >= 10000 THEN 'HIGH_BALANCE'
        WHEN COALESCE(cb.current_point_balance, 0) >= 5000 THEN 'MEDIUM_BALANCE'
        WHEN COALESCE(cb.current_point_balance, 0) >= 1000 THEN 'LOW_BALANCE'
        ELSE 'MINIMAL_BALANCE'
    END as balance_category,
    DATEDIFF(CURRENT_DATE, ta.tier_start_date) as days_in_current_tier
FROM customers c
LEFT JOIN loyalty_earnings le ON c.customer_id = le.customer_id
LEFT JOIN loyalty_redemptions lr ON c.customer_id = lr.customer_id
LEFT JOIN current_balances cb ON c.customer_id = cb.customer_id
LEFT JOIN tier_analysis ta ON c.customer_id = ta.customer_id AND ta.tier_rank = 1
WHERE c.loyalty_program_member = TRUE
ORDER BY current_point_balance DESC; 