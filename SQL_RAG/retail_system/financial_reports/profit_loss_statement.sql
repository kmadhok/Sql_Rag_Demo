-- Profit & Loss Statement Generator
-- Generates comprehensive P&L reports for specified time periods

WITH revenue_breakdown AS (
    SELECT 
        EXTRACT(YEAR FROM order_date) as fiscal_year,
        EXTRACT(MONTH FROM order_date) as fiscal_month,
        pc.category_name,
        s.store_id,
        s.store_name,
        -- Gross Revenue
        SUM(st.unit_price * st.quantity) as gross_sales,
        SUM(st.unit_price * st.quantity * st.discount_rate) as total_discounts,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_sales,
        SUM(st.unit_price * st.quantity * st.tax_rate) as sales_tax_collected
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    JOIN stores s ON st.store_id = s.store_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '24 months'
    GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date), 
             pc.category_name, s.store_id, s.store_name
),
cost_of_goods_sold AS (
    SELECT 
        EXTRACT(YEAR FROM order_date) as fiscal_year,
        EXTRACT(MONTH FROM order_date) as fiscal_month,
        pc.category_name,
        s.store_id,
        -- Cost of Goods Sold
        SUM(p.unit_cost * st.quantity) as cogs,
        SUM(st.quantity) as units_sold
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    JOIN stores s ON st.store_id = s.store_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '24 months'
    GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date),
             pc.category_name, s.store_id
),
operating_expenses AS (
    SELECT 
        EXTRACT(YEAR FROM expense_date) as fiscal_year,
        EXTRACT(MONTH FROM expense_date) as fiscal_month,
        store_id,
        expense_category,
        SUM(expense_amount) as total_expense
    FROM operating_expenses
    WHERE expense_date >= CURRENT_DATE - INTERVAL '24 months'
    GROUP BY EXTRACT(YEAR FROM expense_date), EXTRACT(MONTH FROM expense_date),
             store_id, expense_category
),
expense_summary AS (
    SELECT 
        fiscal_year,
        fiscal_month,
        store_id,
        SUM(CASE WHEN expense_category = 'RENT' THEN total_expense ELSE 0 END) as rent_expense,
        SUM(CASE WHEN expense_category = 'SALARIES' THEN total_expense ELSE 0 END) as salary_expense,
        SUM(CASE WHEN expense_category = 'MARKETING' THEN total_expense ELSE 0 END) as marketing_expense,
        SUM(CASE WHEN expense_category = 'UTILITIES' THEN total_expense ELSE 0 END) as utilities_expense,
        SUM(CASE WHEN expense_category = 'INSURANCE' THEN total_expense ELSE 0 END) as insurance_expense,
        SUM(CASE WHEN expense_category = 'MAINTENANCE' THEN total_expense ELSE 0 END) as maintenance_expense,
        SUM(CASE WHEN expense_category = 'OTHER' THEN total_expense ELSE 0 END) as other_expenses,
        SUM(total_expense) as total_operating_expenses
    FROM operating_expenses
    GROUP BY fiscal_year, fiscal_month, store_id
),
consolidated_pl AS (
    SELECT 
        rb.fiscal_year,
        rb.fiscal_month,
        rb.store_id,
        rb.store_name,
        rb.category_name,
        
        -- Revenue Section
        rb.gross_sales,
        rb.total_discounts,
        rb.net_sales,
        rb.sales_tax_collected,
        
        -- Cost of Goods Sold
        cogs.cogs,
        cogs.units_sold,
        
        -- Gross Profit
        rb.net_sales - cogs.cogs as gross_profit,
        ROUND((rb.net_sales - cogs.cogs) / NULLIF(rb.net_sales, 0) * 100, 2) as gross_margin_pct,
        
        -- Operating Expenses
        COALESCE(es.rent_expense, 0) as rent_expense,
        COALESCE(es.salary_expense, 0) as salary_expense,
        COALESCE(es.marketing_expense, 0) as marketing_expense,
        COALESCE(es.utilities_expense, 0) as utilities_expense,
        COALESCE(es.insurance_expense, 0) as insurance_expense,
        COALESCE(es.maintenance_expense, 0) as maintenance_expense,
        COALESCE(es.other_expenses, 0) as other_expenses,
        COALESCE(es.total_operating_expenses, 0) as total_operating_expenses,
        
        -- Operating Profit
        (rb.net_sales - cogs.cogs) - COALESCE(es.total_operating_expenses, 0) as operating_profit,
        ROUND(((rb.net_sales - cogs.cogs) - COALESCE(es.total_operating_expenses, 0)) / NULLIF(rb.net_sales, 0) * 100, 2) as operating_margin_pct
        
    FROM revenue_breakdown rb
    LEFT JOIN cost_of_goods_sold cogs ON rb.fiscal_year = cogs.fiscal_year 
                                       AND rb.fiscal_month = cogs.fiscal_month 
                                       AND rb.store_id = cogs.store_id 
                                       AND rb.category_name = cogs.category_name
    LEFT JOIN expense_summary es ON rb.fiscal_year = es.fiscal_year 
                                   AND rb.fiscal_month = es.fiscal_month 
                                   AND rb.store_id = es.store_id
)
SELECT 
    fiscal_year,
    fiscal_month,
    CASE fiscal_month
        WHEN 1 THEN 'January'
        WHEN 2 THEN 'February'
        WHEN 3 THEN 'March'
        WHEN 4 THEN 'April'
        WHEN 5 THEN 'May'
        WHEN 6 THEN 'June'
        WHEN 7 THEN 'July'
        WHEN 8 THEN 'August'
        WHEN 9 THEN 'September'
        WHEN 10 THEN 'October'
        WHEN 11 THEN 'November'
        WHEN 12 THEN 'December'
    END as month_name,
    store_id,
    store_name,
    category_name,
    
    -- Revenue Metrics
    ROUND(gross_sales, 2) as gross_sales,
    ROUND(total_discounts, 2) as total_discounts,
    ROUND(net_sales, 2) as net_sales,
    
    -- Cost Metrics
    ROUND(cogs, 2) as cost_of_goods_sold,
    ROUND(gross_profit, 2) as gross_profit,
    gross_margin_pct,
    
    -- Operating Expenses
    ROUND(rent_expense, 2) as rent_expense,
    ROUND(salary_expense, 2) as salary_expense,
    ROUND(marketing_expense, 2) as marketing_expense,
    ROUND(utilities_expense, 2) as utilities_expense,
    ROUND(insurance_expense, 2) as insurance_expense,
    ROUND(maintenance_expense, 2) as maintenance_expense,
    ROUND(other_expenses, 2) as other_expenses,
    ROUND(total_operating_expenses, 2) as total_operating_expenses,
    
    -- Profitability
    ROUND(operating_profit, 2) as operating_profit,
    operating_margin_pct,
    
    -- Performance Indicators
    CASE 
        WHEN operating_margin_pct >= 15 THEN 'EXCELLENT'
        WHEN operating_margin_pct >= 10 THEN 'GOOD'
        WHEN operating_margin_pct >= 5 THEN 'FAIR'
        WHEN operating_margin_pct >= 0 THEN 'POOR'
        ELSE 'LOSS_MAKING'
    END as profitability_rating,
    
    units_sold,
    ROUND(net_sales / NULLIF(units_sold, 0), 2) as revenue_per_unit

FROM consolidated_pl
WHERE fiscal_year >= EXTRACT(YEAR FROM CURRENT_DATE) - 1
ORDER BY fiscal_year DESC, fiscal_month DESC, store_name, category_name; 