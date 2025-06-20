# SQL Query Catalog

### Query #1 – create_tables.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/database_schema/create_tables.sql

```sql
-- Retail Database Schema Creation
-- Core tables for a retail management system

-- Product Categories Table
CREATE TABLE product_categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT,
    category_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES product_categories(category_id)
);

-- Brands Table
CREATE TABLE brands (
    brand_id INT PRIMARY KEY AUTO_INCREMENT,
    brand_name VARCHAR(100) NOT NULL UNIQUE,
    brand_description TEXT,
    website_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Suppliers Table
CREATE TABLE suppliers (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    supplier_name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    payment_terms VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Products Table
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    barcode VARCHAR(50),
    category_id INT NOT NULL,
    brand_id INT,
    supplier_id INT,
    unit_cost DECIMAL(10,2) NOT NULL,
    retail_price DECIMAL(10,2) NOT NULL,
    weight DECIMAL(8,3),
    unit_volume DECIMAL(8,3),
    product_description TEXT,
    specifications JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id),
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    INDEX idx_sku (sku),
    INDEX idx_category (category_id),
    INDEX idx_brand (brand_id)
);

-- Stores Table
CREATE TABLE stores (
    store_id INT PRIMARY KEY AUTO_INCREMENT,
    store_name VARCHAR(100) NOT NULL,
    store_code VARCHAR(20) UNIQUE NOT NULL,
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(100),
    manager_name VARCHAR(100),
    store_type ENUM('FLAGSHIP', 'REGULAR', 'OUTLET', 'ONLINE') DEFAULT 'REGULAR',
    square_footage INT,
    is_active BOOLEAN DEFAULT TRUE,
    opening_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Customers Table
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender ENUM('M', 'F', 'OTHER'),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    registration_date DATE NOT NULL,
    loyalty_program_member BOOLEAN DEFAULT FALSE,
    preferred_contact_method ENUM('EMAIL', 'PHONE', 'SMS') DEFAULT 'EMAIL',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_registration_date (registration_date)
);

-- Sales Transactions Table
CREATE TABLE sales_transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(50) NOT NULL,
    customer_id INT,
    store_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_rate DECIMAL(5,4) DEFAULT 0.0000,
    tax_rate DECIMAL(5,4) DEFAULT 0.0000,
    order_date TIMESTAMP NOT NULL,
    sales_person_id INT,
    payment_method ENUM('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'GIFT_CARD', 'STORE_CREDIT') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    INDEX idx_order_date (order_date),
    INDEX idx_customer (customer_id),
    INDEX idx_store (store_id),
    INDEX idx_product (product_id)
);
```

---

### Query #2 – inventory_turnover.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/inventory_turnover.sql

```sql
-- Inventory Turnover Analysis
-- Calculates inventory turnover ratios and identifies slow-moving stock

WITH inventory_movements AS (
    SELECT 
        product_id,
        SUM(CASE WHEN movement_type = 'SALE' THEN -quantity ELSE quantity END) as net_movement,
        SUM(CASE WHEN movement_type = 'SALE' THEN quantity ELSE 0 END) as total_sold,
        COUNT(CASE WHEN movement_type = 'SALE' THEN 1 END) as sale_transactions
    FROM inventory_movements
    WHERE movement_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY product_id
),
average_inventory AS (
    SELECT 
        product_id,
        AVG(current_stock) as avg_stock_level
    FROM inventory_snapshots
    WHERE snapshot_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY product_id
),
cost_analysis AS (
    SELECT 
        st.product_id,
        SUM(st.quantity * p.unit_cost) as cogs_annual
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY st.product_id
)
SELECT 
    p.product_id,
    p.product_name,
    p.sku,
    pc.category_name,
    COALESCE(im.total_sold, 0) as units_sold_ytd,
    COALESCE(ai.avg_stock_level, 0) as avg_inventory_level,
    COALESCE(ca.cogs_annual, 0) as cogs_annual,
    p.unit_cost * COALESCE(ai.avg_stock_level, 0) as avg_inventory_value,
    CASE 
        WHEN ai.avg_stock_level > 0 AND ca.cogs_annual > 0 THEN 
            ca.cogs_annual / (p.unit_cost * ai.avg_stock_level)
        ELSE 0
    END as inventory_turnover_ratio,
    CASE 
        WHEN im.total_sold > 0 AND ai.avg_stock_level > 0 THEN
            365.0 / (ca.cogs_annual / (p.unit_cost * ai.avg_stock_level))
        ELSE NULL
    END as days_to_sell_inventory,
    CASE 
        WHEN COALESCE(im.total_sold, 0) = 0 THEN 'NO_SALES'
        WHEN ca.cogs_annual / (p.unit_cost * ai.avg_stock_level) < 2 THEN 'SLOW_MOVING'
        WHEN ca.cogs_annual / (p.unit_cost * ai.avg_stock_level) > 12 THEN 'FAST_MOVING'
        ELSE 'NORMAL'
    END as movement_category
FROM products p
JOIN product_categories pc ON p.category_id = pc.category_id
LEFT JOIN inventory_movements im ON p.product_id = im.product_id
LEFT JOIN average_inventory ai ON p.product_id = ai.product_id
LEFT JOIN cost_analysis ca ON p.product_id = ca.product_id
ORDER BY inventory_turnover_ratio DESC;
```

---

### Query #3 – stock_levels.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/stock_levels.sql

```sql
-- Current Stock Levels and Reorder Analysis
-- Identifies products that need restocking based on current inventory and sales velocity

WITH sales_velocity AS (
    SELECT 
        product_id,
        AVG(daily_sales) as avg_daily_sales,
        STDDEV(daily_sales) as sales_stddev
    FROM (
        SELECT 
            product_id,
            DATE(order_date) as sale_date,
            SUM(quantity) as daily_sales
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY product_id, DATE(order_date)
    ) daily_totals
    GROUP BY product_id
),
current_inventory AS (
    SELECT 
        i.product_id,
        p.product_name,
        p.sku,
        i.current_stock,
        i.reserved_stock,
        i.available_stock,
        i.reorder_point,
        i.max_stock_level,
        p.unit_cost,
        pc.category_name
    FROM inventory i
    JOIN products p ON i.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
)
SELECT 
    ci.product_id,
    ci.product_name,
    ci.sku,
    ci.category_name,
    ci.current_stock,
    ci.available_stock,
    ci.reorder_point,
    ci.max_stock_level,
    COALESCE(sv.avg_daily_sales, 0) as avg_daily_sales,
    CASE 
        WHEN sv.avg_daily_sales > 0 THEN ci.available_stock / sv.avg_daily_sales
        ELSE NULL
    END as days_of_stock,
    CASE 
        WHEN ci.available_stock <= ci.reorder_point THEN 'REORDER_NOW'
        WHEN ci.available_stock <= ci.reorder_point * 1.2 THEN 'LOW_STOCK'
        WHEN ci.available_stock >= ci.max_stock_level * 0.9 THEN 'OVERSTOCK'
        ELSE 'NORMAL'
    END as stock_status,
    ci.unit_cost * ci.available_stock as inventory_value
FROM current_inventory ci
LEFT JOIN sales_velocity sv ON ci.product_id = sv.product_id
ORDER BY 
    CASE 
        WHEN ci.available_stock <= ci.reorder_point THEN 1
        WHEN ci.available_stock <= ci.reorder_point * 1.2 THEN 2
        ELSE 3
    END,
    ci.available_stock / NULLIF(sv.avg_daily_sales, 0) ASC;
```

---

### Query #4 – supplier_performance.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/supply_chain/supplier_performance.sql

```sql
-- Supplier Performance Analysis
-- Evaluates supplier reliability, quality, and cost effectiveness

WITH supplier_metrics AS (
    SELECT 
        s.supplier_id,
        s.supplier_name,
        COUNT(DISTINCT po.purchase_order_id) as total_orders,
        COUNT(DISTINCT p.product_id) as products_supplied,
        SUM(po.order_total) as total_order_value,
        AVG(po.order_total) as avg_order_value,
        AVG(DATEDIFF(po.delivery_date, po.order_date)) as avg_delivery_days,
        AVG(DATEDIFF(po.promised_delivery_date, po.delivery_date)) as avg_delivery_variance_days
    FROM suppliers s
    JOIN products p ON s.supplier_id = p.supplier_id
    JOIN purchase_orders po ON s.supplier_id = po.supplier_id
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    AND po.order_status = 'COMPLETED'
    GROUP BY s.supplier_id, s.supplier_name
),
quality_metrics AS (
    SELECT 
        po.supplier_id,
        COUNT(*) as total_deliveries,
        SUM(CASE WHEN qc.quality_rating >= 4 THEN 1 ELSE 0 END) as good_quality_deliveries,
        AVG(qc.quality_rating) as avg_quality_rating,
        SUM(qc.defect_quantity) as total_defects,
        SUM(qc.received_quantity) as total_received_quantity
    FROM purchase_orders po
    JOIN quality_control qc ON po.purchase_order_id = qc.purchase_order_id
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY po.supplier_id
),
cost_analysis AS (
    SELECT 
        p.supplier_id,
        AVG(p.unit_cost) as avg_unit_cost,
        MIN(p.unit_cost) as min_unit_cost,
        MAX(p.unit_cost) as max_unit_cost,
        STDDEV(p.unit_cost) as cost_variability
    FROM products p
    WHERE p.is_active = TRUE
    GROUP BY p.supplier_id
),
delivery_performance AS (
    SELECT 
        po.supplier_id,
        COUNT(*) as total_deliveries,
        SUM(CASE WHEN po.delivery_date <= po.promised_delivery_date THEN 1 ELSE 0 END) as on_time_deliveries,
        SUM(CASE WHEN po.delivery_date > po.promised_delivery_date THEN 1 ELSE 0 END) as late_deliveries,
        AVG(CASE WHEN po.delivery_date > po.promised_delivery_date 
                 THEN DATEDIFF(po.delivery_date, po.promised_delivery_date) 
                 ELSE 0 END) as avg_late_days
    FROM purchase_orders po
    WHERE po.order_date >= CURRENT_DATE - INTERVAL '12 months'
    AND po.delivery_date IS NOT NULL
    GROUP BY po.supplier_id
)
SELECT 
    sm.supplier_id,
    sm.supplier_name,
    sm.total_orders,
    sm.products_supplied,
    sm.total_order_value,
    sm.avg_order_value,
    sm.avg_delivery_days,
    
    -- Delivery Performance
    dp.total_deliveries,
    dp.on_time_deliveries,
    ROUND(dp.on_time_deliveries * 100.0 / dp.total_deliveries, 2) as on_time_delivery_rate,
    dp.late_deliveries,
    dp.avg_late_days,
    
    -- Quality Metrics
    qm.good_quality_deliveries,
    ROUND(qm.good_quality_deliveries * 100.0 / qm.total_deliveries, 2) as quality_rate,
    ROUND(qm.avg_quality_rating, 2) as avg_quality_rating,
    ROUND(qm.total_defects * 100.0 / qm.total_received_quantity, 4) as defect_rate,
    
    -- Cost Analysis
    ca.avg_unit_cost,
    ca.cost_variability,
    
    -- Overall Supplier Score (weighted composite)
    ROUND(
        (dp.on_time_deliveries * 100.0 / dp.total_deliveries) * 0.3 +  -- 30% weight on delivery
        (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) * 0.4 +  -- 40% weight on quality
        (100 - (qm.total_defects * 100.0 / qm.total_received_quantity)) * 0.2 +  -- 20% weight on defects
        GREATEST(0, 100 - sm.avg_delivery_variance_days * 2) * 0.1  -- 10% weight on delivery consistency
    , 2) as supplier_performance_score,
    
    -- Supplier Classification
    CASE 
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 95 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 90 
         AND (qm.total_defects * 100.0 / qm.total_received_quantity) <= 2 THEN 'PREFERRED'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 85 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 80 THEN 'APPROVED'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) >= 70 
         AND (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) >= 70 THEN 'CONDITIONAL'
        ELSE 'UNDER_REVIEW'
    END as supplier_status,
    
    -- Risk Assessment
    CASE 
        WHEN sm.total_orders < 5 THEN 'NEW_SUPPLIER_RISK'
        WHEN (dp.on_time_deliveries * 100.0 / dp.total_deliveries) < 75 THEN 'DELIVERY_RISK'
        WHEN (qm.total_defects * 100.0 / qm.total_received_quantity) > 5 THEN 'QUALITY_RISK'
        WHEN ca.cost_variability > (ca.avg_unit_cost * 0.2) THEN 'COST_VOLATILITY_RISK'
        ELSE 'LOW_RISK'
    END as risk_category

FROM supplier_metrics sm
LEFT JOIN quality_metrics qm ON sm.supplier_id = qm.supplier_id
LEFT JOIN cost_analysis ca ON sm.supplier_id = ca.supplier_id
LEFT JOIN delivery_performance dp ON sm.supplier_id = dp.supplier_id
ORDER BY 
    ROUND(
        (dp.on_time_deliveries * 100.0 / dp.total_deliveries) * 0.3 +
        (qm.good_quality_deliveries * 100.0 / qm.total_deliveries) * 0.4 +
        (100 - (qm.total_defects * 100.0 / qm.total_received_quantity)) * 0.2 +
        GREATEST(0, 100 - sm.avg_delivery_variance_days * 2) * 0.1
    , 2) DESC;
```

---

### Query #5 – inventory_procedures.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/stored_procedures/inventory_procedures.sql

```sql
-- Inventory Management Stored Procedures
-- Procedures for common inventory operations and calculations

DELIMITER $$

-- Procedure to update inventory levels after a sale
CREATE PROCEDURE UpdateInventoryAfterSale(
    IN p_product_id INT,
    IN p_quantity_sold INT,
    IN p_store_id INT
)
BEGIN
    DECLARE v_current_stock INT DEFAULT 0;
    DECLARE v_reserved_stock INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Get current inventory levels
    SELECT current_stock, reserved_stock 
    INTO v_current_stock, v_reserved_stock
    FROM inventory 
    WHERE product_id = p_product_id AND store_id = p_store_id;

    -- Update inventory levels
    UPDATE inventory 
    SET current_stock = current_stock - p_quantity_sold,
        available_stock = current_stock - p_quantity_sold - reserved_stock,
        last_updated = CURRENT_TIMESTAMP
    WHERE product_id = p_product_id AND store_id = p_store_id;

    -- Log inventory movement
    INSERT INTO inventory_movements (
        product_id, store_id, movement_type, quantity, 
        movement_date, reference_type, reference_id
    ) VALUES (
        p_product_id, p_store_id, 'SALE', -p_quantity_sold,
        CURRENT_TIMESTAMP, 'SALE', LAST_INSERT_ID()
    );

    COMMIT;
END$$

-- Procedure to receive inventory from purchase orders
CREATE PROCEDURE ReceiveInventory(
    IN p_product_id INT,
    IN p_store_id INT,
    IN p_quantity_received INT,
    IN p_purchase_order_id VARCHAR(50),
    IN p_unit_cost DECIMAL(10,2)
)
BEGIN
    DECLARE v_current_stock INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Update or insert inventory record
    INSERT INTO inventory (product_id, store_id, current_stock, available_stock, last_updated)
    VALUES (p_product_id, p_store_id, p_quantity_received, p_quantity_received, CURRENT_TIMESTAMP)
    ON DUPLICATE KEY UPDATE 
        current_stock = current_stock + p_quantity_received,
        available_stock = available_stock + p_quantity_received,
        last_updated = CURRENT_TIMESTAMP;

    -- Log inventory movement
    INSERT INTO inventory_movements (
        product_id, store_id, movement_type, quantity, unit_cost,
        movement_date, reference_type, reference_id
    ) VALUES (
        p_product_id, p_store_id, 'RECEIPT', p_quantity_received, p_unit_cost,
        CURRENT_TIMESTAMP, 'PURCHASE_ORDER', p_purchase_order_id
    );

    -- Update product cost if provided
    IF p_unit_cost > 0 THEN
        UPDATE products 
        SET unit_cost = p_unit_cost, updated_at = CURRENT_TIMESTAMP
        WHERE product_id = p_product_id;
    END IF;

    COMMIT;
END$$

-- Procedure to perform inventory transfer between stores
CREATE PROCEDURE TransferInventory(
    IN p_product_id INT,
    IN p_from_store_id INT,
    IN p_to_store_id INT,
    IN p_quantity INT,
    IN p_transfer_reference VARCHAR(50)
)
BEGIN
    DECLARE v_available_stock INT DEFAULT 0;
    DECLARE v_insufficient_stock CONDITION FOR SQLSTATE '45000';
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Check available stock at source store
    SELECT available_stock INTO v_available_stock
    FROM inventory 
    WHERE product_id = p_product_id AND store_id = p_from_store_id;

    IF v_available_stock < p_quantity THEN
        SIGNAL v_insufficient_stock 
        SET MESSAGE_TEXT = 'Insufficient stock for transfer';
    END IF;

    -- Reduce inventory at source store
    UPDATE inventory 
    SET current_stock = current_stock - p_quantity,
        available_stock = available_stock - p_quantity,
        last_updated = CURRENT_TIMESTAMP
    WHERE product_id = p_product_id AND store_id = p_from_store_id;

    -- Increase inventory at destination store
    INSERT INTO inventory (product_id, store_id, current_stock, available_stock, last_updated)
    VALUES (p_product_id, p_to_store_id, p_quantity, p_quantity, CURRENT_TIMESTAMP)
    ON DUPLICATE KEY UPDATE 
        current_stock = current_stock + p_quantity,
        available_stock = available_stock + p_quantity,
        last_updated = CURRENT_TIMESTAMP;

    -- Log outbound movement
    INSERT INTO inventory_movements (
        product_id, store_id, movement_type, quantity,
        movement_date, reference_type, reference_id
    ) VALUES (
        p_product_id, p_from_store_id, 'TRANSFER_OUT', -p_quantity,
        CURRENT_TIMESTAMP, 'TRANSFER', p_transfer_reference
    );

    -- Log inbound movement
    INSERT INTO inventory_movements (
        product_id, store_id, movement_type, quantity,
        movement_date, reference_type, reference_id
    ) VALUES (
        p_product_id, p_to_store_id, 'TRANSFER_IN', p_quantity,
        CURRENT_TIMESTAMP, 'TRANSFER', p_transfer_reference
    );

    COMMIT;
END$$

-- Function to calculate inventory turnover ratio
CREATE FUNCTION GetInventoryTurnover(
    p_product_id INT,
    p_store_id INT,
    p_period_days INT
) RETURNS DECIMAL(10,4)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_cogs DECIMAL(15,2) DEFAULT 0;
    DECLARE v_avg_inventory DECIMAL(15,2) DEFAULT 0;
    DECLARE v_turnover DECIMAL(10,4) DEFAULT 0;

    -- Calculate Cost of Goods Sold for the period
    SELECT COALESCE(SUM(st.quantity * p.unit_cost), 0)
    INTO v_cogs
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    WHERE st.product_id = p_product_id 
    AND st.store_id = p_store_id
    AND st.order_date >= DATE_SUB(CURRENT_DATE, INTERVAL p_period_days DAY);

    -- Calculate average inventory value
    SELECT COALESCE(AVG(i.current_stock * p.unit_cost), 0)
    INTO v_avg_inventory
    FROM inventory_snapshots i
    JOIN products p ON i.product_id = p.product_id
    WHERE i.product_id = p_product_id 
    AND i.store_id = p_store_id
    AND i.snapshot_date >= DATE_SUB(CURRENT_DATE, INTERVAL p_period_days DAY);

    -- Calculate turnover ratio
    IF v_avg_inventory > 0 THEN
        SET v_turnover = v_cogs / v_avg_inventory;
    END IF;

    RETURN v_turnover;
END$$

DELIMITER ;
```

---

### Query #6 – dynamic_pricing.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/pricing_optimization/dynamic_pricing.sql

```sql
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
```

---

### Query #7 – profit_loss_statement.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/financial_reports/profit_loss_statement.sql

```sql
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
```

---

### Query #8 – loyalty_program.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/customer_management/loyalty_program.sql

```sql
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
```

---

### Query #9 – customer_analysis.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/customer_management/customer_analysis.sql

```sql
-- Customer Behavior Analysis
-- Comprehensive analysis of customer purchasing patterns and lifetime value

WITH customer_purchase_history AS (
    SELECT 
        customer_id,
        MIN(order_date) as first_purchase_date,
        MAX(order_date) as last_purchase_date,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT DATE(order_date)) as shopping_days,
        SUM(unit_price * quantity * (1 - discount_rate)) as total_spent,
        AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value,
        DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifespan_days
    FROM sales_transactions
    GROUP BY customer_id
),
customer_categories AS (
    SELECT 
        st.customer_id,
        pc.category_name,
        COUNT(DISTINCT st.order_id) as category_orders,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as category_spent
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    GROUP BY st.customer_id, pc.category_name
),
preferred_categories AS (
    SELECT 
        customer_id,
        category_name as preferred_category,
        category_spent,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY category_spent DESC) as category_rank
    FROM customer_categories
)
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.registration_date,
    cph.first_purchase_date,
    cph.last_purchase_date,
    cph.total_orders,
    cph.shopping_days,
    cph.total_spent,
    cph.avg_order_value,
    cph.customer_lifespan_days,
    CASE 
        WHEN cph.customer_lifespan_days > 0 THEN 
            cph.total_orders / (cph.customer_lifespan_days / 365.0)
        ELSE 0
    END as orders_per_year,
    pc.preferred_category,
    DATEDIFF(CURRENT_DATE, cph.last_purchase_date) as days_since_last_order,
    CASE 
        WHEN cph.total_spent >= 1000 AND cph.total_orders >= 10 THEN 'VIP'
        WHEN cph.total_spent >= 500 AND cph.total_orders >= 5 THEN 'GOLD'
        WHEN cph.total_spent >= 200 AND cph.total_orders >= 3 THEN 'SILVER'
        ELSE 'BRONZE'
    END as customer_tier,
    CASE 
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 365 THEN 'INACTIVE'
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 180 THEN 'AT_RISK'
        WHEN DATEDIFF(CURRENT_DATE, cph.last_purchase_date) > 90 THEN 'DORMANT'
        ELSE 'ACTIVE'
    END as customer_status
FROM customers c
JOIN customer_purchase_history cph ON c.customer_id = cph.customer_id
LEFT JOIN preferred_categories pc ON c.customer_id = pc.customer_id AND pc.category_rank = 1
ORDER BY cph.total_spent DESC;
```

---

### Query #10 – daily_sales_summary.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/sales_reporting/daily_sales_summary.sql

```sql
-- Daily Sales Summary Report
-- Aggregates sales data by date, store, and product category

SELECT 
    DATE(order_date) as sale_date,
    store_id,
    category_name,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT customer_id) as unique_customers,
    SUM(quantity) as total_items_sold,
    SUM(unit_price * quantity) as gross_revenue,
    SUM(unit_price * quantity * discount_rate) as total_discounts,
    SUM(unit_price * quantity * (1 - discount_rate)) as net_revenue,
    AVG(unit_price * quantity) as avg_order_value
FROM sales_transactions st
JOIN products p ON st.product_id = p.product_id
JOIN product_categories pc ON p.category_id = pc.category_id
JOIN stores s ON st.store_id = s.store_id
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(order_date), store_id, category_name
ORDER BY sale_date DESC, net_revenue DESC;
```

---

### Query #11 – monthly_performance.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/sales_reporting/monthly_performance.sql

```sql
-- Monthly Sales Performance Analysis
-- Compares current month performance with previous months

WITH monthly_sales AS (
    SELECT 
        EXTRACT(YEAR FROM order_date) as sale_year,
        EXTRACT(MONTH FROM order_date) as sale_month,
        store_id,
        SUM(unit_price * quantity * (1 - discount_rate)) as monthly_revenue,
        COUNT(DISTINCT order_id) as monthly_orders,
        COUNT(DISTINCT customer_id) as monthly_customers
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date), store_id
),
performance_metrics AS (
    SELECT 
        *,
        LAG(monthly_revenue, 1) OVER (PARTITION BY store_id ORDER BY sale_year, sale_month) as prev_month_revenue,
        LAG(monthly_orders, 1) OVER (PARTITION BY store_id ORDER BY sale_year, sale_month) as prev_month_orders
    FROM monthly_sales
)
SELECT 
    sale_year,
    sale_month,
    store_id,
    monthly_revenue,
    monthly_orders,
    monthly_customers,
    ROUND(((monthly_revenue - prev_month_revenue) / prev_month_revenue * 100), 2) as revenue_growth_pct,
    ROUND(((monthly_orders - prev_month_orders) / prev_month_orders * 100), 2) as order_growth_pct,
    ROUND(monthly_revenue / monthly_orders, 2) as avg_order_value
FROM performance_metrics
WHERE prev_month_revenue IS NOT NULL
ORDER BY sale_year DESC, sale_month DESC, store_id;
```

---

### Query #12 – market_basket_analysis.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/market_basket_analysis.sql

```sql
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
```

---

### Query #13 – product_performance.sql

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/product_performance.sql

```sql
-- Product Performance Analysis
-- Analyzes product sales performance across different dimensions

WITH product_metrics AS (
    SELECT 
        p.product_id,
        p.product_name,
        p.sku,
        p.unit_cost,
        pc.category_name,
        b.brand_name,
        COUNT(DISTINCT st.order_id) as order_count,
        SUM(st.quantity) as total_quantity_sold,
        SUM(st.unit_price * st.quantity) as gross_revenue,
        SUM(st.unit_price * st.quantity * st.discount_rate) as total_discounts,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_revenue,
        AVG(st.unit_price) as avg_selling_price,
        MAX(st.order_date) as last_sale_date,
        MIN(st.order_date) as first_sale_date
    FROM products p
    JOIN product_categories pc ON p.category_id = pc.category_id
    JOIN brands b ON p.brand_id = b.brand_id
    LEFT JOIN sales_transactions st ON p.product_id = st.product_id
        AND st.order_date >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY p.product_id, p.product_name, p.sku, p.unit_cost, pc.category_name, b.brand_name
),
category_totals AS (
    SELECT 
        category_name,
        SUM(net_revenue) as category_revenue,
        SUM(total_quantity_sold) as category_quantity
    FROM product_metrics
    GROUP BY category_name
),
performance_rankings AS (
    SELECT 
        pm.*,
        ct.category_revenue,
        pm.net_revenue / NULLIF(ct.category_revenue, 0) * 100 as category_revenue_share,
        pm.total_quantity_sold / NULLIF(ct.category_quantity, 0) * 100 as category_quantity_share,
        RANK() OVER (ORDER BY pm.net_revenue DESC) as revenue_rank,
        RANK() OVER (ORDER BY pm.total_quantity_sold DESC) as quantity_rank,
        RANK() OVER (PARTITION BY pm.category_name ORDER BY pm.net_revenue DESC) as category_revenue_rank
    FROM product_metrics pm
    JOIN category_totals ct ON pm.category_name = ct.category_name
)
SELECT 
    product_id,
    product_name,
    sku,
    category_name,
    brand_name,
    order_count,
    total_quantity_sold,
    net_revenue,
    avg_selling_price,
    unit_cost,
    ROUND((avg_selling_price - unit_cost) / NULLIF(avg_selling_price, 0) * 100, 2) as margin_percentage,
    ROUND(category_revenue_share, 2) as category_revenue_share_pct,
    revenue_rank,
    quantity_rank,
    category_revenue_rank,
    DATEDIFF(CURRENT_DATE, last_sale_date) as days_since_last_sale,
    CASE 
        WHEN total_quantity_sold = 0 THEN 'NO_SALES'
        WHEN revenue_rank <= 50 THEN 'TOP_PERFORMER'
        WHEN revenue_rank <= 200 THEN 'GOOD_PERFORMER'
        WHEN revenue_rank <= 500 THEN 'AVERAGE_PERFORMER'
        ELSE 'POOR_PERFORMER'
    END as performance_tier,
    CASE 
        WHEN DATEDIFF(CURRENT_DATE, last_sale_date) > 90 THEN 'STALE'
        WHEN DATEDIFF(CURRENT_DATE, last_sale_date) > 30 THEN 'SLOW_MOVING'
        ELSE 'ACTIVE'
    END as sales_velocity
FROM performance_rankings
ORDER BY net_revenue DESC;
```

---

### Query #14 – order_data_migration.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/data_migration/order_data_migration.py

```sql
INSERT INTO sales_transactions (
        order_id, customer_id, store_id, product_id, quantity,
        unit_price, discount_rate, tax_rate, order_date, 
        payment_method, created_at
    )
    SELECT 
        lo.legacy_order_id as order_id,
        cm.new_customer_id as customer_id,
        sm.new_store_id as store_id,
        pm.new_product_id as product_id,
        lo.quantity,
        lo.price as unit_price,
        COALESCE(lo.discount_percent / 100, 0) as discount_rate,
        COALESCE(lo.tax_percent / 100, 0.08) as tax_rate,
        STR_TO_DATE(lo.order_date, '%Y-%m-%d %H:%i:%s') as order_date,
        CASE lo.payment_type
            WHEN 'CC' THEN 'CREDIT_CARD'
            WHEN 'DC' THEN 'DEBIT_CARD'
            WHEN 'CA' THEN 'CASH'
            ELSE 'CASH'
        END as payment_method,
        CURRENT_TIMESTAMP as created_at
    FROM legacy_orders lo
    JOIN customer_mapping cm ON lo.customer_code = cm.legacy_customer_code
    JOIN store_mapping sm ON lo.store_code = sm.legacy_store_code
    JOIN product_mapping pm ON lo.product_sku = pm.legacy_sku
    WHERE lo.migrated = 0
    AND lo.order_date >= '2020-01-01'
    ORDER BY lo.order_date;
```

---

### Query #15 – order_data_migration.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/data_migration/order_data_migration.py

```sql
WITH migration_summary AS (
        SELECT 
            'ORDERS' as table_name,
            COUNT(*) as total_records,
            MIN(order_date) as earliest_date,
            MAX(order_date) as latest_date,
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(DISTINCT product_id) as unique_products,
            SUM(unit_price * quantity * (1 - discount_rate)) as total_revenue
        FROM sales_transactions
        WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
        
        UNION ALL
        
        SELECT 
            'CUSTOMERS' as table_name,
            COUNT(*) as total_records,
            MIN(registration_date) as earliest_date,
            MAX(registration_date) as latest_date,
            NULL as unique_customers,
            NULL as unique_products,
            NULL as total_revenue
        FROM customers
        WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
    ),
    data_quality_checks AS (
        SELECT 
            'DUPLICATE_ORDERS' as check_name,
            COUNT(*) as issues_found
        FROM (
            SELECT order_id, customer_id, product_id, order_date
            FROM sales_transactions
            GROUP BY order_id, customer_id, product_id, order_date
            HAVING COUNT(*) > 1
        ) duplicates
        
        UNION ALL
        
        SELECT 
            'NEGATIVE_PRICES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE unit_price < 0
        
        UNION ALL
        
        SELECT 
            'ZERO_QUANTITIES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE quantity <= 0
        
        UNION ALL
        
        SELECT 
            'INVALID_DISCOUNT_RATES' as check_name,
            COUNT(*) as issues_found
        FROM sales_transactions
        WHERE discount_rate < 0 OR discount_rate > 1
    )
    SELECT 
        'MIGRATION_SUMMARY' as report_section,
        table_name,
        total_records,
        earliest_date,
        latest_date,
        unique_customers,
        unique_products,
        total_revenue,
        NULL as issues_found
    FROM migration_summary
    
    UNION ALL
    
    SELECT 
        'DATA_QUALITY_CHECKS' as report_section,
        check_name as table_name,
        NULL as total_records,
        NULL as earliest_date,
        NULL as latest_date,
        NULL as unique_customers,
        NULL as unique_products,
        NULL as total_revenue,
        issues_found
    FROM data_quality_checks
    ORDER BY report_section, table_name;
```

---

### Query #16 – order_data_migration.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/data_migration/order_data_migration.py

```sql
WITH new_orders AS (
        SELECT 
            order_id,
            customer_id,
            store_id,
            order_date,
            total_amount,
            order_status,
            updated_at
        FROM source_orders
        WHERE updated_at > '{last_sync_timestamp}'
    ),
    order_items AS (
        SELECT 
            oi.order_id,
            oi.product_id,
            oi.quantity,
            oi.unit_price,
            oi.discount_amount,
            p.unit_cost
        FROM source_order_items oi
        JOIN source_products p ON oi.product_id = p.product_id
        JOIN new_orders no ON oi.order_id = no.order_id
    )
    INSERT INTO sales_transactions (
        order_id, customer_id, store_id, product_id, quantity,
        unit_price, discount_rate, order_date, created_at
    )
    SELECT 
        no.order_id,
        no.customer_id,
        no.store_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        CASE 
            WHEN oi.unit_price > 0 THEN oi.discount_amount / (oi.unit_price * oi.quantity)
            ELSE 0
        END as discount_rate,
        no.order_date,
        CURRENT_TIMESTAMP
    FROM new_orders no
    JOIN order_items oi ON no.order_id = oi.order_id
    WHERE NOT EXISTS (
        SELECT 1 FROM sales_transactions st 
        WHERE st.order_id = no.order_id 
        AND st.product_id = oi.product_id
    );
```

---

### Query #17 – warehouse_operations.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/warehouse_operations.py

```sql
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
```

---

### Query #18 – warehouse_operations.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/warehouse_operations.py

```sql
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
```

---

### Query #19 – warehouse_operations.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/warehouse_operations.py

```sql
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
```

---

### Query #20 – warehouse_operations.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/inventory_management/warehouse_operations.py

```sql
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
```

---

### Query #21 – crm_queries.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/customer_management/crm_queries.py

```sql
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
```

---

### Query #22 – crm_queries.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/customer_management/crm_queries.py

```sql
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
```

---

### Query #23 – crm_queries.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/customer_management/crm_queries.py

```sql
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
```

---

### Query #24 – sales_analytics.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/sales_reporting/sales_analytics.py

```sql
SELECT 
        p.product_id,
        p.product_name,
        p.sku,
        pc.category_name,
        SUM(st.quantity) as total_quantity_sold,
        SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as total_revenue,
        COUNT(DISTINCT st.order_id) as order_count,
        AVG(st.unit_price) as avg_selling_price
    FROM sales_transactions st
    JOIN products p ON st.product_id = p.product_id
    JOIN product_categories pc ON p.category_id = pc.category_id
    WHERE st.order_date >= CURRENT_DATE - INTERVAL '{days} days'
    GROUP BY p.product_id, p.product_name, p.sku, pc.category_name
    ORDER BY total_revenue DESC
    LIMIT {limit};
```

---

### Query #25 – sales_analytics.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/sales_reporting/sales_analytics.py

```sql
WITH customer_metrics AS (
        SELECT 
            customer_id,
            MAX(order_date) as last_order_date,
            COUNT(DISTINCT order_id) as frequency,
            SUM(unit_price * quantity * (1 - discount_rate)) as monetary_value,
            DATEDIFF(CURRENT_DATE, MAX(order_date)) as recency_days
        FROM sales_transactions
        WHERE order_date >= CURRENT_DATE - INTERVAL '365 days'
        GROUP BY customer_id
    ),
    rfm_scores AS (
        SELECT 
            customer_id,
            recency_days,
            frequency,
            monetary_value,
            NTILE(5) OVER (ORDER BY recency_days ASC) as recency_score,
            NTILE(5) OVER (ORDER BY frequency DESC) as frequency_score,
            NTILE(5) OVER (ORDER BY monetary_value DESC) as monetary_score
        FROM customer_metrics
    )
    SELECT 
        customer_id,
        recency_days,
        frequency,
        monetary_value,
        recency_score,
        frequency_score,
        monetary_score,
        CASE 
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
            WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Loyal Customers'
            WHEN recency_score >= 3 AND frequency_score <= 2 THEN 'Potential Loyalists'
            WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk'
            WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Lost Customers'
            ELSE 'New Customers'
        END as customer_segment
    FROM rfm_scores
    ORDER BY monetary_value DESC;
```

---

### Query #26 – sales_analytics.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/sales_reporting/sales_analytics.py

```sql
SELECT 
        DATE_TRUNC('week', order_date) as week_start,
        COUNT(DISTINCT order_id) as weekly_orders,
        SUM(unit_price * quantity * (1 - discount_rate)) as weekly_revenue,
        COUNT(DISTINCT customer_id) as weekly_customers,
        AVG(unit_price * quantity) as avg_order_value,
        LAG(SUM(unit_price * quantity * (1 - discount_rate)), 1) 
            OVER (ORDER BY DATE_TRUNC('week', order_date)) as prev_week_revenue
    FROM sales_transactions
    WHERE order_date >= CURRENT_DATE - INTERVAL '12 weeks'
    GROUP BY DATE_TRUNC('week', order_date)
    ORDER BY week_start DESC;
```

---

### Query #27 – business_intelligence.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/business_intelligence.py

```sql
WITH current_period AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_today,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_today,
            COUNT(DISTINCT customer_id) as customers_today
        FROM sales_transactions
        WHERE DATE(order_date) = CURRENT_DATE
    ),
    previous_period AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_yesterday,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_yesterday,
            COUNT(DISTINCT customer_id) as customers_yesterday
        FROM sales_transactions
        WHERE DATE(order_date) = CURRENT_DATE - INTERVAL '1 day'
    ),
    month_to_date AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_mtd,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_mtd,
            COUNT(DISTINCT customer_id) as customers_mtd,
            AVG(unit_price * quantity * (1 - discount_rate)) as avg_order_value_mtd
        FROM sales_transactions
        WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        AND EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE)
    ),
    year_to_date AS (
        SELECT 
            COUNT(DISTINCT order_id) as orders_ytd,
            SUM(unit_price * quantity * (1 - discount_rate)) as revenue_ytd,
            COUNT(DISTINCT customer_id) as customers_ytd
        FROM sales_transactions
        WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    )
    SELECT 
        -- Today's metrics
        cp.orders_today,
        cp.revenue_today,
        cp.customers_today,
        
        -- Day-over-day changes
        ROUND(((cp.orders_today - pp.orders_yesterday) / NULLIF(pp.orders_yesterday, 0) * 100), 2) as orders_change_pct,
        ROUND(((cp.revenue_today - pp.revenue_yesterday) / NULLIF(pp.revenue_yesterday, 0) * 100), 2) as revenue_change_pct,
        
        -- Month to date
        mtd.orders_mtd,
        mtd.revenue_mtd,
        mtd.customers_mtd,
        mtd.avg_order_value_mtd,
        
        -- Year to date
        ytd.orders_ytd,
        ytd.revenue_ytd,
        ytd.customers_ytd,
        
        CURRENT_TIMESTAMP as report_generated_at
    FROM current_period cp
    CROSS JOIN previous_period pp
    CROSS JOIN month_to_date mtd
    CROSS JOIN year_to_date ytd;
```

---

### Query #28 – business_intelligence.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/business_intelligence.py

```sql
WITH funnel_metrics AS (
        SELECT 
            COUNT(DISTINCT session_id) as total_sessions,
            COUNT(DISTINCT CASE WHEN page_views > 1 THEN session_id END) as engaged_sessions,
            COUNT(DISTINCT CASE WHEN product_views > 0 THEN session_id END) as product_view_sessions,
            COUNT(DISTINCT CASE WHEN cart_additions > 0 THEN session_id END) as cart_addition_sessions,
            COUNT(DISTINCT CASE WHEN checkout_starts > 0 THEN session_id END) as checkout_start_sessions,
            COUNT(DISTINCT CASE WHEN orders > 0 THEN session_id END) as converted_sessions
        FROM (
            SELECT 
                w.session_id,
                COUNT(w.page_view_id) as page_views,
                COUNT(CASE WHEN w.event_type = 'product_view' THEN 1 END) as product_views,
                COUNT(CASE WHEN w.event_type = 'add_to_cart' THEN 1 END) as cart_additions,
                COUNT(CASE WHEN w.event_type = 'checkout_start' THEN 1 END) as checkout_starts,
                COUNT(DISTINCT o.order_id) as orders
            FROM website_events w
            LEFT JOIN orders o ON w.session_id = o.session_id
            WHERE w.event_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY w.session_id
        ) session_summary
    )
    SELECT 
        total_sessions,
        engaged_sessions,
        product_view_sessions,
        cart_addition_sessions,
        checkout_start_sessions,
        converted_sessions,
        
        -- Conversion rates at each step
        ROUND(engaged_sessions * 100.0 / NULLIF(total_sessions, 0), 2) as engagement_rate,
        ROUND(product_view_sessions * 100.0 / NULLIF(engaged_sessions, 0), 2) as product_view_rate,
        ROUND(cart_addition_sessions * 100.0 / NULLIF(product_view_sessions, 0), 2) as cart_addition_rate,
        ROUND(checkout_start_sessions * 100.0 / NULLIF(cart_addition_sessions, 0), 2) as checkout_start_rate,
        ROUND(converted_sessions * 100.0 / NULLIF(checkout_start_sessions, 0), 2) as checkout_completion_rate,
        ROUND(converted_sessions * 100.0 / NULLIF(total_sessions, 0), 2) as overall_conversion_rate
    FROM funnel_metrics;
```

---

### Query #29 – business_intelligence.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/business_intelligence.py

```sql
WITH customer_cohorts AS (
        SELECT 
            customer_id,
            DATE_TRUNC('month', MIN(order_date)) as cohort_month,
            MIN(order_date) as first_order_date
        FROM sales_transactions
        GROUP BY customer_id
    ),
    customer_activities AS (
        SELECT 
            cc.customer_id,
            cc.cohort_month,
            DATE_TRUNC('month', st.order_date) as activity_month,
            EXTRACT(EPOCH FROM (DATE_TRUNC('month', st.order_date) - cc.cohort_month)) / (30 * 24 * 60 * 60) as months_since_first_order
        FROM customer_cohorts cc
        JOIN sales_transactions st ON cc.customer_id = st.customer_id
    ),
    cohort_data AS (
        SELECT 
            cohort_month,
            months_since_first_order,
            COUNT(DISTINCT customer_id) as active_customers
        FROM customer_activities
        GROUP BY cohort_month, months_since_first_order
    ),
    cohort_sizes AS (
        SELECT 
            cohort_month,
            COUNT(DISTINCT customer_id) as cohort_size
        FROM customer_cohorts
        GROUP BY cohort_month
    )
    SELECT 
        cd.cohort_month,
        cs.cohort_size,
        cd.months_since_first_order,
        cd.active_customers,
        ROUND(cd.active_customers * 100.0 / cs.cohort_size, 2) as retention_rate
    FROM cohort_data cd
    JOIN cohort_sizes cs ON cd.cohort_month = cs.cohort_month
    WHERE cd.cohort_month >= CURRENT_DATE - INTERVAL '12 months'
    AND cd.months_since_first_order <= 12
    ORDER BY cd.cohort_month, cd.months_since_first_order;
```

---

### Query #30 – business_intelligence.py

**File:** /Users/kanumadhok/SQL_RAG/retail_system/analytics/business_intelligence.py

```sql
WITH product_profitability AS (
        SELECT 
            p.product_id,
            p.product_name,
            pc.category_name,
            b.brand_name,
            p.unit_cost,
            AVG(st.unit_price) as avg_selling_price,
            SUM(st.quantity) as total_units_sold,
            SUM(st.unit_price * st.quantity) as gross_revenue,
            SUM(st.unit_price * st.quantity * st.discount_rate) as total_discounts,
            SUM(st.unit_price * st.quantity * (1 - st.discount_rate)) as net_revenue,
            SUM(p.unit_cost * st.quantity) as total_cost,
            SUM((st.unit_price * (1 - st.discount_rate) - p.unit_cost) * st.quantity) as gross_profit
        FROM products p
        JOIN product_categories pc ON p.category_id = pc.category_id
        JOIN brands b ON p.brand_id = b.brand_id
        LEFT JOIN sales_transactions st ON p.product_id = st.product_id
            AND st.order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY p.product_id, p.product_name, pc.category_name, b.brand_name, p.unit_cost
        HAVING SUM(st.quantity) > 0
    )
    SELECT 
        product_id,
        product_name,
        category_name,
        brand_name,
        total_units_sold,
        net_revenue,
        total_cost,
        gross_profit,
        ROUND((avg_selling_price - unit_cost) / NULLIF(avg_selling_price, 0) * 100, 2) as margin_percentage,
        ROUND(gross_profit / NULLIF(net_revenue, 0) * 100, 2) as profit_margin_pct,
        ROUND(gross_profit / NULLIF(total_units_sold, 0), 2) as profit_per_unit,
        CASE 
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.3 THEN 'HIGH_MARGIN'
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.15 THEN 'MEDIUM_MARGIN'
            WHEN gross_profit / NULLIF(net_revenue, 0) >= 0.05 THEN 'LOW_MARGIN'
            ELSE 'UNPROFITABLE'
        END as profitability_tier
    FROM product_profitability
    ORDER BY gross_profit DESC;
```

---

