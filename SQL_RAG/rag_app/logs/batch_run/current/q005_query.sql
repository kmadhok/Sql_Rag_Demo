WITH MonthlyOrders AS (
  -- Calculate the number of orders per user in the last 6 months
  SELECT
    o.user_id,
    COUNT(o.order_id) AS orders_in_period
  FROM
    `bigquery-public-data.thelook_ecommerce.orders` AS o
  WHERE
    o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH) -- Filter orders within the last 6 months using TIMESTAMP_SUB
  GROUP BY
    o.user_id
),
TotalUsers AS (
  -- Calculate the total number of unique users
  SELECT
    COUNT(DISTINCT id) AS total_unique_users
  FROM
    `bigquery-public-data.thelook_ecommerce.users`
)
-- Calculate the conversion rate: total orders in the period / total unique users
SELECT
  CAST(SUM(mo.orders_in_period) AS FLOAT64) / tu.total_unique_users AS conversion_rate
FROM
  MonthlyOrders AS mo
CROSS JOIN
  TotalUsers AS tu;