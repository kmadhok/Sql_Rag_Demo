-- Advanced Sales Forecasting Model
-- Time series analysis for predicting future sales trends

WITH monthly_sales AS (
    SELECT 
        DATE_TRUNC('month', order_date) as sales_month,
        SUM(unit_price * quantity * (1 - discount_rate)) as monthly_revenue,
        COUNT(DISTINCT order_id) as monthly_orders,
        COUNT(DISTINCT customer_id) as monthly_customers
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '24 months'
    GROUP BY DATE_TRUNC('month', order_date)
),
seasonal_patterns AS (
    SELECT 
        EXTRACT(MONTH FROM sales_month) as month_number,
        AVG(monthly_revenue) as avg_monthly_revenue,
        STDDEV(monthly_revenue) as revenue_std_dev,
        COUNT(*) as data_points
    FROM monthly_sales
    GROUP BY EXTRACT(MONTH FROM sales_month)
),
trend_analysis AS (
    SELECT 
        sales_month,
        monthly_revenue,
        LAG(monthly_revenue, 1) OVER (ORDER BY sales_month) as prev_month_revenue,
        LAG(monthly_revenue, 12) OVER (ORDER BY sales_month) as same_month_prev_year,
        AVG(monthly_revenue) OVER (
            ORDER BY sales_month 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as three_month_avg,
        AVG(monthly_revenue) OVER (
            ORDER BY sales_month 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) as twelve_month_avg
    FROM monthly_sales
),
forecast_base AS (
    SELECT 
        ta.*,
        sp.avg_monthly_revenue as seasonal_baseline,
        sp.revenue_std_dev as seasonal_volatility,
        CASE 
            WHEN ta.same_month_prev_year > 0 THEN 
                (ta.monthly_revenue - ta.same_month_prev_year) / ta.same_month_prev_year
            ELSE 0
        END as yoy_growth_rate,
        CASE 
            WHEN ta.prev_month_revenue > 0 THEN 
                (ta.monthly_revenue - ta.prev_month_revenue) / ta.prev_month_revenue
            ELSE 0
        END as mom_growth_rate
    FROM trend_analysis ta
    JOIN seasonal_patterns sp ON EXTRACT(MONTH FROM ta.sales_month) = sp.month_number
)
SELECT 
    sales_month,
    ROUND(monthly_revenue, 2) as actual_revenue,
    ROUND(three_month_avg, 2) as three_month_trend,
    ROUND(twelve_month_avg, 2) as annual_trend,
    ROUND(seasonal_baseline, 2) as seasonal_baseline,
    ROUND(yoy_growth_rate * 100, 2) as yoy_growth_pct,
    ROUND(mom_growth_rate * 100, 2) as mom_growth_pct,
    -- Simple forecast using trend + seasonality
    ROUND(
        (twelve_month_avg * 0.7) + 
        (seasonal_baseline * 0.3) * 
        (1 + COALESCE(yoy_growth_rate, 0) * 0.5)
    , 2) as forecast_revenue,
    ROUND(seasonal_volatility, 2) as forecast_confidence_range,
    CASE 
        WHEN yoy_growth_rate > 0.1 THEN 'GROWING'
        WHEN yoy_growth_rate < -0.1 THEN 'DECLINING'
        ELSE 'STABLE'
    END as trend_direction,
    CASE 
        WHEN seasonal_volatility / seasonal_baseline > 0.3 THEN 'HIGH_VOLATILITY'
        WHEN seasonal_volatility / seasonal_baseline > 0.15 THEN 'MEDIUM_VOLATILITY'
        ELSE 'LOW_VOLATILITY'
    END as seasonality_pattern
FROM forecast_base
WHERE sales_month >= CURRENT_DATE - INTERVAL '12 months'
ORDER BY sales_month DESC;