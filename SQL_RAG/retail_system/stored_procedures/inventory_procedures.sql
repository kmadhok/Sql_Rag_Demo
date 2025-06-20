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