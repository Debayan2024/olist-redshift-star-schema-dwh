-- ============================================
-- Staging Layer: Raw Data Ingestion
-- Purpose: Land raw data from source systems
-- ============================================

-- Drop existing staging schema if exists
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

-- Staging: Orders
CREATE TABLE staging.orders (
    order_id VARCHAR(50),
    customer_id VARCHAR(50),
    order_date TIMESTAMP,
    order_status VARCHAR(50),
    total_amount DECIMAL(15,2),
    payment_method VARCHAR(50),
    shipping_address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Order Items
CREATE TABLE staging.order_items (
    order_item_id VARCHAR(50),
    order_id VARCHAR(50),
    product_id VARCHAR(50),
    product_name VARCHAR(255),
    quantity INTEGER,
    unit_price DECIMAL(15,2),
    discount_amount DECIMAL(15,2),
    subtotal DECIMAL(15,2),
    created_at TIMESTAMP,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Customers
CREATE TABLE staging.customers (
    customer_id VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10),
    registration_date TIMESTAMP,
    customer_segment VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Products
CREATE TABLE staging.products (
    product_id VARCHAR(50),
    product_name VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    unit_price DECIMAL(15,2),
    cost_price DECIMAL(15,2),
    stock_quantity INTEGER,
    supplier_id VARCHAR(50),
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Payments
CREATE TABLE staging.payments (
    payment_id VARCHAR(50),
    order_id VARCHAR(50),
    payment_date TIMESTAMP,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50),
    amount DECIMAL(15,2),
    transaction_id VARCHAR(100),
    gateway_response TEXT,
    created_at TIMESTAMP,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: User Events (Clickstream)
CREATE TABLE staging.user_events (
    event_id VARCHAR(50),
    user_id VARCHAR(50),
    session_id VARCHAR(50),
    event_type VARCHAR(50),
    event_timestamp TIMESTAMP,
    page_url TEXT,
    referrer_url TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(50),
    ip_address VARCHAR(50),
    event_properties JSONB,
    source_system VARCHAR(50),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on staging tables for faster lookup
CREATE INDEX idx_staging_orders_customer_id ON staging.orders(customer_id);
CREATE INDEX idx_staging_orders_order_date ON staging.orders(order_date);
CREATE INDEX idx_staging_order_items_order_id ON staging.order_items(order_id);
CREATE INDEX idx_staging_order_items_product_id ON staging.order_items(product_id);
CREATE INDEX idx_staging_customers_email ON staging.customers(email);
CREATE INDEX idx_staging_products_category ON staging.products(category);
CREATE INDEX idx_staging_payments_order_id ON staging.payments(order_id);
CREATE INDEX idx_staging_user_events_user_id ON staging.user_events(user_id);
CREATE INDEX idx_staging_user_events_timestamp ON staging.user_events(event_timestamp);

-- Add comments for documentation
COMMENT ON SCHEMA staging IS 'Staging layer for raw data ingestion from source systems';
COMMENT ON TABLE staging.orders IS 'Raw order data from transactional database';
COMMENT ON TABLE staging.order_items IS 'Raw order line items';
COMMENT ON TABLE staging.customers IS 'Raw customer master data';
COMMENT ON TABLE staging.products IS 'Raw product catalog data';
COMMENT ON TABLE staging.payments IS 'Raw payment transaction data';
COMMENT ON TABLE staging.user_events IS 'Raw clickstream and user behavior events';

