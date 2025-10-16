SELECT
    CAST(COUNT(o.order_id) AS FLOAT64) / COUNT(DISTINCT u.id) AS conversion_rate_orders_per_user
FROM
    `bigquery-public-data.thelook_ecommerce.users` AS u
LEFT JOIN
    `bigquery-public-data.thelook_ecommerce.orders` AS o
ON
    u.id = o.user_id
WHERE
    -- Filter orders to include only those created in the past 6 months
    -- Using TIMESTAMP_SUB for TIMESTAMP columns as per BigQuery best practices
    o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH)
    -- Note: If we only wanted to count users who *have* placed orders in the last 6 months,
    -- we would use an INNER JOIN and remove the DISTINCT from COUNT(DISTINCT u.id).
    -- However, the requirement "orders per user" implies we should consider all users,
    -- even those with zero orders in the period, to get an average.
    -- The LEFT JOIN ensures all users are included.
    -- For users with no orders in the past 6 months, o.order_id will be NULL.
    -- COUNT(o.order_id) will correctly count 0 for these users.
    -- COUNT(DISTINCT u.id) will count all unique users.