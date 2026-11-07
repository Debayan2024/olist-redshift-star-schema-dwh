-- ============================================
-- Core Layer: Cleaned and Validated Data
-- Purpose: Cleansed, validated, and business-logic-applied data
-- ============================================

-- Drop existing core schema if exists
DROP SCHEMA IF EXISTS core CASCADE;
CREATE SCHEMA core;

-- Core: Orders
CREATE TABLE core.orders (
    order_key SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    order_date TIMESTAMP NOT NULL,
    order_status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(50),
    shipping_address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(20),
    is_first_order BOOLEAN,
    order_processing_time_hours DECIMAL(10,2),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    CONSTRAINT check_total_amount CHECK (total_amount >= 0)
);

-- Core: Order Items
CREATE TABLE core.order_items (
    order_item_key SERIAL PRIMARY KEY,
    order_item_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    discount_amount DECIMAL(15,2) DEFAULT 0,
    subtotal DECIMAL(15,2) NOT NULL,
    revenue DECIMAL(15,2) GENERATED ALWAYS AS (subtotal - discount_amount) STORED,
    created_at TIMESTAMP NOT NULL,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_quantity CHECK (quantity > 0),
    CONSTRAINT check_unit_price CHECK (unit_price >= 0),
    CONSTRAINT check_discount CHECK (discount_amount >= 0)
);

-- Core: Customers
CREATE TABLE core.customers (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255),
    date_of_birth DATE,
    age INTEGER,
    gender VARCHAR(10),
    registration_date TIMESTAMP NOT NULL,
    customer_segment VARCHAR(50),
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(15,2) DEFAULT 0,
    last_order_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(customer_id, valid_from)
);

-- Core: Products
CREATE TABLE core.products (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    unit_price DECIMAL(15,2) NOT NULL,
    cost_price DECIMAL(15,2),
    margin_percent DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN cost_price > 0 THEN ((unit_price - cost_price) / cost_price * 100)
            ELSE 0
        END
    ) STORED,
    stock_quantity INTEGER DEFAULT 0,
    supplier_id VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(product_id, valid_from),
    CONSTRAINT check_prices CHECK (unit_price >= 0 AND cost_price >= 0)
);

-- Core: Payments
CREATE TABLE core.payments (
    payment_key SERIAL PRIMARY KEY,
    payment_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    transaction_id VARCHAR(100),
    is_successful BOOLEAN,
    processing_time_seconds INTEGER,
    created_at TIMESTAMP NOT NULL,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_amount CHECK (amount >= 0)
);

-- Core: User Events
CREATE TABLE core.user_events (
    event_key SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50),
    session_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    page_url TEXT,
    referrer_url TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(50),
    event_date DATE GENERATED ALWAYS AS (DATE(event_timestamp)) STORED,
    event_hour INTEGER GENERATED ALWAYS AS (EXTRACT(HOUR FROM event_timestamp)) STORED,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_core_orders_customer_id ON core.orders(customer_id);
CREATE INDEX idx_core_orders_order_date ON core.orders(order_date);
CREATE INDEX idx_core_orders_status ON core.orders(order_status);
CREATE INDEX idx_core_orders_is_current ON core.orders(is_current);

CREATE INDEX idx_core_order_items_order_id ON core.order_items(order_id);
CREATE INDEX idx_core_order_items_product_id ON core.order_items(product_id);

CREATE INDEX idx_core_customers_email ON core.customers(email);
CREATE INDEX idx_core_customers_segment ON core.customers(customer_segment);
CREATE INDEX idx_core_customers_is_current ON core.customers(is_current);

CREATE INDEX idx_core_products_category ON core.products(category);
CREATE INDEX idx_core_products_is_active ON core.products(is_active);
CREATE INDEX idx_core_products_is_current ON core.products(is_current);

CREATE INDEX idx_core_payments_order_id ON core.payments(order_id);
CREATE INDEX idx_core_payments_status ON core.payments(payment_status);
CREATE INDEX idx_core_payments_date ON core.payments(payment_date);

CREATE INDEX idx_core_events_user_id ON core.user_events(user_id);
CREATE INDEX idx_core_events_session_id ON core.user_events(session_id);
CREATE INDEX idx_core_events_timestamp ON core.user_events(event_timestamp);
CREATE INDEX idx_core_events_type ON core.user_events(event_type);
CREATE INDEX idx_core_events_date ON core.user_events(event_date);

-- Add comments
COMMENT ON SCHEMA core IS 'Core layer with cleaned and validated business data';
COMMENT ON TABLE core.orders IS 'Cleaned order transactions with business logic applied';
COMMENT ON TABLE core.customers IS 'Customer master data with SCD Type 2 tracking';
COMMENT ON TABLE core.products IS 'Product catalog with SCD Type 2 tracking';
COMMENT ON COLUMN core.customers.valid_from IS 'Start date of this version of the customer record';
COMMENT ON COLUMN core.customers.valid_to IS 'End date of this version (NULL for current version)';
COMMENT ON COLUMN core.customers.is_current IS 'Flag indicating if this is the current version';

