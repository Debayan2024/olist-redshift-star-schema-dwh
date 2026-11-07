-- ============================================
-- ETL: Staging to Core Layer Transformations
-- Purpose: Clean, validate, and apply business logic
-- ============================================

-- ============================================
-- ORDERS: Staging to Core
-- ============================================

INSERT INTO core.orders (
    order_id,
    customer_id,
    order_date,
    order_status,
    total_amount,
    payment_method,
    shipping_address,
    city,
    province,
    postal_code,
    is_first_order,
    order_processing_time_hours,
    created_at,
    updated_at,
    dw_created_at,
    dw_updated_at
)
SELECT DISTINCT
    TRIM(s.order_id) as order_id,
    TRIM(s.customer_id) as customer_id,
    s.order_date,
    UPPER(TRIM(s.order_status)) as order_status,
    COALESCE(s.total_amount, 0) as total_amount,
    TRIM(s.payment_method) as payment_method,
    TRIM(s.shipping_address) as shipping_address,
    TRIM(s.city) as city,
    TRIM(s.province) as province,
    TRIM(s.postal_code) as postal_code,
    -- Check if this is customer's first order
    CASE 
        WHEN ROW_NUMBER() OVER (PARTITION BY s.customer_id ORDER BY s.order_date) = 1 
        THEN TRUE 
        ELSE FALSE 
    END as is_first_order,
    -- Calculate processing time
    EXTRACT(EPOCH FROM (s.updated_at - s.created_at))/3600 as order_processing_time_hours,
    s.created_at,
    s.updated_at,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM staging.orders s
WHERE s.order_id IS NOT NULL
    AND s.customer_id IS NOT NULL
    AND s.order_date IS NOT NULL
    AND s.total_amount >= 0
    AND NOT EXISTS (
        SELECT 1 FROM core.orders c 
        WHERE c.order_id = s.order_id 
        AND c.is_current = TRUE
    )
;

-- ============================================
-- ORDER ITEMS: Staging to Core
-- ============================================

INSERT INTO core.order_items (
    order_item_id,
    order_id,
    product_id,
    product_name,
    quantity,
    unit_price,
    discount_amount,
    subtotal,
    created_at,
    dw_created_at,
    dw_updated_at
)
SELECT DISTINCT
    TRIM(si.order_item_id) as order_item_id,
    TRIM(si.order_id) as order_id,
    TRIM(si.product_id) as product_id,
    TRIM(si.product_name) as product_name,
    si.quantity,
    COALESCE(si.unit_price, 0) as unit_price,
    COALESCE(si.discount_amount, 0) as discount_amount,
    COALESCE(si.subtotal, si.quantity * si.unit_price) as subtotal,
    si.created_at,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM staging.order_items si
WHERE si.order_item_id IS NOT NULL
    AND si.order_id IS NOT NULL
    AND si.product_id IS NOT NULL
    AND si.quantity > 0
    AND si.unit_price >= 0
    AND NOT EXISTS (
        SELECT 1 FROM core.order_items c 
        WHERE c.order_item_id = si.order_item_id
    )
;

-- ============================================
-- CUSTOMERS: Staging to Core (SCD Type 2)
-- ============================================

-- Insert new customers
INSERT INTO core.customers (
    customer_id,
    email,
    phone,
    first_name,
    last_name,
    full_name,
    date_of_birth,
    age,
    gender,
    registration_date,
    customer_segment,
    total_orders,
    total_spent,
    is_active,
    created_at,
    updated_at,
    dw_created_at,
    dw_updated_at,
    valid_from,
    valid_to,
    is_current
)
SELECT
    TRIM(sc.customer_id) as customer_id,
    LOWER(TRIM(sc.email)) as email,
    TRIM(sc.phone) as phone,
    TRIM(sc.first_name) as first_name,
    TRIM(sc.last_name) as last_name,
    TRIM(CONCAT(sc.first_name, ' ', sc.last_name)) as full_name,
    sc.date_of_birth,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, sc.date_of_birth)) as age,
    UPPER(TRIM(sc.gender)) as gender,
    sc.registration_date,
    COALESCE(TRIM(sc.customer_segment), 'REGULAR') as customer_segment,
    0 as total_orders,
    0 as total_spent,
    TRUE as is_active,
    sc.created_at,
    sc.updated_at,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    sc.created_at as valid_from,
    NULL as valid_to,
    TRUE as is_current
FROM staging.customers sc
WHERE sc.customer_id IS NOT NULL
    AND sc.email IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM core.customers cc 
        WHERE cc.customer_id = sc.customer_id
    )
;

-- Update changed customer records (SCD Type 2)
-- Close out old records
UPDATE core.customers cc
SET 
    valid_to = CURRENT_TIMESTAMP,
    is_current = FALSE,
    dw_updated_at = CURRENT_TIMESTAMP
WHERE cc.is_current = TRUE
    AND EXISTS (
        SELECT 1 FROM staging.customers sc
        WHERE sc.customer_id = cc.customer_id
        AND (
            LOWER(TRIM(sc.email)) != cc.email OR
            TRIM(sc.phone) != COALESCE(cc.phone, '') OR
            TRIM(sc.customer_segment) != COALESCE(cc.customer_segment, '')
        )
    )
;

-- Insert new versions of changed records
INSERT INTO core.customers (
    customer_id, email, phone, first_name, last_name, full_name,
    date_of_birth, age, gender, registration_date, customer_segment,
    created_at, updated_at, valid_from, valid_to, is_current
)
SELECT
    TRIM(sc.customer_id),
    LOWER(TRIM(sc.email)),
    TRIM(sc.phone),
    TRIM(sc.first_name),
    TRIM(sc.last_name),
    TRIM(CONCAT(sc.first_name, ' ', sc.last_name)),
    sc.date_of_birth,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, sc.date_of_birth)),
    UPPER(TRIM(sc.gender)),
    sc.registration_date,
    COALESCE(TRIM(sc.customer_segment), 'REGULAR'),
    sc.created_at,
    sc.updated_at,
    CURRENT_TIMESTAMP,
    NULL,
    TRUE
FROM staging.customers sc
INNER JOIN core.customers cc 
    ON sc.customer_id = cc.customer_id
WHERE cc.is_current = FALSE
    AND cc.valid_to = CURRENT_TIMESTAMP
;

-- ============================================
-- PRODUCTS: Staging to Core (SCD Type 2)
-- ============================================

-- Insert new products
INSERT INTO core.products (
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    unit_price,
    cost_price,
    stock_quantity,
    supplier_id,
    is_active,
    created_at,
    updated_at,
    dw_created_at,
    dw_updated_at,
    valid_from,
    valid_to,
    is_current
)
SELECT
    TRIM(sp.product_id) as product_id,
    TRIM(sp.product_name) as product_name,
    TRIM(sp.category) as category,
    TRIM(sp.subcategory) as subcategory,
    TRIM(sp.brand) as brand,
    COALESCE(sp.unit_price, 0) as unit_price,
    COALESCE(sp.cost_price, 0) as cost_price,
    COALESCE(sp.stock_quantity, 0) as stock_quantity,
    TRIM(sp.supplier_id) as supplier_id,
    COALESCE(sp.is_active, TRUE) as is_active,
    sp.created_at,
    sp.updated_at,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    sp.created_at as valid_from,
    NULL as valid_to,
    TRUE as is_current
FROM staging.products sp
WHERE sp.product_id IS NOT NULL
    AND sp.product_name IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM core.products cp 
        WHERE cp.product_id = sp.product_id
    )
;

-- ============================================
-- PAYMENTS: Staging to Core
-- ============================================

INSERT INTO core.payments (
    payment_id,
    order_id,
    payment_date,
    payment_method,
    payment_status,
    amount,
    transaction_id,
    is_successful,
    created_at,
    dw_created_at,
    dw_updated_at
)
SELECT DISTINCT
    TRIM(sp.payment_id) as payment_id,
    TRIM(sp.order_id) as order_id,
    sp.payment_date,
    TRIM(sp.payment_method) as payment_method,
    UPPER(TRIM(sp.payment_status)) as payment_status,
    COALESCE(sp.amount, 0) as amount,
    TRIM(sp.transaction_id) as transaction_id,
    CASE WHEN UPPER(TRIM(sp.payment_status)) = 'SUCCESS' THEN TRUE ELSE FALSE END as is_successful,
    sp.created_at,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM staging.payments sp
WHERE sp.payment_id IS NOT NULL
    AND sp.order_id IS NOT NULL
    AND sp.payment_date IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM core.payments cp 
        WHERE cp.payment_id = sp.payment_id
    )
;

-- ============================================
-- USER EVENTS: Staging to Core
-- ============================================

INSERT INTO core.user_events (
    event_id,
    user_id,
    session_id,
    event_type,
    event_timestamp,
    page_url,
    referrer_url,
    device_type,
    browser,
    dw_created_at
)
SELECT DISTINCT
    TRIM(se.event_id) as event_id,
    TRIM(se.user_id) as user_id,
    TRIM(se.session_id) as session_id,
    TRIM(se.event_type) as event_type,
    se.event_timestamp,
    TRIM(se.page_url) as page_url,
    TRIM(se.referrer_url) as referrer_url,
    TRIM(se.device_type) as device_type,
    TRIM(se.browser) as browser,
    CURRENT_TIMESTAMP
FROM staging.user_events se
WHERE se.event_id IS NOT NULL
    AND se.session_id IS NOT NULL
    AND se.event_timestamp IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM core.user_events ce 
        WHERE ce.event_id = se.event_id
    )
;

-- ============================================
-- DATA QUALITY CHECKS
-- ============================================

-- Check for orphaned order items
SELECT 
    'Orphaned Order Items' as check_name,
    COUNT(*) as issue_count
FROM core.order_items oi
LEFT JOIN core.orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL
HAVING COUNT(*) > 0;

-- Check for negative amounts
SELECT 
    'Negative Order Amounts' as check_name,
    COUNT(*) as issue_count
FROM core.orders
WHERE total_amount < 0
HAVING COUNT(*) > 0;

