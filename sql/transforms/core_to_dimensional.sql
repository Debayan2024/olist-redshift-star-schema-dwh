-- ============================================
-- ETL: Core to Dimensional Layer
-- Purpose: Build star schema for analytics
-- ============================================

-- ============================================
-- POPULATE DATE DIMENSION
-- ============================================

-- Generate date dimension for 5 years (2020-2025)
INSERT INTO analytics.dim_date (
    date_key,
    date_actual,
    day_of_week,
    day_name,
    day_of_month,
    day_of_year,
    week_of_year,
    month_number,
    month_name,
    quarter,
    year,
    is_weekend,
    is_holiday,
    fiscal_year,
    fiscal_quarter
)
SELECT
    TO_CHAR(date_series, 'YYYYMMDD')::INTEGER as date_key,
    date_series as date_actual,
    EXTRACT(DOW FROM date_series) as day_of_week,
    TO_CHAR(date_series, 'Day') as day_name,
    EXTRACT(DAY FROM date_series) as day_of_month,
    EXTRACT(DOY FROM date_series) as day_of_year,
    EXTRACT(WEEK FROM date_series) as week_of_year,
    EXTRACT(MONTH FROM date_series) as month_number,
    TO_CHAR(date_series, 'Month') as month_name,
    EXTRACT(QUARTER FROM date_series) as quarter,
    EXTRACT(YEAR FROM date_series) as year,
    CASE WHEN EXTRACT(DOW FROM date_series) IN (0, 6) THEN TRUE ELSE FALSE END as is_weekend,
    FALSE as is_holiday,  -- Can be updated with holiday calendar
    EXTRACT(YEAR FROM date_series) as fiscal_year,
    EXTRACT(QUARTER FROM date_series) as fiscal_quarter
FROM generate_series('2020-01-01'::DATE, '2025-12-31'::DATE, '1 day'::INTERVAL) as date_series
ON CONFLICT (date_key) DO NOTHING;

-- ============================================
-- POPULATE CUSTOMER DIMENSION
-- ============================================

INSERT INTO analytics.dim_customers (
    customer_id,
    email,
    full_name,
    first_name,
    last_name,
    date_of_birth,
    age,
    age_group,
    gender,
    registration_date,
    customer_segment,
    customer_tier,
    city,
    province,
    region,
    total_lifetime_orders,
    total_lifetime_value,
    average_order_value,
    first_order_date,
    last_order_date,
    days_since_last_order,
    is_active,
    valid_from,
    valid_to,
    is_current
)
SELECT
    c.customer_id,
    c.email,
    c.full_name,
    c.first_name,
    c.last_name,
    c.date_of_birth,
    c.age,
    CASE 
        WHEN c.age < 18 THEN 'Under 18'
        WHEN c.age BETWEEN 18 AND 24 THEN '18-24'
        WHEN c.age BETWEEN 25 AND 34 THEN '25-34'
        WHEN c.age BETWEEN 35 AND 44 THEN '35-44'
        WHEN c.age BETWEEN 45 AND 54 THEN '45-54'
        WHEN c.age >= 55 THEN '55+'
        ELSE 'Unknown'
    END as age_group,
    c.gender,
    c.registration_date,
    c.customer_segment,
    CASE 
        WHEN COALESCE(c.total_spent, 0) >= 50000000 THEN 'VIP'
        WHEN COALESCE(c.total_spent, 0) >= 10000000 THEN 'Gold'
        WHEN COALESCE(c.total_spent, 0) >= 5000000 THEN 'Silver'
        ELSE 'Bronze'
    END as customer_tier,
    o.city,
    o.province,
    CASE 
        WHEN o.province IN ('Hồ Chí Minh', 'Bình Dương', 'Đồng Nai') THEN 'South'
        WHEN o.province IN ('Hà Nội', 'Hải Phòng', 'Quảng Ninh') THEN 'North'
        WHEN o.province IN ('Đà Nẵng', 'Quảng Nam', 'Thừa Thiên Huế') THEN 'Central'
        ELSE 'Other'
    END as region,
    COALESCE(c.total_orders, 0) as total_lifetime_orders,
    COALESCE(c.total_spent, 0) as total_lifetime_value,
    CASE 
        WHEN COALESCE(c.total_orders, 0) > 0 
        THEN COALESCE(c.total_spent, 0) / c.total_orders 
        ELSE 0 
    END as average_order_value,
    (SELECT MIN(order_date)::DATE FROM core.orders WHERE customer_id = c.customer_id) as first_order_date,
    c.last_order_date::DATE as last_order_date,
    CASE 
        WHEN c.last_order_date IS NOT NULL 
        THEN CURRENT_DATE - c.last_order_date::DATE 
        ELSE NULL 
    END as days_since_last_order,
    c.is_active,
    c.valid_from,
    c.valid_to,
    c.is_current
FROM core.customers c
LEFT JOIN (
    SELECT DISTINCT ON (customer_id)
        customer_id, city, province
    FROM core.orders
    ORDER BY customer_id, order_date DESC
) o ON c.customer_id = o.customer_id
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.dim_customers dc
    WHERE dc.customer_id = c.customer_id 
    AND dc.valid_from = c.valid_from
);

-- ============================================
-- POPULATE PRODUCT DIMENSION
-- ============================================

INSERT INTO analytics.dim_products (
    product_id,
    product_name,
    product_name_english,
    category,
    subcategory,
    brand,
    unit_price,
    cost_price,
    margin_percent,
    price_tier,
    supplier_id,
    supplier_name,
    is_active,
    valid_from,
    valid_to,
    is_current
)
SELECT
    p.product_id,
    p.product_name,
    p.product_name as product_name_english,  -- Could be enhanced with translation
    p.category,
    p.subcategory,
    p.brand,
    p.unit_price,
    p.cost_price,
    p.margin_percent,
    CASE 
        WHEN p.unit_price < 100000 THEN 'Budget'
        WHEN p.unit_price BETWEEN 100000 AND 500000 THEN 'Standard'
        WHEN p.unit_price BETWEEN 500000 AND 2000000 THEN 'Premium'
        WHEN p.unit_price > 2000000 THEN 'Luxury'
        ELSE 'Unknown'
    END as price_tier,
    p.supplier_id,
    p.supplier_id as supplier_name,  -- Could be joined with supplier master
    p.is_active,
    p.valid_from,
    p.valid_to,
    p.is_current
FROM core.products p
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.dim_products dp
    WHERE dp.product_id = p.product_id 
    AND dp.valid_from = p.valid_from
);

-- ============================================
-- POPULATE LOCATION DIMENSION
-- ============================================

INSERT INTO analytics.dim_locations (
    city,
    province,
    region,
    country,
    postal_code
)
SELECT DISTINCT
    o.city,
    o.province,
    CASE 
        WHEN o.province IN ('Hồ Chí Minh', 'Bình Dương', 'Đồng Nai', 'Vũng Tàu') THEN 'South'
        WHEN o.province IN ('Hà Nội', 'Hải Phòng', 'Quảng Ninh', 'Hải Dương') THEN 'North'
        WHEN o.province IN ('Đà Nẵng', 'Quảng Nam', 'Thừa Thiên Huế', 'Quảng Ngãi') THEN 'Central'
        ELSE 'Other'
    END as region,
    'Vietnam' as country,
    o.postal_code
FROM core.orders o
WHERE o.city IS NOT NULL 
    AND o.province IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM analytics.dim_locations dl
        WHERE COALESCE(dl.city, '') = COALESCE(o.city, '')
        AND COALESCE(dl.province, '') = COALESCE(o.province, '')
        AND COALESCE(dl.postal_code, '') = COALESCE(o.postal_code, '')
    )
;

-- ============================================
-- POPULATE PAYMENT METHOD DIMENSION
-- ============================================

INSERT INTO analytics.dim_payment_methods (
    payment_method_id,
    payment_method_name,
    payment_type,
    provider,
    is_digital,
    is_active
)
SELECT DISTINCT
    LOWER(REPLACE(payment_method, ' ', '_')) as payment_method_id,
    payment_method as payment_method_name,
    CASE 
        WHEN payment_method IN ('Credit Card', 'Debit Card') THEN 'Card'
        WHEN payment_method IN ('MoMo', 'ZaloPay', 'VNPay') THEN 'E-Wallet'
        WHEN payment_method = 'Bank Transfer' THEN 'Bank Transfer'
        WHEN payment_method = 'COD' THEN 'Cash'
        ELSE 'Other'
    END as payment_type,
    payment_method as provider,
    CASE WHEN payment_method != 'COD' THEN TRUE ELSE FALSE END as is_digital,
    TRUE as is_active
FROM core.orders
WHERE payment_method IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM analytics.dim_payment_methods pm
        WHERE pm.payment_method_id = LOWER(REPLACE(core.orders.payment_method, ' ', '_'))
    )
;

-- ============================================
-- POPULATE ORDER STATUS DIMENSION
-- ============================================

INSERT INTO analytics.dim_order_status (
    order_status_id,
    order_status_name,
    status_category,
    is_completed,
    is_cancelled,
    display_order
)
VALUES
    ('PENDING', 'Pending', 'In Progress', FALSE, FALSE, 1),
    ('CONFIRMED', 'Confirmed', 'In Progress', FALSE, FALSE, 2),
    ('PROCESSING', 'Processing', 'In Progress', FALSE, FALSE, 3),
    ('SHIPPED', 'Shipped', 'In Progress', FALSE, FALSE, 4),
    ('DELIVERED', 'Delivered', 'Completed', TRUE, FALSE, 5),
    ('CANCELLED', 'Cancelled', 'Cancelled', FALSE, TRUE, 6),
    ('RETURNED', 'Returned', 'Returned', FALSE, FALSE, 7),
    ('REFUNDED', 'Refunded', 'Refunded', FALSE, FALSE, 8)
ON CONFLICT (order_status_id) DO NOTHING;

-- ============================================
-- POPULATE FACT: ORDERS
-- ============================================

INSERT INTO analytics.fact_orders (
    order_id,
    order_date_key,
    payment_date_key,
    customer_key,
    location_key,
    payment_method_key,
    order_status_key,
    order_number,
    transaction_id,
    order_quantity,
    gross_amount,
    discount_amount,
    net_amount,
    payment_amount,
    is_first_order,
    order_processing_hours
)
SELECT
    o.order_id,
    TO_CHAR(o.order_date, 'YYYYMMDD')::INTEGER as order_date_key,
    TO_CHAR(p.payment_date, 'YYYYMMDD')::INTEGER as payment_date_key,
    dc.customer_key,
    dl.location_key,
    dpm.payment_method_key,
    dos.order_status_key,
    o.order_id as order_number,
    p.transaction_id,
    (SELECT SUM(quantity) FROM core.order_items WHERE order_id = o.order_id) as order_quantity,
    o.total_amount as gross_amount,
    (SELECT SUM(discount_amount) FROM core.order_items WHERE order_id = o.order_id) as discount_amount,
    o.total_amount as net_amount,
    p.amount as payment_amount,
    o.is_first_order,
    o.order_processing_time_hours
FROM core.orders o
LEFT JOIN core.payments p ON o.order_id = p.order_id AND p.is_successful = TRUE
LEFT JOIN analytics.dim_customers dc ON o.customer_id = dc.customer_id AND dc.is_current = TRUE
LEFT JOIN analytics.dim_locations dl ON COALESCE(o.city, '') = COALESCE(dl.city, '') 
    AND COALESCE(o.province, '') = COALESCE(dl.province, '')
LEFT JOIN analytics.dim_payment_methods dpm ON LOWER(REPLACE(o.payment_method, ' ', '_')) = dpm.payment_method_id
LEFT JOIN analytics.dim_order_status dos ON o.order_status = dos.order_status_id
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.fact_orders fo WHERE fo.order_id = o.order_id
)
AND dc.customer_key IS NOT NULL;

-- ============================================
-- POPULATE FACT: ORDER ITEMS
-- ============================================

INSERT INTO analytics.fact_order_items (
    order_item_id,
    order_id,
    order_date_key,
    customer_key,
    product_key,
    quantity,
    unit_price,
    unit_cost,
    discount_amount,
    gross_revenue,
    net_revenue,
    product_cost,
    gross_profit
)
SELECT
    oi.order_item_id,
    oi.order_id,
    TO_CHAR(o.order_date, 'YYYYMMDD')::INTEGER as order_date_key,
    dc.customer_key,
    dp.product_key,
    oi.quantity,
    oi.unit_price,
    dp.cost_price as unit_cost,
    oi.discount_amount,
    oi.subtotal as gross_revenue,
    oi.revenue as net_revenue,
    dp.cost_price * oi.quantity as product_cost,
    oi.revenue - (dp.cost_price * oi.quantity) as gross_profit
FROM core.order_items oi
INNER JOIN core.orders o ON oi.order_id = o.order_id
LEFT JOIN analytics.dim_customers dc ON o.customer_id = dc.customer_id AND dc.is_current = TRUE
LEFT JOIN analytics.dim_products dp ON oi.product_id = dp.product_id AND dp.is_current = TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.fact_order_items foi WHERE foi.order_item_id = oi.order_item_id
)
AND dc.customer_key IS NOT NULL
AND dp.product_key IS NOT NULL;

-- ============================================
-- POPULATE FACT: DAILY SALES AGGREGATE
-- ============================================

INSERT INTO analytics.fact_daily_sales (
    date_key,
    product_category,
    customer_segment,
    location_province,
    total_orders,
    total_customers,
    new_customers,
    returning_customers,
    total_items_sold,
    total_gross_revenue,
    total_discounts,
    total_net_revenue,
    total_product_cost,
    total_gross_profit,
    average_order_value,
    average_items_per_order
)
SELECT
    foi.order_date_key as date_key,
    dp.category as product_category,
    dc.customer_segment,
    dl.province as location_province,
    COUNT(DISTINCT foi.order_id) as total_orders,
    COUNT(DISTINCT foi.customer_key) as total_customers,
    COUNT(DISTINCT CASE WHEN fo.is_first_order THEN foi.customer_key END) as new_customers,
    COUNT(DISTINCT CASE WHEN NOT fo.is_first_order THEN foi.customer_key END) as returning_customers,
    SUM(foi.quantity) as total_items_sold,
    SUM(foi.gross_revenue) as total_gross_revenue,
    SUM(foi.discount_amount) as total_discounts,
    SUM(foi.net_revenue) as total_net_revenue,
    SUM(foi.product_cost) as total_product_cost,
    SUM(foi.gross_profit) as total_gross_profit,
    AVG(fo.gross_amount) as average_order_value,
    AVG(fo.order_quantity) as average_items_per_order
FROM analytics.fact_order_items foi
INNER JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
LEFT JOIN analytics.dim_products dp ON foi.product_key = dp.product_key
LEFT JOIN analytics.dim_customers dc ON foi.customer_key = dc.customer_key
LEFT JOIN analytics.dim_locations dl ON fo.location_key = dl.location_key
GROUP BY 
    foi.order_date_key,
    dp.category,
    dc.customer_segment,
    dl.province
ON CONFLICT (date_key, product_category, customer_segment, location_province) 
DO UPDATE SET
    total_orders = EXCLUDED.total_orders,
    total_customers = EXCLUDED.total_customers,
    total_items_sold = EXCLUDED.total_items_sold,
    total_gross_revenue = EXCLUDED.total_gross_revenue,
    total_net_revenue = EXCLUDED.total_net_revenue,
    updated_at = CURRENT_TIMESTAMP;

