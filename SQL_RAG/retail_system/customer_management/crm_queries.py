"""
CRM Queries Module
SQL queries for customer relationship management operations
"""

def get_customer_churn_prediction_query():
    """Returns SQL query to identify customers at risk of churning"""
    return """
    WITH customer_metrics AS (
        SELECT 
            customer_id,
            DATEDIFF(CURRENT_DATE, MAX(order_date)) as days_since_last_order,
            COUNT(DISTINCT order_id) as total_orders,
            AVG(DATEDIFF(order_date, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date))) as avg_days_between_orders,
            SUM(unit_price * quantity * (1 - discount_rate)) as total_spent,
            AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '18 months'
        GROUP BY customer_id
        HAVING COUNT(DISTINCT order_id) >= 2
    ),
    churn_indicators AS (
        SELECT 
            *,
            CASE 
                WHEN days_since_last_order > avg_days_between_orders * 2 THEN 3
                WHEN days_since_last_order > avg_days_between_orders * 1.5 THEN 2
                WHEN days_since_last_order > avg_days_between_orders THEN 1
                ELSE 0
            END as recency_risk_score,
            CASE 
                WHEN total_orders <= 2 THEN 2
                WHEN total_orders <= 5 THEN 1
                ELSE 0
            END as frequency_risk_score,
            CASE 
                WHEN avg_order_value < 50 THEN 2
                WHEN avg_order_value < 100 THEN 1
                ELSE 0
            END as monetary_risk_score
        FROM customer_metrics
    )
    SELECT 
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        ci.days_since_last_order,
        ci.total_orders,
        ci.avg_days_between_orders,
        ci.total_spent,
        ci.avg_order_value,
        ci.recency_risk_score + ci.frequency_risk_score + ci.monetary_risk_score as total_churn_risk_score,
        CASE 
            WHEN ci.recency_risk_score + ci.frequency_risk_score + ci.monetary_risk_score >= 5 THEN 'HIGH_RISK'
            WHEN ci.recency_risk_score + ci.frequency_risk_score + ci.monetary_risk_score >= 3 THEN 'MEDIUM_RISK'
            WHEN ci.recency_risk_score + ci.frequency_risk_score + ci.monetary_risk_score >= 1 THEN 'LOW_RISK'
            ELSE 'HEALTHY'
        END as churn_risk_category
    FROM customers c
    JOIN churn_indicators ci ON c.customer_id = ci.customer_id
    ORDER BY total_churn_risk_score DESC, days_since_last_order DESC;
    """

def get_customer_lifetime_value_query():
    """Returns SQL query to calculate customer lifetime value"""
    return """
    WITH customer_cohorts AS (
        SELECT 
            customer_id,
            DATE_TRUNC('month', MIN(order_date)) as cohort_month
        FROM sales_transactions
        GROUP BY customer_id
    ),
    monthly_revenue AS (
        SELECT 
            st.customer_id,
            cc.cohort_month,
            DATE_TRUNC('month', st.order_date) as order_month,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as monthly_revenue,
            DATEDIFF(DATE_TRUNC('month', st.order_date), cc.cohort_month) / 30 as months_since_first_order
        FROM sales_transactions st
        JOIN customer_cohorts cc ON st.customer_id = cc.customer_id
        GROUP BY st.customer_id, cc.cohort_month, DATE_TRUNC('month', st.order_date)
    ),
    customer_lifespan AS (
        SELECT 
            customer_id,
            cohort_month,
            COUNT(DISTINCT order_month) as active_months,
            SUM(monthly_revenue) as total_revenue,
            AVG(monthly_revenue) as avg_monthly_revenue,
            MAX(months_since_first_order) as customer_age_months
        FROM monthly_revenue
        GROUP BY customer_id, cohort_month
    )
    SELECT 
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        cl.cohort_month,
        cl.active_months,
        cl.customer_age_months,
        cl.total_revenue as historical_clv,
        cl.avg_monthly_revenue,
        cl.avg_monthly_revenue * 12 as estimated_annual_value,
        CASE 
            WHEN cl.customer_age_months > 0 THEN
                cl.total_revenue / (cl.customer_age_months / 12.0)
            ELSE cl.total_revenue
        END as annualized_clv,
        CASE 
            WHEN cl.avg_monthly_revenue > 0 THEN
                cl.avg_monthly_revenue * 24  -- Predict 24 month CLV
            ELSE 0
        END as predicted_24m_clv
    FROM customers c
    JOIN customer_lifespan cl ON c.customer_id = cl.customer_id
    ORDER BY cl.total_revenue DESC;
    """

def get_marketing_campaign_response_query(campaign_id):
    """Returns SQL query to analyze marketing campaign response"""
    return f"""
    WITH campaign_targets AS (
        SELECT 
            customer_id,
            campaign_send_date,
            channel_type,
            offer_type
        FROM marketing_campaigns
        WHERE campaign_id = '{campaign_id}'
    ),
    campaign_responses AS (
        SELECT 
            ct.customer_id,
            ct.campaign_send_date,
            ct.channel_type,
            ct.offer_type,
            MIN(st.order_date) as first_order_after_campaign,
            COUNT(DISTINCT st.order_id) as orders_after_campaign,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as revenue_after_campaign
        FROM campaign_targets ct
        LEFT JOIN sales_transactions st ON ct.customer_id = st.customer_id 
            AND st.order_date BETWEEN ct.campaign_send_date AND ct.campaign_send_date + INTERVAL '30 days'
        GROUP BY ct.customer_id, ct.campaign_send_date, ct.channel_type, ct.offer_type
    )
    SELECT 
        channel_type,
        offer_type,
        COUNT(*) as total_sent,
        COUNT(first_order_after_campaign) as responded_customers,
        ROUND(COUNT(first_order_after_campaign) * 100.0 / COUNT(*), 2) as response_rate_pct,
        SUM(orders_after_campaign) as total_orders_generated,
        SUM(revenue_after_campaign) as total_revenue_generated,
        AVG(revenue_after_campaign) as avg_revenue_per_target,
        AVG(CASE WHEN first_order_after_campaign IS NOT NULL THEN revenue_after_campaign END) as avg_revenue_per_responder,
        AVG(DATEDIFF(first_order_after_campaign, campaign_send_date)) as avg_days_to_response
    FROM campaign_responses
    GROUP BY channel_type, offer_type
    ORDER BY response_rate_pct DESC;
    """ 