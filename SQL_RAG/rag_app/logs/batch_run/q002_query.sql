WITH MonthlyRevenue AS (
  SELECT
    -- Extract year and month from the order creation timestamp for grouping
    EXTRACT(YEAR FROM o.created_at) AS order_year,
    EXTRACT(MONTH FROM o.created_at) AS order_month,
    -- Calculate total revenue for each order by summing sale prices of its items
    SUM(oi.sale_price) AS monthly_revenue,
    -- Count the number of distinct orders for each month
    COUNT(DISTINCT o.order_id) AS monthly_orders
  FROM
    `bigquery-public-data.thelook_ecommerce.orders` AS o
  JOIN
    `bigquery-public-data.thelook_ecommerce.order_items` AS oi
  ON
    o.order_id = oi.order_id
  WHERE
    -- Filter orders to include only those created within the last 90 days
    -- Using TIMESTAMP_SUB for TIMESTAMP columns as per BigQuery best practices
    o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  GROUP BY
    order_year,
    order_month
)
SELECT
  -- Combine year and month to display as a single month identifier
  -- CAST to STRING for consistent output format
  CAST(order_year AS STRING) || '-' || LPAD(CAST(order_month AS STRING), 2, '0') AS order_month_year,
  monthly_orders,
  monthly_revenue
FROM
  MonthlyRevenue
ORDER BY
  order_month_year;